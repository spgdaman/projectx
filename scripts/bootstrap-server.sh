#!/usr/bin/env bash
# Run this ONCE on a fresh Contabo Ubuntu 24.04 server as root.
# Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/YOUR_REPO/master/scripts/bootstrap-server.sh | bash
# Or: bash scripts/bootstrap-server.sh

# IMPORTANT: Replace the email below before running.
LETSENCRYPT_EMAIL="REPLACE_WITH_YOUR_EMAIL"

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && error "Run this script as root (sudo bash bootstrap-server.sh)"

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — System update
# ─────────────────────────────────────────────────────────────────────────────
info "Step 1: Updating system packages..."
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git ufw fail2ban

# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Firewall
# ─────────────────────────────────────────────────────────────────────────────
info "Step 2: Configuring UFW firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 6443/tcp   # K3s API server (kubectl from local machine)
ufw --force enable
info "Firewall enabled."

# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Install Docker
# ─────────────────────────────────────────────────────────────────────────────
info "Step 3: Installing Docker..."
curl -fsSL https://get.docker.com | sh
usermod -aG docker "${SUDO_USER:-root}" 2>/dev/null || true
systemctl enable docker
systemctl start docker
info "Docker installed."

# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Start local Docker registry on port 5000
# (K3s pulls images from here — avoids pushing to Docker Hub)
# ─────────────────────────────────────────────────────────────────────────────
info "Step 4: Starting local Docker registry on port 5000..."
docker run -d \
  --name registry \
  --restart=always \
  -p 5000:5000 \
  -v registry-data:/var/lib/registry \
  registry:2
info "Local registry running at localhost:5000"

# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Install K3s (disabling bundled Traefik — we install via Helm)
# ─────────────────────────────────────────────────────────────────────────────
info "Step 5: Installing K3s..."
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable=traefik" sh -

info "Waiting for K3s node to be Ready..."
until kubectl get nodes 2>/dev/null | grep -q "Ready"; do
  sleep 3
done
info "K3s is ready."

# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Configure kubectl for current user
# ─────────────────────────────────────────────────────────────────────────────
info "Step 6: Configuring kubectl..."
mkdir -p "$HOME/.kube"
cp /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
chmod 600 "$HOME/.kube/config"
grep -qxF 'export KUBECONFIG=$HOME/.kube/config' "$HOME/.bashrc" || \
  echo 'export KUBECONFIG=$HOME/.kube/config' >> "$HOME/.bashrc"
export KUBECONFIG="$HOME/.kube/config"
info "kubectl configured."

# ─────────────────────────────────────────────────────────────────────────────
# Step 7 — Install Helm
# ─────────────────────────────────────────────────────────────────────────────
info "Step 7: Installing Helm..."
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
info "Helm installed."

# ─────────────────────────────────────────────────────────────────────────────
# Step 8 — Install Traefik via Helm (ingress controller)
# ─────────────────────────────────────────────────────────────────────────────
info "Step 8: Installing Traefik ingress controller via Helm..."
helm repo add traefik https://helm.traefik.io/traefik
helm repo update
kubectl create namespace traefik --dry-run=client -o yaml | kubectl apply -f -
helm upgrade --install traefik traefik/traefik \
  --namespace traefik \
  --set "ports.web.redirectTo.port=websecure" \
  --set "ports.websecure.tls.enabled=true" \
  --set "service.type=LoadBalancer"
info "Traefik installed."

# ─────────────────────────────────────────────────────────────────────────────
# Step 9 — Install cert-manager (Let's Encrypt SSL)
# ─────────────────────────────────────────────────────────────────────────────
info "Step 9: Installing cert-manager..."
kubectl apply -f \
  https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

info "Waiting for cert-manager to be available..."
kubectl wait --for=condition=available \
  --timeout=120s \
  deployment/cert-manager \
  -n cert-manager
kubectl wait --for=condition=available \
  --timeout=120s \
  deployment/cert-manager-webhook \
  -n cert-manager
info "cert-manager ready."

# ─────────────────────────────────────────────────────────────────────────────
# Step 10 — Create Let's Encrypt ClusterIssuer
# ─────────────────────────────────────────────────────────────────────────────
info "Step 10: Creating Let's Encrypt ClusterIssuer..."
[[ "$LETSENCRYPT_EMAIL" == "REPLACE_WITH_YOUR_EMAIL" ]] && \
  error "Edit LETSENCRYPT_EMAIL at the top of this script before running."

kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ${LETSENCRYPT_EMAIL}
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: traefik
EOF
info "ClusterIssuer created."

# ─────────────────────────────────────────────────────────────────────────────
# Step 11 — Create the bargainhunters namespace
# ─────────────────────────────────────────────────────────────────────────────
info "Step 11: Creating bargainhunters namespace..."
kubectl apply -f k8s/00-namespace.yaml
info "Namespace created."

# ─────────────────────────────────────────────────────────────────────────────
# Step 12 — Allow K3s to pull from localhost:5000 (insecure local registry)
# ─────────────────────────────────────────────────────────────────────────────
info "Step 12: Configuring K3s to pull from local registry..."
mkdir -p /etc/rancher/k3s
cat > /etc/rancher/k3s/registries.yaml <<'EOF'
mirrors:
  "localhost:5000":
    endpoint:
      - "http://localhost:5000"
EOF
systemctl restart k3s
info "Waiting for K3s to come back up after restart..."
until kubectl get nodes 2>/dev/null | grep -q "Ready"; do sleep 3; done
info "K3s registry config applied."

# ─────────────────────────────────────────────────────────────────────────────
# Step 13 — Completion summary
# ─────────────────────────────────────────────────────────────────────────────
SERVER_IP=$(curl -s ifconfig.me)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Server bootstrap complete!"
echo ""
echo "  Server IP: ${SERVER_IP}"
echo ""
echo "  ACTION REQUIRED:"
echo "  1. Point bargainhunters.co.ke A record → ${SERVER_IP}"
echo "  2. Point www.bargainhunters.co.ke A record → ${SERVER_IP}"
echo ""
echo "  NEXT STEPS:"
echo "  3. Copy k8s/02-secret.yaml to server, fill in real values,"
echo "     then: kubectl apply -f k8s/02-secret.yaml"
echo "  4. Run: bash scripts/install-github-runner.sh"
echo "  5. Register the runner (see instructions printed by that script)"
echo "  6. Push to master branch to trigger first CI/CD deploy"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
