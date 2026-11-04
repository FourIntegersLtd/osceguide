// Exam-day burst: every VU is one candidate at the same buzzer. See README.md.
//
//   k6 run -e BASE_URL=... -e WORKER_SECRET=... loadtest/exam_burst.js   (a k6 built with xk6-sse)
//
// Flow per VU: login -> /me/dashboard -> /stations -> POST /attempts -> (voice VUs only) voice-token
// -> wait for the shared buzzer -> worker bootstrap + transcript chunk + final transcript
// -> wait on /me/events (SSE, no polling) for the "attempt" event that carries the mark.
//
// LiveKit allows only 50 concurrent voice sessions today: only VUs 1..VOICE_VUS ask for a room, the
// rest drive the worker routes directly, so the api, DB and marking still see VUS candidates.
import http from 'k6/http';
import sse from 'k6/x/sse';
import { check, fail, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const BASE_URL = (__ENV.BASE_URL || 'http://localhost:8002').replace(/\/$/, '');
const PASSWORD = __ENV.LOAD_PASSWORD || 'Load-test-password-1!';
const EXAM_CODE = __ENV.EXAM_CODE || 'sca';
const WORKER_SECRET = __ENV.WORKER_SECRET || '';
const WORKER_HEADER = __ENV.WORKER_SECRET_HEADER || 'X-Worker-Secret';
const VUS = parseInt(__ENV.VUS || '50', 10);
const VOICE_VUS = Math.min(parseInt(__ENV.VOICE_VUS || '50', 10), VUS); // never more rooms than VOICE_VUS
const BUZZER_DELAY_S = parseInt(__ENV.BUZZER_DELAY_S || '30', 10); // from setup() until everyone submits
const WAIT_MARKING = (__ENV.WAIT_MARKING || 'true') !== 'false'; // false: api-only run, no marking worker
const MARKING_TIMEOUT_S = parseInt(__ENV.MARKING_TIMEOUT_S || '600', 10);

export const options = {
  scenarios: {
    go: { executor: 'per-vu-iterations', vus: VUS, iterations: 1, maxDuration: __ENV.MAX_DURATION || '25m' },
  },
  thresholds: {
    'http_req_duration{phase:start}': ['p(95)<500'],
    'http_req_duration{phase:submit}': ['p(95)<500'],
    http_req_failed: ['rate<0.001'],
    'checks{kind:no429}': ['rate==1'],
    'checks{kind:flow}': ['rate==1'],
    marking_latency: WAIT_MARKING ? ['p(95)<300000'] : [],
  },
};

const markingLatency = new Trend('marking_latency', true);
const markingMissed = new Counter('marking_missed');
const voiceRooms = new Counter('voice_rooms_requested');

const json = { 'Content-Type': 'application/json' };

function post(path, body, headers, phase) {
  return http.post(`${BASE_URL}${path}`, JSON.stringify(body), { headers: { ...json, ...headers }, tags: { phase } });
}
function get(path, headers, phase) {
  return http.get(`${BASE_URL}${path}`, { headers, tags: { phase } });
}
function ok(res, status, name) {
  check(res, { [`${name} not 429`]: (r) => r.status !== 429 }, { kind: 'no429' });
  return check(res, { [`${name} ${status}`]: (r) => r.status === status }, { kind: 'flow' });
}

export function setup() {
  return { buzzerAt: Date.now() + BUZZER_DELAY_S * 1000 };
}

export default function (data) {
  const vu = __VU; // 1-based; the seed makes trainee1..traineeN@load-test.example.com
  const email = `trainee${vu}@load-test.example.com`;

  const login = post('/api/v1/auth/login', { email, password: PASSWORD }, {}, 'login');
  if (!ok(login, 200, 'login')) fail(`login failed for ${email}: ${login.status}`);
  const auth = { Authorization: `Bearer ${login.json('access_token')}` };

  ok(get('/api/v1/me/dashboard', auth, 'dashboard'), 200, 'dashboard');

  const library = get(`/api/v1/stations?exam_code=${EXAM_CODE}&limit=20`, auth, 'stations');
  if (!ok(library, 200, 'stations')) fail('stations failed');
  const items = library.json('items') || [];
  if (items.length === 0) fail('library empty: run scripts/seed_loadtest.py');
  const station = items[(vu - 1) % items.length];

  const start = post(
    '/api/v1/attempts',
    { kind: 'practice', exam_code: EXAM_CODE, station_version_id: station.version_id },
    auth,
    'start',
  );
  if (!ok(start, 201, 'start attempt')) fail(`start failed: ${start.status} ${start.body}`);
  const attemptId = start.json('id');

  if (vu <= VOICE_VUS) {
    voiceRooms.add(1);
    const token = post(`/api/v1/attempts/${attemptId}/voice-token`, {}, auth, 'voice');
    // 200 is a room, 202 a place in the queue; both are fine, a 429 or 5xx is not.
    check(token, { 'voice token 200/202': (r) => r.status === 200 || r.status === 202 }, { kind: 'flow' });
    check(token, { 'voice token not 429': (r) => r.status !== 429 }, { kind: 'no429' });
  }

  // Everyone submits at the same instant.
  const wait = (data.buzzerAt - Date.now()) / 1000;
  if (wait > 0) sleep(wait);

  const worker = { [WORKER_HEADER]: WORKER_SECRET };
  const submit = () => {
    // The worker's bootstrap is what moves created -> running; the transcript then closes it.
    ok(get(`/api/worker/attempts/${attemptId}`, worker, 'bootstrap'), 200, 'worker bootstrap');
    const now = new Date().toISOString();
    const messages = [
      { role: 'assistant', message: 'Hello doctor, thank you for seeing me.', timestamp: now, message_id: `${attemptId}-1`, seq: 0 },
      { role: 'user', message: 'Hello, I am a doctor. How can I help today?', timestamp: now, message_id: `${attemptId}-2`, seq: 1 },
    ];
    ok(post(`/api/worker/attempts/${attemptId}/transcript-chunks`, { attempt_id: attemptId, message: messages[0] }, worker, 'chunk'), 202, 'transcript chunk');
    return post(
      `/api/worker/attempts/${attemptId}/transcript`,
      { attempt_id: attemptId, transcript: { attempt_id: attemptId, messages, complete: true, runtime_label: 'loadtest' } },
      worker,
      'submit',
    );
  };

  if (!WAIT_MARKING) {
    ok(submit(), 202, 'worker transcript');
    return;
  }

  // Open the event stream first so the mark cannot arrive before anyone is listening, then submit and
  // wait for the "attempt" event. The event carries only an id; re-read the attempt once per event.
  let submittedAt = 0;
  sse.open(`${BASE_URL}/api/v1/me/events`, { headers: { ...auth, Accept: 'text/event-stream' } }, (client) => {
    client.on('open', () => {
      submittedAt = Date.now();
      ok(submit(), 202, 'worker transcript');
      setTimeout(() => {
        markingMissed.add(1);
        client.close();
      }, MARKING_TIMEOUT_S * 1000);
    });
    client.on('event', (event) => {
      if (event.name !== 'attempt' || !String(event.data).includes(attemptId)) return;
      const status = get(`/api/v1/attempts/${attemptId}`, auth, 'read').json('status');
      if (status === 'evaluated' || status === 'failed') {
        markingLatency.add(Date.now() - submittedAt);
        check(status, { 'attempt evaluated': (s) => s === 'evaluated' }, { kind: 'flow' });
        client.close();
      }
    });
    client.on('error', (e) => {
      check(null, { 'event stream ok': () => false }, { kind: 'flow' });
      console.error(`sse error: ${e.error ? e.error() : e}`);
    });
  });
}
