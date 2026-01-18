# YouTube Silence Skipper

A Python tool to download YouTube videos and automatically detect silent segments, generating timestamps for skipping.

## Features

- Download YouTube videos (audio or full video)
- Detect silent segments with configurable sensitivity
- Export silence timestamps in JSON format
- Generate detailed reports with timing information
- Customizable silence threshold and minimum duration

## Installation

### Prerequisites

You need to have **ffmpeg** installed on your system:

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

### Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install yt-dlp pydub numpy
```

## Usage

### Basic Usage

```bash
python yt_silence_skipper.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

This will:
1. Download the audio from the YouTube video
2. Analyze it for silent segments (default: >1 second of silence below -40 dBFS)
3. Save a JSON report with all silence timestamps
4. Print a summary to the console

### Advanced Options

**Adjust minimum silence duration** (detect only longer silences):
```bash
python yt_silence_skipper.py "URL" --min-silence 2000
```

**Adjust silence threshold** (lower = more sensitive, detects quieter sounds as silence):
```bash
python yt_silence_skipper.py "URL" --threshold -50
```

**Download full video instead of audio only:**
```bash
python yt_silence_skipper.py "URL" --full-video
```

**Specify output directory:**
```bash
python yt_silence_skipper.py "URL" --output-dir my_videos
```

**Adjust seek step** (smaller = more accurate but slower):
```bash
python yt_silence_skipper.py "URL" --seek-step 5
```

**Combine options:**
```bash
python yt_silence_skipper.py "URL" \
  --min-silence 1500 \
  --threshold -45 \
  --output-dir videos \
  --seek-step 10
```

## Output Format

The tool generates a JSON file with the following structure:

```json
{
  "video_title": "Video Title",
  "video_url": "https://youtube.com/watch?v=...",
  "duration_seconds": 600.5,
  "silence_segments": [
    {
      "start_ms": 5000,
      "end_ms": 7500,
      "duration_ms": 2500,
      "start_time": "00:00:05.000",
      "end_time": "00:00:07.500"
    }
  ],
  "total_silence_seconds": 45.2,
  "silence_percentage": 7.5
}
```

## Parameter Guide

### `--min-silence` (milliseconds)
- **Default:** 1000 (1 second)
- Minimum duration for a segment to be considered silence
- Lower values detect shorter pauses
- Higher values only detect longer silences
- **Examples:**
  - `500` - Detect brief pauses
  - `2000` - Only detect long silences (2+ seconds)

### `--threshold` (dBFS)
- **Default:** -40 dBFS
- Volume level below which audio is considered silent
- More negative = quieter sounds treated as silence
- **Examples:**
  - `-30` - Only very quiet audio is silence (less sensitive)
  - `-50` - Background noise treated as silence (more sensitive)
  - `-60` - Very sensitive, good for clean recordings

### `--seek-step` (milliseconds)
- **Default:** 10ms
- How frequently to check audio levels
- Smaller values = more accurate but slower processing
- **Examples:**
  - `1` - Very precise (slow)
  - `50` - Fast but less precise

## Use Cases

### Podcast/Interview Processing
Detect long pauses between speakers:
```bash
python yt_silence_skipper.py "URL" --min-silence 2000 --threshold -35
```

### Lecture/Tutorial Videos
Detect all significant pauses:
```bash
python yt_silence_skipper.py "URL" --min-silence 1000 --threshold -40
```

### Music Videos
Only detect true silence (not quiet parts):
```bash
python yt_silence_skipper.py "URL" --min-silence 500 --threshold -50
```

### Noisy Recordings
Be less sensitive to background noise:
```bash
python yt_silence_skipper.py "URL" --threshold -30
```

## Integration Examples

### Using the JSON Output

```python
import json

# Load the silence report
with open('video_silence_report.json') as f:
    report = json.load(f)

# Get all silence timestamps
for segment in report['silence_segments']:
    start = segment['start_ms'] / 1000  # Convert to seconds
    end = segment['end_ms'] / 1000
    print(f"Skip from {start:.2f}s to {end:.2f}s")
```

### Video Player Integration

Use the timestamps to implement auto-skip in a video player:

```javascript
// Example for HTML5 video player
const silenceSegments = [
  {start_ms: 5000, end_ms: 7500},
  {start_ms: 15000, end_ms: 18000}
];

video.addEventListener('timeupdate', () => {
  const currentTime = video.currentTime * 1000;
  
  for (const segment of silenceSegments) {
    if (currentTime >= segment.start_ms && currentTime < segment.end_ms) {
      video.currentTime = segment.end_ms / 1000;
      break;
    }
  }
});
```

## Troubleshooting

**"ERROR: Unable to download video"**
- Check your internet connection
- Verify the YouTube URL is correct
- Some videos may be region-restricted or private

**"FileNotFoundError: ffmpeg"**
- Install ffmpeg (see Prerequisites above)
- Make sure ffmpeg is in your system PATH

**Too many/few silence segments detected**
- Adjust `--threshold` (more negative = more sensitive)
- Adjust `--min-silence` (higher = fewer segments)
- Try different combinations to find what works for your content

**Processing is slow**
- Increase `--seek-step` (e.g., 50 or 100)
- Use `--audio-only` (default) instead of full video
- Process shorter videos first to test settings

## License

MIT License - feel free to use and modify!

## Contributing

Contributions welcome! Feel free to submit issues or pull requests.