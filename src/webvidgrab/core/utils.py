"""Utility functions for PSiteDL."""

from __future__ import annotations

import re
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar
from urllib import parse as urlparse

T = TypeVar("T")


def sanitize_filename(stem: str) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Args:
        stem: The original filename stem
        
    Returns:
        Sanitized filename stem safe for filesystem use
    """
    s = re.sub(r'[\\/:*?"<>|]+', "_", (stem or "").strip())
    s = re.sub(r"\s+", " ", s).strip(" .")
    return s[:180]


def extract_page_title(html: str) -> str | None:
    """
    Extract page title from HTML content.
    
    Tries multiple patterns:
    1. Open Graph meta tag (property="og:title")
    2. Regular <title> tag
    
    Args:
        html: HTML content string
        
    Returns:
        Extracted and sanitized title, or None if not found
    """
    patterns = [
        r'<meta[^>]+property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:title["\']',
        r"<title[^>]*>(.*?)</title>",
    ]
    for p in patterns:
        m = re.search(p, html, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            continue
        title = sanitize_filename(re.sub(r"\s+", " ", (m.group(1) or "").strip()))
        if title:
            return title
    return None


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse.urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator for retrying functions on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        raise e
                    # Exponential backoff
                    import time
                    time.sleep(delay * (2 ** attempt))
            raise last_exception  # Should never reach here
        return wrapper
    return decorator


def rename_with_date_seq(path: Path) -> Path:
    """
    Rename a file by appending date and sequence number.
    
    Format: {stem}_{YYYYMMDD}[_{n}].{suffix}
    
    Args:
        path: Original file path
        
    Returns:
        New file path after renaming
    """
    if not path.exists():
        return path
    
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    date_tag = datetime.now().strftime("%Y%m%d")
    
    candidate = parent / f"{stem}_{date_tag}{suffix}"
    if not candidate.exists():
        path.rename(candidate)
        return candidate
    
    idx = 2
    while True:
        candidate = parent / f"{stem}_{date_tag}_{idx}{suffix}"
        if not candidate.exists():
            path.rename(candidate)
            return candidate
        idx += 1
