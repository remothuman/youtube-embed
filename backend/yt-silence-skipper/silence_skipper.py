#!/usr/bin/env python3
"""
YouTube Silence Skipper
Downloads YouTube videos and extracts timestamps of silent segments.
"""

import os
import json
import argparse
from pathlib import Path
import yt_dlp
from pydub import AudioSegment
from pydub.silence import detect_silence
import numpy as np


class YouTubeSilenceSkipper:
    def __init__(self, output_dir="downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def download_video(self, url, audio_only=False, skip_if_exists=True):
        """Download YouTube video and return the filepath."""
        ydl_opts = {
            'format': 'bestaudio/best' if audio_only else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }] if audio_only else [],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First, fetch metadata without downloading so we can compute the
            # exact output filename and skip work if it already exists.
            info = ydl.extract_info(url, download=False)
            filename = ydl.prepare_filename(info)

            if audio_only:
                # Change extension to mp3 after audio extraction
                filename = filename.rsplit('.', 1)[0] + '.mp3'

            if skip_if_exists and Path(filename).exists():
                print(f"File already exists, skipping download: {filename}")
                return filename, info

            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if audio_only:
                # Change extension to mp3 after audio extraction
                filename = filename.rsplit('.', 1)[0] + '.mp3'

            return filename, info
    
    def detect_silence_segments(self, audio_path, min_silence_len=1000, 
                               silence_thresh=-40, seek_step=10):
        """
        Detect silent segments in audio file.
        
        Args:
            audio_path: Path to audio file
            min_silence_len: Minimum length of silence to detect (ms)
            silence_thresh: Silence threshold in dBFS (e.g., -40 dBFS)
            seek_step: Step size for checking silence (ms) - smaller is more accurate but slower
        
        Returns:
            List of tuples (start_ms, end_ms) for each silent segment
        """
        print(f"Loading audio file: {audio_path}")
        audio = AudioSegment.from_file(audio_path)
        
        print(f"Analyzing audio (length: {len(audio)/1000:.2f}s)...")
        print(f"Settings: min_silence={min_silence_len}ms, threshold={silence_thresh}dBFS")
        
        # Detect silence
        silent_segments = detect_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            seek_step=seek_step
        )
        
        print(f"Found {len(silent_segments)} silent segments")
        return silent_segments
    
    def format_timestamp(self, ms):
        """Convert milliseconds to HH:MM:SS.mmm format."""
        seconds = ms / 1000
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def save_silence_report(self, video_info, silent_segments, output_path):
        """Save silence detection results to JSON file."""
        report = {
            'video_title': video_info.get('title'),
            'video_url': video_info.get('webpage_url'),
            'duration_seconds': video_info.get('duration'),
            'silence_segments': [
                {
                    'start_ms': start,
                    'end_ms': end,
                    'duration_ms': end - start
                }
                for start, end in silent_segments
            ],
            'total_silence_seconds': sum((end - start) / 1000 for start, end in silent_segments),
            'silence_percentage': (sum((end - start) for start, end in silent_segments) / 
                                 (video_info.get('duration', 1) * 1000) * 100) if video_info.get('duration') else 0
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def print_summary(self, report):
        """Print a summary of detected silence."""
        print("\n" + "="*60)
        print(f"Video: {report['video_title']}")
        print(f"Duration: {report['duration_seconds']:.2f}s")
        print(f"Silence segments: {len(report['silence_segments'])}")
        print(f"Total silence: {report['total_silence_seconds']:.2f}s ({report['silence_percentage']:.1f}%)")
        print("="*60)
        
        if report['silence_segments']:
            print("\nSilent segments (first 10):")
            for i, seg in enumerate(report['silence_segments'][:10], 1):
                start_time = self.format_timestamp(seg['start_ms'])
                end_time = self.format_timestamp(seg['end_ms'])
                print(f"  {i}. {start_time} - {end_time} ({seg['duration_ms']/1000:.2f}s)")
            
            if len(report['silence_segments']) > 10:
                print(f"  ... and {len(report['silence_segments']) - 10} more")
    
    def process_video(self, url, min_silence_len=1000, silence_thresh=-40, 
                     audio_only=True, seek_step=10):
        """
        Complete pipeline: download video and detect silence.
        
        Args:
            url: YouTube URL
            min_silence_len: Minimum silence duration to detect (ms)
            silence_thresh: Silence threshold in dBFS
            audio_only: Download only audio (faster)
            seek_step: Step size for silence detection (ms)
        """
        print(f"Processing: {url}\n")
        
        # Download
        print("Step 1: Downloading...")
        filepath, info = self.download_video(url, audio_only=audio_only)
        print(f"Downloaded: {filepath}\n")
        
        # Detect silence
        print("Step 2: Detecting silence...")
        silent_segments = self.detect_silence_segments(
            filepath, 
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            seek_step=seek_step
        )
        
        # Save report
        report_path = self.output_dir / f"{Path(filepath).stem}_silence_report.json"
        report = self.save_silence_report(info, silent_segments, report_path)
        print(f"\nSaved report: {report_path}")
        
        # Print summary
        self.print_summary(report)
        
        return filepath, report_path, report


def main():
    parser = argparse.ArgumentParser(
        description='Download YouTube videos and detect silent segments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python yt_silence_skipper.py "https://www.youtube.com/watch?v=VIDEO_ID"
  
  # Adjust sensitivity (detect only longer silences)
  python yt_silence_skipper.py "URL" --min-silence 2000
  
  # Adjust threshold (detect quieter sections as silence)
  python yt_silence_skipper.py "URL" --threshold -50
  
  # Download full video instead of audio only
  python yt_silence_skipper.py "URL" --full-video
        """
    )
    
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--output-dir', '-o', default='downloads', 
                       help='Output directory (default: downloads)')
    parser.add_argument('--min-silence', '-m', type=int, default=500,
                       help='Minimum silence length in ms (default: 500)')
    parser.add_argument('--threshold', '-t', type=int, default=-40,
                       help='Silence threshold in dBFS (default: -40)')
    parser.add_argument('--seek-step', '-s', type=int, default=10,
                       help='Seek step in ms - smaller=more accurate but slower (default: 10)')
    parser.add_argument('--full-video', '-f', action='store_true',
                       help='Download full video instead of audio only')
    
    args = parser.parse_args()
    
    skipper = YouTubeSilenceSkipper(output_dir=args.output_dir)
    skipper.process_video(
        args.url,
        min_silence_len=args.min_silence,
        silence_thresh=args.threshold,
        audio_only=not args.full_video,
        seek_step=args.seek_step
    )


if __name__ == '__main__':
    main()