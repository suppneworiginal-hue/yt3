"""YouTube subtitle fetching using yt-dlp."""

import re
from pathlib import Path
from typing import Literal
import yt_dlp
from core.config import CACHE_DIR, DEFAULT_LANGS, ensure_cache_dir
from core.cache import load_from_cache, save_to_cache
from core.utils import cookies_file_path


def extract_video_id(url: str) -> str | None:
    """
    Extract YouTube video ID from URL.
    
    Args:
        url: YouTube URL (various formats supported)
        
    Returns:
        Video ID or None if invalid
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_subtitles(url: str, langs: list[str] = None, prefer_manual: bool = True, use_cache: bool = True) -> dict:
    """
    Fetch YouTube subtitles using yt-dlp.
    
    Args:
        url: YouTube video URL
        langs: List of language codes to try (default: DEFAULT_LANGS)
        prefer_manual: Whether to prefer manual subtitles over auto (default: True)
        use_cache: Whether to use cache if available
        
    Returns:
        Dict with keys:
        - video_id: str
        - source: "cache" | "manual" | "auto"
        - lang: str
        - raw_vtt: str
        - cookies_used: bool
        - requested_langs: list[str]
        - available_manual_langs: list[str] (optional)
        - available_auto_langs: list[str] (optional)
        
    Raises:
        ValueError: If URL is invalid or subtitles are not available
        Exception: For other errors (rate limits, etc.)
    """
    if langs is None:
        langs = DEFAULT_LANGS
    
    # Extract video ID
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Некоректне посилання на YouTube.")
    
    # Check if cookies file exists
    cookies_path = cookies_file_path()
    cookies_used = cookies_path is not None
    
    # Check cache: first try clean_txt (if both clean and raw exist, we can use cache)
    if use_cache:
        clean_cached = load_from_cache(video_id, "clean_txt")
        raw_cached = load_from_cache(video_id, "raw_vtt")
        if clean_cached and raw_cached:
            # Both exist, use cache
            return {
                "video_id": video_id,
                "source": "cache",
                "lang": "unknown",  # Cache doesn't store lang
                "raw_vtt": raw_cached,
                "cookies_used": False,  # Cache doesn't track cookies usage
                "requested_langs": langs,
                "available_manual_langs": [],
                "available_auto_langs": [],
            }
        elif raw_cached:
            # Only raw exists, can still use it
            return {
                "video_id": video_id,
                "source": "cache",
                "lang": "unknown",
                "raw_vtt": raw_cached,
                "cookies_used": False,  # Cache doesn't track cookies usage
                "requested_langs": langs,
                "available_manual_langs": [],
                "available_auto_langs": [],
            }
    
    # Fetch from YouTube
    ensure_cache_dir()
    temp_dir = Path(CACHE_DIR) / video_id / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # First, extract info to check available subtitles
    info_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    # Add cookies if available
    if cookies_path:
        info_opts['cookiefile'] = cookies_path
    
    try:
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Check for manual subtitles
            subtitles = info.get('subtitles', {})
            auto_captions = info.get('automatic_captions', {})
            
            # Extract available languages
            available_manual_langs = list(subtitles.keys()) if subtitles else []
            available_auto_langs = list(auto_captions.keys()) if auto_captions else []
            
            selected_lang = None
            source: Literal["manual", "auto"] = "manual"
            
            # Selection logic based on prefer_manual
            if prefer_manual:
                # Try manual subtitles first
                for lang in langs:
                    if lang in subtitles:
                        selected_lang = lang
                        source = "manual"
                        break
                
                # If no manual, try auto captions
                if not selected_lang:
                    for lang in langs:
                        if lang in auto_captions:
                            selected_lang = lang
                            source = "auto"
                            break
            else:
                # Try auto captions first
                for lang in langs:
                    if lang in auto_captions:
                        selected_lang = lang
                        source = "auto"
                        break
                
                # If no auto, try manual subtitles
                if not selected_lang:
                    for lang in langs:
                        if lang in subtitles:
                            selected_lang = lang
                            source = "manual"
                            break
            
            if not selected_lang:
                raise ValueError("Субтитри недоступні для цього відео.")
            
            # Download the subtitle
            ydl_opts = {
                'writesubtitles': (source == "manual"),
                'writeautomaticsub': (source == "auto"),
                'subtitleslangs': [selected_lang],
                'subtitlesformat': 'vtt',
                'skip_download': True,
                'outtmpl': str(temp_dir / '%(id)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }
            
            # Add cookies if available
            if cookies_path:
                ydl_opts['cookiefile'] = cookies_path
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                ydl_download.download([url])
            
            # Find the downloaded VTT file
            vtt_files = list(temp_dir.glob("*.vtt"))
            if not vtt_files:
                raise ValueError("Не вдалося завантажити субтитри.")
            
            raw_vtt = vtt_files[0].read_text(encoding='utf-8')
            
            # Cache the raw VTT
            save_to_cache(video_id, "raw_vtt", raw_vtt)
            
            return {
                "video_id": video_id,
                "source": source,
                "lang": selected_lang,
                "raw_vtt": raw_vtt,
                "cookies_used": cookies_used,
                "requested_langs": langs,
                "available_manual_langs": available_manual_langs,
                "available_auto_langs": available_auto_langs,
            }
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "429" in error_msg or "rate limit" in error_msg.lower():
            raise Exception("YouTube тимчасово блокує запити (429). Спробуй пізніше або використай кеш.")
        elif "subtitles" in error_msg.lower() or "caption" in error_msg.lower():
            raise ValueError("Субтитри недоступні для цього відео.")
        else:
            raise Exception(f"Помилка завантаження: {error_msg}")
    except Exception as e:
        if isinstance(e, (ValueError, Exception)) and not isinstance(e, yt_dlp.utils.DownloadError):
            raise
        raise Exception(f"Помилка: {str(e)}")

