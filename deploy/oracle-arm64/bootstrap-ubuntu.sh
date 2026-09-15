#!/usr/bin/env bash
set -Eeuo pipefail

if (( EUID == 0 )); then
  echo "Run this script as the normal Ubuntu user; it invokes sudo when needed." >&2
  exit 1
fi

if [[ "$(uname -m)" != "aarch64" && "$(uname -m)" != "arm64" ]]; then
  echo "This bootstrap is for an Oracle Ampere ARM64 VM." >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  echo "Cannot identify the operating system." >&2
  exit 1
fi

source /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "Ubuntu is required; detected ${ID:-unknown}." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y ca-certificates curl jq openssl unzip ufw
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

docker_repo="deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable"
echo "$docker_repo" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"

swap_kib="$(awk 'NR > 1 { total += $3 } END { print total + 0 }' /proc/swaps)"
if (( swap_kib < 2097152 )); then
  if [[ ! -f /swapfile ]]; then
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
  fi
  sudo swapon /swapfile || true
  if ! grep -qE '^/swapfile[[:space:]]' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
  fi
fi

sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo "Docker, Compose, a 4 GB swap safety net, and the host firewall are ready."
echo "Log out and back in once so your Docker group membership becomes active."
echo "OCI networking must also allow TCP 80/443 and restrict TCP 22 to your own IP."
