"""
Download Manager supervising concurrent worker threads, task queues, and telemetry.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, List, Optional, Callable
from pathlib import Path

from yt_downloader.core.enums import TaskStatus
from yt_downloader.core.models import DownloadTask, TaskProgress
from yt_downloader.infrastructure.ytdlp_engine import YtDlpEngine
from yt_downloader.services.history_service import HistoryService
from yt_downloader.services.config_service import ConfigService


class DownloadManager:
    """Thread-safe orchestrator for concurrent media downloads."""

    def __init__(
        self,
        engine: Optional[YtDlpEngine] = None,
        history_service: Optional[HistoryService] = None,
        config_service: Optional[ConfigService] = None,
    ):
        self.engine = engine or YtDlpEngine()
        self.history_service = history_service or HistoryService()
        self.config_service = config_service or ConfigService()

        max_workers = self.config_service.config.max_concurrent_downloads
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="dl-worker")

        self._tasks: Dict[str, DownloadTask] = {}
        self._cancel_events: Dict[str, threading.Event] = {}
        self._futures: Dict[str, Future] = {}
        self._lock = threading.RLock()
        self._listeners: List[Callable[[DownloadTask], None]] = []

    def set_max_concurrency(self, max_workers: int) -> None:
        with self._lock:
            self._executor.shutdown(wait=False)
            self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="dl-worker")

    def subscribe(self, callback: Callable[[DownloadTask], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def _notify(self, task: DownloadTask) -> None:
        with self._lock:
            listeners_copy = list(self._listeners)
        for listener in listeners_copy:
            try:
                listener(task)
            except Exception:
                pass

    def enqueue(self, task: DownloadTask) -> str:
        """Enqueue a single download task."""
        with self._lock:
            self._tasks[task.id] = task
            cancel_event = threading.Event()
            self._cancel_events[task.id] = cancel_event

            future = self._executor.submit(self._worker_execute, task, cancel_event)
            self._futures[task.id] = future

        self._notify(task)
        return task.id

    def enqueue_batch(self, tasks: List[DownloadTask]) -> List[str]:
        """Enqueue a collection of tasks (e.g. playlist items)."""
        ids = []
        for task in tasks:
            ids.append(self.enqueue(task))
        return ids

    def cancel(self, task_id: str) -> bool:
        """Signal cancellation to an active or queued task."""
        with self._lock:
            if task_id in self._cancel_events:
                self._cancel_events[task_id].set()
                task = self._tasks.get(task_id)
                if task and not task.status.is_finished:
                    task.status = TaskStatus.CANCELLED
                    task.progress.status = TaskStatus.CANCELLED
                    task.progress.message = "Cancelled by user"
                    self._notify(task)
                return True
        return False

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> List[DownloadTask]:
        with self._lock:
            return list(self._tasks.values())

    def get_active_tasks(self) -> List[DownloadTask]:
        with self._lock:
            return [t for t in self._tasks.values() if t.status.is_active or t.status == TaskStatus.QUEUED]

    def _worker_execute(self, task: DownloadTask, cancel_event: threading.Event) -> None:
        def on_progress(p: TaskProgress):
            self._notify(task)

        try:
            task.status = TaskStatus.DOWNLOADING
            self._notify(task)

            output_file = self.engine.download_stream(
                task=task,
                progress_callback=on_progress,
                cancel_event=cancel_event,
            )

            if output_file and output_file.exists():
                media_type = "audio" if task.config.audio_only else "video"
                quality_str = (
                    task.config.audio_format.value.upper()
                    if task.config.audio_only
                    else task.config.quality.value
                )
                self.history_service.record_completed_download(
                    task_id=task.id,
                    url=task.url,
                    title=task.title,
                    uploader="YouTube",
                    duration_str=task.progress.eta_str,
                    file_path=output_file,
                    media_type=media_type,
                    quality_or_format=quality_str,
                )

        except Exception as e:
            if not cancel_event.is_set():
                task.status = TaskStatus.FAILED
                task.progress.status = TaskStatus.FAILED
                task.progress.message = str(e)
                task.error_message = str(e)
        finally:
            self._notify(task)

    def shutdown(self, wait: bool = False) -> None:
        with self._lock:
            for event in self._cancel_events.values():
                event.set()
            self._executor.shutdown(wait=wait)
