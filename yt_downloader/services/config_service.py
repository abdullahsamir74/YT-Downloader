"""
Configuration Service for managing application settings and preferences.
"""

from typing import Callable, List, Optional

from yt_downloader.core.enums import (
    AudioBitrate,
    AudioFormat,
    QualityPreset,
    SubtitleMode,
    ThemeName,
)
from yt_downloader.core.models import AppConfig
from yt_downloader.infrastructure.storage import SettingsStore


class ConfigService:
    """Service providing reactive configuration management."""

    def __init__(self, store: Optional[SettingsStore] = None):
        self._store = store or SettingsStore()
        self._config = self._store.load_config()
        self._listeners: List[Callable[[AppConfig], None]] = []

    @property
    def config(self) -> AppConfig:
        return self._config

    def reload(self) -> AppConfig:
        self._config = self._store.load_config()
        self._notify()
        return self._config

    def update(
        self,
        default_output_dir: Optional[str] = None,
        default_quality: Optional[QualityPreset] = None,
        default_audio_format: Optional[AudioFormat] = None,
        default_audio_bitrate: Optional[AudioBitrate] = None,
        default_subtitle_mode: Optional[SubtitleMode] = None,
        max_concurrent_downloads: Optional[int] = None,
        theme: Optional[ThemeName] = None,
        embed_metadata_default: Optional[bool] = None,
        embed_thumbnail_default: Optional[bool] = None,
    ) -> AppConfig:
        """Update any configuration parameters and persist changes."""
        if default_output_dir is not None:
            self._config.default_output_dir = default_output_dir
        if default_quality is not None:
            self._config.default_quality = default_quality
        if default_audio_format is not None:
            self._config.default_audio_format = default_audio_format
        if default_audio_bitrate is not None:
            self._config.default_audio_bitrate = default_audio_bitrate
        if default_subtitle_mode is not None:
            self._config.default_subtitle_mode = default_subtitle_mode
        if max_concurrent_downloads is not None:
            self._config.max_concurrent_downloads = max(
                1, min(10, max_concurrent_downloads)
            )
        if theme is not None:
            self._config.theme = theme
        if embed_metadata_default is not None:
            self._config.embed_metadata_default = embed_metadata_default
        if embed_thumbnail_default is not None:
            self._config.embed_thumbnail_default = embed_thumbnail_default

        self._store.save_config(self._config)
        self._notify()
        return self._config

    def subscribe(self, callback: Callable[[AppConfig], None]) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        for listener in self._listeners:
            try:
                listener(self._config)
            except Exception:
                pass
