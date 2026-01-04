"""Prompt template loading and variable injection logic."""

import re
from pathlib import Path
from core.config import STORY_CORE_PROMPT_PATH, STORY_PROMPT_PATH


def load_prompt_file(path: str) -> str:
    """
    Load prompt file exactly as-is (UTF-8).
    
    Args:
        path: Path to the prompt file
        
    Returns:
        File content as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        Exception: For other read errors
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    
    return file_path.read_text(encoding='utf-8')


def load_template_from_file(path: str) -> str | None:
    """
    Load a prompt template from a file.
    
    Args:
        path: Path to the template file
        
    Returns:
        Template content as string, or None if file doesn't exist or can't be read
    """
    try:
        file_path = Path(path)
        if file_path.exists():
            return file_path.read_text(encoding='utf-8')
        return None
    except Exception:
        return None


def get_default_story_core_template() -> str:
    """Return fallback default STORY_CORE prompt template."""
    return """ORIGINAL_STORY:
{ORIGINAL_STORY}

Створи STORY_CORE на основі цього тексту."""


def get_default_story_template() -> str:
    """Return fallback default STORY prompt template."""
    return """STORY_CORE:
{STORY_CORE}

TARGET_LENGTH_CHARS: {TARGET_LENGTH_CHARS}
CHAR_TOLERANCE: ±100

Створи історію на основі STORY_CORE."""


def inject_subtitles_into_prompt(prompt_text: str, subtitles: str) -> str:
    """
    Inject subtitles into prompt text.
    
    Rules:
    - If {{SUBTITLES}} placeholder exists, replace it with subtitles
    - Otherwise, find ORIGINAL_STORY: block and update it, or append if not found
    - Do not duplicate ORIGINAL_STORY blocks (replace existing one)
    
    Args:
        prompt_text: Current prompt text
        subtitles: Subtitles text to inject
        
    Returns:
        Prompt text with subtitles injected
    """
    if not subtitles or not subtitles.strip():
        return prompt_text
    
    subtitles = subtitles.rstrip()
    
    # First, try to replace {{SUBTITLES}} placeholder
    if "{{SUBTITLES}}" in prompt_text:
        return prompt_text.replace("{{SUBTITLES}}", subtitles)
    
    # Otherwise, handle ORIGINAL_STORY block
    # Check if ORIGINAL_STORY: exists - replace it (don't duplicate)
    if "ORIGINAL_STORY:" in prompt_text:
        # Try to replace existing ORIGINAL_STORY block (from ORIGINAL_STORY: until CORE OBJECTIVE)
        pattern = r'(ORIGINAL_STORY:\s*)(.*?)(\nCORE OBJECTIVE\b)'
        
        def replace_func(match):
            prefix = match.group(1).rstrip()
            suffix = match.group(3).lstrip()
            return f"{prefix}\n{{{subtitles}}}\n\n{suffix}"
        
        result = re.sub(pattern, replace_func, prompt_text, flags=re.MULTILINE | re.DOTALL)
        
        # If replacement happened, return it
        if result != prompt_text:
            return result
        
        # If pattern didn't match (no CORE OBJECTIVE after), try to find and replace any ORIGINAL_STORY: ... block
        # Match ORIGINAL_STORY: followed by content until next major section (all caps) or end
        pattern2 = r'(ORIGINAL_STORY:\s*)(.*?)(?=\n[A-Z][A-Z\s]{3,}:|$)'
        result = re.sub(pattern2, rf"\1\n{{{subtitles}}}\n\n", prompt_text, flags=re.MULTILINE | re.DOTALL)
        if result != prompt_text:
            return result
    
    # If no ORIGINAL_STORY: found, append it before CORE OBJECTIVE if it exists
    if "CORE OBJECTIVE" in prompt_text:
        # Insert before CORE OBJECTIVE
        return re.sub(
            r'(\nCORE OBJECTIVE\b)',
            f"\nORIGINAL_STORY:\n{{{subtitles}}}\n\n\\1",
            prompt_text,
            count=1,
            flags=re.MULTILINE
        )
    
    # If no CORE OBJECTIVE, append at the end
    return f"{prompt_text}\n\nORIGINAL_STORY:\n{{{subtitles}}}"


def inject_story_core_into_prompt(prompt_text: str, story_core: str) -> str:
    """
    Inject STORY_CORE into story prompt text.
    
    Rules:
    - If {{STORY_CORE}} placeholder exists, replace it with story_core
    - Otherwise, find STORY_CORE: block and update it, or insert if not found
    - Do not duplicate STORY_CORE blocks (replace existing one)
    
    Args:
        prompt_text: Current prompt text
        story_core: STORY_CORE text to inject
        
    Returns:
        Prompt text with STORY_CORE injected
    """
    if not story_core or not story_core.strip():
        return prompt_text
    
    story_core = story_core.rstrip()
    
    # First, try to replace {{STORY_CORE}} placeholder
    if "{{STORY_CORE}}" in prompt_text:
        return prompt_text.replace("{{STORY_CORE}}", story_core)
    
    # Otherwise, handle STORY_CORE: block
    # Check if STORY_CORE: exists - replace it (don't duplicate)
    if "STORY_CORE:" in prompt_text:
        # Try to replace existing STORY_CORE block
        # Match STORY_CORE: followed by content until next major section (all caps header) or end
        pattern = r'(STORY_CORE:\s*)(.*?)(?=\n[A-Z][A-Z\s]{3,}:|$)'
        
        def replace_func(match):
            prefix = match.group(1).rstrip()
            return f"{prefix}\n{{{story_core}}}\n\n"
        
        result = re.sub(pattern, replace_func, prompt_text, flags=re.MULTILINE | re.DOTALL)
        if result != prompt_text:
            return result
    
    # If no STORY_CORE: found, insert it after "INPUT VARIABLES" if it exists
    if "INPUT VARIABLES" in prompt_text:
        # Insert after INPUT VARIABLES section
        return re.sub(
            r'(INPUT VARIABLES[^\n]*\n)',
            f"\\1STORY_CORE:\n{{{story_core}}}\n\n",
            prompt_text,
            count=1,
            flags=re.MULTILINE
        )
    
    # If no INPUT VARIABLES, insert at the top
    return f"STORY_CORE:\n{{{story_core}}}\n\n{prompt_text}"


def inject_all_story_variables(prompt_text: str, story_core: str, target_length_chars: int) -> str:
    """
    Inject all story variables (STORY_CORE, TARGET_LENGTH_CHARS) into prompt text.
    
    Rules:
    - Replace {{STORY_CORE}}, {{TARGET_LENGTH_CHARS}} placeholders if present
    - If placeholders are missing, append them under INPUT VARIABLES section
    - Do not duplicate blocks (replace existing ones)
    - Remove any SLIDE_COUNT references (model will choose automatically)
    
    Args:
        prompt_text: Current prompt text
        story_core: STORY_CORE text to inject
        target_length_chars: Target length in characters (int)
        
    Returns:
        Prompt text with all variables injected
    """
    if not prompt_text:
        return prompt_text
    
    result = prompt_text
    
    # Replace {{STORY_CORE}} placeholder
    if "{{STORY_CORE}}" in result:
        if story_core and story_core.strip():
            result = result.replace("{{STORY_CORE}}", story_core.rstrip())
        else:
            result = result.replace("{{STORY_CORE}}", "")
    
    # Replace {{TARGET_LENGTH_CHARS}} placeholder
    if "{{TARGET_LENGTH_CHARS}}" in result:
        result = result.replace("{{TARGET_LENGTH_CHARS}}", str(target_length_chars))
    
    # Remove {{SLIDE_COUNT}} placeholder if present (model will choose automatically)
    if "{{SLIDE_COUNT}}" in result:
        result = result.replace("{{SLIDE_COUNT}}", "")
    
    # If placeholders are not present, handle block-based injection
    # First, handle STORY_CORE block
    if story_core and story_core.strip():
        story_core = story_core.rstrip()
        if "STORY_CORE:" in result:
            # Replace existing STORY_CORE block
            pattern = r'(STORY_CORE:\s*)(.*?)(?=\n[A-Z][A-Z\s]{3,}:|$)'
            def replace_func(match):
                prefix = match.group(1).rstrip()
                return f"{prefix}\n{{{story_core}}}\n\n"
            result = re.sub(pattern, replace_func, result, flags=re.MULTILINE | re.DOTALL)
        elif "{{STORY_CORE}}" not in result:
            # No STORY_CORE block or placeholder found, need to insert
            if "INPUT VARIABLES" in result:
                # Insert after INPUT VARIABLES
                result = re.sub(
                    r'(INPUT VARIABLES[^\n]*\n)',
                    f"\\1STORY_CORE:\n{{{story_core}}}\n\n",
                    result,
                    count=1,
                    flags=re.MULTILINE
                )
            else:
                # Insert at the top
                result = f"STORY_CORE:\n{{{story_core}}}\n\n{result}"
    
    # Handle TARGET_LENGTH_CHARS block
    if "TARGET_LENGTH_CHARS:" in result:
        # Replace existing TARGET_LENGTH_CHARS block
        pattern = r'(TARGET_LENGTH_CHARS:\s*)(.*?)(?=\n[A-Z][A-Z\s]{3,}:|$)'
        def replace_func(match):
            prefix = match.group(1).rstrip()
            return f"{prefix}{target_length_chars}\n\n"
        result = re.sub(pattern, replace_func, result, flags=re.MULTILINE | re.DOTALL)
    elif "{{TARGET_LENGTH_CHARS}}" not in result:
        # No TARGET_LENGTH_CHARS block or placeholder found, need to insert
        if "INPUT VARIABLES" in result:
            # Insert after INPUT VARIABLES (or after STORY_CORE if it exists)
            if "STORY_CORE:" in result:
                result = re.sub(
                    r'(STORY_CORE:\s*\{[^}]*\}\s*\n)',
                    f"\\1TARGET_LENGTH_CHARS: {target_length_chars}\n\n",
                    result,
                    count=1,
                    flags=re.MULTILINE | re.DOTALL
                )
            else:
                result = re.sub(
                    r'(INPUT VARIABLES[^\n]*\n)',
                    f"\\1TARGET_LENGTH_CHARS: {target_length_chars}\n\n",
                    result,
                    count=1,
                    flags=re.MULTILINE
                )
        else:
            # Insert at the top (after STORY_CORE if it exists)
            if result.startswith("STORY_CORE:"):
                result = re.sub(
                    r'(STORY_CORE:\s*\{[^}]*\}\s*\n)',
                    f"\\1TARGET_LENGTH_CHARS: {target_length_chars}\n\n",
                    result,
                    count=1,
                    flags=re.MULTILINE | re.DOTALL
                )
            else:
                result = f"TARGET_LENGTH_CHARS: {target_length_chars}\n\n{result}"
    
    # Remove SLIDE_COUNT block if present (model will choose automatically)
    if "SLIDE_COUNT:" in result:
        pattern = r'(SLIDE_COUNT:\s*)(.*?)(?=\n[A-Z][A-Z\s]{3,}:|$)'
        result = re.sub(pattern, "", result, flags=re.MULTILINE | re.DOTALL)
    
    # Add instruction about automatic slide count selection if not present
    if "Choose the number of slides automatically" not in result and "SLIDE_COUNT" not in result:
        # Try to add instruction after TARGET_LENGTH_CHARS or in GLOBAL HARD RULES section
        if "GLOBAL HARD RULES" in result:
            result = re.sub(
                r'(GLOBAL HARD RULES[^\n]*\n)',
                "\\1\nChoose the number of slides automatically based on TARGET_LENGTH_CHARS.\nAvoid giant blocks; break frequently into short spoken slides.\n\n",
                result,
                count=1,
                flags=re.MULTILINE
            )
        elif "TARGET_LENGTH_CHARS:" in result:
            # Add after TARGET_LENGTH_CHARS
            result = re.sub(
                r'(TARGET_LENGTH_CHARS:\s*\d+\s*\n)',
                "\\1\nNote: Choose the number of slides automatically based on TARGET_LENGTH_CHARS.\nAvoid giant blocks; break frequently into short spoken slides.\n\n",
                result,
                count=1,
                flags=re.MULTILINE
            )
    
    return result


def fill_story_core_prompt(template: str, original_story: str) -> str:
    """
    Fill STORY_CORE prompt template with ORIGINAL_STORY variable.
    
    Replaces the section from "ORIGINAL_STORY:" until "CORE OBJECTIVE" with:
    ORIGINAL_STORY:
    {<original_story>}
    
    CORE OBJECTIVE
    
    Args:
        template: The prompt template
        original_story: The clean subtitles text to inject (will be rstrip'd)
        
    Returns:
        Filled prompt with ORIGINAL_STORY replaced
        
    Raises:
        ValueError: If ORIGINAL_STORY: or CORE OBJECTIVE pattern not found
    """
    if not original_story or not original_story.strip():
        raise ValueError("ORIGINAL_STORY не може бути порожнім")
    
    # Strip trailing whitespace from original_story
    original_story = original_story.rstrip()
    
    # Pattern to match:
    # - Group 1: "ORIGINAL_STORY:" followed by optional whitespace
    # - Group 2: Everything until "CORE OBJECTIVE" (non-greedy, including newlines)
    # - Group 3: "\nCORE OBJECTIVE" (word boundary to ensure exact match)
    pattern = r'(ORIGINAL_STORY:\s*)(.*?)(\nCORE OBJECTIVE\b)'
    
    def replace_func(match):
        prefix = match.group(1).rstrip()  # "ORIGINAL_STORY:" (normalize whitespace)
        # We ignore group 2 (the content to replace)
        suffix = match.group(3).lstrip()  # "CORE OBJECTIVE" (remove leading \n)
        # Replacement: ORIGINAL_STORY:\n{<original_story>}\n\nCORE OBJECTIVE
        return f"{prefix}\n{{{original_story}}}\n\n{suffix}"  # Ensure newline after ORIGINAL_STORY: and empty line before CORE OBJECTIVE
    
    result = re.sub(pattern, replace_func, template, flags=re.MULTILINE | re.DOTALL)
    
    # If no match found, raise clear exception
    if result == template:
        if "ORIGINAL_STORY:" not in template:
            raise ValueError("Шаблон промпту не містить 'ORIGINAL_STORY:'")
        if "CORE OBJECTIVE" not in template:
            raise ValueError("Шаблон промпту не містить 'CORE OBJECTIVE' після 'ORIGINAL_STORY:'")
        raise ValueError("Не вдалося знайти блок ORIGINAL_STORY для заміни. Перевірте формат промпту.")
    
    return result


def fill_story_prompt(template: str, story_core: str, target_chars: int, slide_count: int | None = None) -> str:
    """
    Fill STORY prompt template with STORY_CORE, TARGET_LENGTH_CHARS, and optionally SLIDE_COUNT.
    
    Args:
        template: The prompt template
        story_core: The generated story core text
        target_chars: Target length in characters
        slide_count: Optional slide count (default: None)
        
    Returns:
        Filled prompt with variables replaced
    """
    result = template
    
    # Replace STORY_CORE block
    # Pattern to match "STORY_CORE:" followed by content in braces
    # We want to replace the content inside the braces, keeping the braces
    pattern_story_core = r'(STORY_CORE:\s*\{)[^}]*(})'
    def replace_story_core(match):
        prefix = match.group(1)
        suffix = match.group(2)
        return f"{prefix}{story_core}{suffix}"
    
    result = re.sub(pattern_story_core, replace_story_core, result, flags=re.MULTILINE | re.DOTALL)
    
    # If no match, try simple replacement
    if result == template:
        result = result.replace("{STORY_CORE}", story_core)
    
    # Replace TARGET_LENGTH_CHARS
    # Pattern to match "TARGET_LENGTH_CHARS:" followed by content in braces or just the value
    pattern_target = r'(TARGET_LENGTH_CHARS:\s*)\{[^}]*\}'
    def replace_target(match):
        prefix = match.group(1)
        return f"{prefix}{target_chars}"
    
    result = re.sub(pattern_target, replace_target, result, flags=re.MULTILINE | re.DOTALL)
    
    # If no match, try simple replacement
    if "{TARGET_LENGTH_CHARS}" in result:
        result = result.replace("{TARGET_LENGTH_CHARS}", str(target_chars))
    
    # Replace SLIDE_COUNT if present and slide_count is provided
    if slide_count is not None:
        pattern_slide = r'(SLIDE_COUNT:\s*)\{[^}]*\}'
        def replace_slide(match):
            prefix = match.group(1)
            return f"{prefix}{slide_count}"
        
        result = re.sub(pattern_slide, replace_slide, result, flags=re.MULTILINE | re.DOTALL)
        
        # If no match, try simple replacement
        if "{SLIDE_COUNT}" in result:
            result = result.replace("{SLIDE_COUNT}", str(slide_count))
    
    return result

