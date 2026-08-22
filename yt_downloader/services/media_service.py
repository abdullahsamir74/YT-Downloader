"""
Media service for high-level URL inspection, validation, and stream discovery.
"""

import re
from typing import Optional, Union, Tuple
from yt_downloader.core.models import MediaItem, PlaylistInfo
from yt_downloader.infrastructure.ytdlp_engine import YtDlpEngine


class MediaService:
    """Provides high-level video & playlist parsing with URL type detection."""

    def __init__(self, engine: Optional[YtDlpEngine] = None):
        self.engine = engine or YtDlpEngine()

    @staticmethod
    def is_playlist_url(url: str) -> bool:
        """Check if URL points to a playlist or video-in-playlist."""
        u = url.lower()
        return "list=" in u or "/playlist" in u

    @staticmethod
    def clean_url(url: str) -> str:
        """Strip surrounding spaces and basic shell characters."""
        return url.strip().strip("'\"<>")

    def inspect_url(self, url: str) -> Tuple[str, Optional[Union[MediaItem, PlaylistInfo]]]:
        """
        Inspect URL and return (type_str, entity).
        type_str is 'playlist', 'video', or 'unknown'.
        """
        clean = self.clean_url(url)
        if not clean:
            return ("unknown", None)

        if self.is_playlist_url(clean):
            try:
                info = self.engine.fetch_playlist_info(clean)
                if info and info.entries:
                    return ("playlist", info)
            except Exception:
                pass

        try:
            item = self.engine.fetch_media_info(clean)
            if item:
                return ("video", item)
        except Exception:
            pass

        return ("unknown", None)

    def fetch_video(self, url: str) -> Optional[MediaItem]:
        return self.engine.fetch_media_info(self.clean_url(url))

    def fetch_playlist(self, url: str) -> Optional[PlaylistInfo]:
        return self.engine.fetch_playlist_info(self.clean_url(url))
