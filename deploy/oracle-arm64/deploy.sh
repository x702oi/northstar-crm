#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/northstar.env"
COMPOSE_FILE="$SCRIPT_DIR/compose.yaml"
SECRETS_DIR="$SCRIPT_DIR/secrets"

usage() {
  cat <<'USAGE'
Usage:
  ./deploy.sh init IMAGE SITE_NAME ACME_EMAIL
  ./deploy.sh apply
  ./deploy.sh status
  ./deploy.sh logs [SERVICE]
  ./deploy.sh password

Example:
  ./deploy.sh init ghcr.io/acme/northstar-crm:COMMIT_SHA \
    northstar.203.0.113.10.sslip.io admin@example.com
  ./deploy.sh apply
USAGE
}

select_docker() {
  if docker info >/dev/null 2>&1; then
    DOCKER=(docker)
  elif sudo -n docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
  else
    echo "Docker is unavailable. Run bootstrap-ubuntu.sh, then log out and back in." >&2
    exit 1
  fi
}

compose() {
  "${DOCKER[@]}" compose --project-directory "$SCRIPT_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

require_config() {
  if [[ ! -f "$ENV_FILE" || ! -s "$SECRETS_DIR/db_root_password" || ! -s "$SECRETS_DIR/admin_password" ]]; then
    echo "Deployment configuration is missing. Run ./deploy.sh init first." >&2
    exit 1
  fi
}

init_config() {
  if (( $# != 3 )); then
    usage
    exit 2
  fi
  local image_ref="$1"
  local site_name="$2"
  local acme_email="$3"

  if [[ -e "$ENV_FILE" || -e "$SECRETS_DIR" ]]; then
    echo "Configuration already exists; refusing to overwrite secrets." >&2
    exit 1
  fi
  if [[ "$image_ref" =~ [[:space:]] || "$image_ref" != *:* ]]; then
    echo "IMAGE must be a tagged container reference without spaces." >&2
    exit 2
  fi
  if [[ ! "$site_name" =~ ^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$ || "$site_name" != *.* ]]; then
    echo "SITE_NAME must be a DNS hostname." >&2
    exit 2
  fi
  if [[ ! "$acme_email" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]]; then
    echo "ACME_EMAIL must be a valid email address." >&2
    exit 2
  fi

  umask 077
  mkdir -p "$SECRETS_DIR"
  openssl rand -hex 32 > "$SECRETS_DIR/db_root_password"
  openssl rand -base64 30 | tr -d '\n' > "$SECRETS_DIR/admin_password"
  printf '\n' >> "$SECRETS_DIR/admin_password"
  cat > "$ENV_FILE" <<EOF
CUSTOM_IMAGE=$image_ref
SITE_NAME=$site_name
LETSENCRYPT_EMAIL=$acme_email
MARIADB_IMAGE=mariadb:11.8
REDIS_IMAGE=redis:8.6-alpine
TRAEFIK_IMAGE=traefik:v3.7
PULL_POLICY=always
GUNICORN_WORKERS=2
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=120
CLIENT_MAX_BODY_SIZE=50m
DOCKER_SUBNET=172.31.250.0/24
EOF
  chmod 600 "$ENV_FILE" "$SECRETS_DIR/db_root_password" "$SECRETS_DIR/admin_password"
  echo "Created northstar.env and two mode-600 secret files."
}

apply_stack() {
  require_config
  select_docker
  compose config --quiet
  compose pull
  compose up -d db redis-cache redis-queue
  compose --profile setup run --rm configurator
  compose --profile setup run --rm site-init
  compose up -d --remove-orphans backend websocket queue-short queue-long scheduler frontend proxy

  local site_name
  site_name="$(awk -F= '$1 == "SITE_NAME" { print substr($0, index($0, "=") + 1) }' "$ENV_FILE")"
  for _ in {1..24}; do
    if curl -fsS --max-time 5 "https://${site_name}/api/method/ping" >/dev/null 2>&1; then
      echo "Northstar CRM is available at https://${site_name}"
      return 0
    fi
    sleep 5
  done
  echo "The stack started, but HTTPS is not ready yet. Check ./deploy.sh status and ./deploy.sh logs proxy." >&2
}

show_status() {
  require_config
  select_docker
  compose ps
}

show_logs() {
  require_config
  select_docker
  if (( $# > 1 )); then
    usage
    exit 2
  fi
  if (( $# == 1 )); then
    compose logs --tail=200 "$1"
  else
    compose logs --tail=200
  fi
}

show_password() {
  require_config
  cat "$SECRETS_DIR/admin_password"
}

command="${1:-}"
if (( $# > 0 )); then
  shift
fi

case "$command" in
  init) init_config "$@" ;;
  apply) apply_stack "$@" ;;
  status) show_status "$@" ;;
  logs) show_logs "$@" ;;
  password) show_password "$@" ;;
  *) usage; exit 2 ;;
esac
