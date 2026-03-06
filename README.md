# YouTube Downloader

A Python-based YouTube video and playlist downloader with quality selection, audio extraction, and automatic English subtitle downloading.

## Features

- Download single videos or entire playlists
- Multiple quality options (480p to Best Available)
- Audio-only download (MP3 format)
- Automatic English subtitle download
- Auto-embed subtitles into videos (main_Subtitles.py)
- Playlist videos numbered for organization
- Anti-blocking measures with automatic retries
- Progress tracking with speed and ETA

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install FFmpeg (Required for audio conversion and subtitle embedding)

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add to PATH.

## Usage

### Basic Version (main.py)
Downloads videos with external subtitle files:
```bash
python main.py
```

### Enhanced Version (main_Subtitles.py)
Downloads videos with embedded subtitles and playlist numbering:
```bash
python main_Subtitles.py
```

### Menu Options

1. **Download Single Video** - Download one video with quality selection
2. **Download Playlist** - Download entire YouTube playlist
3. **Download Audio Only (MP3)** - Extract audio in MP3 format
4. **Exit** - Close the application

### Quality Options

- SD (480p)
- HD (720p)
- Full HD (1080p) - Default
- 2K (1440p)
- Best Available Quality

## Files

- `main.py` - Basic downloader with subtitle files saved separately
- `main_Subtitles.py` - Enhanced version with auto-embed subtitles and playlist numbering
- `requirements.txt` - Python dependencies
- `downloads/` - Default download directory (created automatically)

## Requirements

- Python 3.7+
- yt-dlp (installed via requirements.txt)
- ffmpeg (must be installed separately)

## Notes

- English subtitles are downloaded automatically when available
- Subtitles are embedded directly into videos (main_Subtitles.py only)
- Playlist videos are numbered (01-, 02-, etc.) for easy organization
- The downloader includes anti-blocking measures and automatic retries
- Internet connection required for downloading

## Troubleshooting

**"ffmpeg not found" warning:**
- Install ffmpeg using the instructions above
- Verify installation: `ffmpeg -version`

**Download fails:**
- Check your internet connection
- Verify the YouTube URL is correct
- Try a different quality option
- The tool will automatically retry failed downloads
