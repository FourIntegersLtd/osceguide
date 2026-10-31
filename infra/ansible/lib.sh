# Shared by add-worker.sh and remove-worker.sh. Sourced, not run.
set -euo pipefail

ANSIBLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$ANSIBLE_DIR/../.." && pwd)"
INVENTORY="$ANSIBLE_DIR/inventory/hosts.yml"
CONTROL_SSH="osce-k3s-control"                       # ~/.ssh/config entry, user root
SSH_KEY="$HOME/.ssh/osce_prod"
SERVER_PREFIX="osceguide-livekit-agent-prod-"        # Hetzner server name = K3s node name
TEMPLATE_SERVER="${TEMPLATE_SERVER:-${SERVER_PREFIX}01}"  # new servers copy its type, location, image, network, firewalls
# The production rollout counts nodes with this label to set replicas
# (assessment/scripts/k8s_rollout_on_control_plane.sh); keep the two in step.
WORKER_LABEL="osceguide.io/livekit-worker=true"
NAMESPACE="assessment-platform"                      # production workers
DRAIN_TIMEOUT="20m"                                  # above the workers' 15-minute drain (terminationGracePeriodSeconds 900)
RAILWAY_PROJECT="c2afb568-4fe0-4172-8052-83af4dcd1453"  # "OSCE Guide server backend"
RAILWAY_SERVICES=(platform-api platform-worker)      # both read LIVEKIT_SELF_HOSTED_SEATS
HOST_INDENT="        "                               # inventory/hosts.yml: a host under livekit_workers.hosts
VAR_INDENT="          "                              # and its variables

export ANSIBLE_PRIVATE_KEY_FILE="$SSH_KEY"
cd "$ANSIBLE_DIR"

log() { printf '\n==> %s\n' "$*"; }
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }

kc() { ssh -n -o BatchMode=yes "$CONTROL_SSH" kubectl "$@"; }          # kubectl on the control plane
on_server() { ssh -n -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=5 "root@$1" "${@:2}"; }
railway_prod() { (cd "$REPO_ROOT/api" && railway "$@" -p "$RAILWAY_PROJECT" -e production); }

seats_on() { railway_prod variables -s "$1" --kv | sed -n 's/^LIVEKIT_SELF_HOSTED_SEATS=//p'; }

preflight() {
  local tool service
  for tool in hcloud jq ansible-playbook railway ssh security; do
    command -v "$tool" >/dev/null || die "$tool is not installed (README, 'One-time setup')."
  done
  HCLOUD_TOKEN="$(security find-generic-password -a "$USER" -s osceguide-hcloud-token -w 2>/dev/null)" \
    || die "No Hetzner API token in the keychain (README, 'One-time setup')."
  export HCLOUD_TOKEN
  ./vault-pass.sh >/dev/null 2>&1 || die "No Ansible vault password in the keychain (README, 'One-time setup')."
  kc get nodes >/dev/null || die "Cannot reach the control plane as $CONTROL_SSH."
  for service in "${RAILWAY_SERVICES[@]}"; do
    [[ -n "$(seats_on "$service")" ]] || die "Railway production $service has no LIVEKIT_SELF_HOSTED_SEATS (logged in? railway login)."
  done
}

labelled_node_count() { kc get nodes -l "$WORKER_LABEL" --no-headers | wc -l | tr -d ' '; }
is_labelled() { kc get nodes -l "$WORKER_LABEL" -o name | grep -qx "node/$1"; }   # kubectl refuses a name with -l

# One production pod of each worker per labelled node; the production rollout
# applies the same count, so a later promote keeps it.
scale_workers() {
  local deployment
  log "Scaling production workers to $1"
  kc -n "$NAMESPACE" scale deployment/assessment-worker deployment/assistant-worker --replicas="$1"
  for deployment in assessment-worker assistant-worker; do
    kc -n "$NAMESPACE" rollout status "deployment/$deployment" --timeout=600s
  done
}

latest_deploy() { railway_prod deployment list -s "$1" --json | jq -r '.[0] | "\(.id) \(.status)"'; }

# Seats the api may hand to our own workers: one pod per node, each capped at
# LIVEKIT_ASSESSMENT_MAX_CONCURRENT_JOBS (assessment/k8s/README.md, "Capacity").
# The api reads it at startup, so this waits for both services to redeploy.
set_seats() {
  local nodes="$1" cap seats i service id status
  local before=()
  cap="$(kc -n "$NAMESPACE" get configmap assessment-worker-config \
    -o jsonpath='{.data.LIVEKIT_ASSESSMENT_MAX_CONCURRENT_JOBS}')"
  [[ "$cap" =~ ^[0-9]+$ ]] || die "Could not read the per-pod cap from the cluster."
  seats=$((nodes * cap))
  for i in "${!RAILWAY_SERVICES[@]}"; do
    service="${RAILWAY_SERVICES[$i]}"
    before[$i]=""
    [[ "$(seats_on "$service")" == "$seats" ]] && continue   # unchanged: Railway would not redeploy
    before[$i]="$(latest_deploy "$service" | cut -d' ' -f1)"
    log "Railway $service (production): LIVEKIT_SELF_HOSTED_SEATS=$seats"
    railway_prod variables -s "$service" --set "LIVEKIT_SELF_HOSTED_SEATS=$seats" >/dev/null
  done
  for i in "${!RAILWAY_SERVICES[@]}"; do
    [[ -n "${before[$i]}" ]] || continue
    service="${RAILWAY_SERVICES[$i]}"
    log "Waiting for $service to redeploy"
    for attempt in $(seq 90); do
      read -r id status <<<"$(latest_deploy "$service")"
      if [[ "$id" != "${before[$i]}" ]]; then
        case "$status" in
          SUCCESS) break ;;
          FAILED|CRASHED|REMOVED) die "$service redeploy $id ended $status." ;;
        esac
      fi
      [[ "$attempt" == 90 ]] && die "$service did not redeploy within 15 minutes."
      sleep 10
    done
  done
}

# --- Hetzner --------------------------------------------------------------------

# Sets server_type, location, image, network, firewall_args and ssh_key_id from
# TEMPLATE_SERVER, so new servers match it.
read_template() {
  local template fingerprint firewall
  template="$(hcloud server describe "$TEMPLATE_SERVER" -o json)"
  server_type="$(jq -r .server_type.name <<<"$template")"
  # LOCATION= overrides it, e.g. when Hetzner has no capacity there; it must be in the network's zone.
  location="${LOCATION:-$(jq -r '.location.name // .datacenter.location.name' <<<"$template")}"
  image="${IMAGE:-$(jq -r '.image.name // empty' <<<"$template")}"
  [[ -n "$image" ]] || die "$TEMPLATE_SERVER was built from a snapshot; set IMAGE (e.g. IMAGE=ubuntu-26.04)."
  network="$(jq -r '.private_net[0].network' <<<"$template")"
  firewall_args=()
  while read -r firewall; do
    [[ -n "$firewall" ]] && firewall_args+=(--firewall "$firewall")
  done < <(jq -r '.public_net.firewalls[]?.id' <<<"$template")
  fingerprint="$(ssh-keygen -E md5 -lf "$SSH_KEY.pub" | awk '{print $2}' | sed 's/^MD5://')"
  ssh_key_id="$(hcloud ssh-key list -o json | jq -r --arg fp "$fingerprint" '.[] | select(.fingerprint == $fp) | .id')"
  [[ -n "$ssh_key_id" ]] || die "$SSH_KEY.pub is not an SSH key in the Hetzner project."
}

next_server_number() {
  local last
  last="$(hcloud server list -o json | jq -r --arg p "$SERVER_PREFIX" \
    '[.[] | .name | select(startswith($p)) | ltrimstr($p) | tonumber] | max // 0')"
  printf '%02d' $((10#$last + 1))
}

create_server() {
  log "Creating $1 ($server_type, $location, $image)"
  hcloud server create --name "$1" --type "$server_type" --location "$location" \
    --image "$image" --ssh-key "$ssh_key_id" --network "$network" ${firewall_args[@]+"${firewall_args[@]}"} \
    --label role=livekit-worker >/dev/null
}

wait_for_ssh() {
  local attempt
  log "Waiting for SSH on $1"
  ssh-keygen -R "$1" >/dev/null 2>&1 || true   # Hetzner reuses IPs
  for attempt in $(seq 60); do
    ssh -n -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o BatchMode=yes -o ConnectTimeout=5 \
      "root@$1" 'cloud-init status --wait >/dev/null 2>&1 || true' && return 0
    sleep 5
  done
  die "$1 never accepted SSH."
}

# The interface carrying the private IP (it can take a moment to come up).
private_interface() {
  local attempt iface
  for attempt in $(seq 30); do
    iface="$(on_server "$1" "ip -o -4 addr show | grep -F ' $2/' | awk '{print \$2}'")"
    [[ -n "$iface" ]] && { echo "$iface"; return 0; }
    sleep 2
  done
  die "$1 has no interface with $2."
}

# --- Inventory ------------------------------------------------------------------

# "host node-name" for every worker in the inventory.
inventory_workers() {
  ansible-inventory --list | jq -r \
    '._meta.hostvars | to_entries[] | select(.value.k3s_node_name) | "\(.key) \(.value.k3s_node_name)"'
}

add_inventory_host() {   # host public-ip private-ip interface node-name
  printf '\n%s%s:\n%sansible_host: %s\n%sansible_user: root\n%sprivate_ip: %s\n%sprivate_interface: %s\n%sk3s_node_name: %s\n' \
    "$HOST_INDENT" "$1" "$VAR_INDENT" "$2" "$VAR_INDENT" "$VAR_INDENT" "$3" "$VAR_INDENT" "$4" "$VAR_INDENT" "$5" >> "$INVENTORY"
}

remove_inventory_host() {
  local tmp
  tmp="$(mktemp)"
  awk -v h="$HOST_INDENT$1:" -v v="$VAR_INDENT" '
    $0 == h { skip = 1; blanks = ""; next }
    skip && (index($0, v) == 1 || $0 == "") { next }
    { skip = 0 }
    $0 == "" { blanks = blanks "\n"; next }     # held, so the blank line before a removed host goes too
    { printf "%s", blanks; blanks = ""; print }
  ' "$INVENTORY" > "$tmp" && mv "$tmp" "$INVENTORY"
}

join_node() {   # host node-name
  log "Joining $2 to K3s"
  ansible-playbook playbooks/provision-worker.yml --limit "$1" </dev/null
  kc wait --for=condition=Ready "node/$2" --timeout=180s
}
