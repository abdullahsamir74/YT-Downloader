"""
History and Media Library Service for managing downloaded items and system launching.
"""

import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from yt_downloader.core.models import HistoryRecord, format_bytes
from yt_downloader.infrastructure.storage import HistoryStore


class HistoryService:
    """Service handling history records, statistics, and system file opening."""

    def __init__(self, store: Optional[HistoryStore] = None):
        self._store = store or HistoryStore()

    def record_completed_download(
        self,
        task_id: str,
        url: str,
        title: str,
        uploader: str,
        duration_str: str,
        file_path: Path,
        media_type: str,
        quality_or_format: str,
    ) -> HistoryRecord:
        """Create and persist a new download record."""
        size_bytes = file_path.stat().st_size if file_path.exists() else 0
        record = HistoryRecord(
            id=task_id,
            url=url,
            title=title,
            uploader=uploader,
            duration_str=duration_str,
            file_path=str(file_path.resolve()),
            file_size_bytes=size_bytes,
            file_size_str=format_bytes(size_bytes),
            media_type=media_type,
            quality_or_format=quality_or_format,
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._store.add_record(record)
        return record

    def list_all(self) -> List[HistoryRecord]:
        """Return all history records sorted by completion date descending."""
        return self._store.list_records()

    def search(self, query: str) -> List[HistoryRecord]:
        """Filter download records by title, channel, or format."""
        q = query.lower().strip()
        if not q:
            return self.list_all()
        return [
            r for r in self.list_all()
            if q in r.title.lower() or q in r.uploader.lower() or q in r.quality_or_format.lower()
        ]

    def delete(self, record_id: str) -> bool:
        return self._store.delete_record(record_id)

    def clear(self) -> None:
        self._store.clear_all()

    def get_statistics(self) -> Dict[str, Any]:
        records = self.list_all()
        total_size = sum(r.file_size_bytes for r in records)
        video_count = sum(1 for r in records if r.media_type == "video")
        audio_count = sum(1 for r in records if r.media_type == "audio")

        return {
            "total_downloads": len(records),
            "total_size_bytes": total_size,
            "total_size_str": format_bytes(total_size),
            "video_count": video_count,
            "audio_count": audio_count,
        }

    def open_file_in_system(self, file_path_str: str) -> bool:
        """Launch downloaded media file in user's default media player silently."""
        path = Path(file_path_str)
        if not path.exists():
            return False

        sys_name = platform.system()
        try:
            if sys_name == "Linux":
                subprocess.Popen(
                    ["xdg-open", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            elif sys_name == "Darwin":
                subprocess.Popen(
                    ["open", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            elif sys_name == "Windows":
                os.startfile(str(path))
            return True
        except Exception:
            return False

    def open_folder_in_system(self, file_or_dir_path_str: str) -> bool:
        """Open containing folder in system file manager silently."""
        path = Path(file_or_dir_path_str)
        target_dir = path if path.is_dir() else path.parent
        if not target_dir.exists():
            return False

        sys_name = platform.system()
        try:
            if sys_name == "Linux":
                subprocess.Popen(
                    ["xdg-open", str(target_dir)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            elif sys_name == "Darwin":
                subprocess.Popen(
                    ["open", str(target_dir)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            elif sys_name == "Windows":
                os.startfile(str(target_dir))
            return True
        except Exception:
            return False
