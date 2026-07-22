"""
Data models for YouTube Downloader.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class VideoInfo:
    id: str
    title: str
    uploader: str
    duration_str: str
    view_count: int
    url: str


@dataclass
class PlaylistItem:
    index: int
    id: str
    title: str
    duration_str: str
    url: str


@dataclass
class PlaylistInfo:
    id: str
    title: str
    uploader: str
    entries: List[PlaylistItem] = field(default_factory=list)
    url: str = ""


@dataclass
class DownloadOpts:
    quality: str = "1080p"
    audio_only: bool = False
    audio_format: str = "mp3"
    audio_bitrate: str = "192"
    subtitles: str = "embed"  # embed, separate, none
    output_dir: Path = field(default_factory=lambda: Path("downloads"))


@dataclass
class BatchItem:
    video_file: Path
    subtitle_file: Optional[Path]
    status: str = "ready"  # ready, missing_sub, done, error
    error: Optional[str] = None
