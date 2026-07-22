"""
Terminal User Interface (TUI) components and app controller.
"""

import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)
from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from yt_downloader.models import (
    VideoInfo,
    PlaylistInfo,
    PlaylistItem,
    DownloadOpts,
    BatchItem,
)
from yt_downloader.engine import Downloader, SubtitleEmbedder, scan_batch, format_bytes

console = Console()


def bind_number_shortcuts(prompt, count: int):
    """Binds keys 1..count to move cursor hover pointer to that index without auto-executing."""
    for i in range(count):
        key = str(i + 1)

        def make_handler(idx):
            def handler(event):
                prompt.content_control.selected_choice_index = idx
                if hasattr(event, "app") and event.app:
                    event.app.invalidate()

            return handler

        try:
            prompt.register_kb(key)(make_handler(i))
        except Exception:
            pass


def display_banner(ffmpeg_ok: bool):
    console.clear()
    text = Text()
    text.append("⚡ YouTube Downloader\n", style="bold cyan")
    text.append("Video & Audio Downloader\n", style="dim")
    text.append("System: ", style="dim")
    if ffmpeg_ok:
        text.append("✓ FFmpeg Ready", style="bold green")
    else:
        text.append("⚠️ FFmpeg Not Found", style="bold yellow")
    console.print(Panel(text, border_style="cyan", padding=(0, 2)))


def display_info_card(title: str, items: List[tuple]):
    table = Table.grid(padding=(0, 2))
    table.add_column(style="cyan", justify="right")
    table.add_column(style="bold white")

    for k, v in items:
        table.add_row(k, str(v))

    console.print(Panel(table, title=f"[bold magenta]{title}[/bold magenta]", border_style="magenta", padding=(0, 2)))


class App:
    def __init__(self, output_dir: str = "downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.downloader = Downloader()
        self.embedder = SubtitleEmbedder()

    def run(self):
        while True:
            try:
                display_banner(self.embedder.is_available)
                console.print()
                choices = [
                    Choice("single", "1. 📹 Download Video"),
                    Choice("playlist", "2. 📚 Download Playlist"),
                    Choice("audio", "3. 🎵 Download Audio (MP3)"),
                    Choice("batch", "4. ⚙️ Batch Embed Subtitles"),
                    Choice("library", "5. 📁 View Downloads"),
                    Choice("exit", "6. 🚪 Exit"),
                ]
                prompt = inquirer.select(
                    message="Select action:",
                    choices=choices,
                    default="single",
                    raise_keyboard_interrupt=False,
                )
                bind_number_shortcuts(prompt, len(choices))
                action = prompt.execute()

                if not action or action == "exit":
                    console.print("\n[bold cyan]Goodbye! 👋[/bold cyan]")
                    sys.exit(0)

                if action == "single":
                    self.handle_single()
                elif action == "playlist":
                    self.handle_playlist()
                elif action == "audio":
                    self.handle_audio()
                elif action == "batch":
                    self.handle_batch()
                elif action == "library":
                    self.handle_library()

            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold cyan]Goodbye! 👋[/bold cyan]")
                sys.exit(0)

    def _wait_enter(self):
        try:
            input("\nPress Enter to continue...")
        except (KeyboardInterrupt, EOFError):
            pass

    def _prompt_url(self, msg: str = "Enter YouTube URL:") -> Optional[str]:
        res = inquirer.text(message=msg, raise_keyboard_interrupt=False).execute()
        return res.strip() if res else None

    def _prompt_options(self, is_audio: bool = False) -> Optional[DownloadOpts]:
        opts = DownloadOpts(output_dir=self.output_dir, audio_only=is_audio)

        if is_audio:
            fmt_choices = [
                Choice("mp3", "1. MP3"),
                Choice("m4a", "2. M4A"),
                Choice("flac", "3. FLAC"),
            ]
            fmt_p = inquirer.select(message="Audio Format:", choices=fmt_choices, raise_keyboard_interrupt=False)
            bind_number_shortcuts(fmt_p, len(fmt_choices))
            fmt = fmt_p.execute()
            if not fmt:
                return None
            opts.audio_format = fmt

            bit_choices = [Choice("320", "1. 320 kbps"), Choice("192", "2. 192 kbps"), Choice("128", "3. 128 kbps")]
            bit_p = inquirer.select(message="Bitrate:", choices=bit_choices, raise_keyboard_interrupt=False)
            bind_number_shortcuts(bit_p, len(bit_choices))
            bit = bit_p.execute()
            if not bit:
                return None
            opts.audio_bitrate = bit
        else:
            q_choices = [
                Choice("1080p", "1. 1080p (Full HD)"),
                Choice("720p", "2. 720p (HD)"),
                Choice("480p", "3. 480p (SD)"),
                Choice("1440p", "4. 1440p (2K)"),
                Choice("2160p", "5. 2160p (4K)"),
                Choice("best", "6. Best Quality"),
            ]
            q_p = inquirer.select(message="Quality:", choices=q_choices, default="1080p", raise_keyboard_interrupt=False)
            bind_number_shortcuts(q_p, len(q_choices))
            q = q_p.execute()
            if not q:
                return None
            opts.quality = q

            if self.embedder.is_available:
                sub_choices = [
                    Choice("embed", "1. Embed subtitles into MP4"),
                    Choice("separate", "2. Save separate .srt file"),
                    Choice("none", "3. No subtitles"),
                ]
                sub_p = inquirer.select(message="Subtitles:", choices=sub_choices, raise_keyboard_interrupt=False)
                bind_number_shortcuts(sub_p, len(sub_choices))
                sub = sub_p.execute()
                if not sub:
                    return None
                opts.subtitles = sub
            else:
                opts.subtitles = "separate"

        return opts

    def _execute_download(self, url: str, opts: DownloadOpts, title: str, prefix: Optional[str] = None):
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=35, complete_style="cyan"),
            TaskProgressColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"{title[:30]}...", total=100)

            def hook(d):
                st = d.get("status")
                if st == "downloading":
                    tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    cur = d.get("downloaded_bytes") or 0
                    pct = (cur / tot * 100) if tot > 0 else 0
                    fn = Path(d.get("filename", "")).name or title
                    progress.update(task, completed=pct, description=f"{fn[:30]}")
                elif st == "finished":
                    progress.update(task, completed=95, description="Processing...")

            ok = self.downloader.download(url, opts, progress_cb=hook, prefix=prefix)
            if ok:
                progress.update(task, completed=100, description="[bold green]✓ Completed")
                console.print(f"[bold green]✓ Saved to {opts.output_dir}[/bold green]\n")
            else:
                console.print("[bold red]✗ Download failed.[/bold red]\n")

    def handle_single(self):
        url = self._prompt_url("Enter Video URL:")
        if not url:
            return

        with console.status("[bold cyan]Fetching info...", spinner="dots"):
            info = self.downloader.fetch_info(url)

        if not info or isinstance(info, PlaylistInfo):
            console.print("[bold red]Invalid video URL.[/bold red]")
            self._wait_enter()
            return

        display_info_card("📹 Video Info", [("Title:", info.title), ("Channel:", info.uploader), ("Duration:", info.duration_str), ("Views:", f"{info.view_count:,}")])
        opts = self._prompt_options(is_audio=False)
        if not opts:
            return

        self._execute_download(url, opts, info.title)
        self._wait_enter()

    def handle_playlist(self):
        url = self._prompt_url("Enter Playlist URL:")
        if not url:
            return

        with console.status("[bold cyan]Fetching playlist...", spinner="dots"):
            info = self.downloader.fetch_info(url)

        if not info or not isinstance(info, PlaylistInfo):
            console.print("[bold red]Invalid playlist URL.[/bold red]")
            self._wait_enter()
            return

        display_info_card("📚 Playlist Info", [("Title:", info.title), ("Channel:", info.uploader), ("Total:", len(info.entries))])

        choices = [Choice(value=item, name=f"[{item.index:02d}] {item.title[:50]} ({item.duration_str})", enabled=True) for item in info.entries]
        selected = inquirer.checkbox(message="Select videos (Space toggle, Enter confirm):", choices=choices, raise_keyboard_interrupt=False).execute()
        if not selected:
            self._wait_enter()
            return

        opts = self._prompt_options(is_audio=False)
        if not opts:
            return

        pad = len(str(len(selected)))
        for idx, item in enumerate(selected, 1):
            prefix = str(idx).zfill(pad)
            console.print(f"[bold cyan][{idx}/{len(selected)}][/bold cyan] {item.title}")
            self._execute_download(item.url, opts, item.title, prefix=prefix)

        console.print(Panel("[bold green]✓ Playlist Download Complete![/bold green]", border_style="green"))
        self._wait_enter()

    def handle_audio(self):
        url = self._prompt_url("Enter URL:")
        if not url:
            return

        with console.status("[bold cyan]Fetching info...", spinner="dots"):
            info = self.downloader.fetch_info(url)

        if not info:
            console.print("[bold red]Invalid URL.[/bold red]")
            self._wait_enter()
            return

        if isinstance(info, PlaylistInfo):
            display_info_card("📚 Playlist Info", [("Title:", info.title), ("Total:", len(info.entries))])
            choices = [Choice(value=item, name=f"[{item.index:02d}] {item.title[:50]}", enabled=True) for item in info.entries]
            selected = inquirer.checkbox(message="Select videos:", choices=choices, raise_keyboard_interrupt=False).execute()
            if not selected:
                return

            opts = self._prompt_options(is_audio=True)
            if not opts:
                return

            pad = len(str(len(selected)))
            for idx, item in enumerate(selected, 1):
                prefix = str(idx).zfill(pad)
                self._execute_download(item.url, opts, item.title, prefix=prefix)
        else:
            display_info_card("🎵 Video Info", [("Title:", info.title), ("Duration:", info.duration_str)])
            opts = self._prompt_options(is_audio=True)
            if not opts:
                return
            self._execute_download(url, opts, info.title)

        self._wait_enter()

    def handle_batch(self):
        try:
            folder_str = input(f"Target folder [{self.output_dir.resolve()}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        folder = Path(folder_str) if folder_str else self.output_dir.resolve()
        items = scan_batch(folder)

        if not items:
            console.print("[yellow]No video files found.[/yellow]")
            self._wait_enter()
            return

        table = Table(title="⚙️ Batch Subtitle Scanner", border_style="cyan")
        table.add_column("Video File", style="bold white")
        table.add_column("Subtitle File", style="yellow")
        table.add_column("Status", style="bold")

        ready = [i for i in items if i.status == "ready"]
        for item in items:
            sub_name = item.subtitle_file.name if item.subtitle_file else "None"
            st = "[bold green]✓ Ready[/bold green]" if item.status == "ready" else "[bold red]✗ Missing Sub[/bold red]"
            table.add_row(item.video_file.name, sub_name, st)

        console.print(table)
        if not ready:
            self._wait_enter()
            return

        confirm = inquirer.confirm(message=f"Embed subtitles into {len(ready)} video(s)?", default=True, raise_keyboard_interrupt=False).execute()
        if confirm:
            for item in ready:
                self.embedder.embed(item.video_file, item.subtitle_file)
            console.print(Panel("[bold green]✓ Subtitles Embedded![/bold green]", border_style="green"))

        self._wait_enter()

    def handle_library(self):
        if not self.output_dir.exists() or not any(self.output_dir.iterdir()):
            console.print(f"[yellow]No files in {self.output_dir}[/yellow]")
            self._wait_enter()
            return

        table = Table(title=f"📁 Downloads ({self.output_dir.resolve()})", border_style="green")
        table.add_column("Filename", style="bold white")
        table.add_column("Size", style="cyan")

        for f in sorted(self.output_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file() and not f.name.startswith("."):
                table.add_row(f.name, format_bytes(f.stat().st_size))

        console.print(table)
        self._wait_enter()
