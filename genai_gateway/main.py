"""FastAPI Gateway for Google Gemini via Vertex AI"""

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

# Validate required config
if not GCP_PROJECT_ID:
    raise RuntimeError("GCP_PROJECT_ID environment variable is required")

# Initialize Vertex AI
try:
    vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
    logger.info(f"Vertex AI initialized: project={GCP_PROJECT_ID}, location={GCP_LOCATION}, model={GEMINI_MODEL}")
except Exception as e:
    logger.error(f"Failed to initialize Vertex AI: {e}")
    raise

# Create FastAPI app
app = FastAPI(
    title="GenAI Gateway",
    description="FastAPI gateway for Google Gemini via Vertex AI",
    version="1.0.0"
)


class GenerateRequest(BaseModel):
    """Request model for /generate endpoint"""
    prompt: str


class GenerateResponse(BaseModel):
    """Response model for /generate endpoint (success)"""
    text: str


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str
    detail: str


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "project": GCP_PROJECT_ID, "model": GEMINI_MODEL}


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Generate text using Google Gemini via Vertex AI.
    
    Request JSON:
        {"prompt": "your prompt here"}
    
    Response JSON (success):
        {"text": "generated text"}
    
    Response JSON (error):
        {"error": "error message", "detail": "error details (max 500 chars)"}
    """
    try:
        # Validate input
        if not request.prompt or not request.prompt.strip():
            raise HTTPException(
                status_code=400,
                detail="Prompt cannot be empty"
            )
        
        # Initialize model
        model = GenerativeModel(GEMINI_MODEL)
        
        # Configure generation (no temperature override - use model defaults)
        # Vertex AI Gemini models have good defaults; avoid forcing temperature
        generation_config = GenerationConfig(
            max_output_tokens=8192,  # Allow long outputs for story generation
            candidate_count=1,
        )
        
        # Generate content with timeout handling
        logger.info(f"Generating with model={GEMINI_MODEL}, prompt_length={len(request.prompt)}")
        
        try:
            response = model.generate_content(
                request.prompt,
                generation_config=generation_config,
            )
        except Exception as gen_error:
            error_msg = str(gen_error)[:500]
            logger.error(f"Generation failed: {error_msg}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Generation failed",
                    "detail": error_msg
                }
            )
        
        # Extract text from response
        if not response.candidates:
            logger.warning("No candidates in response")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "No response from model",
                    "detail": "Model returned empty candidates list"
                }
            )
        
        candidate = response.candidates[0]
        
        # Check for safety blocks
        if hasattr(candidate, 'finish_reason') and candidate.finish_reason != 1:  # 1 = STOP (normal completion)
            finish_reason_name = getattr(candidate.finish_reason, 'name', str(candidate.finish_reason))
            logger.warning(f"Generation blocked: finish_reason={finish_reason_name}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Content blocked",
                    "detail": f"Model blocked response due to: {finish_reason_name}"
                }
            )
        
        # Extract text
        generated_text = candidate.content.parts[0].text if candidate.content.parts else ""
        
        if not generated_text:
            logger.warning("Empty text in response")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Empty response",
                    "detail": "Model returned empty text"
                }
            )
        
        logger.info(f"Generation successful: output_length={len(generated_text)}")
        
        return {"text": generated_text}
        
    except HTTPException:
        # Re-raise FastAPI HTTPExceptions
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        error_detail = str(e)[:500]
        logger.error(f"Unexpected error: {error_detail}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": error_detail
            }
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    error_detail = str(exc)[:500]
    logger.error(f"Unhandled exception: {error_detail}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": error_detail
        }
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)




