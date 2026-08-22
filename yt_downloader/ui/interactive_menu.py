"""
Interactive Rich Console Dashboard with dynamic defaults, stepwise back navigation, and download summary.
"""

import sys
from pathlib import Path
from typing import Optional, List, Tuple, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.text import Text
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
from yt_downloader.core.models import DownloadConfig, DownloadTask, TaskProgress, format_bytes, MediaItem, PlaylistInfo
from yt_downloader.infrastructure.ffmpeg_engine import FFmpegEngine
from yt_downloader.infrastructure.ytdlp_engine import YtDlpEngine
from yt_downloader.services.config_service import ConfigService
from yt_downloader.services.history_service import HistoryService
from yt_downloader.services.media_service import MediaService
from yt_downloader.services.subtitle_service import SubtitleService
from yt_downloader.services.download_manager import DownloadManager

console = Console()


def prompt_numbered_choice(
    title: str,
    options: List[Tuple[str, Any]],
    default_idx: int = 1,
    back_label: str = "Back to previous step",
) -> Any:
    """Displays a numbered list of choices with choice [0] to go back to the previous step."""
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    for idx, (label, _) in enumerate(options, 1):
        is_def = " [dim](default)[/dim]" if idx == default_idx else ""
        console.print(f"  [bold cyan][{idx}][/bold cyan] {label}{is_def}")

    console.print(f"  [bold yellow][0][/bold yellow] 🔙 {back_label}")

    valid_choices = [str(i) for i in range(0, len(options) + 1)]

    choice = Prompt.ask(
        "\n[bold cyan]Select choice[/bold cyan]",
        choices=valid_choices,
        default=str(default_idx),
        show_choices=False,
    )

    if choice == "0":
        return None

    return options[int(choice) - 1][1]


class InteractiveConsoleApp:
    """Rich interactive console dashboard with dynamic settings and stepwise back navigation."""

    def __init__(self):
        self.ffmpeg_engine = FFmpegEngine()
        self.ytdlp_engine = YtDlpEngine(self.ffmpeg_engine)
        self.config_service = ConfigService()
        self.history_service = HistoryService()
        self.media_service = MediaService(self.ytdlp_engine)
        self.subtitle_service = SubtitleService(self.ffmpeg_engine)
        self.download_manager = DownloadManager(
            engine=self.ytdlp_engine,
            history_service=self.history_service,
            config_service=self.config_service,
        )

    def print_banner(self):
        console.clear()
        ffmpeg_st = (
            f"[bold green]✓ FFmpeg {self.ffmpeg_engine.ffmpeg_version or 'Ready'}[/bold green]"
            if self.ffmpeg_engine.is_ffmpeg_available
            else "[bold yellow]⚠️ FFmpeg Missing[/bold yellow]"
        )
        content = Text.from_markup(
            f"[bold cyan]⚡ YT-DOWNLOADER PRO v2.0[/bold cyan]\n"
            f"[dim]Clean Architecture • High Performance • Multi-Format[/dim]\n\n"
            f"System Engine: {ffmpeg_st}"
        )
        console.print(Panel(content, border_style="cyan", padding=(0, 2)))

    def run(self):
        while True:
            try:
                self.print_banner()
                console.print()

                menu_table = Table.grid(padding=(0, 2))
                menu_table.add_column(style="bold cyan", justify="right")
                menu_table.add_column(style="bold white")

                menu_table.add_row("[1]", "📹 Download Single Video")
                menu_table.add_row("[2]", "📚 Download Playlist (Selective)")
                menu_table.add_row("[3]", "🎵 Extract High-Quality Audio")
                menu_table.add_row("[4]", "⚙️ Batch Embed Subtitles (Local Folder)")
                menu_table.add_row("[5]", "📁 View Media Library & History")
                menu_table.add_row("[6]", "🛠️ Configuration & Settings")
                menu_table.add_row("[0]", "🚪 Exit")

                console.print(Panel(menu_table, title="[bold cyan]Main Menu[/bold cyan]", border_style="blue", padding=(1, 2)))

                choice = Prompt.ask(
                    "\n[bold cyan]Select an option[/bold cyan]",
                    choices=["0", "1", "2", "3", "4", "5", "6"],
                    default="1",
                    show_choices=False,
                )

                if choice == "0":
                    console.print("\n[bold cyan]Goodbye! 👋[/bold cyan]")
                    sys.exit(0)
                elif choice == "1":
                    self.handle_video()
                elif choice == "2":
                    self.handle_playlist()
                elif choice == "3":
                    self.handle_audio()
                elif choice == "4":
                    self.handle_batch()
                elif choice == "5":
                    self.handle_library()
                elif choice == "6":
                    self.handle_settings()

            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold cyan]Goodbye! 👋[/bold cyan]")
                sys.exit(0)

    def _wait_enter(self):
        try:
            Prompt.ask("\n[dim]Press Enter to continue...[/dim]", default="", show_default=False)
        except (KeyboardInterrupt, EOFError):
            pass

    # ==========================================
    # Dynamic Options & Default Index Helpers
    # ==========================================
    def _get_quality_options(self) -> List[Tuple[str, QualityPreset]]:
        return [
            ("1080p (Full HD)", QualityPreset.FHD_1080P),
            ("720p (HD Standard)", QualityPreset.HD_720P),
            ("480p (SD Compact)", QualityPreset.SD_480P),
            ("1440p (2K Quad HD)", QualityPreset.QHD_2K),
            ("2160p (4K Ultra HD)", QualityPreset.UHD_4K),
            ("360p (Low Quality)", QualityPreset.SD_360P),
            ("Best Available (Highest Possible)", QualityPreset.BEST),
        ]

    def _get_quality_default_idx(self) -> int:
        cur = self.config_service.config.default_quality
        for idx, (_, val) in enumerate(self._get_quality_options(), 1):
            if val == cur:
                return idx
        return 1

    def _get_subtitle_options(self) -> List[Tuple[str, SubtitleMode]]:
        return [
            ("Embed subtitles directly into video (MP4/MKV)", SubtitleMode.EMBED),
            ("Save separate .srt subtitle file", SubtitleMode.SEPARATE),
            ("No subtitles", SubtitleMode.NONE),
        ]

    def _get_subtitle_default_idx(self) -> int:
        cur = self.config_service.config.default_subtitle_mode
        for idx, (_, val) in enumerate(self._get_subtitle_options(), 1):
            if val == cur:
                return idx
        return 1

    def _get_audio_format_options(self) -> List[Tuple[str, AudioFormat]]:
        return [
            ("MP3 (Universal compatibility)", AudioFormat.MP3),
            ("M4A (Apple / AAC High Efficiency)", AudioFormat.M4A),
            ("FLAC (Lossless Studio Quality)", AudioFormat.FLAC),
            ("OPUS (Modern / Best Compression)", AudioFormat.OPUS),
            ("WAV (Uncompressed Studio Master)", AudioFormat.WAV),
            ("AAC (Standard Advanced Audio)", AudioFormat.AAC),
        ]

    def _get_audio_format_default_idx(self) -> int:
        cur = self.config_service.config.default_audio_format
        for idx, (_, val) in enumerate(self._get_audio_format_options(), 1):
            if val == cur:
                return idx
        return 1

    def _get_bitrate_options(self) -> List[Tuple[str, AudioBitrate]]:
        return [
            ("320 kbps (Maximum Quality)", AudioBitrate.B320),
            ("256 kbps (Very High Quality)", AudioBitrate.B256),
            ("192 kbps (High Quality - Recommended)", AudioBitrate.B192),
            ("128 kbps (Standard Quality)", AudioBitrate.B128),
            ("Auto (Best Variable Bitrate)", AudioBitrate.AUTO),
        ]

    def _get_bitrate_default_idx(self) -> int:
        cur = self.config_service.config.default_audio_bitrate
        for idx, (_, val) in enumerate(self._get_bitrate_options(), 1):
            if val == cur:
                return idx
        return 3

    def _print_video_card(self, item: MediaItem):
        info_table = Table.grid(padding=(0, 2))
        info_table.add_column(style="cyan", justify="right")
        info_table.add_column(style="bold white")
        info_table.add_row("Title:", item.title)
        info_table.add_row("Channel:", item.uploader)
        info_table.add_row("Duration:", item.duration_str)
        info_table.add_row("Views:", f"{item.view_count:,}")
        info_table.add_row("Available Streams:", ", ".join(item.available_resolutions[:6]) or "Auto")
        console.print(Panel(info_table, title="[bold green]Video Information[/bold green]", border_style="green"))

    def _print_download_summary_card(self, title: str, config: DownloadConfig):
        """Displays a summary card of chosen options before download begins."""
        summary_table = Table.grid(padding=(0, 2))
        summary_table.add_column(style="cyan bold", justify="right")
        summary_table.add_column(style="bold white")

        summary_table.add_row("Title:", title)
        if config.audio_only:
            summary_table.add_row("Extraction Mode:", f"[bold green]Audio Only ({config.audio_format.value.upper()} @ {config.audio_bitrate.value} kbps)[/bold green]")
        else:
            summary_table.add_row("Target Quality:", f"[bold green]{config.quality.value} ({config.quality.label})[/bold green]")
            summary_table.add_row("Subtitles:", f"[yellow]{config.subtitles.label}[/yellow]")

        summary_table.add_row("Save Destination:", str(Path(config.output_dir).resolve()))
        summary_table.add_row("Post-Processing:", "Embed Cover Art • Embed ID3 Metadata & Chapters")

        console.print(Panel(summary_table, title="[bold cyan]🚀 Download Summary & Plan[/bold cyan]", border_style="cyan", padding=(0, 2)))

    # ==========================================
    # 1. Single Video Stepwise Flow
    # ==========================================
    def handle_video(self):
        url = ""
        item: Optional[MediaItem] = None
        quality: Optional[QualityPreset] = None
        subtitles: Optional[SubtitleMode] = None
        step = 1

        while step > 0:
            if step == 1:
                console.print("\n[bold cyan]📹 Single Video Download[/bold cyan]")
                if url:
                    url_input = Prompt.ask("Enter YouTube Video URL (or 0 to return to Main Menu)", default=url)
                else:
                    url_input = Prompt.ask("Enter YouTube Video URL (or 0 to return to Main Menu)")

                if url_input.strip() == "0" or not url_input.strip():
                    return

                url = url_input.strip()
                with console.status("[bold cyan]Fetching video metadata...", spinner="dots"):
                    item = self.media_service.fetch_video(url)

                if not item:
                    console.print("[bold red]✗ Could not retrieve video information. Check URL.[/bold red]")
                    self._wait_enter()
                    continue

                self._print_video_card(item)
                step = 2

            elif step == 2:
                quality = prompt_numbered_choice(
                    "Step 2: Select Target Video Quality",
                    self._get_quality_options(),
                    default_idx=self._get_quality_default_idx(),
                    back_label="Back to URL input",
                )
                if quality is None:
                    step = 1
                    continue
                step = 3

            elif step == 3:
                subtitles = prompt_numbered_choice(
                    "Step 3: Select Subtitles Strategy",
                    self._get_subtitle_options(),
                    default_idx=self._get_subtitle_default_idx(),
                    back_label="Back to Quality selection",
                )
                if subtitles is None:
                    step = 2
                    continue
                step = 4

            elif step == 4:
                config = DownloadConfig(
                    quality=quality,
                    audio_only=False,
                    subtitles=subtitles,
                    output_dir=Path(self.config_service.config.default_output_dir),
                    embed_thumbnail=True,
                    embed_metadata=True,
                )
                self._print_download_summary_card(item.title, config)
                self._execute_live_download(url, config, item.title)
                self._wait_enter()
                return

    # ==========================================
    # 2. Playlist Stepwise Flow
    # ==========================================
    def handle_playlist(self):
        url = ""
        info: Optional[PlaylistInfo] = None
        scope = "all"
        selected_entries: List[Any] = []
        quality: Optional[QualityPreset] = None
        step = 1

        while step > 0:
            if step == 1:
                console.print("\n[bold cyan]📚 Playlist Downloader[/bold cyan]")
                if url:
                    url_input = Prompt.ask("Enter Playlist URL (or 0 to return to Main Menu)", default=url)
                else:
                    url_input = Prompt.ask("Enter Playlist URL (or 0 to return to Main Menu)")

                if url_input.strip() == "0" or not url_input.strip():
                    return

                url = url_input.strip()
                with console.status("[bold cyan]Fetching playlist items...", spinner="dots"):
                    info = self.media_service.fetch_playlist(url)

                if not info or not info.entries:
                    console.print("[bold red]✗ Could not retrieve playlist. Check URL.[/bold red]")
                    self._wait_enter()
                    continue

                console.print(f"\n[bold green]Found {len(info.entries)} videos in playlist:[/bold green] {info.title}")

                table = Table(title=info.title, border_style="cyan")
                table.add_column("#", style="cyan", justify="right")
                table.add_column("Title", style="white")
                table.add_column("Duration", style="yellow")

                for entry in info.entries[:25]:
                    title_display = (entry.title or f"Video {entry.index}")[:55]
                    table.add_row(f"{entry.index:02d}", title_display, entry.duration_str)

                if len(info.entries) > 25:
                    table.add_row("...", f"... and {len(info.entries) - 25} more videos", "")

                console.print(table)
                step = 2

            elif step == 2:
                scope_options = [
                    (f"Download ALL ({len(info.entries)}) videos in playlist", "all"),
                    ("Select specific video numbers or range (e.g. 1-5, 8, 10-12)", "range"),
                ]
                scope = prompt_numbered_choice(
                    "Step 2: Download Scope",
                    scope_options,
                    default_idx=1,
                    back_label="Back to URL input",
                )
                if scope is None:
                    step = 1
                    continue

                if scope == "range":
                    step = 3
                else:
                    selected_entries = info.entries
                    step = 4

            elif step == 3:
                range_str = Prompt.ask("Enter video numbers or range (e.g. 1-5, 8, 10-12) or 0 to go back")
                if range_str.strip() == "0":
                    step = 2
                    continue

                indices = self._parse_range(range_str, len(info.entries))
                selected_entries = [e for e in info.entries if e.index in indices]

                if not selected_entries:
                    console.print("[yellow]No valid items selected from range.[/yellow]")
                    continue

                step = 4

            elif step == 4:
                quality = prompt_numbered_choice(
                    f"Step 3: Select Target Quality for {len(selected_entries)} Selected Video(s)",
                    self._get_quality_options(),
                    default_idx=self._get_quality_default_idx(),
                    back_label="Back to Scope selection",
                )
                if quality is None:
                    step = 2
                    continue
                step = 5

            elif step == 5:
                pad = len(str(len(selected_entries)))
                for i, item in enumerate(selected_entries, 1):
                    prefix = str(i).zfill(pad)
                    cfg = DownloadConfig(
                        quality=quality,
                        output_dir=Path(self.config_service.config.default_output_dir),
                        custom_prefix=prefix,
                    )
                    v_title = item.title or f"Video {i}"
                    console.print(f"\n[bold cyan][{i}/{len(selected_entries)}][/bold cyan] {v_title}")
                    self._execute_live_download(item.url, cfg, v_title)

                console.print("\n[bold green]✓ Playlist Download Finished![/bold green]")
                self._wait_enter()
                return

    # ==========================================
    # 3. Audio Extraction Stepwise Flow
    # ==========================================
    def handle_audio(self):
        url = ""
        item: Optional[MediaItem] = None
        fmt: Optional[AudioFormat] = None
        bitrate: Optional[AudioBitrate] = None
        step = 1

        while step > 0:
            if step == 1:
                console.print("\n[bold cyan]🎵 High-Quality Audio Extraction[/bold cyan]")
                if url:
                    url_input = Prompt.ask("Enter YouTube URL (or 0 to return to Main Menu)", default=url)
                else:
                    url_input = Prompt.ask("Enter YouTube URL (or 0 to return to Main Menu)")

                if url_input.strip() == "0" or not url_input.strip():
                    return

                url = url_input.strip()
                with console.status("[bold cyan]Fetching track information...", spinner="dots"):
                    item = self.media_service.fetch_video(url)

                if item:
                    console.print(f"🎵 [bold green]{item.title}[/bold green] ([yellow]{item.duration_str}[/yellow]) by [cyan]{item.uploader}[/cyan]")
                step = 2

            elif step == 2:
                fmt = prompt_numbered_choice(
                    "Step 2: Select Audio Codec / Format",
                    self._get_audio_format_options(),
                    default_idx=self._get_audio_format_default_idx(),
                    back_label="Back to URL input",
                )
                if fmt is None:
                    step = 1
                    continue
                step = 3

            elif step == 3:
                bitrate = prompt_numbered_choice(
                    "Step 3: Select Bitrate Quality",
                    self._get_bitrate_options(),
                    default_idx=self._get_bitrate_default_idx(),
                    back_label="Back to Audio Codec selection",
                )
                if bitrate is None:
                    step = 2
                    continue
                step = 4

            elif step == 4:
                title = item.title if item else "Audio Track"
                config = DownloadConfig(
                    audio_only=True,
                    audio_format=fmt,
                    audio_bitrate=bitrate,
                    output_dir=Path(self.config_service.config.default_output_dir),
                    embed_thumbnail=True,
                    embed_metadata=True,
                )
                self._print_download_summary_card(title, config)
                self._execute_live_download(url, config, f"[Audio] {title}")
                self._wait_enter()
                return

    # ==========================================
    # 4. Batch Subtitles Stepwise Flow
    # ==========================================
    def handle_batch(self):
        default_dir = str(Path(self.config_service.config.default_output_dir).resolve())
        folder_str = default_dir
        items: List[Any] = []
        step = 1

        while step > 0:
            if step == 1:
                console.print("\n[bold cyan]⚙️ Batch Subtitle Studio[/bold cyan]")
                folder_input = Prompt.ask("Target Folder to scan (or 0 to return to Main Menu)", default=folder_str)
                if folder_input.strip() == "0":
                    return

                folder_str = folder_input.strip()
                folder = Path(folder_str)
                items = self.subtitle_service.scan_folder(folder)
                if not items:
                    console.print("[yellow]No video files found in directory.[/yellow]")
                    self._wait_enter()
                    continue

                table = Table(title=f"Scanned Directory: {folder}", border_style="cyan")
                table.add_column("Status", style="bold")
                table.add_column("Video File", style="white")
                table.add_column("Subtitle Candidate", style="yellow")

                ready = [i for i in items if i.status == "ready"]
                for it in items:
                    st = "[bold green]✓ Ready[/bold green]" if it.status == "ready" else "[bold red]✗ Missing Sub[/bold red]"
                    sub_name = it.subtitle_file.name if it.subtitle_file else "None"
                    table.add_row(st, it.video_file.name, sub_name)

                console.print(table)

                if not ready:
                    console.print("[yellow]No ready video/subtitle pairs found for embedding.[/yellow]")
                    self._wait_enter()
                    continue

                step = 2

            elif step == 2:
                ready = [i for i in items if i.status == "ready"]
                batch_options = [
                    (f"Embed subtitles into {len(ready)} video(s) now", True),
                ]
                action = prompt_numbered_choice(
                    "Step 2: Confirm Subtitle Embedding",
                    batch_options,
                    default_idx=1,
                    back_label="Back to Folder scan",
                )
                if action is None:
                    step = 1
                    continue

                with Progress(console=console) as progress:
                    p_task = progress.add_task("Embedding subtitles...", total=len(ready))
                    for it in ready:
                        self.subtitle_service.embed_file(it.video_file, it.subtitle_file)
                        progress.advance(p_task)
                console.print("\n[bold green]✓ All subtitles embedded successfully![/bold green]")
                self._wait_enter()
                return

    # ==========================================
    # 5. Media Library Flow
    # ==========================================
    def handle_library(self):
        while True:
            stats = self.history_service.get_statistics()
            console.print(f"\n[bold cyan]📁 Media Library[/bold cyan] (Total: {stats['total_downloads']} files | {stats['total_size_str']})")

            records = self.history_service.list_all()
            if not records:
                console.print("[yellow]No downloads recorded yet.[/yellow]")
                self._wait_enter()
                return

            table = Table(title="Downloaded Media History", border_style="cyan")
            table.add_column("#", style="cyan", justify="right")
            table.add_column("Title", style="white")
            table.add_column("Type", style="magenta")
            table.add_column("Quality", style="yellow")
            table.add_column("Size", style="green")
            table.add_column("Date", style="dim")

            for idx, r in enumerate(records[:20], 1):
                table.add_row(str(idx), r.title[:45], r.media_type.upper(), r.quality_or_format, r.file_size_str, r.completed_at)

            console.print(table)

            action_options = [
                ("▶ Open / Play Media in default player", "open_file"),
                ("📁 Open Containing Folder in File Manager", "open_folder"),
                ("🗑️ Delete Record from History", "delete_record"),
                ("🧹 Clear All Download History", "clear_history"),
            ]
            action = prompt_numbered_choice("Library Actions:", action_options, default_idx=1, back_label="Return to Main Menu")
            if action is None:
                return

            if action == "open_file":
                num = Prompt.ask(f"Enter record number [1-{min(20, len(records))}] (or 0 to cancel)", default="1")
                if num.strip() != "0":
                    try:
                        rec_idx = int(num) - 1
                        if 0 <= rec_idx < len(records):
                            self.history_service.open_file_in_system(records[rec_idx].file_path)
                    except Exception:
                        pass
            elif action == "open_folder":
                self.history_service.open_folder_in_system(self.config_service.config.default_output_dir)
            elif action == "delete_record":
                num = Prompt.ask(f"Enter record number to delete [1-{min(20, len(records))}] (or 0 to cancel)", default="1")
                if num.strip() != "0":
                    try:
                        rec_idx = int(num) - 1
                        if 0 <= rec_idx < len(records):
                            self.history_service.delete(records[rec_idx].id)
                            console.print("[bold green]✓ Record removed![/bold green]")
                    except Exception:
                        pass
            elif action == "clear_history":
                confirm = prompt_numbered_choice(
                    "Confirm clear all history?",
                    [("Yes, clear all history", True), ("No, keep history", False)],
                    default_idx=2,
                    back_label="Cancel and return to Library",
                )
                if confirm is True:
                    self.history_service.clear()
                    console.print("[bold green]✓ All history cleared![/bold green]")

    # ==========================================
    # 6. Settings Flow
    # ==========================================
    def handle_settings(self):
        while True:
            cfg = self.config_service.config
            console.print("\n[bold cyan]🛠️ Configuration & Preferences[/bold cyan]")

            settings_table = Table.grid(padding=(0, 2))
            settings_table.add_column(style="cyan", justify="right")
            settings_table.add_column(style="bold white")
            settings_table.add_row("1. Default Output Directory:", cfg.default_output_dir)
            settings_table.add_row("2. Default Quality:", f"{cfg.default_quality.value} ({cfg.default_quality.label})")
            settings_table.add_row("3. Default Audio Codec:", f"{cfg.default_audio_format.value.upper()} ({cfg.default_audio_format.label})")
            settings_table.add_row("4. Default Subtitles Mode:", cfg.default_subtitle_mode.label)
            settings_table.add_row("5. Concurrent Workers Limit:", str(cfg.max_concurrent_downloads))

            console.print(Panel(settings_table, title="[bold green]Current Settings[/bold green]", border_style="green"))

            setting_options = [
                ("Change Default Output Directory", "dir"),
                ("Change Default Video Quality", "quality"),
                ("Change Default Audio Codec", "audio"),
                ("Change Default Subtitle Mode", "subtitles"),
                ("Change Concurrent Worker Count", "workers"),
            ]
            action = prompt_numbered_choice("Select Setting to Modify:", setting_options, default_idx=1, back_label="Return to Main Menu")
            if action is None:
                return

            if action == "dir":
                new_dir = Prompt.ask("Enter new default output directory path (or 0 to cancel)", default=cfg.default_output_dir)
                if new_dir.strip() != "0":
                    self.config_service.update(default_output_dir=new_dir)
                    console.print("[bold green]✓ Output directory updated![/bold green]")
            elif action == "quality":
                q = prompt_numbered_choice(
                    "Select Default Quality:",
                    self._get_quality_options(),
                    default_idx=self._get_quality_default_idx(),
                    back_label="Cancel",
                )
                if q is not None:
                    self.config_service.update(default_quality=q)
                    console.print(f"[bold green]✓ Default quality updated to {q.value}![/bold green]")
            elif action == "audio":
                a = prompt_numbered_choice(
                    "Select Default Audio Codec:",
                    self._get_audio_format_options(),
                    default_idx=self._get_audio_format_default_idx(),
                    back_label="Cancel",
                )
                if a is not None:
                    self.config_service.update(default_audio_format=a)
                    console.print(f"[bold green]✓ Default audio codec updated to {a.value.upper()}![/bold green]")
            elif action == "subtitles":
                s = prompt_numbered_choice(
                    "Select Default Subtitles Mode:",
                    self._get_subtitle_options(),
                    default_idx=self._get_subtitle_default_idx(),
                    back_label="Cancel",
                )
                if s is not None:
                    self.config_service.update(default_subtitle_mode=s)
                    console.print(f"[bold green]✓ Default subtitles mode updated to {s.label}![/bold green]")
            elif action == "workers":
                worker_choices = [
                    ("1 Worker (Low bandwidth / single thread)", 1),
                    ("2 Workers (Balanced)", 2),
                    ("3 Workers (Recommended)", 3),
                    ("4 Workers (High speed)", 4),
                    ("6 Workers (High bandwidth)", 6),
                ]
                cur_workers = cfg.max_concurrent_downloads
                w_def_idx = next((i for i, (_, val) in enumerate(worker_choices, 1) if val == cur_workers), 3)
                w = prompt_numbered_choice("Select Concurrent Worker Count:", worker_choices, default_idx=w_def_idx, back_label="Cancel")
                if w is not None:
                    self.config_service.update(max_concurrent_downloads=w)
                    console.print(f"[bold green]✓ Worker count updated to {w}![/bold green]")

    def _execute_live_download(self, url: str, config: DownloadConfig, title: str):
        quality_tag = config.audio_format.value.upper() if config.audio_only else config.quality.value
        task = DownloadTask(url=url, title=title, config=config)

        console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn(f"[bold cyan][{quality_tag}][/bold cyan] [bold white]{{task.description}}[/bold white]"),
            BarColumn(bar_width=35, complete_style="cyan"),
            TaskProgressColumn(),
            TextColumn("{task.fields[size_text]}"),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            bar = progress.add_task(f"{title[:35]}", total=None, size_text="")

            def on_progress(p: TaskProgress):
                if p.status == TaskStatus.DOWNLOADING:
                    cur_str = format_bytes(p.downloaded_bytes)
                    tot_str = format_bytes(p.total_bytes) if p.total_bytes > 0 else "--"
                    if p.total_bytes > 0:
                        progress.update(
                            bar,
                            completed=p.downloaded_bytes,
                            total=p.total_bytes,
                            size_text=f"{cur_str} / {tot_str}",
                        )
                    else:
                        progress.update(bar, size_text=cur_str)
                elif p.status == TaskStatus.PROCESSING:
                    progress.update(bar, description="[bold yellow]Processing / Muxing...")

            try:
                out = self.ytdlp_engine.download_stream(task, progress_callback=on_progress)
                if out and out.exists():
                    progress.update(bar, completed=100, total=100, description="[bold green]✓ Completed")
                    file_size = format_bytes(out.stat().st_size)

                    completion_table = Table.grid(padding=(0, 2))
                    completion_table.add_column(style="green bold", justify="right")
                    completion_table.add_column(style="white")
                    completion_table.add_row("Quality:", f"[bold cyan]{quality_tag}[/bold cyan]")
                    completion_table.add_row("File Size:", f"[bold green]{file_size}[/bold green]")
                    completion_table.add_row("Saved Location:", str(out.resolve()))

                    console.print()
                    console.print(Panel(completion_table, title="[bold green]✓ Download Finished Successfully[/bold green]", border_style="green", padding=(0, 2)))

                    media_type = "audio" if config.audio_only else "video"
                    quality_str = config.audio_format.value if config.audio_only else config.quality.value
                    self.history_service.record_completed_download(
                        task_id=task.id,
                        url=url,
                        title=task.title,
                        uploader="YouTube",
                        duration_str="--:--",
                        file_path=out,
                        media_type=media_type,
                        quality_or_format=quality_str,
                    )
            except Exception as e:
                console.print(f"\n[bold red]✗ Download failed:[/bold red] {str(e)}")

    @staticmethod
    def _parse_range(range_str: str, max_val: int) -> List[int]:
        res = set()
        for part in range_str.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    s, e = int(start.strip()), int(end.strip())
                    for i in range(max(1, s), min(max_val, e) + 1):
                        res.add(i)
                except Exception:
                    pass
            elif part.isdigit():
                val = int(part)
                if 1 <= val <= max_val:
                    res.add(val)
        return sorted(list(res))
