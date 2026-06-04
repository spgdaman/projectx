#!/usr/bin/env bash
# Run this ONCE on the server AFTER bootstrap-server.sh completes.
# Usage: sudo bash scripts/install-github-runner.sh

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && error "Run this script as root (sudo bash install-github-runner.sh)"

RUNNER_USER="github-runner"
RUNNER_HOME="/home/${RUNNER_USER}"
RUNNER_DIR="${RUNNER_HOME}/actions-runner"

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Create dedicated runner user
# ─────────────────────────────────────────────────────────────────────────────
info "Step 1: Creating ${RUNNER_USER} user..."
if id "${RUNNER_USER}" &>/dev/null; then
  warn "User ${RUNNER_USER} already exists, skipping creation."
else
  useradd -m -s /bin/bash "${RUNNER_USER}"
fi
info "User ${RUNNER_USER} ready."

# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Get latest runner version from GitHub API
# ─────────────────────────────────────────────────────────────────────────────
info "Step 2: Fetching latest GitHub Actions runner version..."
RUNNER_VERSION=$(curl -s \
  https://api.github.com/repos/actions/runner/releases/latest \
  | grep '"tag_name"' | cut -d'"' -f4 | tr -d 'v')
info "Latest runner version: ${RUNNER_VERSION}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Download and extract runner
# ─────────────────────────────────────────────────────────────────────────────
info "Step 3: Downloading runner v${RUNNER_VERSION}..."
curl -o /tmp/runner.tar.gz -L \
  "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"

mkdir -p "${RUNNER_DIR}"
tar xzf /tmp/runner.tar.gz -C "${RUNNER_DIR}"
rm /tmp/runner.tar.gz
chown -R "${RUNNER_USER}:${RUNNER_USER}" "${RUNNER_DIR}"
info "Runner extracted to ${RUNNER_DIR}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Install runner system dependencies
# ─────────────────────────────────────────────────────────────────────────────
info "Step 4: Installing runner system dependencies..."
"${RUNNER_DIR}/bin/installdependencies.sh"

# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Add github-runner to docker group
# ─────────────────────────────────────────────────────────────────────────────
info "Step 5: Adding ${RUNNER_USER} to docker group..."
usermod -aG docker "${RUNNER_USER}"
info "Done."

# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Copy K3s kubeconfig to runner home
# ─────────────────────────────────────────────────────────────────────────────
info "Step 6: Copying kubeconfig for ${RUNNER_USER}..."
mkdir -p "${RUNNER_HOME}/.kube"
cp /etc/rancher/k3s/k3s.yaml "${RUNNER_HOME}/.kube/config"
chown "${RUNNER_USER}:${RUNNER_USER}" "${RUNNER_HOME}/.kube/config"
chmod 600 "${RUNNER_HOME}/.kube/config"

# Write KUBECONFIG into the runner's .env so kubectl works in workflow steps
echo "KUBECONFIG=${RUNNER_HOME}/.kube/config" >> "${RUNNER_DIR}/.env"
info "kubeconfig ready for ${RUNNER_USER}."

# ─────────────────────────────────────────────────────────────────────────────
# Step 7 — Create systemd service
# ─────────────────────────────────────────────────────────────────────────────
info "Step 7: Creating systemd service..."
cat > /etc/systemd/system/actions-runner.service <<EOF
[Unit]
Description=GitHub Actions runner (Bargain Hunters)
After=network.target docker.service k3s.service

[Service]
Type=simple
User=${RUNNER_USER}
WorkingDirectory=${RUNNER_DIR}
ExecStart=${RUNNER_DIR}/run.sh
Restart=always
RestartSec=10
KillMode=process
TimeoutStopSec=5min

[Install]
WantedBy=multi-user.target
EOF

# ─────────────────────────────────────────────────────────────────────────────
# Step 8 — Enable service (do NOT start yet — registration must happen first)
# ─────────────────────────────────────────────────────────────────────────────
info "Step 8: Enabling actions-runner service (not starting yet)..."
systemctl daemon-reload
systemctl enable actions-runner
info "Service enabled. It will start automatically after registration."

# ─────────────────────────────────────────────────────────────────────────────
# Step 9 — Print manual registration instructions
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ONE MANUAL STEP REQUIRED: Register the runner"
echo ""
echo "  1. Go to your GitHub repo:"
echo "     Settings → Actions → Runners → New self-hosted runner"
echo "     (select: Linux, x64)"
echo ""
echo "  2. Copy the ./config.sh command shown on that page."
echo "     It looks like:"
echo "     ./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token XXXXX"
echo ""
echo "  3. Run it as the ${RUNNER_USER} user:"
echo "     sudo -u ${RUNNER_USER} bash -c \\"
echo "       'cd ${RUNNER_DIR} && \\"
echo "        ./config.sh \\"
echo "          --url https://github.com/YOUR_ORG/YOUR_REPO \\"
echo "          --token XXXXX \\"
echo "          --name bargainhunters-vps \\"
echo "          --labels self-hosted,linux,x64 \\"
echo "          --unattended'"
echo ""
echo "  4. Start the runner service:"
echo "     sudo systemctl start actions-runner"
echo "     sudo systemctl status actions-runner"
echo ""
echo "  5. Add these secrets to your GitHub repo"
echo "     (Settings → Secrets → Actions → New repository secret):"
echo "     SECRET_KEY        — Django secret key"
echo "     DATABASE_URL      — postgres://bargainhunters:PASS@postgres-service:5432/bargainhunters"
echo "     POSTGRES_PASSWORD — DB password"
echo "     REDIS_URL         — redis://redis-service:6379/1"
echo "     CELERY_BROKER_URL — redis://redis-service:6379/1"
echo "     CELERY_RESULT_BACKEND — redis://redis-service:6379/2"
echo "     MPESA_CONSUMER_KEY    — (optional)"
echo "     MPESA_CONSUMER_SECRET — (optional)"
echo "     MPESA_CALLBACK_URL    — (optional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
