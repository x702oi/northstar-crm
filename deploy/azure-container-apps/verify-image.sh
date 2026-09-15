#!/usr/bin/env bash
set -Eeuo pipefail

registry_name="${REGISTRY_NAME:-northstarcrma}"
image_name="${IMAGE_NAME:-northstar-crm}"

if ! command -v az >/dev/null 2>&1; then
  echo "Run this script in Azure Cloud Shell." >&2
  exit 1
fi

az account show >/dev/null

az acr repository show-tags \
  --name "${registry_name}" \
  --repository "${image_name}" \
  --orderby time_desc \
  --output table
