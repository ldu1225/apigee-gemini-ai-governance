#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-${GCP_PROJECT_ID:-your-gcp-project-id}}"
export GCP_PROJECT_ID="$PROJECT_ID"

echo "============================================================================"
echo "🚀 Apigee x Gemini AI Governance & Chargeback Demo Provisioner"
echo "   Target Google Cloud Project: $PROJECT_ID"
echo "============================================================================"

echo "[1/3] Setting active GCP project & ADC quota project..."
gcloud config set project "$PROJECT_ID" || true
gcloud auth application-default set-quota-project "$PROJECT_ID" || true

echo "[2/3] Enabling BigQuery API and provisioning BigQuery Dataset, Views & Traffic..."
gcloud services enable bigquery.googleapis.com --project="$PROJECT_ID" || true
python3 bigquery/provision_bq.py "$PROJECT_ID"

echo "[3/3] Starting Live Apigee AI Gateway & Looker Studio Chargeback Web Server..."
echo "      Gateway API Endpoint : http://127.0.0.1:8080/v1/models:generateContent"
echo "      Interactive Demo UI  : http://127.0.0.1:8080/"
echo "============================================================================"

PYTHONPATH=. uvicorn gateway-service.main:app --host 127.0.0.1 --port 8080
