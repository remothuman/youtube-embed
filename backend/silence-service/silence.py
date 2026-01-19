"""
Silence detection logic using yt-dlp and pydub.
"""

import os
import re
import tempfile
import yt_dlp
from pydub import AudioSegment
from pydub.silence import detect_silence as pydub_detect_silence

MAX_VIDEO_DURATION_HOURS = 12
MAX_VIDEO_DURATION_SEC = MAX_VIDEO_DURATION_HOURS * 3600

# Detection settings (detect all >=100ms, frontend filters further)
MIN_SILENCE_LEN_MS = 100
SILENCE_THRESH_DBFS = -40
SEEK_STEP_MS = 10


class SilenceDetectionError(Exception):
    """Base exception for silence detection errors."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_video_id(video_id: str) -> bool:
    """Validate YouTube video ID format."""
    # YouTube video IDs are 11 characters, alphanumeric with - and _
    return bool(re.match(r"^[a-zA-Z0-9_-]{11}$", video_id))


def extract_silence_segments(video_id: str) -> tuple[list[dict], float]:
    """
    Download audio and detect silence segments.

    Returns:
        tuple of (segments list, duration in seconds)

    Raises:
        SilenceDetectionError: If detection fails
    """
    if not validate_video_id(video_id):
        raise SilenceDetectionError("invalid_video_id", "Invalid video ID format")

    url = f"https://www.youtube.com/watch?v={video_id}"

    # Use temp directory for audio file
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, f"{video_id}.mp3")

        # Download audio (lowest quality for speed)
        ydl_opts = {
            "format": "worstaudio/worst",
            "outtmpl": os.path.join(tmpdir, f"{video_id}.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "64",  # Low quality fine for silence detection
                }
            ],
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first to check duration
                info = ydl.extract_info(url, download=False)

                if info is None:
                    raise SilenceDetectionError(
                        "video_unavailable", "Could not fetch video information"
                    )

                duration_sec = info.get("duration", 0)

                if duration_sec > MAX_VIDEO_DURATION_SEC:
                    raise SilenceDetectionError(
                        "video_too_long",
                        f"Video exceeds maximum duration of {MAX_VIDEO_DURATION_HOURS} hours",
                    )

                # Check for age restriction
                if info.get("age_limit", 0) >= 18:
                    raise SilenceDetectionError(
                        "age_restricted", "Cannot process age-restricted videos"
                    )

                # Download audio
                ydl.download([url])

        except yt_dlp.utils.DownloadError as e:
            error_str = str(e).lower()
            if "private" in error_str or "unavailable" in error_str:
                raise SilenceDetectionError(
                    "video_unavailable", "Video is private or unavailable"
                )
            if "age" in error_str:
                raise SilenceDetectionError(
                    "age_restricted", "Cannot process age-restricted videos"
                )
            raise SilenceDetectionError("download_failed", f"Download failed: {e}")

        # Find the downloaded file (extension might vary)
        audio_file = None
        for f in os.listdir(tmpdir):
            if f.startswith(video_id) and f.endswith(".mp3"):
                audio_file = os.path.join(tmpdir, f)
                break

        if not audio_file or not os.path.exists(audio_file):
            raise SilenceDetectionError(
                "download_failed", "Audio file not found after download"
            )

        # Load and analyze audio
        try:
            audio = AudioSegment.from_file(audio_file)
        except Exception as e:
            raise SilenceDetectionError(
                "download_failed", f"Failed to load audio: {e}"
            )

        # Get actual duration from audio (more accurate than metadata)
        actual_duration_sec = len(audio) / 1000.0

        # Detect silence
        silent_segments = pydub_detect_silence(
            audio,
            min_silence_len=MIN_SILENCE_LEN_MS,
            silence_thresh=SILENCE_THRESH_DBFS,
            seek_step=SEEK_STEP_MS,
        )

        # Format segments
        segments = [
            {"start_ms": start, "end_ms": end, "duration_ms": end - start}
            for start, end in silent_segments
        ]

        return segments, actual_duration_sec
