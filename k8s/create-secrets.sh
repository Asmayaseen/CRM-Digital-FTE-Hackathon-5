#!/usr/bin/env bash
# create-secrets.sh — Generate Kubernetes secrets from .env for minikube
# Usage: bash k8s/create-secrets.sh
# Run from project root

set -e

ENV_FILE=".env"
NAMESPACE="customer-success-fte"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: .env file not found. Run from project root."
  exit 1
fi

source "$ENV_FILE"

echo "Creating namespace..."
kubectl apply -f k8s/namespace.yaml

echo "Creating secrets in namespace: $NAMESPACE"

kubectl create secret generic fte-secrets \
  --namespace="$NAMESPACE" \
  --from-literal=GROQ_API_KEY="${GROQ_API_KEY}" \
  --from-literal=POSTGRES_USER="${POSTGRES_USER:-fte_user}" \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-changeme}" \
  --from-literal=TWILIO_ACCOUNT_SID="${TWILIO_ACCOUNT_SID:-}" \
  --from-literal=TWILIO_AUTH_TOKEN="${TWILIO_AUTH_TOKEN:-}" \
  --from-literal=TWILIO_WHATSAPP_NUMBER="${TWILIO_WHATSAPP_NUMBER:-}" \
  --from-file=GMAIL_CREDENTIALS=./credentials/gmail-credentials.json \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secrets created successfully!"
kubectl get secrets -n "$NAMESPACE"
