"""
Core domain module for YT-Downloader.
"""

from yt_downloader.core.enums import (
    AudioBitrate,
    AudioFormat,
    QualityPreset,
    SubtitleMode,
    TaskStatus,
    ThemeName,
)
from yt_downloader.core.exceptions import (
    CancelledError,
    DownloadError,
    FFmpegNotFoundError,
    MetadataExtractionError,
    MuxingError,
    NetworkError,
    StreamNotFoundError,
    YTDownloaderError,
)
from yt_downloader.core.interfaces import (
    IDownloadEngine,
    IHistoryRepository,
    ISettingsRepository,
    ISubtitleEngine,
)
from yt_downloader.core.models import (
    AppConfig,
    BatchItem,
    DownloadConfig,
    DownloadTask,
    HistoryRecord,
    MediaItem,
    PlaylistInfo,
    PlaylistItem,
    StreamInfo,
    TaskProgress,
    format_bytes,
    format_seconds,
)

__all__ = [
    "QualityPreset",
    "AudioFormat",
    "AudioBitrate",
    "SubtitleMode",
    "TaskStatus",
    "ThemeName",
    "YTDownloaderError",
    "MetadataExtractionError",
    "DownloadError",
    "StreamNotFoundError",
    "FFmpegNotFoundError",
    "MuxingError",
    "NetworkError",
    "CancelledError",
    "MediaItem",
    "StreamInfo",
    "PlaylistItem",
    "PlaylistInfo",
    "DownloadConfig",
    "DownloadTask",
    "TaskProgress",
    "BatchItem",
    "HistoryRecord",
    "AppConfig",
    "format_seconds",
    "format_bytes",
    "IDownloadEngine",
    "ISubtitleEngine",
    "IHistoryRepository",
    "ISettingsRepository",
]
