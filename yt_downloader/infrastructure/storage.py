"""
Persistent storage implementation for download history and application settings.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any

from yt_downloader.core.models import HistoryRecord, AppConfig
from yt_downloader.core.enums import QualityPreset, AudioFormat, AudioBitrate, SubtitleMode, ThemeName


def get_default_config_dir() -> Path:
    """Returns ~/.config/yt-downloader or equivalent platform directory."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        base = Path(xdg_config)
    else:
        base = Path.home() / ".config"
    config_dir = base / "yt-downloader"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _atomic_write_json(file_path: Path, data: Any) -> None:
    """Atomically write JSON data to file to prevent corruption."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = file_path.with_name(f".tmp_{file_path.name}")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(file_path)
    except Exception:
        if temp_file.exists():
            temp_file.unlink(missing_ok=True)
        raise


class HistoryStore:
    """Manages persistent record of all completed downloads."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.file_path = storage_path or (get_default_config_dir() / "history.json")

    def list_records(self) -> List[HistoryRecord]:
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return []
                records = []
                for item in data:
                    records.append(
                        HistoryRecord(
                            id=item.get("id", ""),
                            url=item.get("url", ""),
                            title=item.get("title", ""),
                            uploader=item.get("uploader", ""),
                            duration_str=item.get("duration_str", ""),
                            file_path=item.get("file_path", ""),
                            file_size_bytes=item.get("file_size_bytes", 0),
                            file_size_str=item.get("file_size_str", "0 B"),
                            media_type=item.get("media_type", "video"),
                            quality_or_format=item.get("quality_or_format", ""),
                            completed_at=item.get("completed_at", ""),
                        )
                    )
                return records
        except Exception:
            return []

    def add_record(self, record: HistoryRecord) -> None:
        records = self.list_records()
        # Prepend latest record
        records.insert(0, record)
        # Limit to 500 records
        records = records[:500]
        data = [
            {
                "id": r.id,
                "url": r.url,
                "title": r.title,
                "uploader": r.uploader,
                "duration_str": r.duration_str,
                "file_path": r.file_path,
                "file_size_bytes": r.file_size_bytes,
                "file_size_str": r.file_size_str,
                "media_type": r.media_type,
                "quality_or_format": r.quality_or_format,
                "completed_at": r.completed_at,
            }
            for r in records
        ]
        _atomic_write_json(self.file_path, data)

    def delete_record(self, record_id: str) -> bool:
        records = self.list_records()
        new_records = [r for r in records if r.id != record_id]
        if len(new_records) != len(records):
            data = [
                {
                    "id": r.id,
                    "url": r.url,
                    "title": r.title,
                    "uploader": r.uploader,
                    "duration_str": r.duration_str,
                    "file_path": r.file_path,
                    "file_size_bytes": r.file_size_bytes,
                    "file_size_str": r.file_size_str,
                    "media_type": r.media_type,
                    "quality_or_format": r.quality_or_format,
                    "completed_at": r.completed_at,
                }
                for r in new_records
            ]
            _atomic_write_json(self.file_path, data)
            return True
        return False

    def clear_all(self) -> None:
        _atomic_write_json(self.file_path, [])


class SettingsStore:
    """Manages persistent application configuration."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.file_path = storage_path or (get_default_config_dir() / "settings.json")

    def load_config(self) -> AppConfig:
        if not self.file_path.exists():
            return AppConfig()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AppConfig.from_dict(data)
        except Exception:
            return AppConfig()

    def save_config(self, config: AppConfig) -> None:
        _atomic_write_json(self.file_path, config.to_dict())
