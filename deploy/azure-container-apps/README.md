# Azure Container Apps deployment

This directory contains the browser-only image build path for Northstar CRM.
It targets Azure Container Apps, which requires Linux AMD64 images.

## Build the image without Docker on Windows

1. Open Azure Cloud Shell in the Azure portal and select Bash.
2. Upload and extract the Northstar CRM release archive.
3. Enter the extracted project directory.
4. Run:

   ```bash
   chmod +x deploy/azure-container-apps/*.sh
   REGISTRY_NAME=northstarcrma deploy/azure-container-apps/build-image.sh
   ```

Azure Container Registry builds the image remotely and stores it as:

```text
northstarcrma.azurecr.io/northstar-crm:v1
```

Confirm the image exists with:

```bash
REGISTRY_NAME=northstarcrma deploy/azure-container-apps/verify-image.sh
```

Do not create the Container App until this build reports success. Frappe is a
multi-service system; the runtime deployment needs database, Redis, workers,
scheduler, websocket, frontend, and persistent storage configuration.
