"""
Persistent storage implementation for download history and application settings.
"""

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from yt_downloader.core.models import AppConfig, HistoryRecord

# Serialize read-modify-write operations on a given history/settings file.
# DownloadManager runs several worker threads that may finish simultaneously;
# without this lock two workers can overwrite each other's history records.
_FILE_LOCKS: Dict[Path, threading.RLock] = {}
_FILE_LOCKS_GUARD = threading.Lock()


def _get_file_lock(file_path: Path) -> threading.RLock:
    """Return the process-wide re-entrant lock guarding ``file_path``."""
    try:
        key = file_path.resolve()
    except OSError:
        key = file_path.absolute()
    with _FILE_LOCKS_GUARD:
        return _FILE_LOCKS.setdefault(key, threading.RLock())


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
    """Atomically write JSON data to file to prevent corruption.

    A unique temporary file is used so concurrent writers cannot truncate or
    replace each other's in-flight output.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{file_path.name}.",
        suffix=".tmp",
        dir=str(file_path.parent),
    )
    temp_file = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_file, file_path)
    except Exception:
        try:
            temp_file.unlink(missing_ok=True)
        except OSError:
            pass
        raise


class HistoryStore:
    """Manages persistent record of all completed downloads."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.file_path = storage_path or (get_default_config_dir() / "history.json")
        self._lock = _get_file_lock(self.file_path)

    def list_records(self) -> List[HistoryRecord]:
        with self._lock:
            if not self.file_path.exists():
                return []
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError, TypeError):
                return []

            if not isinstance(data, list):
                return []

            records: List[HistoryRecord] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                try:
                    records.append(
                        HistoryRecord(
                            id=str(item.get("id", "")),
                            url=str(item.get("url", "")),
                            title=str(item.get("title", "")),
                            uploader=str(item.get("uploader", "")),
                            duration_str=str(item.get("duration_str", "")),
                            file_path=str(item.get("file_path", "")),
                            file_size_bytes=int(item.get("file_size_bytes", 0) or 0),
                            file_size_str=str(item.get("file_size_str", "0 B")),
                            media_type=str(item.get("media_type", "video")),
                            quality_or_format=str(item.get("quality_or_format", "")),
                            completed_at=str(item.get("completed_at", "")),
                        )
                    )
                except (TypeError, ValueError):
                    # Skip a malformed entry rather than losing the whole file.
                    continue
            return records

    @staticmethod
    def _to_dict(record: HistoryRecord) -> Dict[str, Any]:
        return {
            "id": record.id,
            "url": record.url,
            "title": record.title,
            "uploader": record.uploader,
            "duration_str": record.duration_str,
            "file_path": record.file_path,
            "file_size_bytes": record.file_size_bytes,
            "file_size_str": record.file_size_str,
            "media_type": record.media_type,
            "quality_or_format": record.quality_or_format,
            "completed_at": record.completed_at,
        }

    def add_record(self, record: HistoryRecord) -> None:
        with self._lock:
            records = self.list_records()
            # Prepend the latest record and keep the ledger bounded.
            records.insert(0, record)
            records = records[:500]
            _atomic_write_json(self.file_path, [self._to_dict(r) for r in records])

    def delete_record(self, record_id: str) -> bool:
        with self._lock:
            records = self.list_records()
            new_records = [r for r in records if r.id != record_id]
            if len(new_records) == len(records):
                return False
            _atomic_write_json(self.file_path, [self._to_dict(r) for r in new_records])
            return True

    def clear_all(self) -> None:
        with self._lock:
            _atomic_write_json(self.file_path, [])


class SettingsStore:
    """Manages persistent application configuration."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.file_path = storage_path or (get_default_config_dir() / "settings.json")
        self._lock = _get_file_lock(self.file_path)

    def load_config(self) -> AppConfig:
        with self._lock:
            if not self.file_path.exists():
                return AppConfig()
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    return AppConfig()
                return AppConfig.from_dict(data)
            except (OSError, ValueError, TypeError):
                return AppConfig()

    def save_config(self, config: AppConfig) -> None:
        with self._lock:
            _atomic_write_json(self.file_path, config.to_dict())
