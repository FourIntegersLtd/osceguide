# K3s worker nodes

Adds and removes LiveKit worker nodes on the Hetzner K3s cluster, end to end, from
this Mac. Production capacity changes as soon as a script finishes.

The control plane is `116.203.41.207` (private `10.0.0.3`). `kubectl get nodes` on it
lists the workers; `osceguide-livekit-agent-prod-01` is the template new ones copy.

## One-time setup

```sh
brew install hcloud
# Hetzner console > the project > Security > API tokens > Generate (Read & Write)
security add-generic-password -U -a "$USER" -s osceguide-hcloud-token -w
# The Ansible Vault password that encrypts the K3s join token
security add-generic-password -U -a "$USER" -s osceguide-ansible-vault -w
railway login
```

Each `security` line prompts for the value and stores it in the macOS keychain;
nothing is written to the repo. `ssh osce-k3s-control` must work (root, `~/.ssh/osce_prod`).

## Add workers

```sh
infra/ansible/add-worker.sh        # one
infra/ansible/add-worker.sh 2      # two
```

For each new worker it:

1. Rents a Hetzner server named `osceguide-livekit-agent-prod-NN` (next free number),
   copying prod-01's type, location, image, private network and firewalls, with the
   `osce_prod` SSH key. Set `IMAGE=...` if prod-01's image has no name, and
   `LOCATION=fsn1` (or `hel1`) when Hetzner has no capacity in nbg1
   (`resource_unavailable`); all three share the private network's zone.
2. Waits for SSH, finds its private IP and interface, adds it to `inventory/hosts.yml`.
3. Runs `playbooks/provision-worker.yml`: installs the K3s agent, joins the control
   plane over the private network and labels the node `osceguide.io/livekit-worker=true`.

Then, once:

4. Scales the production workers to one pod per labelled node and waits for them.
5. Sets `LIVEKIT_SELF_HOSTED_SEATS` = nodes × the per-pod cap on Railway production
   `platform-api` and `platform-worker` and waits for both to redeploy.

If it stops part way, a server not yet in the inventory is deleted. Fix the cause and
run `infra/ansible/add-worker.sh 0`: it joins any inventory host not yet in the
cluster, then sets the replicas and seats.

Commit `inventory/hosts.yml` afterwards. Promotes keep the replica count: the
production rollout sets it from the labelled nodes (`assessment/k8s/README.md`).

## Remove a worker

```sh
infra/ansible/remove-worker.sh 3   # osceguide-livekit-agent-prod-03
```

It asks you to type the number, then lowers the Railway seats and waits for the api to
redeploy, drains the node (live consultations finish; it waits up to 20 minutes),
scales production down, deletes the Hetzner server and the K3s node, and removes it
from the inventory. If the drain fails it uncordons the node and restores the seats;
if it stops after that, rerun it. It refuses to remove prod-01 (the template), an
unlabelled node or the last worker.

## By hand

`ansible-playbook playbooks/provision-worker.yml --limit <host>` joins a server
already in the inventory. It is idempotent: rerunning it on a configured worker
changes nothing.

## Secrets

`group_vars/livekit_workers_vault.yml` holds the K3s join token, encrypted with
Ansible Vault; only the encrypted form is committed. `vault-pass.sh` reads the vault
password from the keychain. Never commit a decrypted copy or a password file.
