"""
YT-Downloader Pro: Modern YouTube Downloader with Clean Architecture & Interactive Console Dashboard.
"""

from yt_downloader.core.models import MediaItem, PlaylistInfo, DownloadConfig, DownloadTask
from yt_downloader.core.enums import QualityPreset, AudioFormat, SubtitleMode, TaskStatus
from yt_downloader.services.download_manager import DownloadManager
from yt_downloader.services.media_service import MediaService
from yt_downloader.ui.interactive_menu import InteractiveConsoleApp
from yt_downloader.cli import main

__version__ = "2.0.0"
__all__ = [
    "MediaItem",
    "PlaylistInfo",
    "DownloadConfig",
    "DownloadTask",
    "QualityPreset",
    "AudioFormat",
    "SubtitleMode",
    "TaskStatus",
    "DownloadManager",
    "MediaService",
    "InteractiveConsoleApp",
    "main",
]
