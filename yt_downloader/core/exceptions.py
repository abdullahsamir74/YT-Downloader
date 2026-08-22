"""
Domain exceptions for YT-Downloader.
"""


class YTDownloaderError(Exception):
    """Base exception for all YT-Downloader errors."""

    def __init__(self, message: str, details: str = ""):
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class MetadataExtractionError(YTDownloaderError):
    """Raised when media metadata could not be fetched."""
    pass


class DownloadError(YTDownloaderError):
    """Raised when video/audio stream download fails."""
    pass


class StreamNotFoundError(DownloadError):
    """Raised when the requested quality or format is unavailable."""
    pass


class FFmpegNotFoundError(YTDownloaderError):
    """Raised when FFmpeg binary is missing from system PATH."""
    pass


class MuxingError(YTDownloaderError):
    """Raised when FFmpeg fails to mux audio, video, or subtitles."""
    pass


class NetworkError(YTDownloaderError):
    """Raised on connection timeout or network failure."""
    pass


class CancelledError(YTDownloaderError):
    """Raised when a download task is cancelled by the user."""
    pass
