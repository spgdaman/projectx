"""
One-shot deployment script — runs the full server bootstrap and k8s deploy
via paramiko SSH. Run with the project venv:
  env\Scripts\python.exe scripts\deploy_remote.py
"""

import os, sys, time, stat, io
import paramiko

# ── Credentials & config ──────────────────────────────────────────────────────
HOST              = "13.140.133.70"
USER              = "root"
PASSWORD          = "W3w3n!h@g@"
LETSENCRYPT_EMAIL = "simonwaigi@outlook.com"
SECRET_KEY        = r"6&t@o9&2!%6+!m5(3zid_0^nf7pidh74&(s)7a4(i@(nbk3+5a"
POSTGRES_PASSWORD = "W3w3n!h@g@"
DATABASE_URL      = f"postgres://bargainhunters:{POSTGRES_PASSWORD}@postgres-service:5432/bargainhunters"
REDIS_URL         = "redis://redis-service:6379/1"
BROKER_URL        = "redis://redis-service:6379/1"
RESULT_BACKEND    = "redis://redis-service:6379/2"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Helpers ───────────────────────────────────────────────────────────────────

def run(client, cmd, timeout=600, allow_fail=False):
    """Execute a command, stream stdout/stderr, raise on non-zero exit."""
    print(f"\n\033[36m$ {cmd.strip()[:120]}\033[0m")
    chan = client.get_transport().open_session()
    chan.set_combine_stderr(False)
    chan.exec_command(cmd)

    buf_out, buf_err = b"", b""
    while True:
        if chan.recv_ready():
            chunk = chan.recv(4096)
            buf_out += chunk
            sys.stdout.write(chunk.decode(errors="replace"))
            sys.stdout.flush()
        if chan.recv_stderr_ready():
            chunk = chan.recv_stderr(4096)
            buf_err += chunk
            sys.stderr.write("\033[33m" + chunk.decode(errors="replace") + "\033[0m")
            sys.stderr.flush()
        if chan.exit_status_ready() and not chan.recv_ready() and not chan.recv_stderr_ready():
            break
        time.sleep(0.05)

    rc = chan.recv_exit_status()
    if rc != 0 and not allow_fail:
        raise RuntimeError(f"Command exited {rc}")
    return rc


def sftp_mkdir_p(sftp, remote_dir):
    """Recursively create remote directory."""
    dirs = []
    d = remote_dir
    while d not in ("/", ""):
        dirs.insert(0, d)
        d = os.path.dirname(d)
    for d in dirs:
        try:
            sftp.mkdir(d)
        except IOError:
            pass  # already exists


def upload_dir(sftp, local_dir, remote_dir):
    """Upload a local directory tree to the server."""
    sftp_mkdir_p(sftp, remote_dir)
    for entry in os.scandir(local_dir):
        rpath = f"{remote_dir}/{entry.name}"
        if entry.is_dir():
            upload_dir(sftp, entry.path, rpath)
        else:
            print(f"  upload {entry.path} → {rpath}")
            sftp.put(entry.path, rpath)


def write_remote(sftp, remote_path, content):
    """Write a string to a remote file."""
    sftp_mkdir_p(sftp, os.path.dirname(remote_path))
    f = sftp.open(remote_path, "w")
    f.write(content)
    f.close()


# ── Connect ───────────────────────────────────────────────────────────────────
print("\n\033[32m━━━ Connecting to server ━━━\033[0m")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
print(f"Connected to {HOST}")

# ── Step 1: System update (already done — skip) ───────────────────────────────
print("\n\033[32m━━━ Step 1: System update (already done, skipping) ━━━\033[0m")

# ── Step 2: Firewall ──────────────────────────────────────────────────────────
# Run all UFW rules in ONE compound command — allow SSH *before* enabling the
# firewall, then enable it. The connection will reset; we reconnect below.
print("\n\033[32m━━━ Step 2: Firewall ━━━\033[0m")
try:
    run(client, (
        "ufw allow ssh && "
        "ufw allow 80/tcp && "
        "ufw allow 443/tcp && "
        "ufw allow 6443/tcp && "
        "ufw default deny incoming && "
        "ufw default allow outgoing && "
        "ufw --force enable"
    ), allow_fail=True)
except Exception:
    pass  # connection drop after ufw enable is normal
print("Firewall configured. Reconnecting...")
time.sleep(5)
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, timeout=30)
print("Reconnected.")

# ── Step 3: Docker (already installed — skip) ────────────────────────────────
print("\n\033[32m━━━ Step 3: Docker (already installed, skipping) ━━━\033[0m")

# ── Step 4: Local registry (already running — skip) ──────────────────────────
print("\n\033[32m━━━ Step 4: Local registry (already running, skipping) ━━━\033[0m")

# ── Step 5: K3s (already installed — skip) ───────────────────────────────────
print("\n\033[32m━━━ Step 5: K3s (already installed, skipping) ━━━\033[0m")
run(client, "until kubectl get nodes 2>/dev/null | grep -q Ready; do sleep 3; echo 'waiting...'; done")

# ── Step 6: kubectl config ────────────────────────────────────────────────────
print("\n\033[32m━━━ Step 6: kubectl config ━━━\033[0m")
run(client, "mkdir -p $HOME/.kube && cp /etc/rancher/k3s/k3s.yaml $HOME/.kube/config && chmod 600 $HOME/.kube/config")
run(client, "grep -qxF 'export KUBECONFIG=$HOME/.kube/config' $HOME/.bashrc || echo 'export KUBECONFIG=$HOME/.kube/config' >> $HOME/.bashrc")

# ── Step 7: Helm (already installed — skip) ──────────────────────────────────
print("\n\033[32m━━━ Step 7: Helm (already installed, skipping) ━━━\033[0m")

# ── Step 8: Traefik via Helm ──────────────────────────────────────────────────
print("\n\033[32m━━━ Step 8: Traefik ━━━\033[0m")
run(client, "helm repo add traefik https://helm.traefik.io/traefik 2>&1 && helm repo update 2>&1 | tail -5")
run(client, "kubectl create namespace traefik --dry-run=client -o yaml | kubectl apply -f -")
# Traefik v3 (chart v40+) — entrypoints web/websecure are on by default.
# HTTP→HTTPS redirect is applied via a global middleware after install.
run(client, (
    "helm upgrade --install traefik traefik/traefik "
    "--namespace traefik "
    "--set service.type=LoadBalancer "
    "--set ports.web.exposedPort=80 "
    "--set ports.websecure.exposedPort=443 2>&1"
), timeout=120)

# Wait for Traefik pod to be ready
run(client, "kubectl rollout status deployment/traefik -n traefik --timeout=120s 2>&1", timeout=150)

# Apply a global HTTP→HTTPS redirect middleware (Traefik v3 CRD approach)
run(client, r"""kubectl apply -f - <<'EOF'
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: redirect-https
  namespace: bargainhunters
spec:
  redirectScheme:
    scheme: https
    permanent: true
EOF""", allow_fail=True)

# ── Step 9: cert-manager ──────────────────────────────────────────────────────
print("\n\033[32m━━━ Step 9: cert-manager ━━━\033[0m")
run(client, "kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml 2>&1", timeout=120)
run(client, "kubectl wait --for=condition=available --timeout=180s deployment/cert-manager -n cert-manager 2>&1", timeout=200)
run(client, "kubectl wait --for=condition=available --timeout=120s deployment/cert-manager-webhook -n cert-manager 2>&1", timeout=150)

# ── Step 10: ClusterIssuer ────────────────────────────────────────────────────
print("\n\033[32m━━━ Step 10: Let's Encrypt ClusterIssuer ━━━\033[0m")
issuer_yaml = f"""apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: {LETSENCRYPT_EMAIL}
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: traefik
"""
sftp = client.open_sftp()
write_remote(sftp, "/tmp/clusterissuer.yaml", issuer_yaml)
run(client, "kubectl apply -f /tmp/clusterissuer.yaml && rm /tmp/clusterissuer.yaml")

# ── Step 11: Upload k8s manifests ─────────────────────────────────────────────
print("\n\033[32m━━━ Step 11: Upload k8s manifests ━━━\033[0m")
sftp_mkdir_p(sftp, "/root/bargainhunters/k8s")
upload_dir(sftp, os.path.join(REPO_ROOT, "k8s"), "/root/bargainhunters/k8s")

# ── Step 12: Apply namespace ──────────────────────────────────────────────────
print("\n\033[32m━━━ Step 12: Namespace ━━━\033[0m")
run(client, "kubectl apply -f /root/bargainhunters/k8s/00-namespace.yaml")

# ── Step 13: Local registry config for K3s ───────────────────────────────────
print("\n\033[32m━━━ Step 13: K3s registry config ━━━\033[0m")
registries_yaml = """mirrors:
  "localhost:5000":
    endpoint:
      - "http://localhost:5000"
"""
run(client, "mkdir -p /etc/rancher/k3s")
write_remote(sftp, "/etc/rancher/k3s/registries.yaml", registries_yaml)
run(client, "systemctl restart k3s && sleep 5 && until kubectl get nodes 2>/dev/null | grep -q Ready; do sleep 3; done")

# ── Step 14: K8s secret ───────────────────────────────────────────────────────
print("\n\033[32m━━━ Step 14: K8s secret ━━━\033[0m")
secret_yaml = f"""apiVersion: v1
kind: Secret
metadata:
  name: bargainhunters-secret
  namespace: bargainhunters
type: Opaque
stringData:
  SECRET_KEY: "{SECRET_KEY}"
  DATABASE_URL: "{DATABASE_URL}"
  POSTGRES_PASSWORD: "{POSTGRES_PASSWORD}"
  REDIS_URL: "{REDIS_URL}"
  CELERY_BROKER_URL: "{BROKER_URL}"
  CELERY_RESULT_BACKEND: "{RESULT_BACKEND}"
  MPESA_CONSUMER_KEY: ""
  MPESA_CONSUMER_SECRET: ""
  MPESA_CALLBACK_URL: "https://www.bargainhunters.co.ke/api/v1/webhooks/mpesa/"
"""
write_remote(sftp, "/tmp/secret.yaml", secret_yaml)
run(client, "kubectl apply -f /tmp/secret.yaml && rm /tmp/secret.yaml")

# ── Step 15: Apply all manifests ──────────────────────────────────────────────
print("\n\033[32m━━━ Step 15: Apply K8s manifests ━━━\033[0m")
run(client, "kubectl apply -f /root/bargainhunters/k8s/01-configmap.yaml")
run(client, "kubectl apply -f /root/bargainhunters/k8s/03-postgres.yaml")
run(client, "kubectl apply -f /root/bargainhunters/k8s/04-redis.yaml")

# ── Step 16: Install GitHub runner ───────────────────────────────────────────
print("\n\033[32m━━━ Step 16: GitHub Actions runner ━━━\033[0m")

RUNNER_USER = "github-runner"
RUNNER_DIR  = f"/home/{RUNNER_USER}/actions-runner"

# Create user
run(client, f"id {RUNNER_USER} &>/dev/null || useradd -m -s /bin/bash {RUNNER_USER}")

# Get latest runner version
_, out, _ = client.exec_command("curl -s https://api.github.com/repos/actions/runner/releases/latest | grep '\"tag_name\"' | cut -d'\"' -f4 | tr -d 'v'")
runner_version = out.read().decode().strip()
print(f"Runner version: {runner_version}")

run(client, f"mkdir -p {RUNNER_DIR}")
run(client, (
    f"curl -o /tmp/runner.tar.gz -L "
    f"'https://github.com/actions/runner/releases/download/v{runner_version}/"
    f"actions-runner-linux-x64-{runner_version}.tar.gz' 2>&1 | tail -3"
), timeout=120)
run(client, f"tar xzf /tmp/runner.tar.gz -C {RUNNER_DIR} && rm /tmp/runner.tar.gz")
run(client, f"chown -R {RUNNER_USER}:{RUNNER_USER} {RUNNER_DIR}")
run(client, f"{RUNNER_DIR}/bin/installdependencies.sh 2>&1 | tail -10", timeout=120)
run(client, f"usermod -aG docker {RUNNER_USER}")

# kubeconfig for runner
run(client, f"mkdir -p /home/{RUNNER_USER}/.kube && cp /etc/rancher/k3s/k3s.yaml /home/{RUNNER_USER}/.kube/config && chown {RUNNER_USER}:{RUNNER_USER} /home/{RUNNER_USER}/.kube/config && chmod 600 /home/{RUNNER_USER}/.kube/config")
run(client, f"grep -q KUBECONFIG {RUNNER_DIR}/.env 2>/dev/null || echo 'KUBECONFIG=/home/{RUNNER_USER}/.kube/config' >> {RUNNER_DIR}/.env")

# systemd service
service = f"""[Unit]
Description=GitHub Actions runner (Bargain Hunters)
After=network.target docker.service k3s.service

[Service]
Type=simple
User={RUNNER_USER}
WorkingDirectory={RUNNER_DIR}
ExecStart={RUNNER_DIR}/run.sh
Restart=always
RestartSec=10
KillMode=process
TimeoutStopSec=5min

[Install]
WantedBy=multi-user.target
"""
write_remote(sftp, "/etc/systemd/system/actions-runner.service", service)
run(client, "systemctl daemon-reload && systemctl enable actions-runner")

sftp.close()

# ── Done ──────────────────────────────────────────────────────────────────────
print("""
\033[32m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m
\033[32m  Server bootstrap COMPLETE!\033[0m

  What's deployed so far:
  ✓ Docker + local registry (localhost:5000)
  ✓ K3s
  ✓ Traefik (ingress controller)
  ✓ cert-manager + Let's Encrypt ClusterIssuer
  ✓ bargainhunters namespace
  ✓ K8s secret (all credentials applied)
  ✓ ConfigMap
  ✓ Postgres StatefulSet
  ✓ Redis Deployment
  ✓ GitHub Actions runner installed (not yet registered)

  NEXT STEPS (manual):
  1. Point DNS A records for bargainhunters.co.ke → 13.140.133.70
  2. Register the runner:
       Go to: https://github.com/spgdaman/projectx/settings/actions/runners/new
       Copy the ./config.sh command, then run on the server:

       ssh root@13.140.133.70
       sudo -u github-runner bash -c '
         cd /home/github-runner/actions-runner &&
         ./config.sh \\
           --url https://github.com/spgdaman/projectx \\
           --token <TOKEN_FROM_GITHUB> \\
           --name bargainhunters-vps \\
           --labels self-hosted,linux,x64 \\
           --unattended
       '
       sudo systemctl start actions-runner

  3. Add these GitHub repository secrets
     (Settings → Secrets → Actions):
       SECRET_KEY, DATABASE_URL, POSTGRES_PASSWORD,
       REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND

  4. Push to master → CI/CD builds images & deploys everything.
     The first push will also run Django migrate + collectstatic
     via the initContainers in k8s/05-django.yaml.
\033[32m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m
""")
client.close()
