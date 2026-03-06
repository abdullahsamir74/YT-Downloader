"""
YouTube Video/Playlist Downloader with Quality Selection and Audio Extraction
Requires: pip install yt-dlp
"""

import yt_dlp
import os
import sys
from pathlib import Path


class YouTubeDownloader:
    def __init__(self, output_path="downloads"):
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)

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

    def download_video(self, url, quality="3", download_audio_only=False):
        """Download video with specified quality"""

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
                "outtmpl": str(self.output_path / "%(title)s.%(ext)s"),
                "progress_hooks": [self.progress_hook],
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
                "outtmpl": str(self.output_path / "%(title)s.%(ext)s"),
                "merge_output_format": "mp4",
                "progress_hooks": [self.progress_hook],
                "socket_timeout": 30,
                "retries": 10,
                "fragment_retries": 10,
                "sleep_interval": 1,
                "max_sleep_interval": 5,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"\nDownloading from: {url}")
                ydl.download([url])
                print("\n✓ Download completed successfully!")
                return True
        except Exception as e:
            print(f"\n✗ Error downloading: {e}")
            return False

    def download_playlist(self, url, quality="3", download_audio_only=False):
        """Download entire playlist"""
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

            for i, entry in enumerate(info["entries"], 1):
                if entry:
                    print(
                        f"\n[{i}/{len(info['entries'])}] {entry.get('title', 'Unknown')}"
                    )
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    self.download_video(video_url, quality, download_audio_only)

            print("\n✓ Playlist download completed!")
            return True
        else:
            print(
                "This doesn't appear to be a playlist. Downloading as single video..."
            )
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
    print(
        "Note: yt-dlp automatically handles audio/video merging for high-quality videos"
    )
    print("      and includes anti-blocking measures with automatic retries.")
    print("      English subtitles will be downloaded automatically when available.\n")

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
