# YouTube Downloader

A fast, production-grade console application for downloading YouTube videos, playlists, and audio with a modern terminal interface.

---

## Features

- **Interactive Menu**: Smooth keyboard navigation with number key shortcuts (`1`–`6`) to quickly jump between options.
- **Quality Options**: Download in 4K, 2K, 1080p, 720p, 480p, or Best Available quality.
- **Audio Extraction**: Download high-quality audio tracks in MP3, M4A, or FLAC formats.
- **Selective Playlist Downloader**: Interactive checklist table to pick specific videos from any playlist, auto-numbered (`01-`, `02-`).
- **Auto Subtitle Embedding**: Automatically downloads and embeds English subtitles directly into `.mp4` video files via FFmpeg.
- **Batch Subtitle Embedder**: Easily scan local folders to pair `.mp4` videos with `.srt` subtitles and embed them in one click.
- **Live Progress Dashboard**: Real-time progress bars showing download speed, ETA countdown, and status.
- **Direct CLI Mode**: Pass command-line flags to run direct downloads without menus.

---

## Quick Start

### 1. Installation

Dependencies and project metadata are managed via `pyproject.toml`.

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies using pyproject.toml
pip install -e .
# Or with uv:
uv pip install -e .
```

### 2. Run the App

```bash
python main.py
```

### 3. Prerequisites

- **Python 3.12+**
- **FFmpeg** (required for audio conversion & subtitle embedding):
  - **Linux**: `sudo apt install ffmpeg`
  - **macOS**: `brew install ffmpeg`
  - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

---

## Usage Guide

### 1. Interactive Mode (Default)

Launch the interactive app:

```bash
python main.py
```

Use the arrow keys or press number keys `1`–`6` to navigate options:

1. **Download Video** – Single video download with quality & subtitle selection.
2. **Download Playlist** – Download selected playlist items.
3. **Download Audio** – Extract audio only (MP3 / M4A / FLAC).
4. **Batch Embed Subtitles** – Embed local `.srt` files into `.mp4` videos.
5. **View Downloads** – List downloaded files in `./downloads`.
6. **Exit** – Close the app.

---

### 2. Command Line Mode

Run direct downloads without entering interactive menus:

```bash
# Download a video in 1080p
python main.py --url "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" --quality 1080p

# Download audio only (MP3)
python main.py --url "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" --audio-only --audio-format mp3
```

---

## Troubleshooting

- **FFmpeg Not Found**: Ensure FFmpeg is installed and added to your system PATH (`ffmpeg -version`).
- **Download Cancelled**: Press <kbd>Ctrl</kbd>+<kbd>C</kbd> at any prompt to return to the main menu or exit cleanly.

---

## License

MIT License
