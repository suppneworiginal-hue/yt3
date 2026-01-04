"""Subtitle cleaning utilities."""

import re
from core.config import MAX_SUBTITLE_CHARS


def normalize_token(token: str) -> str:
    """
    Normalize a token for comparison (lowercase, strip punctuation).
    
    Args:
        token: Input token
        
    Returns:
        Normalized token
    """
    # Lowercase
    normalized = token.lower()
    
    # Strip punctuation at ends: .,!?;:()[]{}\"'"
    # Keep inner apostrophes (e.g., "don't" -> "don't")
    normalized = re.sub(r'^[.,!?;:()\[\]{}"\'"]+', '', normalized)
    normalized = re.sub(r'[.,!?;:()\[\]{}"\'"]+$', '', normalized)
    
    # Collapse weird unicode quotes to normal (optional but helpful)
    normalized = normalized.replace('"', '"').replace('"', '"')
    normalized = normalized.replace(''', "'").replace(''', "'")
    
    return normalized


def collapse_consecutive_repeated_phrases(text: str) -> str:
    """
    Remove consecutive repeated phrases using variable period detection.
    
    Algorithm:
    - Tokenize text into words
    - Normalize tokens (lowercase, strip punctuation)
    - Check for consecutive repeats using variable period lengths (18 down to 3)
    - Remove consecutive duplicates while preserving non-consecutive repeats
    
    Args:
        text: Input text
        
    Returns:
        Text with consecutive repeated phrases collapsed
    """
    if not text:
        return text
    
    # Normalize spaces
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Tokenize into words
    tokens = text.split()
    
    if len(tokens) < 6:  # Too short to have meaningful repeats
        return text
    
    # Build normalized tokens for comparison
    norm_tokens = [normalize_token(t) for t in tokens]
    
    # Check for consecutive repeats using variable period lengths
    # Start from larger periods and work down (18..3)
    for period in range(18, 2, -1):  # 18 down to 3
        if period > len(tokens) // 2:  # Period too large for text
            continue
        
        i = 0
        while i + 2 * period <= len(tokens):
            # Check if normalized tokens match at this period
            if norm_tokens[i:i+period] == norm_tokens[i+period:i+2*period]:
                # Found a repeat! Count how many times it repeats
                j = i + period
                while (j + period <= len(tokens) and 
                       norm_tokens[j:j+period] == norm_tokens[i:i+period]):
                    j += period
                
                # Keep first block, delete the rest
                del tokens[i+period:j]
                del norm_tokens[i+period:j]
                # Re-check same i (might still repeat after deletion)
                continue
            
            i += 1
    
    # Join tokens back with single spaces
    result = ' '.join(tokens)
    
    # Normalize any remaining whitespace issues
    result = re.sub(r' +', ' ', result)
    
    return result


def vtt_to_clean_text(vtt: str, return_stats: bool = False) -> tuple[str, dict] | str:
    """
    Convert VTT subtitle format to clean text.
    
    Rules:
    - Remove WEBVTT headers, timestamps, cue numbers, metadata lines
    - Remove HTML tags like <c>, <i>, </i>, etc
    - Replace multiple spaces/newlines with single spaces/newlines appropriately
    - Preserve sentence flow; join lines that are broken mid-sentence
    - Strip leading/trailing whitespace
    - Cap length to MAX_SUBTITLE_CHARS (truncate safely at boundary)
    
    Args:
        vtt: Raw VTT subtitle content
        return_stats: If True, return tuple of (text, stats_dict)
        
    Returns:
        Clean text, or tuple of (clean text, stats_dict) if return_stats=True
    """
    if not vtt:
        return ""
    
    lines = vtt.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Skip WEBVTT header
        if line.strip().startswith('WEBVTT'):
            continue
        
        # Skip empty lines (we'll handle spacing later)
        if not line.strip():
            continue
        
        # Skip timestamp lines (format: 00:00:00.000 --> 00:00:00.000)
        if re.match(r'^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}', line):
            continue
        
        # Skip cue numbers (standalone numbers)
        if re.match(r'^\d+$', line.strip()):
            continue
        
        # Skip metadata lines (NOTE, STYLE, etc.)
        if line.strip().startswith('NOTE') or line.strip().startswith('STYLE'):
            continue
        
        # Remove HTML tags
        line = re.sub(r'<[^>]+>', '', line)
        
        # Remove cue settings (like position, align, etc.)
        line = re.sub(r'^\S+:\s*', '', line)
        
        # Clean up the line
        line = line.strip()
        
        if line:
            cleaned_lines.append(line)
    
    # Deduplication: Remove consecutive duplicate lines (case-insensitive)
    deduplicated_lines = []
    prev_line_normalized = None
    repeat_count = 0
    
    for line in cleaned_lines:
        if not line:
            continue
        
        line_normalized = line.strip().lower()
        
        # Check if identical to previous line (case-insensitive)
        if line_normalized == prev_line_normalized:
            repeat_count += 1
            # Collapse "runaway repetition": if same line repeats more than 2 times, keep max 2
            if repeat_count > 2:
                continue  # Skip third+ occurrence
            # Keep first and second occurrence (repeat_count 1 means second occurrence)
            deduplicated_lines.append(line)
        else:
            # New line, reset counter and update previous
            repeat_count = 0
            prev_line_normalized = line_normalized
            deduplicated_lines.append(line)
    
    # Join lines intelligently
    # If a line doesn't end with punctuation, it's likely a continuation
    result_parts = []
    for i, line in enumerate(deduplicated_lines):
        if not line:
            continue
        
        # If previous line doesn't end with sentence-ending punctuation, join with space
        if result_parts and not re.search(r'[.!?]\s*$', result_parts[-1]):
            result_parts[-1] += " " + line
        else:
            result_parts.append(line)
    
    # Join all parts with newlines (sentence boundaries)
    result = '\n'.join(result_parts)
    
    # Normalize whitespace: multiple spaces to single space
    result = re.sub(r' +', ' ', result)
    
    # Normalize newlines: multiple newlines to single newline
    result = re.sub(r'\n\s*\n+', '\n', result)
    
    # Remove exact duplicate paragraphs (consecutive only)
    # Split into sentences/chunks by sentence endings
    chunks = re.split(r'([.!?]\s+)', result)
    # Recombine chunks with their separators
    sentences = []
    for i in range(0, len(chunks), 2):
        if i < len(chunks):
            sentence = chunks[i]
            if i + 1 < len(chunks):
                sentence += chunks[i + 1]
            sentences.append(sentence)
    
    # Remove consecutive duplicate sentences
    deduplicated_sentences = []
    prev_sentence = None
    for sentence in sentences:
        sentence_normalized = sentence.strip().lower()
        if sentence_normalized and sentence_normalized != prev_sentence:
            deduplicated_sentences.append(sentence)
            prev_sentence = sentence_normalized
    
    result = ''.join(deduplicated_sentences)
    
    # Strip leading/trailing whitespace
    result = result.strip()
    
    # Track stats before phrase deduplication
    clean_chars_before_dedupe = len(result)
    
    # Apply phrase-level deduplication
    result = collapse_consecutive_repeated_phrases(result)
    
    # Fallback: if result is empty but vtt contains visible lines, extract visible text
    if not result and vtt:
        # Try to extract any visible text that might have been missed
        fallback_lines = []
        for line in lines:
            line = line.strip()
            # Skip timestamps, headers, metadata
            if not line or line.startswith('WEBVTT') or line.startswith('NOTE') or line.startswith('STYLE'):
                continue
            if re.match(r'^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}', line):
                continue
            if re.match(r'^\d+$', line):
                continue
            # Remove HTML tags
            line = re.sub(r'<[^>]+>', '', line)
            line = line.strip()
            if line and len(line) > 2:  # Only keep substantial lines
                fallback_lines.append(line)
        
        if fallback_lines:
            result = ' '.join(fallback_lines)
            # Normalize spaces
            result = re.sub(r' +', ' ', result).strip()
            # Re-apply deduplication to fallback result
            result = collapse_consecutive_repeated_phrases(result)
    
    # Cap length safely
    if len(result) > MAX_SUBTITLE_CHARS:
        # Truncate at sentence boundary if possible
        truncated = result[:MAX_SUBTITLE_CHARS]
        # Try to find last sentence boundary
        last_period = truncated.rfind('.')
        last_exclamation = truncated.rfind('!')
        last_question = truncated.rfind('?')
        last_newline = truncated.rfind('\n')
        
        boundary = max(last_period, last_exclamation, last_question, last_newline)
        if boundary > MAX_SUBTITLE_CHARS * 0.8:  # Only if we're not losing too much
            result = truncated[:boundary + 1]
        else:
            result = truncated
    
    if return_stats:
        clean_chars_after_dedupe = len(result)
        removed_chars = clean_chars_before_dedupe - clean_chars_after_dedupe
        dedupe_ratio = clean_chars_after_dedupe / clean_chars_before_dedupe if clean_chars_before_dedupe > 0 else 1.0
        
        return result, {
            "clean_chars_before_dedupe": clean_chars_before_dedupe,
            "clean_chars_after_dedupe": clean_chars_after_dedupe,
            "dedupe_ratio": dedupe_ratio,
            "removed_chars": removed_chars,
        }
    
    return result

