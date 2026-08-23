"""
Robust yt-dlp Infrastructure Adapter for metadata extraction and media stream downloads.
"""

import threading
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
import yt_dlp

from yt_downloader.core.enums import QualityPreset, AudioFormat, SubtitleMode, TaskStatus
from yt_downloader.core.exceptions import (
    MetadataExtractionError,
    DownloadError,
    StreamNotFoundError,
    CancelledError,
)
from yt_downloader.core.models import (
    MediaItem,
    StreamInfo,
    PlaylistItem,
    PlaylistInfo,
    DownloadTask,
    TaskProgress,
    format_seconds,
    format_bytes,
)
from yt_downloader.infrastructure.ffmpeg_engine import FFmpegEngine


class YtDlpEngine:
    """Production-grade engine wrapping yt-dlp with telemetry and cancellation support."""

    def __init__(self, ffmpeg_engine: Optional[FFmpegEngine] = None):
        self.ffmpeg_engine = ffmpeg_engine or FFmpegEngine()

    def _base_ydl_opts(self) -> Dict[str, Any]:
        return {
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "retries": 5,
            "fragment_retries": 5,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "noplaylist": True,
        }

    def fetch_media_info(self, url: str) -> Optional[MediaItem]:
        """Extract rich video metadata and available stream formats."""
        opts = self._base_ydl_opts()
        opts.update({
            "skip_download": True,
            "extract_flat": False,
        })

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None

                # If this resolved into a playlist entry dictionary
                if "entries" in info and info["entries"]:
                    first_entry = info["entries"][0]
                    if first_entry:
                        info = first_entry

                dur = int(info.get("duration") or 0)
                resolutions = set()
                streams = []

                for f in info.get("formats") or []:
                    h = f.get("height")
                    if h:
                        res_str = f"{h}p"
                        resolutions.add(res_str)
                    streams.append(
                        StreamInfo(
                            format_id=str(f.get("format_id", "")),
                            resolution=f"{f.get('height', 'audio')}p" if f.get("height") else "audio",
                            ext=f.get("ext", "mp4"),
                            vcodec=f.get("vcodec", "none"),
                            acodec=f.get("acodec", "none"),
                            filesize_approx=int(f.get("filesize") or f.get("filesize_approx") or 0),
                            fps=f.get("fps"),
                            is_video=bool(f.get("vcodec") and f.get("vcodec") != "none"),
                            is_audio=bool(f.get("acodec") and f.get("acodec") != "none"),
                        )
                    )

                # Order resolutions
                sorted_res = sorted(
                    list(resolutions),
                    key=lambda r: int(r.replace("p", "")) if r.replace("p", "").isdigit() else 0,
                    reverse=True,
                )

                uploader = (
                    info.get("uploader")
                    or info.get("channel")
                    or info.get("creator")
                    or "Unknown Channel"
                )

                return MediaItem(
                    id=str(info.get("id", "")),
                    title=str(info.get("title", "Unknown Title")),
                    uploader=uploader,
                    url=url,
                    duration=dur,
                    duration_str=format_seconds(dur),
                    view_count=int(info.get("view_count") or 0),
                    thumbnail_url=str(info.get("thumbnail") or ""),
                    description=str(info.get("description") or "")[:500],
                    upload_date=str(info.get("upload_date") or ""),
                    available_resolutions=sorted_res,
                    is_live=bool(info.get("is_live")),
                    is_short="shorts" in url,
                    streams=streams,
                )
        except Exception as e:
            raise MetadataExtractionError("Could not retrieve video info", str(e))

    def fetch_playlist_info(self, url: str) -> Optional[PlaylistInfo]:
        """Extract playlist entries using fast flat-extraction."""
        opts = self._base_ydl_opts()
        opts.update({
            "skip_download": True,
            "extract_flat": "in_playlist",
            "noplaylist": False,
        })

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info or "entries" not in info:
                    return None

                entries: List[PlaylistItem] = []
                for idx, entry in enumerate(info.get("entries") or [], 1):
                    if not entry:
                        continue
                    v_id = str(entry.get("id") or "")
                    dur = int(entry.get("duration") or 0)
                    raw_url = str(entry.get("url") or "").strip()
                    if raw_url:
                        if raw_url.startswith("http://") or raw_url.startswith("https://"):
                            v_url = raw_url
                        elif raw_url.startswith("/"):
                            v_url = f"https://www.youtube.com{raw_url}"
                        elif "watch" in raw_url:
                            v_url = f"https://www.youtube.com/{raw_url.lstrip('/')}"
                        else:
                            v_url = f"https://www.youtube.com/watch?v={raw_url}"
                    elif v_id:
                        v_url = f"https://www.youtube.com/watch?v={v_id}"
                    else:
                        v_url = ""
                    v_title = str(entry.get("title") or f"Video {idx}")
                    v_uploader = str(entry.get("uploader") or entry.get("channel") or "Unknown Channel")
                    v_thumb = str(entry.get("thumbnail") or "")
                    entries.append(
                        PlaylistItem(
                            index=idx,
                            id=v_id,
                            title=v_title,
                            duration_str=format_seconds(dur),
                            duration=dur,
                            url=v_url,
                            uploader=v_uploader,
                            thumbnail_url=v_thumb,
                            selected=True,
                        )
                    )

                p_title = str(info.get("title") or "Playlist")
                p_uploader = str(info.get("uploader") or info.get("channel") or "Unknown Channel")
                p_thumb = str(info.get("thumbnail") or (entries[0].thumbnail_url if entries else ""))

                return PlaylistInfo(
                    id=str(info.get("id") or ""),
                    title=p_title,
                    uploader=p_uploader,
                    url=url,
                    thumbnail_url=p_thumb,
                    entries=entries,
                    total_count=len(entries),
                )
        except Exception as e:
            raise MetadataExtractionError("Could not retrieve playlist info", str(e))

    def download_stream(
        self,
        task: DownloadTask,
        progress_callback: Optional[Callable[[TaskProgress], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Path:
        """Execute stream download with progress telemetry and post-processing."""
        cfg = task.config
        cfg.output_dir.mkdir(parents=True, exist_ok=True)

        prefix_str = f"{cfg.custom_prefix} - " if cfg.custom_prefix else ""
        outtmpl = str(cfg.output_dir / f"{prefix_str}%(title)s.%(ext)s")

        format_map = {
            QualityPreset.BEST: "bestvideo+bestaudio/best",
            QualityPreset.UHD_4K: "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best",
            QualityPreset.QHD_2K: "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best",
            QualityPreset.FHD_1080P: "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            QualityPreset.HD_720P: "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            QualityPreset.SD_480P: "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
            QualityPreset.SD_360P: "bestvideo[height<=360]+bestaudio/best[height<=360]/best",
        }

        ydl_opts: Dict[str, Any] = {
            "outtmpl": outtmpl,
            "socket_timeout": 30,
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": cfg.concurrent_fragments,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": False,
        }

        if cfg.rate_limit_bytes:
            ydl_opts["ratelimit"] = cfg.rate_limit_bytes

        postprocessors = []

        if cfg.audio_only:
            ydl_opts["format"] = "bestaudio/best"
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": cfg.audio_format.value,
                "preferredquality": cfg.audio_bitrate.value if cfg.audio_bitrate.value != "0" else "192",
            })
            if cfg.embed_metadata:
                postprocessors.append({"key": "FFmpegMetadata", "add_chapters": True})
            if cfg.embed_thumbnail:
                ydl_opts["writethumbnail"] = True
                postprocessors.append({"key": "EmbedThumbnail"})
        else:
            ydl_opts["format"] = format_map.get(cfg.quality, format_map[QualityPreset.FHD_1080P])
            ydl_opts["merge_output_format"] = "mp4"
            if cfg.embed_metadata:
                postprocessors.append({"key": "FFmpegMetadata", "add_chapters": True})
            if cfg.embed_thumbnail:
                ydl_opts["writethumbnail"] = True
                postprocessors.append({"key": "EmbedThumbnail"})

        if not cfg.audio_only and cfg.subtitles != SubtitleMode.NONE:
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True
            ydl_opts["subtitleslangs"] = cfg.subtitle_langs or ["en"]
            ydl_opts["subtitlesformat"] = "srt/best"

        if postprocessors:
            ydl_opts["postprocessors"] = postprocessors

        downloaded_file: Optional[Path] = None

        def progress_hook(d: Dict[str, Any]):
            if cancel_event and cancel_event.is_set():
                raise CancelledError("Download was cancelled by user")

            status = d.get("status")
            filename = d.get("filename", "")
            if filename:
                task.progress.current_file = Path(filename).name

            if status == "downloading":
                task.status = TaskStatus.DOWNLOADING
                task.progress.status = TaskStatus.DOWNLOADING
                cur = d.get("downloaded_bytes") or 0
                tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                spd = d.get("speed") or 0
                eta = d.get("eta")

                task.progress.downloaded_bytes = int(cur)
                task.progress.total_bytes = int(tot)
                task.progress.percent = (cur / tot * 100.0) if tot > 0 else 0.0
                task.progress.speed_bytes = float(spd)
                task.progress.speed_str = f"{format_bytes(spd)}/s" if spd > 0 else "-- B/s"
                task.progress.eta_seconds = eta
                task.progress.eta_str = format_seconds(eta) if eta is not None else "--:--"
                task.progress.message = f"Downloading: {task.progress.percent:.1f}% ({task.progress.speed_str})"

                if progress_callback:
                    progress_callback(task.progress)

            elif status == "finished":
                task.status = TaskStatus.PROCESSING
                task.progress.status = TaskStatus.PROCESSING
                task.progress.message = "Processing & converting..."
                if progress_callback:
                    progress_callback(task.progress)

        ydl_opts["progress_hooks"] = [progress_hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(task.url, download=True)
                if not info:
                    raise DownloadError("Failed to download stream: no info returned")

                target_filename = ydl.prepare_filename(info)
                downloaded_file = Path(target_filename)

                # For audio post-processing, file extension changes
                if cfg.audio_only:
                    audio_target = downloaded_file.with_suffix(f".{cfg.audio_format.value}")
                    if audio_target.exists():
                        downloaded_file = audio_target

                # If merged format is mp4 or other video containers
                if not cfg.audio_only:
                    for cand_ext in [".mp4", ".mkv", ".webm", ".mov"]:
                        cand_target = downloaded_file.with_suffix(cand_ext)
                        if cand_target.exists():
                            downloaded_file = cand_target
                            break

                # If the exact path does not exist, find closest matching file in output dir
                if not downloaded_file.exists():
                    valid_exts = (
                        {f".{cfg.audio_format.value}", ".mp3", ".m4a", ".flac", ".opus", ".wav", ".aac", ".ogg"}
                        if cfg.audio_only
                        else {".mp4", ".mkv", ".webm", ".mov", ".avi", ".ts", ".flv"}
                    )
                    matches = [
                        p for p in cfg.output_dir.glob(f"*{prefix_str}*")
                        if p.is_file() and p.suffix.lower() in valid_exts
                    ]
                    if matches:
                        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        downloaded_file = matches[0]

                # If user requested embedded subtitles and FFmpeg is available
                if (
                    not cfg.audio_only
                    and cfg.subtitles == SubtitleMode.EMBED
                    and self.ffmpeg_engine.is_ffmpeg_available
                    and downloaded_file.exists()
                ):
                    task.progress.message = "Embedding subtitles into video..."
                    if progress_callback:
                        progress_callback(task.progress)
                    try:
                        self.ffmpeg_engine.embed_subtitle(downloaded_file)
                    except Exception:
                        pass  # Preserve video if subtitle embedding fails

                task.status = TaskStatus.COMPLETED
                task.progress.status = TaskStatus.COMPLETED
                task.progress.percent = 100.0
                task.progress.message = "Completed"
                task.output_file = downloaded_file
                if progress_callback:
                    progress_callback(task.progress)

                return downloaded_file

        except yt_dlp.utils.DownloadCancelled:
            task.status = TaskStatus.CANCELLED
            task.progress.status = TaskStatus.CANCELLED
            task.progress.message = "Cancelled"
            if progress_callback:
                progress_callback(task.progress)
            raise CancelledError("Download cancelled")
        except CancelledError:
            task.status = TaskStatus.CANCELLED
            task.progress.status = TaskStatus.CANCELLED
            task.progress.message = "Cancelled"
            if progress_callback:
                progress_callback(task.progress)
            raise
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.progress.status = TaskStatus.FAILED
            task.progress.message = f"Error: {str(e)}"
            task.error_message = str(e)
            if progress_callback:
                progress_callback(task.progress)
            raise DownloadError(f"Download failed: {str(e)}")
