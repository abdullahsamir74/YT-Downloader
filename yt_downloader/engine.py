"""
Core engine wrapping yt-dlp and FFmpeg.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Union, List
import yt_dlp

from yt_downloader.models import (
    VideoInfo,
    PlaylistInfo,
    PlaylistItem,
    DownloadOpts,
    BatchItem,
)


def format_duration(seconds: Optional[int]) -> str:
    if not seconds or seconds <= 0:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"


def format_bytes(num_bytes: Union[int, float]) -> str:
    if not num_bytes or num_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    i = 0
    while num_bytes >= 1024 and i < len(units) - 1:
        num_bytes /= 1024
        i += 1
    return f"{num_bytes:.1f} {units[i]}"


class SubtitleEmbedder:
    """FFmpeg subtitle embedder."""

    def __init__(self):
        self.ffmpeg_path = shutil.which("ffmpeg")

    @property
    def is_available(self) -> bool:
        return self.ffmpeg_path is not None

    def find_subtitle(self, video_file: Path) -> Optional[Path]:
        for ext in [".en.srt", ".srt", ".vtt"]:
            candidate = video_file.with_suffix(ext)
            if candidate.exists():
                return candidate
        return None

    def embed(self, video_file: Path, subtitle_file: Optional[Path] = None) -> bool:
        if not self.is_available or not video_file.exists():
            return False

        if subtitle_file is None:
            subtitle_file = self.find_subtitle(video_file)

        if not subtitle_file or not subtitle_file.exists():
            return False

        temp_out = video_file.with_name(f"{video_file.stem}_temp{video_file.suffix}")
        cmd = [
            self.ffmpeg_path,
            "-i", str(video_file),
            "-i", str(subtitle_file),
            "-c", "copy",
            "-c:s", "mov_text",
            "-metadata:s:s:0", "language=eng",
            "-y",
            str(temp_out),
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and temp_out.exists():
                video_file.unlink(missing_ok=True)
                temp_out.rename(video_file)
                subtitle_file.unlink(missing_ok=True)
                return True
            if temp_out.exists():
                temp_out.unlink(missing_ok=True)
            return False
        except Exception:
            if temp_out.exists():
                temp_out.unlink(missing_ok=True)
            return False


class Downloader:
    """yt-dlp downloader engine."""

    def __init__(self):
        self.sub_embedder = SubtitleEmbedder()

    def fetch_info(self, url: str) -> Optional[Union[VideoInfo, PlaylistInfo]]:
        opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None

                if "entries" in info and info["entries"]:
                    entries = []
                    for idx, entry in enumerate(info.get("entries") or [], 1):
                        if entry:
                            v_id = entry.get("id") or ""
                            dur = entry.get("duration") or 0
                            entries.append(
                                PlaylistItem(
                                    index=idx,
                                    id=v_id,
                                    title=entry.get("title", f"Video {idx}"),
                                    duration_str=format_duration(dur),
                                    url=f"https://www.youtube.com/watch?v={v_id}" if v_id else "",
                                )
                            )
                    return PlaylistInfo(
                        id=info.get("id", ""),
                        title=info.get("title", "Playlist"),
                        uploader=info.get("uploader") or info.get("channel") or "Unknown",
                        entries=entries,
                        url=url,
                    )
                else:
                    dur = info.get("duration") or 0
                    return VideoInfo(
                        id=info.get("id", ""),
                        title=info.get("title", "Video"),
                        uploader=info.get("uploader") or info.get("channel") or "Unknown",
                        duration_str=format_duration(dur),
                        view_count=int(info.get("view_count") or 0),
                        url=url,
                    )
        except Exception:
            return None

    def download(
        self,
        url: str,
        opts: DownloadOpts,
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
        prefix: Optional[str] = None,
    ) -> bool:
        opts.output_dir.mkdir(parents=True, exist_ok=True)
        outtmpl = str(opts.output_dir / (f"{prefix}-%(title)s.%(ext)s" if prefix else "%(title)s.%(ext)s"))

        format_map = {
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
            "2160p": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "best": "bestvideo+bestaudio/best",
        }

        ydl_opts: Dict[str, Any] = {
            "outtmpl": outtmpl,
            "progress_hooks": [progress_cb] if progress_cb else [],
            "socket_timeout": 30,
            "retries": 10,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "quiet": True,
            "no_warnings": True,
        }

        if opts.audio_only:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": opts.audio_format,
                    "preferredquality": opts.audio_bitrate,
                }
            ]
        else:
            ydl_opts["format"] = format_map.get(opts.quality, format_map["1080p"])
            ydl_opts["merge_output_format"] = "mp4"

        if opts.subtitles != "none":
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True
            ydl_opts["subtitleslangs"] = ["en"]
            ydl_opts["subtitlesformat"] = "srt"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not opts.audio_only and opts.subtitles == "embed" and self.sub_embedder.is_available and info:
                    target_filename = ydl.prepare_filename(info)
                    target_path = Path(target_filename)
                    if not target_path.exists():
                        candidates = list(opts.output_dir.glob(f"*{prefix or ''}*.mp4"))
                        if candidates:
                            candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                            target_path = candidates[0]
                    if target_path.exists():
                        self.sub_embedder.embed(target_path)
                return True
        except Exception:
            return False


def scan_batch(folder: Path) -> List[BatchItem]:
    """Scan folder for video and subtitle pairs."""
    embedder = SubtitleEmbedder()
    items = []
    if not folder.exists() or not folder.is_dir():
        return items

    for f in sorted(folder.glob("*.mp4")):
        if "_temp" in f.stem or "_embedded" in f.stem:
            continue
        sub = embedder.find_subtitle(f)
        items.append(BatchItem(video_file=f, subtitle_file=sub, status="ready" if sub else "missing_sub"))

    return items
