#!/bin/bash
# Deploy script for Google Cloud Run

set -e

# Configuration (edit these)
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="${GCP_LOCATION:-us-central1}"
SERVICE_NAME="genai-gateway"

echo "================================"
echo "GenAI Gateway - Cloud Run Deploy"
echo "================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Confirm
read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Deployment cancelled."
    exit 1
fi

# Set project
echo "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    aiplatform.googleapis.com \
    containerregistry.googleapis.com

# Build container
echo "Building container..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID,GCP_LOCATION=$REGION \
  --memory 512Mi \
  --cpu 1 \
  --timeout 120s \
  --max-instances 10 \
  --min-instances 0

# Get service URL
echo ""
echo "================================"
echo "Deployment complete!"
echo "================================"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo "Service URL: $SERVICE_URL"
echo ""
echo "Test with:"
echo "curl $SERVICE_URL/health"
echo ""
echo "Configure in Streamlit:"
echo "GenAI App URL: $SERVICE_URL/generate"
echo "================================"




