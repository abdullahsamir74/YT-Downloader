"""
Core enums for YT-Downloader.
"""

from enum import Enum


class QualityPreset(str, Enum):
    BEST = "best"
    UHD_4K = "2160p"
    QHD_2K = "1440p"
    FHD_1080P = "1080p"
    HD_720P = "720p"
    SD_480P = "480p"
    SD_360P = "360p"

    @property
    def label(self) -> str:
        labels = {
            self.BEST: "Best Available",
            self.UHD_4K: "4K (2160p)",
            self.QHD_2K: "2K (1440p)",
            self.FHD_1080P: "1080p (Full HD)",
            self.HD_720P: "720p (HD)",
            self.SD_480P: "480p (SD)",
            self.SD_360P: "360p (Low)",
        }
        return labels.get(self, self.value)


class AudioFormat(str, Enum):
    MP3 = "mp3"
    M4A = "m4a"
    FLAC = "flac"
    OPUS = "opus"
    WAV = "wav"
    AAC = "aac"

    @property
    def label(self) -> str:
        labels = {
            self.MP3: "MP3 (Universal)",
            self.M4A: "M4A (Apple / AAC)",
            self.FLAC: "FLAC (Lossless)",
            self.OPUS: "OPUS (High Efficiency)",
            self.WAV: "WAV (Uncompressed)",
            self.AAC: "AAC (Standard)",
        }
        return labels.get(self, self.value.upper())


class AudioBitrate(str, Enum):
    AUTO = "0"
    B128 = "128"
    B192 = "192"
    B256 = "256"
    B320 = "320"

    @property
    def label(self) -> str:
        labels = {
            self.AUTO: "Auto (Best)",
            self.B128: "128 kbps (Standard)",
            self.B192: "192 kbps (High)",
            self.B256: "256 kbps (Very High)",
            self.B320: "320 kbps (Maximum)",
        }
        return labels.get(self, f"{self.value} kbps")


class SubtitleMode(str, Enum):
    EMBED = "embed"
    SEPARATE = "separate"
    NONE = "none"

    @property
    def label(self) -> str:
        labels = {
            self.EMBED: "Embed in Video (MP4/MKV)",
            self.SEPARATE: "Save as .srt file",
            self.NONE: "No Subtitles",
        }
        return labels.get(self, self.value)


class TaskStatus(str, Enum):
    QUEUED = "queued"
    FETCHING = "fetching"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_active(self) -> bool:
        return self in (self.FETCHING, self.DOWNLOADING, self.PROCESSING)

    @property
    def is_finished(self) -> bool:
        return self in (self.COMPLETED, self.FAILED, self.CANCELLED)


class ThemeName(str, Enum):
    TOKYO_NIGHT = "tokyo-night"
    CYBERPUNK = "cyberpunk"
    CATPPUCCIN = "catppuccin"
    DRACULA = "dracula"
    NORD = "nord"
    DARK = "dark"
