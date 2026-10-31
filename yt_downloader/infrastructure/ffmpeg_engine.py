"""
FFmpeg Infrastructure Engine for subtitle muxing, audio processing, and metadata tagging.
"""

import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from yt_downloader.core.exceptions import FFmpegNotFoundError, MuxingError
from yt_downloader.core.models import BatchItem


class FFmpegEngine:
    """Production-grade FFmpeg wrapper for media manipulation."""

    def __init__(self):
        self._ffmpeg_path = shutil.which("ffmpeg")
        self._ffprobe_path = shutil.which("ffprobe")

    @property
    def is_ffmpeg_available(self) -> bool:
        return self._ffmpeg_path is not None

    def _require_ffmpeg(self) -> str:
        if not self._ffmpeg_path:
            raise FFmpegNotFoundError("FFmpeg is not installed or not in PATH")
        return self._ffmpeg_path

    @property
    def ffmpeg_version(self) -> Optional[str]:
        if not self.is_ffmpeg_available:
            return None
        try:
            res = subprocess.run(
                [self._require_ffmpeg(), "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            match = re.search(r"ffmpeg version\s+([^\s]+)", res.stdout)
            return match.group(1) if match else "Installed"
        except Exception:
            return "Installed"

    def find_matching_subtitle(self, video_path: Path) -> Optional[Path]:
        """Look for matching subtitle files (.srt, .vtt, .ass) in the same directory."""
        if not video_path.exists():
            return None

        stem = video_path.stem
        parent = video_path.parent

        # Check precise suffixes first.
        sub_extensions = [
            f"{stem}.en.srt",
            f"{stem}.eng.srt",
            f"{stem}.srt",
            f"{stem}.en.vtt",
            f"{stem}.vtt",
            f"{stem}.ass",
        ]
        for sub_name in sub_extensions:
            candidate = parent / sub_name
            if candidate.exists() and candidate.is_file():
                return candidate

        # Case-insensitive exact or language-suffixed match (e.g.
        # ``movie.en.srt`` for ``movie.mp4``).  Avoid substring matching so
        # ``movie2.srt`` is not used for ``movie.mp4``.
        stem_lower = stem.lower()
        subtitle_exts = {".srt", ".vtt", ".ass", ".ssa"}
        try:
            candidates = list(parent.iterdir())
        except OSError:
            return None
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix.lower() not in subtitle_exts:
                continue
            candidate_stem = candidate.stem.lower()
            if (
                candidate_stem == stem_lower
                or candidate_stem.startswith(f"{stem_lower}.")
                or candidate_stem.startswith(f"{stem_lower}_")
            ):
                return candidate

        return None

    def embed_subtitle(
        self,
        video_path: Path,
        subtitle_path: Optional[Path] = None,
        language: str = "eng",
    ) -> bool:
        """
        Embeds subtitle track into video file atomically.
        Uses mov_text for MP4 containers, or subrip/ass for MKV.
        """
        if not self.is_ffmpeg_available:
            raise FFmpegNotFoundError("FFmpeg is not installed or not in PATH")

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if subtitle_path is None:
            subtitle_path = self.find_matching_subtitle(video_path)

        if not subtitle_path or not subtitle_path.exists():
            return False

        temp_out = video_path.with_name(f".tmp_embed_{video_path.name}")

        # Choose subtitle codec depending on container.
        ext = video_path.suffix.lower()
        if ext in [".mp4", ".m4v", ".mov"]:
            sub_codec = "mov_text"
        elif ext == ".webm":
            sub_codec = "webvtt"
        else:
            sub_codec = "copy"

        cmd = [
            self._require_ffmpeg(),
            "-y",  # Overwrite output
            "-i",
            str(video_path),
            "-i",
            str(subtitle_path),
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            sub_codec,
            "-metadata:s:s:0",
            f"language={language}",
            "-map",
            "0:v",
            "-map",
            "0:a?",
            "-map",
            "1:s?",
            str(temp_out),
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            if (
                res.returncode == 0
                and temp_out.exists()
                and temp_out.stat().st_size > 0
            ):
                # Atomically replace video file
                video_path.unlink(missing_ok=True)
                temp_out.rename(video_path)
                # Cleanup standalone subtitle file after successful embedding
                try:
                    subtitle_path.unlink(missing_ok=True)
                except OSError:
                    pass
                return True
            else:
                if temp_out.exists():
                    temp_out.unlink(missing_ok=True)
                error_msg = res.stderr[-500:] if res.stderr else "Unknown error"
                raise MuxingError("Failed to embed subtitle with FFmpeg", error_msg)
        except Exception as e:
            if temp_out.exists():
                temp_out.unlink(missing_ok=True)
            if isinstance(e, FFmpegNotFoundError):
                raise
            if isinstance(e, MuxingError):
                raise
            raise MuxingError("Subtitle embedding failed", str(e)) from e

    def scan_directory_for_pairs(self, directory: Path) -> List[BatchItem]:
        """Scan a folder for video files and check for matching subtitle files."""
        items: List[BatchItem] = []
        if not directory.exists() or not directory.is_dir():
            return items

        video_extensions = {".mp4", ".mkv", ".webm", ".mov", ".avi"}

        try:
            entries = sorted(directory.iterdir())
        except OSError:
            return items

        for entry in entries:
            if entry.is_file() and entry.suffix.lower() in video_extensions:
                if entry.name.startswith(".tmp_") or "_temp" in entry.stem:
                    continue
                sub = self.find_matching_subtitle(entry)
                status = "ready" if sub else "missing_sub"
                items.append(
                    BatchItem(
                        video_file=entry,
                        subtitle_file=sub,
                        status=status,
                    )
                )

        return items
