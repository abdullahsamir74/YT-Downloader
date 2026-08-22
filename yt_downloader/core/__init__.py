"""
Core domain module for YT-Downloader.
"""

from yt_downloader.core.enums import (
    QualityPreset,
    AudioFormat,
    AudioBitrate,
    SubtitleMode,
    TaskStatus,
    ThemeName,
)
from yt_downloader.core.exceptions import (
    YTDownloaderError,
    MetadataExtractionError,
    DownloadError,
    StreamNotFoundError,
    FFmpegNotFoundError,
    MuxingError,
    NetworkError,
    CancelledError,
)
from yt_downloader.core.models import (
    MediaItem,
    StreamInfo,
    PlaylistItem,
    PlaylistInfo,
    DownloadConfig,
    DownloadTask,
    TaskProgress,
    BatchItem,
    HistoryRecord,
    AppConfig,
    format_seconds,
    format_bytes,
)
from yt_downloader.core.interfaces import (
    IDownloadEngine,
    ISubtitleEngine,
    IHistoryRepository,
    ISettingsRepository,
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
