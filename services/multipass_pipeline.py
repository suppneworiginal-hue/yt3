"""Multi-PASS AI-controlled story generation pipeline."""

import json
import re
from services.llm_backends import generate_text


def extract_json_from_text(text: str) -> str:
    """
    Extract the first complete JSON object or array from text.
    
    Args:
        text: Text potentially containing JSON
        
    Returns:
        Extracted JSON string
        
    Raises:
        ValueError: If no valid JSON found
    """
    # Strip code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    
    # Find first { or [
    json_start = -1
    start_char = None
    for i, char in enumerate(cleaned):
        if char in ['{', '[']:
            json_start = i
            start_char = char
            break
    
    if json_start == -1:
        raise ValueError("No JSON object/array found in text")
    
    # Extract complete JSON by matching braces/brackets
    brace_depth = 0
    bracket_depth = 0
    in_string = False
    escape_next = False
    
    for i in range(json_start, len(cleaned)):
        char = cleaned[i]
        
        # Handle string escaping
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        
        # Track strings (don't count braces inside strings)
        if char == '"':
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        # Track braces and brackets
        if char == '{':
            brace_depth += 1
        elif char == '}':
            brace_depth -= 1
        elif char == '[':
            bracket_depth += 1
        elif char == ']':
            bracket_depth -= 1
        
        # Check if we've closed the starting structure
        if start_char == '{' and brace_depth == 0:
            return cleaned[json_start:i+1]
        elif start_char == '[' and bracket_depth == 0:
            return cleaned[json_start:i+1]
    
    # If we get here, no complete JSON found
    raise ValueError("Incomplete JSON in text")


def llm_json(prompt: str, backend: str = "openai") -> dict:
    """
    Call LLM expecting JSON output with automatic repair.
    
    Args:
        prompt: The prompt requesting JSON output
        backend: LLM backend to use
        
    Returns:
        Parsed JSON dict or list
        
    Raises:
        Exception: If JSON cannot be parsed after repair attempt
    """
    response = generate_text(prompt, backend=backend)
    
    # Try to parse JSON
    try:
        json_text = extract_json_from_text(response)
        return json.loads(json_text)
        
    except (json.JSONDecodeError, ValueError) as e:
        # Attempt repair with AI
        repair_prompt = f"""The following text should be valid JSON but has errors. Fix it and output ONLY valid JSON, nothing else.

TEXT TO REPAIR:
{response}

OUTPUT REQUIREMENTS:
- Valid JSON only
- No explanations
- No markdown
- No code fences"""
        
        repaired_response = generate_text(repair_prompt, backend=backend)
        
        # Try parsing again with improved extraction
        try:
            json_text = extract_json_from_text(repaired_response)
            return json.loads(json_text)
        except (json.JSONDecodeError, ValueError) as repair_error:
            raise Exception(f"JSON parsing failed even after repair. Original: {str(e)}, Repair: {str(repair_error)}")


def run_multipass(clean_subtitles: str, target_chars: int = None, slides_hint: int = None, backend: str = "openai") -> dict:
    """
    Run Multi-PASS AI-controlled story generation pipeline.
    
    Args:
        clean_subtitles: Cleaned subtitle text (ORIGINAL_STORY)
        target_chars: Target character count (optional)
        slides_hint: Hint for number of slides (optional)
        backend: LLM backend to use
        
    Returns:
        Dict with all PASS outputs:
        {
            "pass0_analysis": {...},
            "story_core": {...},
            "beats_json": [...],
            "story_slides": [{"Text":"{...}","Prompt":"{...}"}],
            "quality_report": {...}
        }
    """
    results = {}
    
    # PASS 0: AI Analyzer
    pass0_prompt = f"""You are a YouTube Story Analyzer.

INPUT:
Clean subtitles from a YouTube video (ORIGINAL_STORY):
{clean_subtitles[:10000]}

{f"TARGET CHARACTER COUNT: {target_chars}" if target_chars else ""}

TASK:
Analyze this story and provide recommendations for optimal slide structure.

OUTPUT (JSON only, no explanations, no markdown):
{{
    "avg_wpm_guess": number,
    "pacing_risk": "low|medium|high",
    "recommended_slide_sec": number (typically 45-75, around 1 minute per slide),
    "recommended_slide_count": integer,
    "target_chars_per_slide": integer (computed from TARGET/slide_count),
    "tone_target": "neutral|intimate|cold|energetic",
    "notes": "string"
}}

DO NOT include anything outside JSON. No markdown."""
    
    pass0_result = llm_json(pass0_prompt, backend=backend)
    
    # Type check
    if not isinstance(pass0_result, dict):
        raise ValueError(f"PASS0 must return dict, got {type(pass0_result)}")
    
    results["pass0_analysis"] = pass0_result
    
    # PASS 1: AI Story Core Controller
    pass1_prompt = f"""You are a Story Core Architect for YouTube retention.

INPUT:
{clean_subtitles[:10000]}

PASS0 ANALYSIS:
{json.dumps(pass0_result, indent=2)}

TASK:
Extract the core conflict and structure that will drive retention.

OUTPUT (JSON only, no explanations, no markdown):
{{
    "core_conflict": "string",
    "promise_to_viewer": "string",
    "stakes": "string",
    "hidden_reveal": "string",
    "twist_timing": "early|mid|late",
    "ending_payoff": "string"
}}

DO NOT include anything outside JSON. No markdown."""
    
    pass1_result = llm_json(pass1_prompt, backend=backend)
    
    # Type check
    if not isinstance(pass1_result, dict):
        raise ValueError(f"PASS1 must return dict, got {type(pass1_result)}")
    
    results["story_core"] = pass1_result
    
    # PASS 2: AI Beat Architect
    slide_count = pass0_result.get("recommended_slide_count", slides_hint or 10)
    
    pass2_prompt = f"""You are a Beat Architect for YouTube storytelling.

STORY CORE:
{json.dumps(pass1_result, indent=2)}

PASS0 RECOMMENDATIONS:
{json.dumps(pass0_result, indent=2)}

TARGET SLIDE COUNT: {slide_count}

TASK:
Design beat-by-beat structure for each slide.

OUTPUT (JSON array only, no markdown):
[
    {{
        "slide": 1,
        "beat_goal": "string",
        "pressure": "string",
        "reveal": "string",
        "viewer_question": "string",
        "physical_anchor": "string"
    }},
    ...
]

DO NOT include anything outside JSON. No markdown."""
    
    pass2_result = llm_json(pass2_prompt, backend=backend)
    
    # Type check
    if not isinstance(pass2_result, list):
        raise ValueError(f"PASS2 must return list, got {type(pass2_result)}")
    
    results["beats_json"] = pass2_result
    
    # PASS 3: AI Narration Controller
    pass3_prompt = f"""You are a Narration Controller for YouTube stories.

STORY CORE:
{json.dumps(pass1_result, indent=2)}

BEATS:
{json.dumps(pass2_result, indent=2)}

TARGET CHARACTER COUNT: {target_chars if target_chars else "flexible"}
TONE: {pass0_result.get("tone_target", "neutral")}

TASK:
Write the actual narrative for each slide following the beats.

CRITICAL REQUIREMENTS:
- Output MUST be a JSON array
- Each slide MUST have exactly: {{"Text":"{{...}}","Prompt":"{{...}}"}}
- Text: The spoken narration (wrapped in braces {{ }})
- Prompt: Voice style instructions for TTS (wrapped in braces {{ }}, rich but concise)
- Stay close to target character count ±10%
- Use conversational, first-person POV where appropriate
- Show don't tell, no moralizing

FORMAT RULES:
- Text and Prompt MUST include braces {{ }}
- DO NOT include anything outside JSON
- No markdown
- No explanations

OUTPUT (JSON array only):
[
    {{"Text":"{{Your narration here}}","Prompt":"{{Voice delivery style}}"}},
    {{"Text":"{{Slide 2 narration}}","Prompt":"{{Voice style 2}}"}},
    ...
]

DO NOT include anything outside JSON. No markdown."""
    
    pass3_result = llm_json(pass3_prompt, backend=backend)
    
    # Type check
    if not isinstance(pass3_result, list):
        raise ValueError(f"PASS3 must return list, got {type(pass3_result)}")
    
    # Validate each slide has Text and Prompt
    for i, slide in enumerate(pass3_result):
        if not isinstance(slide, dict):
            raise ValueError(f"PASS3 slide {i+1} must be dict, got {type(slide)}")
        if "Text" not in slide or "Prompt" not in slide:
            raise ValueError(f"PASS3 slide {i+1} missing Text or Prompt keys")
    
    results["story_slides"] = pass3_result
    
    # PASS 5: AI Quality Judge + Repair
    pass5_prompt = f"""You are a Quality Judge for YouTube stories.

GENERATED SLIDES:
{json.dumps(pass3_result, indent=2)}

STORY CORE:
{json.dumps(pass1_result, indent=2)}

TASK:
Evaluate the generated slides and identify issues. Repair if needed.

EVALUATION CRITERIA:
- Hook strength (slides 1-2)
- Retention chain (unresolved loops)
- Pacing consistency
- POV consistency
- Repetition or filler
- Ending impact

OUTPUT (JSON only, no markdown):
{{
    "status": "pass|fail",
    "issues": [
        {{"slide": integer, "problem": "string", "fix": "string"}}
    ],
    "repaired_slides": [
        {{"slide": integer, "Text": "{{...}}", "Prompt": "{{...}}"}}
    ]
}}

If status is "pass", repaired_slides can be empty.
If status is "fail", provide repaired versions of problematic slides only.

DO NOT include anything outside JSON. No markdown."""
    
    pass5_result = llm_json(pass5_prompt, backend=backend)
    
    # Type check
    if not isinstance(pass5_result, dict):
        raise ValueError(f"PASS5 must return dict, got {type(pass5_result)}")
    
    results["quality_report"] = pass5_result
    
    # Apply repairs if any
    if pass5_result.get("status") == "fail" and pass5_result.get("repaired_slides"):
        # Replace repaired slides in the original array
        slides = results["story_slides"]
        for repaired in pass5_result["repaired_slides"]:
            slide_num = repaired.get("slide")
            if slide_num and 0 < slide_num <= len(slides):
                slides[slide_num - 1] = {
                    "Text": repaired.get("Text", ""),
                    "Prompt": repaired.get("Prompt", "")
                }
        results["story_slides"] = slides
    
    return results

