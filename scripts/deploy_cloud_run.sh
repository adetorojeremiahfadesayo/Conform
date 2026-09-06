#!/usr/bin/env bash
# CONFORM — Google Cloud Run Deployment Script
#
# Builds the multi-stage Docker container and deploys to Google Cloud Run.
#
# Prerequisites:
# 1. gcloud CLI installed and authenticated (gcloud auth login)
# 2. Google Cloud project configured (gcloud config set project <PROJECT_ID>)
# 3. Artifact Registry or Container Registry API enabled

set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="conform"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "============================================================"
echo " Deploying CONFORM to Google Cloud Run"
echo " Project: ${PROJECT_ID}"
echo " Region:  ${REGION}"
echo " Service: ${SERVICE_NAME}"
echo " Image:   ${IMAGE}"
echo "============================================================"

# 1. Build and push container image using Cloud Build
echo "--> Building container image via Google Cloud Build..."
gcloud builds submit --tag "${IMAGE}" .

# 2. Deploy to Cloud Run
echo "--> Deploying service to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_REGION=${REGION},BUILD_BUDGET_USD=10.00"

# 3. Get the live URL
SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)')"

echo "============================================================"
echo " Deployment Complete!"
echo " Live Hosted Application URL: ${SERVICE_URL}"
echo " Use this URL for your Devpost submission form."
echo "============================================================"
