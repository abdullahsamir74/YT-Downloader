# ⚡ YT-Downloader Pro v2.0

<div align="center">

**A high-performance YouTube downloader and media extraction suite built with Clean Architecture, an interactive terminal dashboard, and a scriptable CLI engine.**

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Engine](https://img.shields.io/badge/Engine-yt--dlp-red.svg?logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![Muxer](https://img.shields.io/badge/FFmpeg-Enabled-007808.svg?logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![UI](https://img.shields.io/badge/UI-Rich%20Dashboard-cyan.svg)](https://github.com/Textualize/rich)
[![Package Manager](https://img.shields.io/badge/uv-Fast%20Packaging-purple.svg)](https://github.com/astral-sh/uv)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 🌟 Overview

**YT-Downloader Pro** is designed for speed, flexibility, and reliability. It combines high-resolution video ripping, lossless audio extraction, selective playlist downloading, and local batch subtitle muxing into a unified terminal dashboard with live download telemetry and persistent settings.

---

## 🚀 Key Features

### 📹 Single Video Downloads
- **Multi-Resolution Support**: 4K Ultra HD (2160p), 2K Quad HD (1440p), 1080p Full HD, 720p HD, 480p, 360p, or Best Available.
- **Metadata Inspection**: Live stream discovery, duration, view count, channel name, and available resolutions.
- **Subtitles Strategy**: Embed subtitles directly into container (`.mp4` / `.mkv`), save separate `.srt` files, or omit subtitles.
- **Auto Tagging**: Automatic high-resolution thumbnail and chapter metadata embedding.

### 📚 Selective Playlist Downloader
- **Scope Selection**: Download entire playlists or select specific index ranges (e.g. `1-5, 8, 10-12`).
- **Auto-Numbering**: Automatic sequential prefixes (`01 - `, `02 - `) for organized local storage.
- **Live Summary**: Inspect full playlist metadata before initiating download batches.

### 🎵 High-Quality Audio Extraction Studio
- **Multiple Codecs**: Extract audio tracks in **MP3**, **M4A (AAC)**, **FLAC (Lossless)**, **OPUS**, **WAV**, or **AAC**.
- **Bitrate Controls**: 320 kbps (Maximum), 256 kbps, 192 kbps (Recommended), 128 kbps, or Auto VBR.
- **Album Art Embedding**: Automatic ID3 metadata and high-res cover art tagging.

### ⚙️ Batch Subtitle Studio
- **Local Directory Scanner**: Scan any local folder to detect video files paired with subtitles (`.srt`, `.vtt`, `.ass`).
- **Atomic Muxing**: Fast, lossless embedding of external subtitles into video containers using FFmpeg without re-encoding video streams.

### 📁 Media Library & History
- **Persistent Ledger**: Stores download history with file sizes, formats, timestamps, and resolutions.
- **System Integration**: Open downloaded media in default player or reveal containing directory with a single keystroke.
- **Storage Statistics**: Real-time breakdown of total files, video count, audio count, and disk space used.

### 🛠️ Persistent Settings & Dynamic Defaults
- **Customizable Preferences**: Configure default resolution, audio codec, subtitle mode, output path, and concurrent worker limits.
- **Dynamic Indicators**: Selected preferences automatically become the default options across all menus.
- **Stepwise Back Navigation**: Move between steps seamlessly using `0` to go back or return to previous prompts.

---

## 📦 Installation & Setup

Manage dependencies and virtual environments with `uv`:

```bash
# 1. Clone the repository
git clone https://github.com/abdullahsamir74/YT-Downloader.git
cd YT-Downloader

# 2. Sync and install dependencies
uv sync

# 3. Activate the virtual environment
# On Linux / macOS:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate
```

---

## 💻 Usage Guide

### 1. Interactive Dashboard (Default)

Launch the interactive console menu:

```bash
# Using activated environment:
python main.py

# Or directly with uv:
uv run python main.py
```

#### Menu Navigation
| Option | Description |
| :---: | :--- |
| <kbd>1</kbd> | 📹 **Download Single Video** (Select quality & subtitle mode) |
| <kbd>2</kbd> | 📚 **Download Playlist** (Select all or specific video ranges) |
| <kbd>3</kbd> | 🎵 **Extract Audio** (MP3, FLAC, M4A, OPUS up to 320k) |
| <kbd>4</kbd> | ⚙️ **Batch Embed Subtitles** (Scan & mux local folder) |
| <kbd>5</kbd> | 📁 **View Media Library** (Browse, play, or reveal files) |
| <kbd>6</kbd> | 🛠️ **Settings & Preferences** (Configure default paths & quality) |
| <kbd>0</kbd> | 🚪 **Back / Exit** (Step back to previous prompt or exit) |

---

### 2. Scriptable CLI Mode

Execute direct downloads or inspect metadata via command-line arguments:

```bash
# Download a video in 1080p with embedded subtitles
uv run python main.py --url "https://www.youtube.com/watch?v=..." --quality 1080p

# Download in 4K Ultra HD (2160p)
uv run python main.py --url "https://www.youtube.com/watch?v=..." --quality 2160p

# Extract audio in MP3 at 320 kbps
uv run python main.py --url "https://www.youtube.com/watch?v=..." --audio-only --audio-format mp3 --audio-bitrate 320

# Extract lossless FLAC audio
uv run python main.py --url "https://www.youtube.com/watch?v=..." --audio-only --audio-format flac

# Inspect video metadata without downloading
uv run python main.py --url "https://www.youtube.com/watch?v=..." --info

# Output inspected metadata as raw JSON
uv run python main.py --url "https://www.youtube.com/watch?v=..." --info --json

# Specify custom output directory
uv run python main.py --url "https://www.youtube.com/watch?v=..." --output-dir "/path/to/media"
```

#### CLI Reference
```
options:
  -h, --help            Show help message and exit
  --url, -u URL         YouTube video or playlist URL for direct download
  --quality, -q QUAL    Target quality: best, 2160p, 1440p, 1080p, 720p, 480p, 360p (default: 1080p)
  --audio-only, -a      Extract audio stream only
  --audio-format FMT    Audio codec: mp3, m4a, flac, opus, wav, aac (default: mp3)
  --audio-bitrate BR    Audio bitrate: 320, 256, 192, 128, 0 (default: 192)
  --subtitles, -s MODE  Subtitle strategy: embed, separate, none (default: embed)
  --output-dir, -o DIR  Custom destination directory (default: downloads)
  --info, -i            Inspect URL metadata without downloading
  --json                Output inspected metadata in JSON format
```

---

## 🛠️ System Requirements

- **Python**: `>= 3.12`
- **FFmpeg**: Recommended for stream muxing, audio transcoding, and subtitle embedding (`sudo apt install ffmpeg` / `brew install ffmpeg` / `winget install ffmpeg`).
- **uv**: Fast Python package manager ([Astral uv](https://github.com/astral-sh/uv)).

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
