# GenAI Gateway - FastAPI + Google Gemini (Vertex AI)

Minimal FastAPI gateway that provides a simple HTTP interface to Google Gemini via Vertex AI.

## Features

- ✅ Simple JSON API: `POST /generate` with `{"prompt": "..."}`
- ✅ Returns `{"text": "..."}`
- ✅ Health check: `GET /health`
- ✅ Production-ready error handling
- ✅ Cloud Run compatible
- ✅ No streaming, no markdown - strict JSON only

## API Endpoints

### GET /health
Health check.

**Response:**
```json
{
  "status": "ok",
  "project": "your-gcp-project",
  "model": "gemini-1.5-pro"
}
```

### POST /generate
Generate text using Gemini.

**Request:**
```json
{
  "prompt": "Your prompt here"
}
```

**Response (Success):**
```json
{
  "text": "Generated text from Gemini"
}
```

**Response (Error):**
```json
{
  "error": "Error type",
  "detail": "Detailed error message (max 500 chars)"
}
```

## Local Development

### Prerequisites

1. **Google Cloud Setup:**
   ```bash
   # Install gcloud CLI
   # https://cloud.google.com/sdk/docs/install
   
   # Authenticate
   gcloud auth application-default login
   
   # Set project
   gcloud config set project YOUR_PROJECT_ID
   
   # Enable Vertex AI API
   gcloud services enable aiplatform.googleapis.com
   ```

2. **Python 3.11+**

### Install Dependencies

```bash
cd genai_gateway
pip install -r requirements.txt
```

### Environment Variables

Create `.env` file:
```bash
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=us-central1        # Optional, defaults to us-central1
GEMINI_MODEL=gemini-1.5-pro     # Optional, defaults to gemini-1.5-pro
PORT=8080                       # Optional, defaults to 8080
```

### Run Locally

```bash
# Option 1: Direct Python
export GCP_PROJECT_ID=your-project-id
python main.py

# Option 2: Using uvicorn directly
export GCP_PROJECT_ID=your-project-id
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Option 3: With .env file
# Install python-dotenv first: pip install python-dotenv
# Then load vars: set -a; source .env; set +a
python main.py
```

### Test Locally

```bash
# Health check
curl http://localhost:8080/health

# Generate text
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Reply with: Hello World"}'

# Expected response:
# {"text":"Hello World"}
```

## Deploy to Cloud Run

### Build and Deploy

```bash
# Set your GCP project
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1

# Build container
gcloud builds submit --tag gcr.io/$PROJECT_ID/genai-gateway

# Deploy to Cloud Run
gcloud run deploy genai-gateway \
  --image gcr.io/$PROJECT_ID/genai-gateway \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID,GCP_LOCATION=$REGION \
  --memory 512Mi \
  --timeout 120s

# Get the URL
gcloud run services describe genai-gateway --region $REGION --format 'value(status.url)'
```

### Configure in Streamlit App

After deployment, copy the Cloud Run URL and paste it in:
**Streamlit Sidebar → GenAI App Settings → GenAI App URL**

Example:
```
https://genai-gateway-xxxxx-uc.a.run.app/generate
```

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GCP_PROJECT_ID` | Yes | - | Your GCP Project ID |
| `GCP_LOCATION` | No | us-central1 | Vertex AI location/region |
| `GEMINI_MODEL` | No | gemini-1.5-pro | Gemini model name |
| `PORT` | No | 8080 | Server port |

### Supported Gemini Models

- `gemini-1.5-pro` (recommended, best quality)
- `gemini-1.5-flash` (faster, cheaper)
- `gemini-1.0-pro` (older generation)

## Troubleshooting

**"GCP_PROJECT_ID environment variable is required"**
- Set `GCP_PROJECT_ID` before running

**"403 Forbidden" or "Permission denied"**
- Run: `gcloud auth application-default login`
- Ensure Vertex AI API is enabled
- Check IAM permissions (need `aiplatform.user` role)

**"Model not found"**
- Check model name spelling
- Ensure model is available in your region
- Try switching to `gemini-1.5-flash`

**"Content blocked"**
- Gemini safety filters blocked the content
- Check prompt for policy violations
- Response will include block reason in detail

## Security Notes

- No authentication required for local dev
- For production: Add API key auth or Cloud Run IAM
- Never expose this endpoint publicly without auth
- Use Cloud Run's built-in authentication for production

## Cost Optimization

- Use `gemini-1.5-flash` for development (cheaper)
- Set memory limits in Cloud Run (512Mi sufficient)
- Enable request logging to monitor usage
- Consider request rate limiting for production

## Integration with Story Generator

Once deployed, configure in your Streamlit app:

1. Switch LLM Backend to "GenAI App"
2. Enter your Cloud Run URL in "GenAI App URL"
3. Click "Test GenAI App connection"
4. If successful, you can use GenAI App for all generation tasks

The gateway will use your GCP trial credits instead of OpenAI API.




