#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/northstar.env"
COMPOSE_FILE="$SCRIPT_DIR/compose.yaml"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "northstar.env is missing. Initialize the deployment first." >&2
  exit 1
fi

if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
elif sudo -n docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
else
  echo "Docker is unavailable." >&2
  exit 1
fi

compose() {
  "${DOCKER[@]}" compose --project-directory "$SCRIPT_DIR" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

site_name="$(awk -F= '$1 == "SITE_NAME" { print substr($0, index($0, "=") + 1) }' "$ENV_FILE")"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="$SCRIPT_DIR/backups/$timestamp"

umask 077
mkdir -p "$destination"
compose exec -T backend bench --site "$site_name" backup --with-files --compress
compose cp "backend:/home/frappe/frappe-bench/sites/$site_name/private/backups/." "$destination"

if ! find "$destination" -type f -size +0c -print -quit | grep -q .; then
  echo "Backup verification failed: no non-empty files were copied." >&2
  exit 1
fi

echo "Full site backup copied to $destination"
echo "Move it to encrypted off-host storage; this VM is a single failure domain."
