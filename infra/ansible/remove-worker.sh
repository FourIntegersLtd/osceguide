#!/usr/bin/env bash
# Removes one LiveKit worker node, end to end: lowers Railway's seats first (and
# waits for the api to pick them up), drains the node so live consultations
# finish, scales the production workers down, deletes the Hetzner server and the
# K3s node, and drops it from the inventory. Rerun it if it stops part way.
#
#   infra/ansible/remove-worker.sh <number>     # e.g. 3 for osceguide-livekit-agent-prod-03
source "$(dirname "$0")/lib.sh"

[[ "${1:-}" =~ ^[0-9]+$ ]] || die "Usage: remove-worker.sh <number>"
number="$(printf '%02d' $((10#$1)))"
name="$SERVER_PREFIX$number"
host="livekit-worker-$number"
[[ "$name" != "$TEMPLATE_SERVER" ]] || die "$name is the template new servers are copied from; keep it."
preflight

confirm() {
  read -r -p "$1 Type $((10#$number)) to confirm: " answer
  [[ "$answer" =~ ^0*$((10#$number))$ ]] || die "Not confirmed."
}

if kc get node "$name" >/dev/null 2>&1; then
  is_labelled "$name" || die "$name is not labelled as a worker; it holds no production pod. Remove it by hand."
  nodes="$(labelled_node_count)"
  (( nodes > 1 )) || die "$name is the last worker node."
  remaining=$((nodes - 1))
  confirm "Delete $name and its Hetzner server, leaving $remaining worker node(s)?"

  # If the drain fails, put the node and the seats back as they were.
  restore() {
    (( $? == 0 )) && return
    printf 'Stopped part way: uncordoning %s and restoring the seats.\n' "$name" >&2
    kc uncordon "$name" || true
    set_seats "$nodes" || true
  }
  trap restore EXIT
  set_seats "$remaining"   # first, so the api stops admitting to the seats being removed
  log "Draining $name (live consultations finish first, up to $DRAIN_TIMEOUT)"
  kc cordon "$name"
  kc drain "$name" --ignore-daemonsets --delete-emptydir-data --timeout="$DRAIN_TIMEOUT"
  scale_workers "$remaining"   # drops the pods the drain left Pending
  trap - EXIT
else
  log "$name is no longer a K3s node; finishing the clean-up"
  confirm "Delete what is left of $name?"
fi

# The server goes before the node object, so its k3s-agent cannot re-register it.
details="$(hcloud server describe "$name" -o json 2>/dev/null || true)"
if [[ -n "$details" ]]; then
  log "Deleting Hetzner server $name"
  hcloud server delete "$name" >/dev/null
  ssh-keygen -R "$(jq -r .public_net.ipv4.ip <<<"$details")" >/dev/null 2>&1 || true
fi
kc delete node "$name" --ignore-not-found
remove_inventory_host "$host"

log "Done. Commit infra/ansible/inventory/hosts.yml."
kc get nodes -L osceguide.io/livekit-worker
