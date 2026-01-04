"""Generator functions for YouTube subtitles and story generation."""

from services.youtube_subtitles import fetch_subtitles, extract_video_id
from services.subtitles_cleaner import vtt_to_clean_text
from core.cache import save_to_cache, load_from_cache
from services.prompts import load_prompt_file, fill_story_core_prompt
from services.llm_client import generate_text
from core.config import STORY_CORE_PROMPT_PATH


def fetch_and_clean_subtitles(url: str, lang_mode: str = "auto", prefer_manual: bool = True, use_cache: bool = True) -> tuple[str, str, dict]:
    """
    Fetch and clean YouTube subtitles.
    
    Args:
        url: YouTube video URL
        lang_mode: Language mode ("auto", "en", "uk", "ru")
        prefer_manual: Whether to prefer manual subtitles over auto
        use_cache: Whether to use cache if available
        
    Returns:
        Tuple of (raw_vtt, clean_text, meta_dict)
        meta_dict contains: video_id, source, lang, cookies_used, lang_mode
    """
    # Map lang_mode to langs list
    lang_map = {
        "auto": ["en", "uk", "ru"],
        "en": ["en"],
        "uk": ["uk"],
        "ru": ["ru"]
    }
    langs = lang_map.get(lang_mode, ["en", "uk", "ru"])
    # Extract video ID for cache checking
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Некоректне посилання на YouTube.")
    
    # Check clean_txt cache first (as per requirements)
    if use_cache:
        clean_cached = load_from_cache(video_id, "clean_txt")
        if clean_cached:
            # Also get raw_vtt from cache
            raw_cached = load_from_cache(video_id, "raw_vtt")
            if raw_cached:
                return (
                    raw_cached,
                    clean_cached,
                    {
                        "video_id": video_id,
                        "source": "cache",
                        "lang": "unknown",
                        "cookies_used": False,  # Cache doesn't track cookies usage
                        "lang_mode": lang_mode,
                    }
                )
    
    # Fetch subtitles (will check raw_vtt cache internally)
    result = fetch_subtitles(url, langs=langs, prefer_manual=prefer_manual, use_cache=use_cache)
    
    raw_vtt = result["raw_vtt"]
    video_id = result["video_id"]
    
    # If from cache, try to get clean_txt from cache
    if result["source"] == "cache":
        clean_cached = load_from_cache(video_id, "clean_txt")
        if clean_cached:
            clean_text = clean_cached
            # For cached text, we don't have stats, use current length
            clean_stats = {
                "clean_chars_before_dedupe": len(clean_text),
                "clean_chars_after_dedupe": len(clean_text),
                "dedupe_ratio": 1.0,
                "removed_chars": 0,
            }
        else:
            # Cache miss for clean, need to clean
            clean_text, clean_stats = vtt_to_clean_text(raw_vtt, return_stats=True)
            save_to_cache(video_id, "clean_txt", clean_text)
    else:
        # Not from cache, clean and cache
        clean_text, clean_stats = vtt_to_clean_text(raw_vtt, return_stats=True)
        save_to_cache(video_id, "clean_txt", clean_text)
    
    meta = {
        "video_id": video_id,
        "source": result["source"],
        "lang": result["lang"],
        "cookies_used": result.get("cookies_used", False),
        "lang_mode": lang_mode,
        **clean_stats,  # Add deduplication stats
    }
    
    return raw_vtt, clean_text, meta


def generate_story_core(clean_subtitles: str) -> tuple[str, str]:
    """
    Generate STORY_CORE from clean subtitles.
    
    Steps:
    1. Load prompt from "story_core_prompt.txt"
    2. Inject ORIGINAL_STORY
    3. Call LLM
    4. Return filled_prompt + output
    
    Args:
        clean_subtitles: Clean subtitles text (ORIGINAL_STORY)
        
    Returns:
        Tuple of (filled_prompt, story_core_output)
        
    Raises:
        FileNotFoundError: If prompt file not found
        ValueError: If API key not set
        Exception: For LLM errors
    """
    # Load prompt file (must exist, no fallback)
    prompt_template = load_prompt_file(str(STORY_CORE_PROMPT_PATH))
    
    # Inject ORIGINAL_STORY
    filled_prompt = fill_story_core_prompt(prompt_template, clean_subtitles)
    
    # Call LLM
    story_core_output = generate_text(filled_prompt)
    
    return filled_prompt, story_core_output


def generate_story_stub(prompt: str) -> str:
    """
    Stub function to generate final story from prompt.
    
    Args:
        prompt: Filled story prompt
        
    Returns:
        Empty string (stub implementation)
    """
    # TODO: Implement real LLM call in later stages
    return ""

