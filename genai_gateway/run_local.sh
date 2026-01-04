#!/bin/bash
# Local development run script

# Load environment variables if .env exists
if [ -f .env ]; then
    echo "Loading .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check required config
if [ -z "$GCP_PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID not set"
    echo "Either:"
    echo "  1. Create .env file with GCP_PROJECT_ID=your-project-id"
    echo "  2. Export: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

echo "Starting GenAI Gateway..."
echo "Project: $GCP_PROJECT_ID"
echo "Location: ${GCP_LOCATION:-us-central1}"
echo "Model: ${GEMINI_MODEL:-gemini-1.5-pro}"
echo "Port: ${PORT:-8080}"
echo ""

# Run the app
python main.py




