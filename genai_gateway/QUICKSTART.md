# Quick Start Guide

## 🚀 Option 1: Local Development (5 minutes)

### Prerequisites
- Python 3.11+
- Google Cloud account with Vertex AI API enabled
- GCloud CLI installed and authenticated

### Steps

```bash
# 1. Navigate to gateway folder
cd genai_gateway

# 2. Install dependencies
pip install -r requirements.txt

# 3. Authenticate with Google Cloud
gcloud auth application-default login

# 4. Set your project ID
export GCP_PROJECT_ID=your-actual-project-id

# 5. Run the gateway
python main.py
```

Server starts on `http://localhost:8080`

### Test It

```bash
# In another terminal
cd genai_gateway
python test_local.py
```

### Configure Streamlit App

1. Open your Streamlit app
2. In sidebar, select: **LLM Backend → "GenAI App"**
3. Enter URL: `http://localhost:8080/generate`
4. Click **"Test GenAI App connection"**
5. Should see: ✅ Connected!

---

## ☁️ Option 2: Deploy to Cloud Run (10 minutes)

### Prerequisites
- Google Cloud Project with billing enabled
- GCloud CLI installed and authenticated

### Steps

```bash
# 1. Set variables
export PROJECT_ID=your-project-id
export REGION=us-central1

# 2. Navigate to folder
cd genai_gateway

# 3. Make deploy script executable
chmod +x deploy.sh

# 4. Run deployment (or follow manual steps below)
./deploy.sh

# OR Manual deployment:

# Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com aiplatform.googleapis.com

# Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/genai-gateway --project $PROJECT_ID

# Deploy
gcloud run deploy genai-gateway \
  --image gcr.io/$PROJECT_ID/genai-gateway \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID \
  --memory 512Mi \
  --timeout 120s \
  --project $PROJECT_ID

# Get URL
gcloud run services describe genai-gateway \
  --region $REGION \
  --project $PROJECT_ID \
  --format 'value(status.url)'
```

### Configure Streamlit App

1. Copy the Cloud Run URL (e.g., `https://genai-gateway-xxxxx-uc.a.run.app`)
2. In Streamlit sidebar:
   - Select: **LLM Backend → "GenAI App"**
   - Enter: `https://genai-gateway-xxxxx-uc.a.run.app/generate`
3. Click **"Test GenAI App connection"**
4. Should see: ✅ Connected!

---

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8080/health
# {"status":"ok","project":"your-project","model":"gemini-1.5-pro"}
```

### Generate Text
```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a one-sentence story about a cat."}'

# {"text":"The cat sat by the window..."}
```

### From Python
```python
import requests

response = requests.post(
    "http://localhost:8080/generate",
    json={"prompt": "Reply with: OK"}
)
print(response.json())
# {'text': 'OK'}
```

---

## 💰 Cost Optimization

**For Development:**
- Use `gemini-1.5-flash` (faster, cheaper)
- Set in `.env`: `GEMINI_MODEL=gemini-1.5-flash`

**For Production:**
- Start with `gemini-1.5-pro` (best quality)
- Monitor usage in GCP Console
- Consider rate limiting if needed

---

## 🔒 Security (Production)

**Local dev:** No auth needed (localhost only)

**Cloud Run production:**
```bash
# Option 1: Require authentication
gcloud run deploy genai-gateway --no-allow-unauthenticated ...

# Option 2: Add API key (implement in main.py)
# Add middleware to check X-API-Key header

# Option 3: Use Cloud Run IAM
# Streamlit app calls with service account token
```

---

## ❓ Troubleshooting

**"GCP_PROJECT_ID environment variable is required"**
```bash
export GCP_PROJECT_ID=your-project-id
```

**"Permission denied" / "403 Forbidden"**
```bash
gcloud auth application-default login
gcloud auth login
```

**"Vertex AI API not enabled"**
```bash
gcloud services enable aiplatform.googleapis.com --project your-project-id
```

**Connection refused**
- Check server is running: `curl http://localhost:8080/health`
- Check port is correct (default 8080)

**"Content blocked" response**
- Gemini safety filters blocked the content
- Check prompt for policy violations
- Try rewording the prompt

---

## 📊 Monitoring

**Local:**
- Check terminal logs for request/response info

**Cloud Run:**
```bash
# View logs
gcloud run services logs read genai-gateway --region us-central1

# Monitor in real-time
gcloud run services logs tail genai-gateway --region us-central1
```

**GCP Console:**
- Cloud Run → genai-gateway → Metrics
- View request count, latency, errors
- Check costs in Billing

---

## ✅ Success Checklist

- [ ] Server starts without errors
- [ ] `/health` returns 200 OK
- [ ] `/generate` with simple prompt works
- [ ] Streamlit "Test GenAI App connection" succeeds
- [ ] Full story generation completes
- [ ] No Gemini API errors in logs

Once all checked, you're ready to use your GCP trial credits for story generation! 🎉




