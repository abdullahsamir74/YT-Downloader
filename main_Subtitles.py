"""
YouTube Video/Playlist Downloader with Quality Selection and Audio Extraction
Features: Auto-embed subtitles, Playlist numbering
Requires: pip install yt-dlp
          ffmpeg must be installed and in PATH
"""

import yt_dlp
import os
import sys
import subprocess
from pathlib import Path
import re


class YouTubeDownloader:
    def __init__(self, output_path="downloads"):
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)
        self.ffmpeg_available = None  # Cache ffmpeg check

        # Quality options mapping
        self.quality_options = {
            "1": {
                "format": "bestvideo[height<=480]+bestaudio/best[height<=480]",
                "name": "SD (480p)",
            },
            "2": {
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "name": "HD (720p)",
            },
            "3": {
                "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "name": "Full HD (1080p)",
            },
            "4": {
                "format": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
                "name": "2K (1440p)",
            },
            "5": {"format": "bestvideo+bestaudio/best", "name": "Best Quality"},
        }

    def check_ffmpeg(self):
        """Check if ffmpeg is installed (cached)"""
        if self.ffmpeg_available is not None:
            return self.ffmpeg_available

        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            self.ffmpeg_available = True
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("\n⚠️  WARNING: ffmpeg not found!")
            print("   Subtitles will NOT be embedded automatically.")
            print("   Install ffmpeg from: https://ffmpeg.org/download.html")
            self.ffmpeg_available = False
            return False

    def find_video_file(self, base_path, playlist_index=None):
        """Find the actual downloaded video file, handling filesystem character replacements"""
        folder = Path(base_path).parent

        # Get the expected filename pattern
        if playlist_index:
            pattern = f"{playlist_index}-*"
        else:
            pattern = "*"

        # Find all mp4 files matching the pattern
        video_files = list(folder.glob(f"{pattern}.mp4"))

        # Sort by modification time (most recent first)
        if video_files:
            video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return video_files[0]

        return None

    def embed_subtitles(self, video_path_hint, playlist_index=None):
        """Embed subtitle file into video"""
        # Find the actual video file
        video_file = self.find_video_file(video_path_hint, playlist_index)

        if not video_file or not video_file.exists():
            print(f"   ⚠️  Video file not found: {video_path_hint}")
            return None

        print(f"   → Found video: {video_file.name}")

        # Look for subtitle files with the same base name
        subtitle_file = None
        base_name = video_file.stem

        for ext in [".en.srt", ".srt"]:
            potential_sub = video_file.with_suffix(ext)
            if potential_sub.exists():
                subtitle_file = potential_sub
                break

        if not subtitle_file:
            print("   → No subtitle file found, skipping embed")
            return str(video_file)

        print(f"   → Embedding subtitles from {subtitle_file.name}...")

        # Create temporary output file
        temp_output = video_file.with_name(video_file.stem + "_temp" + video_file.suffix)

        # FFmpeg command to embed subtitles
        cmd = [
            "ffmpeg",
            "-i", str(video_file),
            "-i", str(subtitle_file),
            "-c", "copy",
            "-c:s", "mov_text",
            "-metadata:s:s:0", "language=eng",
            "-y",  # Overwrite without asking
            str(temp_output)
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode == 0:
                # Replace original with embedded version
                video_file.unlink()
                temp_output.rename(video_file)

                # Delete subtitle file
                subtitle_file.unlink()

                print(f"   ✅ Subtitles embedded successfully!")
                return str(video_file)
            else:
                print(f"   ⚠️  Failed to embed subtitles")
                if temp_output.exists():
                    temp_output.unlink()
                return str(video_file)

        except Exception as e:
            print(f"   ⚠️  Error embedding subtitles: {e}")
            if temp_output.exists():
                temp_output.unlink()
            return str(video_file)

    def get_video_info(self, url):
        """Get video information without downloading"""
        ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist"}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            print(f"Error fetching video info: {e}")
            return None

    def download_video(self, url, quality="3", download_audio_only=False, playlist_index=None, total_videos=1, current_num=1):
        """Download video with specified quality"""

        # Create output template with optional numbering
        if playlist_index is not None:
            outtmpl = str(self.output_path / f"{playlist_index}-%(title)s.%(ext)s")
        else:
            outtmpl = str(self.output_path / "%(title)s.%(ext)s")

        if download_audio_only:
            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "outtmpl": outtmpl,
                "progress_hooks": [self.progress_hook],
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en"],
                "subtitlesformat": "srt",
                "socket_timeout": 30,
                "retries": 10,
                "fragment_retries": 10,
                "sleep_interval": 1,
                "max_sleep_interval": 5,
            }
        else:
            format_string = self.quality_options.get(
                quality, self.quality_options["3"]
            )["format"]

            ydl_opts = {
                "format": format_string,
                "outtmpl": outtmpl,
                "merge_output_format": "mp4",
                "progress_hooks": [self.progress_hook],
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en"],
                "subtitlesformat": "srt",
                "socket_timeout": 30,
                "retries": 10,
                "fragment_retries": 10,
                "sleep_interval": 1,
                "max_sleep_interval": 5,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if playlist_index:
                    print(f"\n[{current_num}/{total_videos}] Downloading from: {url}")
                else:
                    print(f"\nDownloading from: {url}")

                info = ydl.extract_info(url, download=True)

                print("\n✓ Download completed successfully!")

                # Auto-embed subtitles for video files (not audio)
                if not download_audio_only and self.check_ffmpeg():
                    # Use a hint path for finding the actual file
                    title = info.get('title', 'video')
                    hint_path = self.output_path / f"{title}.mp4"
                    self.embed_subtitles(hint_path, playlist_index)

                return True
        except Exception as e:
            print(f"\n✗ Error downloading: {e}")
            return False

    def download_playlist(self, url, quality="3", download_audio_only=False):
        """Download entire playlist with numbering"""
        print("Fetching playlist information...")
        info = self.get_video_info(url)

        if not info:
            return False

        if "entries" in info:
            print(f"\nPlaylist: {info.get('title', 'Unknown')}")
            print(f"Total videos: {len(info['entries'])}")

            confirm = input("\nDo you want to download all videos? (y/n): ")
            if confirm.lower() != "y":
                return False

            # Calculate padding for numbers (e.g., 001, 002 for 100+ videos)
            total_videos = len(info['entries'])
            padding = len(str(total_videos))

            for i, entry in enumerate(info["entries"], 1):
                if entry:
                    # Format index with padding (e.g., 01, 02, 03 or 001, 002, 003)
                    index = str(i).zfill(padding)

                    print(f"\n{'='*60}")
                    print(f"Video {i}/{total_videos}: {entry.get('title', 'Unknown')}")
                    print('='*60)
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    self.download_video(url=video_url, quality=quality,
                                      download_audio_only=download_audio_only,
                                      playlist_index=index,
                                      total_videos=total_videos,
                                      current_num=i)

            print("\n✓ Playlist download completed!")
            return True
        else:
            print("This doesn't appear to be a playlist. Downloading as single video...")
            return self.download_video(url, quality, download_audio_only)

    def progress_hook(self, d):
        """Display download progress"""
        if d["status"] == "downloading":
            percent = d.get("_percent_str", "N/A")
            speed = d.get("_speed_str", "N/A")
            eta = d.get("_eta_str", "N/A")
            print(f"\rProgress: {percent} | Speed: {speed} | ETA: {eta}", end="")
        elif d["status"] == "finished":
            print("\n→ Processing file...")


def display_menu():
    """Display main menu"""
    print("\n" + "=" * 50)
    print("YouTube Video Downloader")
    print("=" * 50)
    print("\n1. Download Single Video")
    print("2. Download Playlist")
    print("3. Download Audio Only (MP3)")
    print("4. Exit")
    return input("\nSelect option (1-4): ")


def display_quality_menu():
    """Display quality selection menu"""
    print("\nSelect Quality:")
    print("1. SD (480p)")
    print("2. HD (720p)")
    print("3. Full HD (1080p)")
    print("4. 2K (1440p)")
    print("5. Best Available Quality")
    return input("\nSelect quality (1-5) [default: 3]: ") or "3"


def main():
    downloader = YouTubeDownloader()

    print("Welcome to YouTube Downloader!")
    print("Features:")
    print("  • Auto-embed subtitles into videos")
    print("  • Playlist videos numbered (01-, 02-, etc.)")
    print("  • Anti-blocking measures with automatic retries")
    print("  • English subtitles downloaded automatically\n")

    # Check ffmpeg availability once at startup
    downloader.check_ffmpeg()

    while True:
        choice = display_menu()

        if choice == "1":
            url = input("\nEnter YouTube video URL: ").strip()
            if url:
                quality = display_quality_menu()
                downloader.download_video(url, quality)

        elif choice == "2":
            url = input("\nEnter YouTube playlist URL: ").strip()
            if url:
                quality = display_quality_menu()
                downloader.download_playlist(url, quality)

        elif choice == "3":
            url = input("\nEnter YouTube video/playlist URL: ").strip()
            if url:
                is_playlist = input("Is this a playlist? (y/n): ").lower() == "y"
                if is_playlist:
                    downloader.download_playlist(url, download_audio_only=True)
                else:
                    downloader.download_video(url, download_audio_only=True)

        elif choice == "4":
            print("\nThank you for using YouTube Downloader!")
            sys.exit(0)

        else:
            print("\n✗ Invalid option. Please try again.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user.")
        sys.exit(0)