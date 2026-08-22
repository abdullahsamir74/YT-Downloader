"""
Enhanced CLI and scriptable entry point for YT-Downloader using Rich and Clean Architecture.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

from yt_downloader.core.enums import QualityPreset, AudioFormat, AudioBitrate, SubtitleMode, TaskStatus
from yt_downloader.core.models import DownloadConfig, DownloadTask, TaskProgress, format_bytes
from yt_downloader.infrastructure.ffmpeg_engine import FFmpegEngine
from yt_downloader.infrastructure.ytdlp_engine import YtDlpEngine
from yt_downloader.services.media_service import MediaService
from yt_downloader.services.history_service import HistoryService
from yt_downloader.ui.interactive_menu import InteractiveConsoleApp

console = Console()


def print_media_info_card(media_item) -> None:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="cyan bold", justify="right")
    table.add_column(style="white")

    table.add_row("Title:", media_item.title)
    table.add_row("Channel / Uploader:", media_item.uploader)
    table.add_row("Duration:", media_item.duration_str)
    table.add_row("View Count:", f"{media_item.view_count:,}")
    table.add_row("Upload Date:", media_item.upload_date or "N/A")
    table.add_row("Available Resolutions:", ", ".join(media_item.available_resolutions) or "N/A")

    console.print(
        Panel(
            table,
            title="[bold cyan]⚡ Media Information[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def execute_cli_download(
    url: str,
    config: DownloadConfig,
    title: Optional[str] = None,
) -> bool:
    ffmpeg_engine = FFmpegEngine()
    ytdlp_engine = YtDlpEngine(ffmpeg_engine)
    history_service = HistoryService()

    task = DownloadTask(
        url=url,
        title=title or url,
        config=config,
    )

    console.print(f"[bold cyan]⚡ Connecting to stream:[/bold cyan] {url}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=35, complete_style="cyan"),
        TaskProgressColumn(),
        TextColumn("{task.fields[size_text]}"),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        bar_task = progress.add_task(f"Downloading...", total=None, size_text="")

        def on_progress(p: TaskProgress):
            if p.status == TaskStatus.DOWNLOADING:
                cur = p.downloaded_bytes
                tot = p.total_bytes
                cur_str = format_bytes(cur)
                tot_str = format_bytes(tot) if tot > 0 else "--"
                size_str = f"{cur_str} / {tot_str}"

                if tot > 0:
                    progress.update(
                        bar_task,
                        completed=cur,
                        total=tot,
                        description=f"{p.current_file[:25] or 'Downloading'}",
                        size_text=size_str,
                    )
                else:
                    progress.update(
                        bar_task,
                        description=f"{p.current_file[:25] or 'Downloading'}",
                        size_text=size_str,
                    )
            elif p.status == TaskStatus.PROCESSING:
                progress.update(bar_task, description="[bold yellow]Processing / Muxing...")

        try:
            output_file = ytdlp_engine.download_stream(task, progress_callback=on_progress)
            if output_file and output_file.exists():
                progress.update(bar_task, completed=100, total=100, description="[bold green]✓ Completed")
                console.print(f"\n[bold green]✓ Saved file to:[/bold green] {output_file.resolve()}\n")

                media_type = "audio" if config.audio_only else "video"
                quality_str = config.audio_format.value if config.audio_only else config.quality.value
                history_service.record_completed_download(
                    task_id=task.id,
                    url=url,
                    title=task.title,
                    uploader="YouTube",
                    duration_str="--:--",
                    file_path=output_file,
                    media_type=media_type,
                    quality_or_format=quality_str,
                )
                return True
            else:
                console.print("\n[bold red]✗ Download failed: file not found.[/bold red]")
                return False
        except Exception as e:
            console.print(f"\n[bold red]✗ Download error:[/bold red] {str(e)}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="⚡ Modern YouTube Downloader (Interactive Dashboard & Scriptable CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="⚡ YT-Downloader Pro 2.0.0",
        help="Show program version and exit",
    )
    parser.add_argument("--url", "-u", type=str, help="YouTube video or playlist URL for direct download")
    parser.add_argument(
        "--quality",
        "-q",
        type=str,
        default="1080p",
        choices=["best", "2160p", "1440p", "1080p", "720p", "480p", "360p"],
        help="Video target quality (default: 1080p)",
    )
    parser.add_argument("--audio-only", "-a", action="store_true", help="Extract audio stream only")
    parser.add_argument(
        "--audio-format",
        type=str,
        default="mp3",
        choices=["mp3", "m4a", "flac", "opus", "wav", "aac"],
        help="Target audio codec (default: mp3)",
    )
    parser.add_argument(
        "--audio-bitrate",
        type=str,
        default="192",
        choices=["128", "192", "256", "320", "0"],
        help="Audio bitrate in kbps (default: 192)",
    )
    parser.add_argument(
        "--subtitles",
        "-s",
        type=str,
        default="embed",
        choices=["embed", "separate", "none"],
        help="Subtitle handling strategy (default: embed)",
    )
    parser.add_argument("--output-dir", "-o", type=str, default="downloads", help="Output directory")
    parser.add_argument("--info", "-i", action="store_true", help="Inspect URL metadata without downloading")
    parser.add_argument("--json", action="store_true", help="Print inspected metadata as JSON")

    args = parser.parse_args()

    # 1. Direct CLI Mode (flags provided)
    if args.url or args.info:
        if not args.url:
            console.print("[bold red]Error: --url is required when using CLI mode[/bold red]")
            sys.exit(1)

        media_service = MediaService()

        if args.info:
            item_type, entity = media_service.inspect_url(args.url)
            if not entity:
                console.print("[bold red]Failed to inspect URL metadata.[/bold red]")
                sys.exit(1)

            if args.json:
                print(json.dumps(entity.__dict__, default=str, indent=2))
            else:
                if item_type == "video":
                    print_media_info_card(entity)
                else:
                    console.print(f"[bold cyan]📚 Playlist:[/bold cyan] {entity.title} ({len(entity.entries)} items)")
            sys.exit(0)

        config = DownloadConfig(
            quality=QualityPreset(args.quality),
            audio_only=args.audio_only,
            audio_format=AudioFormat(args.audio_format),
            audio_bitrate=AudioBitrate(args.audio_bitrate),
            subtitles=SubtitleMode(args.subtitles),
            output_dir=Path(args.output_dir),
        )

        ok = execute_cli_download(args.url, config)
        sys.exit(0 if ok else 1)

    # 2. Interactive Rich Console Dashboard (Default)
    app = InteractiveConsoleApp()
    app.run()


if __name__ == "__main__":
    main()
