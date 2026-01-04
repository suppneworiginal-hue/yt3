"""LLM client for text generation (backward compatibility wrapper)."""

# Import from backends module
from services.llm_backends import generate_text

# Re-export for backward compatibility
__all__ = ['generate_text']

