"""
Subtitle & Batch Muxing Service.
"""

from pathlib import Path
from typing import Callable, List, Optional

from yt_downloader.core.models import BatchItem
from yt_downloader.infrastructure.ffmpeg_engine import FFmpegEngine


class SubtitleService:
    """Provides subtitle management, directory scanning, and batch embedding."""

    def __init__(self, ffmpeg_engine: Optional[FFmpegEngine] = None):
        self.ffmpeg = ffmpeg_engine or FFmpegEngine()

    @property
    def is_available(self) -> bool:
        return self.ffmpeg.is_ffmpeg_available

    @property
    def ffmpeg_version(self) -> Optional[str]:
        return self.ffmpeg.ffmpeg_version

    def scan_folder(self, folder: Path) -> List[BatchItem]:
        return self.ffmpeg.scan_directory_for_pairs(folder)

    def embed_file(
        self, video_path: Path, subtitle_path: Optional[Path] = None
    ) -> bool:
        return self.ffmpeg.embed_subtitle(video_path, subtitle_path)

    def batch_embed(
        self,
        items: List[BatchItem],
        progress_cb: Optional[Callable[[int, int, BatchItem], None]] = None,
    ) -> List[BatchItem]:
        """Run batch embedding on ready items sequentially with progress reports."""
        results = []
        total = len(items)
        for idx, item in enumerate(items, 1):
            if item.status == "ready":
                if not item.subtitle_file:
                    item.status = "error"
                    item.error = "No subtitle file paired with this video"
                else:
                    try:
                        success = self.ffmpeg.embed_subtitle(
                            item.video_file, item.subtitle_file
                        )
                        item.status = "done" if success else "error"
                        if not success:
                            item.error = "FFmpeg returned non-zero code"
                    except Exception as e:
                        item.status = "error"
                        item.error = str(e)
            results.append(item)
            if progress_cb:
                progress_cb(idx, total, item)
        return results
