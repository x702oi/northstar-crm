#!/usr/bin/env bash
set -Eeuo pipefail

registry_name="${REGISTRY_NAME:-northstarcrma}"
image_name="${IMAGE_NAME:-northstar-crm}"
image_tag="${IMAGE_TAG:-v1}"

if ! command -v az >/dev/null 2>&1; then
  echo "Run this script in Azure Cloud Shell." >&2
  exit 1
fi

az account show >/dev/null

az acr build \
  --registry "${registry_name}" \
  --image "${image_name}:${image_tag}" \
  --file deploy/azure-container-apps/Dockerfile \
  .

echo "Image built: ${registry_name}.azurecr.io/${image_name}:${image_tag}"
