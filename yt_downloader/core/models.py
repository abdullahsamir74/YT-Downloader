"""
Strongly typed domain models for YT-Downloader.
"""

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from yt_downloader.core.enums import (
    AudioBitrate,
    AudioFormat,
    QualityPreset,
    SubtitleMode,
    TaskStatus,
    ThemeName,
)


def format_seconds(seconds: Optional[float | int]) -> str:
    """Format numeric seconds into HH:MM:SS or MM:SS."""
    if not seconds or seconds <= 0:
        return "00:00"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"


def format_bytes(num_bytes: Optional[float | int]) -> str:
    """Format byte count into human readable units (B, KB, MB, GB)."""
    if not num_bytes or num_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    val = float(num_bytes)
    while val >= 1024 and i < len(units) - 1:
        val /= 1024
        i += 1
    return f"{val:.1f} {units[i]}" if i > 0 else f"{int(val)} B"


@dataclass
class StreamInfo:
    """Metadata about a single audio or video stream."""

    format_id: str
    resolution: str
    ext: str
    vcodec: str = "none"
    acodec: str = "none"
    filesize_approx: int = 0
    fps: Optional[int] = None
    is_video: bool = True
    is_audio: bool = True


@dataclass
class MediaItem:
    """Comprehensive metadata for a video, short, or audio stream."""

    id: str
    title: str
    uploader: str
    url: str
    duration: int = 0
    duration_str: str = "00:00"
    view_count: int = 0
    thumbnail_url: str = ""
    description: str = ""
    upload_date: str = ""
    available_resolutions: List[str] = field(default_factory=list)
    is_live: bool = False
    is_short: bool = False
    streams: List[StreamInfo] = field(default_factory=list)


@dataclass
class PlaylistItem:
    """An individual item within a playlist."""

    index: int
    id: str
    title: str
    duration_str: str
    duration: int
    url: str
    uploader: str = ""
    thumbnail_url: str = ""
    selected: bool = True


@dataclass
class PlaylistInfo:
    """Metadata and item listing for a YouTube playlist."""

    id: str
    title: str
    uploader: str
    url: str
    thumbnail_url: str = ""
    entries: List[PlaylistItem] = field(default_factory=list)
    total_count: int = 0


@dataclass
class DownloadConfig:
    """Configuration options for a download task."""

    quality: QualityPreset = QualityPreset.FHD_1080P
    audio_only: bool = False
    audio_format: AudioFormat = AudioFormat.MP3
    audio_bitrate: AudioBitrate = AudioBitrate.B192
    subtitles: SubtitleMode = SubtitleMode.EMBED
    subtitle_langs: List[str] = field(default_factory=lambda: ["en"])
    output_dir: Path = field(default_factory=lambda: Path("downloads"))
    filename_template: Optional[str] = None
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    custom_prefix: Optional[str] = None
    concurrent_fragments: int = 4
    rate_limit_bytes: Optional[int] = None

    def __post_init__(self):
        # Accept a plain string from API/CLI callers while keeping the
        # strongly-typed Path contract internally.
        if not isinstance(self.output_dir, Path):
            self.output_dir = Path(self.output_dir)
        if self.subtitle_langs is None:
            self.subtitle_langs = ["en"]


@dataclass
class TaskProgress:
    """Real-time progress telemetry for a download task."""

    task_id: str
    status: TaskStatus = TaskStatus.QUEUED
    downloaded_bytes: int = 0
    total_bytes: int = 0
    percent: float = 0.0
    speed_bytes: float = 0.0
    speed_str: str = "0 B/s"
    eta_seconds: Optional[int] = None
    eta_str: str = "--:--"
    current_file: str = ""
    message: str = "Queued"


@dataclass
class DownloadTask:
    """Entity representing a discrete download job."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    url: str = ""
    title: str = "Untitled"
    config: DownloadConfig = field(default_factory=DownloadConfig)
    status: TaskStatus = TaskStatus.QUEUED
    progress: TaskProgress = field(init=False)
    output_file: Optional[Path] = None
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def __post_init__(self):
        self.progress = TaskProgress(task_id=self.id, status=self.status)


@dataclass
class BatchItem:
    """Pairing of a local video file and its associated subtitle file."""

    video_file: Path
    subtitle_file: Optional[Path]
    status: str = "ready"  # ready, missing_sub, done, error
    error: Optional[str] = None
    output_file: Optional[Path] = None


@dataclass
class HistoryRecord:
    """Persistent history record of a completed media download."""

    id: str
    url: str
    title: str
    uploader: str
    duration_str: str
    file_path: str
    file_size_bytes: int
    file_size_str: str
    media_type: str  # "video" | "audio"
    quality_or_format: str
    completed_at: str  # ISO formatted string


@dataclass
class AppConfig:
    """Persistent application settings and user preferences."""

    default_output_dir: str = "downloads"
    default_quality: QualityPreset = QualityPreset.FHD_1080P
    default_audio_format: AudioFormat = AudioFormat.MP3
    default_audio_bitrate: AudioBitrate = AudioBitrate.B192
    default_subtitle_mode: SubtitleMode = SubtitleMode.EMBED
    max_concurrent_downloads: int = 3
    theme: ThemeName = ThemeName.CYBERPUNK
    embed_metadata_default: bool = True
    embed_thumbnail_default: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_output_dir": self.default_output_dir,
            "default_quality": self.default_quality.value,
            "default_audio_format": self.default_audio_format.value,
            "default_audio_bitrate": self.default_audio_bitrate.value,
            "default_subtitle_mode": self.default_subtitle_mode.value,
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "theme": self.theme.value,
            "embed_metadata_default": self.embed_metadata_default,
            "embed_thumbnail_default": self.embed_thumbnail_default,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Build configuration from persisted data, tolerating corrupt fields.

        Settings files can be edited by hand or written by older versions.  A
        single invalid value must not discard every other valid preference.
        """
        if not isinstance(data, dict):
            return cls()

        def enum_value(enum_type, key: str, default):
            raw = data.get(key, default.value)
            try:
                return enum_type(raw)
            except (TypeError, ValueError):
                return default

        def bool_value(key: str, default: bool) -> bool:
            raw = data.get(key, default)
            if isinstance(raw, bool):
                return raw
            if isinstance(raw, str):
                return raw.strip().lower() in {"1", "true", "yes", "on"}
            if raw is None:
                return default
            return bool(raw)

        try:
            max_workers = int(data.get("max_concurrent_downloads", 3))
        except (TypeError, ValueError):
            max_workers = 3
        max_workers = max(1, min(10, max_workers))

        output_dir = data.get("default_output_dir", "downloads")
        if not isinstance(output_dir, str) or not output_dir.strip():
            output_dir = "downloads"

        return cls(
            default_output_dir=output_dir,
            default_quality=enum_value(
                QualityPreset, "default_quality", QualityPreset.FHD_1080P
            ),
            default_audio_format=enum_value(
                AudioFormat, "default_audio_format", AudioFormat.MP3
            ),
            default_audio_bitrate=enum_value(
                AudioBitrate, "default_audio_bitrate", AudioBitrate.B192
            ),
            default_subtitle_mode=enum_value(
                SubtitleMode, "default_subtitle_mode", SubtitleMode.EMBED
            ),
            max_concurrent_downloads=max_workers,
            theme=enum_value(ThemeName, "theme", ThemeName.CYBERPUNK),
            embed_metadata_default=bool_value("embed_metadata_default", True),
            embed_thumbnail_default=bool_value("embed_thumbnail_default", True),
        )
