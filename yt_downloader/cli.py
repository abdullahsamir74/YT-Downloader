"""
CLI entry point for YouTube Downloader application.
"""

import sys
import argparse
from pathlib import Path
from yt_downloader.ui import App
from yt_downloader.engine import Downloader
from yt_downloader.models import DownloadOpts


def main():
    parser = argparse.ArgumentParser(description="YouTube Downloader Console App")
    parser.add_argument(
        "--url",
        "-u",
        type=str,
        help="YouTube video or playlist URL for direct download",
    )
    parser.add_argument(
        "--quality",
        "-q",
        type=str,
        default="1080p",
        choices=["480p", "720p", "1080p", "1440p", "2160p", "best"],
        help="Target video quality",
    )
    parser.add_argument(
        "--audio-only", "-a", action="store_true", help="Download audio only"
    )
    parser.add_argument(
        "--audio-format",
        type=str,
        default="mp3",
        choices=["mp3", "m4a", "flac"],
        help="Audio format",
    )
    parser.add_argument(
        "--subtitles",
        "-s",
        type=str,
        default="embed",
        choices=["embed", "separate", "none"],
        help="Subtitle handling mode",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="downloads",
        help="Output directory path",
    )

    args = parser.parse_args()

    if args.url:
        print(f"⚡ Downloading: {args.url}")
        downloader = Downloader()
        opts = DownloadOpts(
            quality=args.quality,
            audio_only=args.audio_only,
            audio_format=args.audio_format,
            subtitles=args.subtitles,
            output_dir=Path(args.output_dir),
        )

        def simple_cb(d):
            if d.get("status") == "downloading":
                pct = d.get("_percent_str", "0%")
                spd = d.get("_speed_str", "0 B/s")
                eta = d.get("_eta_str", "00:00")
                print(f"\rProgress: {pct} | Speed: {spd} | ETA: {eta}", end="")

        ok = downloader.download(args.url, opts, progress_cb=simple_cb)
        if ok:
            print("\n✓ Download completed successfully!")
        sys.exit(0 if ok else 1)

    app = App(output_dir=args.output_dir)
    app.run()


if __name__ == "__main__":
    main()
