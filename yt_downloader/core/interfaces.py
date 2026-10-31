"""
Interface protocols for YT-Downloader Clean Architecture.
"""

import threading
from pathlib import Path
from typing import Callable, List, Optional, Protocol

from yt_downloader.core.models import (
    AppConfig,
    BatchItem,
    DownloadTask,
    HistoryRecord,
    MediaItem,
    PlaylistInfo,
    TaskProgress,
)


class IDownloadEngine(Protocol):
    """Protocol for underlying download engines (yt-dlp)."""

    def fetch_media_info(self, url: str) -> Optional[MediaItem]:
        """Fetch metadata for a single video or audio stream."""
        ...

    def fetch_playlist_info(self, url: str) -> Optional[PlaylistInfo]:
        """Fetch metadata and item list for a playlist."""
        ...

    def download_stream(
        self,
        task: DownloadTask,
        progress_callback: Optional[Callable[[TaskProgress], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Path:
        """Download media according to task configuration. Returns final file path."""
        ...


class ISubtitleEngine(Protocol):
    """Protocol for subtitle extraction, detection, and embedding."""

    @property
    def is_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is installed and accessible."""
        ...

    def find_matching_subtitle(self, video_path: Path) -> Optional[Path]:
        """Find corresponding subtitle file (.srt, .vtt, .ass) for a video file."""
        ...

    def embed_subtitle(
        self,
        video_path: Path,
        subtitle_path: Optional[Path] = None,
        language: str = "eng",
    ) -> bool:
        """Embed subtitles into video container using FFmpeg."""
        ...

    def scan_directory_for_pairs(self, directory: Path) -> List[BatchItem]:
        """Scan a folder and pair video files with subtitle candidates."""
        ...


class IHistoryRepository(Protocol):
    """Protocol for storing and retrieving download history."""

    def add_record(self, record: HistoryRecord) -> None: ...

    def list_records(self) -> List[HistoryRecord]: ...

    def delete_record(self, record_id: str) -> bool: ...

    def clear_all(self) -> None: ...


class ISettingsRepository(Protocol):
    """Protocol for reading and persisting user preferences."""

    def load_config(self) -> AppConfig: ...

    def save_config(self, config: AppConfig) -> None: ...
