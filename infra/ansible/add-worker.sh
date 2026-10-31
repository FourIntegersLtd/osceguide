#!/usr/bin/env bash
# Adds LiveKit worker nodes, end to end: rents the Hetzner servers, joins them to
# K3s with Ansible, scales the production workers to one per node and raises
# Railway's LIVEKIT_SELF_HOSTED_SEATS to match. Production changes when it finishes.
#
#   infra/ansible/add-worker.sh [how-many]   # default 1; 0 only finishes an earlier failed run
source "$(dirname "$0")/lib.sh"

how_many="${1:-1}"
[[ "$how_many" =~ ^[0-9]+$ ]] || die "Usage: add-worker.sh [how-many]"
preflight

# A server created but not yet in the inventory is useless; delete it on failure.
unrecorded=""
on_exit() {
  local status=$?
  (( status == 0 )) && return
  if [[ -n "$unrecorded" ]]; then
    printf 'Deleting %s, which never made it into the inventory.\n' "$unrecorded" >&2
    hcloud server delete "$unrecorded" >/dev/null || printf 'Delete it by hand: hcloud server delete %s\n' "$unrecorded" >&2
  fi
  printf 'Fix the cause, then run add-worker.sh 0 to finish joining and set capacity.\n' >&2
}
trap on_exit EXIT

# Finish hosts an earlier run left in the inventory but never joined.
while read -r host name; do
  is_labelled "$name" || join_node "$host" "$name"
done < <(inventory_workers)

(( how_many > 0 )) && read_template
for _ in $(seq "$how_many"); do
  number="$(next_server_number)"
  name="$SERVER_PREFIX$number"
  host="livekit-worker-$number"

  create_server "$name"
  unrecorded="$name"
  details="$(hcloud server describe "$name" -o json)"
  public_ip="$(jq -r .public_net.ipv4.ip <<<"$details")"
  private_ip="$(jq -r '.private_net[0].ip' <<<"$details")"
  wait_for_ssh "$public_ip"
  iface="$(private_interface "$public_ip" "$private_ip")"
  add_inventory_host "$host" "$public_ip" "$private_ip" "$iface" "$name"
  unrecorded=""

  join_node "$host" "$name"
done

nodes="$(labelled_node_count)"
scale_workers "$nodes"
set_seats "$nodes"   # after the pods are up, so nobody is admitted to a pod that is not there

log "Done: $nodes worker nodes. Commit infra/ansible/inventory/hosts.yml."
kc get nodes -L osceguide.io/livekit-worker
