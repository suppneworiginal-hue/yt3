"""File caching utilities for subtitles."""

from pathlib import Path
from core.config import CACHE_DIR, ensure_cache_dir


def get_cache_path(video_id: str, kind: str) -> Path:
    """
    Get the cache file path for a video and cache kind.
    
    Args:
        video_id: YouTube video ID
        kind: Cache kind ("raw_vtt" or "clean_txt")
        
    Returns:
        Path to the cache file
    """
    ensure_cache_dir()
    cache_base = Path(CACHE_DIR) / video_id
    cache_base.mkdir(parents=True, exist_ok=True)
    
    if kind == "raw_vtt":
        return cache_base / "raw.vtt"
    elif kind == "clean_txt":
        return cache_base / "clean.txt"
    else:
        raise ValueError(f"Unknown cache kind: {kind}")


def load_from_cache(video_id: str, kind: str) -> str | None:
    """
    Load cached content for a video.
    
    Args:
        video_id: YouTube video ID
        kind: Cache kind ("raw_vtt" or "clean_txt")
        
    Returns:
        Cached content as string, or None if not found
    """
    cache_path = get_cache_path(video_id, kind)
    if cache_path.exists():
        try:
            return cache_path.read_text(encoding='utf-8')
        except Exception:
            return None
    return None


def save_to_cache(video_id: str, kind: str, content: str) -> None:
    """
    Save content to cache.
    
    Args:
        video_id: YouTube video ID
        kind: Cache kind ("raw_vtt" or "clean_txt")
        content: Content to cache
    """
    cache_path = get_cache_path(video_id, kind)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(content, encoding='utf-8')

