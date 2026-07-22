import os
import subprocess
from pathlib import Path


def embed_subtitles_batch(folder_path=".", keep_originals=False):
    """
    Embeds subtitle files into video files in the specified folder.
    Works with numbered playlist files (01-, 02-, etc.) and special characters.
    
    Args:
        folder_path: Path to the folder containing videos
        keep_originals: If True, keeps original files and creates *_embedded.mp4
    """
    folder = Path(folder_path)
    
    # Find all mp4 files
    video_files = sorted(list(folder.glob("*.mp4")))
    
    if not video_files:
        print("No .mp4 files found in the folder!")
        return
    
    print(f"Found {len(video_files)} video file(s)")
    print("=" * 70)
    
    # Check ffmpeg
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ERROR: ffmpeg not found! Please install ffmpeg first.")
        print("   Visit: https://ffmpeg.org/download.html")
        return
    
    successful = 0
    failed = 0
    skipped = 0
    
    for video_file in video_files:
        print(f"\n📹 Processing: {video_file.name}")
        
        # Skip if it's a temp or embedded file
        if "_temp" in video_file.stem or "_embedded" in video_file.stem:
            print("   ⚠️  SKIP: Temporary or already embedded file")
            skipped += 1
            continue
        
        # Look for corresponding subtitle file (.en.srt, .srt, etc.)
        subtitle_file = None
        for ext in [".en.srt", ".srt"]:
            potential_sub = video_file.with_suffix(ext)
            if potential_sub.exists():
                subtitle_file = potential_sub
                break
        
        if not subtitle_file:
            print(f"   ⚠️  SKIP: No subtitle file found")
            skipped += 1
            continue
        
        print(f"   ✓ Found subtitle: {subtitle_file.name}")
        
        # Output filename
        if keep_originals:
            output_file = video_file.with_name(video_file.stem + "_embedded.mp4")
        else:
            output_file = video_file.with_name(video_file.stem + "_temp.mp4")
        
        # Skip if output already exists
        if keep_originals and output_file.exists():
            print(f"   ⚠️  SKIP: Embedded version already exists")
            skipped += 1
            continue
        
        print(f"   → Embedding subtitles...")
        
        # FFmpeg command
        cmd = [
            "ffmpeg",
            "-i", str(video_file),
            "-i", str(subtitle_file),
            "-c", "copy",
            "-c:s", "mov_text",
            "-metadata:s:s:0", "language=eng",
            "-y",
            str(output_file)
        ]
        
        try:
            # Run ffmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode == 0:
                if not keep_originals:
                    # Replace original with embedded version
                    video_file.unlink()
                    output_file.rename(video_file)
                    
                    # Delete subtitle file
                    subtitle_file.unlink()
                    print(f"   ✅ SUCCESS: Subtitles embedded, originals deleted")
                else:
                    print(f"   ✅ SUCCESS: Created {output_file.name}")
                    
                successful += 1
            else:
                print(f"   ❌ FAILED: Error embedding subtitles")
                print(f"      {result.stderr[:200]}")
                if output_file.exists():
                    output_file.unlink()
                failed += 1
                
        except Exception as e:
            print(f"   ❌ FAILED: {str(e)}")
            if output_file.exists():
                output_file.unlink()
            failed += 1
        
        print("-" * 70)
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY:")
    print(f"  ✅ Successful: {successful}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⚠️  Skipped: {skipped}")
    print(f"  📁 Total files: {len(video_files)}")
    print("=" * 70)
    
    if successful > 0 and not keep_originals:
        print("\n✓ Original .mp4 and .srt files have been replaced with embedded versions!")


def preview_files(folder_path="."):
    """Preview what files will be processed"""
    folder = Path(folder_path)
    video_files = sorted(list(folder.glob("*.mp4")))
    
    if not video_files:
        print("No .mp4 files found!")
        return
    
    print(f"\nFound {len(video_files)} video file(s):")
    print("=" * 70)
    
    count_with_subs = 0
    count_without_subs = 0
    
    for video_file in video_files:
        if "_temp" in video_file.stem or "_embedded" in video_file.stem:
            continue
            
        # Look for subtitle
        has_subtitle = False
        subtitle_name = ""
        for ext in [".en.srt", ".srt"]:
            potential_sub = video_file.with_suffix(ext)
            if potential_sub.exists():
                has_subtitle = True
                subtitle_name = potential_sub.name
                break
        
        if has_subtitle:
            print(f"✓ {video_file.name}")
            print(f"  └─ {subtitle_name}")
            count_with_subs += 1
        else:
            print(f"✗ {video_file.name} (no subtitle)")
            count_without_subs += 1
    
    print("=" * 70)
    print(f"Videos with subtitles: {count_with_subs}")
    print(f"Videos without subtitles: {count_without_subs}")
    print("=" * 70)


if __name__ == "__main__":
    import sys
    
    print("Batch Subtitle Embedder")
    print("=" * 70)
    
    # Get folder path
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = input("Enter folder path (press Enter for current folder): ").strip()
        if not folder:
            folder = "."
    
    folder = Path(folder)
    if not folder.exists():
        print(f"❌ Folder not found: {folder}")
        sys.exit(1)
    
    print(f"\nScanning folder: {folder.absolute()}\n")
    
    # Preview files
    preview_files(folder)
    
    print("\nOptions:")
    print("1. Embed subtitles and DELETE originals (recommended)")
    print("2. Embed subtitles and KEEP originals (creates *_embedded.mp4)")
    print("3. Cancel")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        confirm = input("\n⚠️  This will DELETE original .mp4 and .srt files. Continue? (yes/no): ")
        if confirm.lower() == "yes":
            embed_subtitles_batch(folder, keep_originals=False)
        else:
            print("❌ Cancelled")
    elif choice == "2":
        embed_subtitles_batch(folder, keep_originals=True)
    else:
        print("❌ Cancelled")
