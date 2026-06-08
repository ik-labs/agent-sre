#!/usr/bin/env bash
# Deploy Agent SRE to Cloud Run (public, unauthenticated per hackathon requirement).
# Secrets go through Secret Manager; Vertex auth is via the runtime service account (ADC, no key).
set -euo pipefail

PROJECT=agent-sre-hk
REGION=us-central1
SERVICE=agent-sre
PROJECT_NUMBER=389498242223
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

cd "$(dirname "$0")/.."

# Phoenix key from local .env -> Secret Manager (never baked into the image or repo).
PHOENIX_API_KEY="$(grep -E '^PHOENIX_API_KEY=' .env | cut -d= -f2-)"
[ -n "$PHOENIX_API_KEY" ] || { echo "PHOENIX_API_KEY missing from .env"; exit 1; }

gcloud config set project "$PROJECT" >/dev/null
gcloud services enable secretmanager.googleapis.com run.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com >/dev/null

echo "==> Secret Manager: phoenix-api-key"
if gcloud secrets describe phoenix-api-key >/dev/null 2>&1; then
  printf '%s' "$PHOENIX_API_KEY" | gcloud secrets versions add phoenix-api-key --data-file=- >/dev/null
else
  printf '%s' "$PHOENIX_API_KEY" | gcloud secrets create phoenix-api-key --data-file=- >/dev/null
fi

echo "==> IAM for runtime SA ($SA)"
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:${SA}" --role=roles/aiplatform.user --condition=None >/dev/null
gcloud secrets add-iam-policy-binding phoenix-api-key \
  --member="serviceAccount:${SA}" --role=roles/secretmanager.secretAccessor >/dev/null

echo "==> Deploying to Cloud Run (Cloud Build; ~5-10 min the first time)"
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances=1 \
  --memory 2Gi --cpu 1 --timeout 600 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_LOCATION=${REGION},GEMINI_MODEL=gemini-2.5-flash,PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/s/phx-jp,PHOENIX_PROJECT_NAME=incident-agent" \
  --set-secrets "PHOENIX_API_KEY=phoenix-api-key:latest"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo
echo "Live URL: $URL"
