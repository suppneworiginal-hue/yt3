"""LLM backend router supporting multiple providers."""

import os
import json
import requests
from openai import OpenAI
from core.config import LLM_MODEL, LLM_TEMPERATURE, GENAI_APP_URL, GENAI_APP_TOKEN, GENAI_APP_AUTH_MODE


def call_openai(prompt: str) -> str:
    """
    Call OpenAI API (ChatGPT).
    
    Args:
        prompt: The prompt text to send to the LLM
        
    Returns:
        Generated text from the LLM
        
    Raises:
        ValueError: If API key is not set
        Exception: For API errors
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it to use OpenAI.")
    
    try:
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=LLM_TEMPERATURE,
        )
        
        # Extract and return the generated text
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content.strip()
        else:
            raise Exception("No response from OpenAI")
            
    except Exception as e:
        raise Exception(f"OpenAI generation failed: {str(e)}")


def call_genai_app(prompt: str) -> str:
    """
    Call GenAI App Builder endpoint.
    
    Configuration priority:
    1. Streamlit session_state (UI inputs)
    2. Environment variables
    3. Error if still missing
    
    Args:
        prompt: The prompt text to send to the LLM
        
    Returns:
        Generated text from the LLM
        
    Raises:
        RuntimeError: If endpoint URL is not configured
        Exception: For API errors
    """
    # Import streamlit inside function to avoid circular imports
    try:
        import streamlit as st
        # Priority 1: Read from session_state (UI inputs)
        url = st.session_state.get("genai_app_url", "").strip()
        token = st.session_state.get("genai_app_token", "").strip()
    except:
        # Fallback if streamlit not available or session_state not accessible
        url = ""
        token = ""
    
    # Priority 2: Fallback to environment variables
    if not url:
        url = GENAI_APP_URL
    if not token:
        token = GENAI_APP_TOKEN
    
    # Validate URL
    if not url:
        raise RuntimeError("GenAI App URL не налаштовано. Вкажи його в боковій панелі (Sidebar → GenAI App Settings).")
    
    try:
        # Build headers
        headers = {"Content-Type": "application/json"}
        
        # Add authentication if token is provided
        if token:
            if GENAI_APP_AUTH_MODE == "bearer":
                headers["Authorization"] = f"Bearer {token}"
            elif GENAI_APP_AUTH_MODE == "api-key":
                headers["X-API-Key"] = token
            # Add other auth modes as needed
        
        # Build payload
        payload = {"prompt": prompt}
        
        # Call endpoint with timeout
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=60
        )
        
        # Check status
        if response.status_code != 200:
            error_snippet = response.text[:500] if response.text else "(порожня відповідь)"
            raise RuntimeError(f"GenAI App повернув статус {response.status_code}: {error_snippet}")
        
        # Parse response
        try:
            response_data = response.json()
        except json.JSONDecodeError as e:
            raise RuntimeError(f"GenAI App повернув некоректний JSON: {response.text[:500]}")
        
        # Extract text from various possible formats
        generated_text = None
        
        # Try common response formats
        if "text" in response_data:
            generated_text = response_data["text"]
        elif "output" in response_data:
            generated_text = response_data["output"]
        elif "candidates" in response_data and len(response_data["candidates"]) > 0:
            # Vertex AI / GenAI App Builder format
            candidate = response_data["candidates"][0]
            if "content" in candidate:
                generated_text = candidate["content"]
            elif "text" in candidate:
                generated_text = candidate["text"]
        elif "response" in response_data:
            generated_text = response_data["response"]
        elif "message" in response_data:
            generated_text = response_data["message"]
        
        if generated_text is None:
            raise RuntimeError(f"Не вдалось витягти текст з відповіді GenAI App. Ключі відповіді: {list(response_data.keys())}")
        
        return generated_text.strip()
        
    except requests.exceptions.Timeout:
        raise RuntimeError("GenAI App запит перевищив час очікування (60s)")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"GenAI App запит не вдався: {str(e)}")
    except RuntimeError:
        # Re-raise RuntimeError as-is (already has good messages)
        raise
    except Exception as e:
        raise RuntimeError(f"GenAI App виклик не вдався: {str(e)}")


def generate_text(prompt: str, backend: str = "openai") -> str:
    """
    Generate text using the specified backend.
    
    Args:
        prompt: The prompt text to send to the LLM
        backend: Backend to use ("openai" or "genai_app")
        
    Returns:
        Generated text from the LLM
        
    Raises:
        ValueError: If backend is invalid or not configured
        Exception: For API errors
    """
    if backend == "openai":
        return call_openai(prompt)
    elif backend == "genai_app":
        return call_genai_app(prompt)
    else:
        raise ValueError(f"Unknown backend: {backend}. Use 'openai' or 'genai_app'.")

