"""Video stream detector - finds video URLs from webpage content."""

from __future__ import annotations

import re
from typing import Callable
from urllib import parse as urlparse

from .utils import sanitize_filename, extract_page_title


class VideoDetector:
    """Detects video stream URLs from webpage content."""
    
    def __init__(self, log_func: Callable[[str], None] | None = None):
        """
        Initialize detector.
        
        Args:
            log_func: Optional logging function
        """
        self.log_func = log_func or (lambda x: None)
    
    def fetch_html(self, url: str, referer: str | None = None) -> str:
        """
        Fetch HTML content from URL.
        
        Args:
            url: Webpage URL
            referer: Optional referer header
            
        Returns:
            HTML content as string
        """
        from urllib import request as urlrequest
        
        DEFAULT_UA = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        
        headers = {"User-Agent": DEFAULT_UA, "Accept": "*/*"}
        if referer:
            headers["Referer"] = referer
            
        req = urlrequest.Request(url, headers=headers)
        with urlrequest.urlopen(req, timeout=25) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="ignore")
    
    def extract_candidates(self, html: str, base_url: str) -> list[str]:
        """
        Extract potential video URLs from HTML content.
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative paths
            
        Returns:
            List of candidate video URLs, sorted by score (descending)
        """
        patterns = [
            r"""https?://[^\s"'<>\\]+""",
            r"""https?:\\/\\/[^\s"'<>\\]+""",
            r"""["']([^"'<>]+(?:\.m3u8|\.mpd|\.mp4|\.webm|\.m4s|\.ts)(?:\?[^"'<>]*)?)["']""",
        ]
        
        urls: list[str] = []
        for p in patterns:
            for raw in re.findall(p, html, flags=re.IGNORECASE):
                item = str(raw).strip().strip("\"'").replace("\\/", "/")
                if item.startswith("//"):
                    item = "https:" + item
                item = urlparse.urljoin(base_url, item)
                low = item.lower()
                if not low.startswith(("http://", "https://")):
                    continue
                if any(k in low for k in (".m3u8", ".mpd", ".mp4", ".webm", ".m4s", ".ts", "manifest", "playlist")):
                    urls.append(item)
        
        # De-duplicate and sort by score
        dedup = list(dict.fromkeys(urls))
        dedup.sort(key=self._candidate_score, reverse=True)
        return dedup
    
    def _candidate_score(self, url: str) -> int:
        """
        Score a video URL candidate based on quality indicators.
        
        Args:
            url: Video URL
            
        Returns:
            Score (higher = better quality)
        """
        low = url.lower()
        score = 0
        
        # File type scoring
        if ".m3u8" in low:
            score += 200
        if ".mpd" in low:
            score += 180
        if ".mp4" in low or ".webm" in low:
            score += 100
        
        # Resolution scoring
        for k in ("2160", "1440", "1080", "720", "480", "360"):
            if k in low:
                score += int(k)
                break
        
        # Manifest/playlist bonus
        if any(k in low for k in ("master", "manifest", "playlist", "index")):
            score += 30
        
        return score
    
    def probe_height(self, url: str, referer: str, log_lines: list[str]) -> int:
        """
        Probe video stream to get resolution information.
        
        Args:
            url: Video stream URL
            referer: Referer header
            log_lines: List to append log messages
            
        Returns:
            Best resolution height found, or 0 if probing failed
        """
        import subprocess
        
        ytdlp_cmd = self._resolve_ytdlp_cmd()
        if not ytdlp_cmd:
            return 0
        
        cmd = [
            *ytdlp_cmd,
            "--add-header", f"Referer:{referer}",
            "--add-header", "User-Agent: Mozilla/5.0",
            "--list-formats",
            url
        ]
        
        proc = subprocess.run(cmd, capture_output=True, text=True)
        log_lines.append(f"[probe-candidate] {url}")
        log_lines.append(f"[probe-candidate-exit] {proc.returncode}")
        log_lines.append(proc.stdout or "")
        log_lines.append(proc.stderr or "")
        
        best = 0
        for line in (proc.stdout or "").splitlines():
            m = re.search(r"\b(\d{3,4})p\b", line.lower())
            if m:
                best = max(best, int(m.group(1)))
                continue
            m = re.search(r"\b(\d{2,4})x(\d{2,4})\b", line.lower())
            if m:
                best = max(best, int(m.group(2)))
        
        return best
    
    def _resolve_ytdlp_cmd(self) -> list[str] | None:
        """Resolve yt-dlp command path."""
        import shutil
        import subprocess
        import sys
        from pathlib import Path
        
        exe = shutil.which("yt-dlp")
        if exe:
            return [exe]
        
        # Try as module
        check = subprocess.run(
            [sys.executable, "-c", "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('yt_dlp') else 1)"]
        )
        if check.returncode == 0:
            return [sys.executable, "-m", "yt_dlp"]
        
        return None
    
    def detect(self, page_url: str) -> tuple[str | None, int, str | None]:
        """
        Detect best video stream from webpage.
        
        Args:
            page_url: Webpage URL
            
        Returns:
            Tuple of (best_video_url, candidate_count, page_title)
        """
        self.log_func(f"[url] {page_url}")
        
        # Fetch and parse HTML
        html = self.fetch_html(page_url, referer=page_url)
        page_title = extract_page_title(html)
        self.log_func(f"[page-title] {page_title or '(none)'}")
        
        # Extract candidates
        candidates = self.extract_candidates(html, page_url)
        self.log_func(f"[html-candidates] {len(candidates)}")
        
        # Find best candidate
        best_url = None
        best_score = -1
        
        for c in candidates[:20]:
            score = self._candidate_score(c)
            if score > best_score:
                best_score = score
                best_url = c
        
        return best_url, len(candidates), page_title
