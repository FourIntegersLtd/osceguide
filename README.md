# OSCE Guide

A platform for practising and running medical exams. Doctors practise stations
with an AI patient and get marked feedback. Institutions and employers run real
exams on it and review the results.

Everything lives in this one repository, in three folders. Each one deploys on
its own when its folder changes.

| Folder | What it is | Built with |
|---|---|---|
| `api/` | The backend. Accounts, stations, attempts, marking, exams, billing | Python, FastAPI, SQLAlchemy, Postgres |
| `web/` | The website and app people use | Next.js, TypeScript, Tailwind |
| `assessment/` | The marking engine, and the voice workers that play the patient and the tutor | Python, LiveKit |

The api uses the marking engine directly from `assessment/packages/osce_assessment`,
so a change to the engine and the api code that needs it go in one commit.

## Run it on your machine

```bash
# api, on http://localhost:8002
cd api
docker compose up -d && poetry run alembic upgrade head
poetry run python scripts/seed_platform.py   # a new database has no exams until this runs
make start

# web, on http://localhost:3100
cd web
npm install && npm run dev

# assessment (tests only; the workers need LiveKit keys, see assessment/README.md)
cd assessment
poetry install && poetry run pytest -q
```

## Check your work before you push

```bash
cd api && make ci
cd web && npm run ci
cd assessment && poetry run pytest -q
```

Each of these also runs "guard" tests. A guard is a test that reads the code
itself and fails when a house rule is broken, for example a screen reaching
into a folder it should not, or a function with no explanation. The failure
message says what to change.

## Where to start reading

1. `AGENTS.md` here: the map of the repository, who owns which area, and the rules everyone follows.
2. `api/docs/README.md`: how the backend is put together, in reading order.
3. `web/AGENTS.md` and `web/docs/DESIGN.md`: how the app is layered and how it should look.
4. `assessment/AGENTS.md`: what the engine and the workers may and may not know about.
5. `web/docs/BACKLOG.md`: the one list of work that is still open.

## How changes reach people

A push to `main` goes to staging for the folders it touched. Production changes
only when someone runs the matching "Promote ... to production" workflow. The
table at the top of `AGENTS.md` has the detail for each folder.
