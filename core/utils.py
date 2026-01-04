"""Utility functions for the Story Generator app."""

import re
from pathlib import Path
from core.config import COOKIES_FILE


def safe_int(value: any, default: int = 0) -> int:
    """Safely convert value to integer, returning default if conversion fails."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def count_chars(text: str) -> int:
    """
    Count characters in text.
    
    Args:
        text: Input text
        
    Returns:
        Character count
    """
    return len(text)


def normalize_newlines(text: str) -> str:
    """
    Normalize newlines in text (convert various newline formats to \n).
    
    Args:
        text: Input text
        
    Returns:
        Text with normalized newlines
    """
    # Replace Windows (\r\n) and old Mac (\r) newlines with Unix (\n)
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    # Normalize multiple newlines to single newline
    text = re.sub(r'\n\s*\n+', '\n', text)
    return text


def cookies_file_path() -> str | None:
    """
    Get absolute path to cookies file if it exists in project root.
    
    Returns:
        Absolute path to COOKIES_FILE if it exists, else None
    """
    cookies_path = Path(COOKIES_FILE)
    if cookies_path.exists() and cookies_path.is_file():
        return str(cookies_path.resolve())
    return None

