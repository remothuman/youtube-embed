#!/usr/bin/env python3
"""
Example usage of the YouTubeSilenceSkipper class
"""

from yt_silence_skipper import YouTubeSilenceSkipper
import json


def example_basic():
    """Basic usage example."""
    print("=== BASIC USAGE ===\n")
    
    skipper = YouTubeSilenceSkipper(output_dir="downloads")
    
    # Process a video with default settings
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Replace with actual URL
    
    filepath, report_path, report = skipper.process_video(video_url)
    
    print(f"\nDownloaded to: {filepath}")
    print(f"Report saved to: {report_path}")


def example_custom_settings():
    """Example with custom detection settings."""
    print("\n=== CUSTOM SETTINGS ===\n")
    
    skipper = YouTubeSilenceSkipper(output_dir="my_videos")
    
    video_url = "https://www.youtube.com/watch?v=VIDEO_ID"  # Replace with actual URL
    
    # Detect only longer silences (2+ seconds) with stricter threshold
    filepath, report_path, report = skipper.process_video(
        url=video_url,
        min_silence_len=2000,      # 2 seconds minimum
        silence_thresh=-35,         # Less sensitive (stricter)
        audio_only=True,            # Audio only (faster)
        seek_step=20                # Faster processing
    )


def example_programmatic_access():
    """Example of using the data programmatically."""
    print("\n=== PROGRAMMATIC ACCESS ===\n")
    
    skipper = YouTubeSilenceSkipper()
    
    # Download video
    url = "https://www.youtube.com/watch?v=VIDEO_ID"  # Replace with actual URL
    filepath, info = skipper.download_video(url, audio_only=True)
    
    # Detect silence with custom settings
    silent_segments = skipper.detect_silence_segments(
        filepath,
        min_silence_len=1500,
        silence_thresh=-42
    )
    
    # Process the results yourself
    print(f"Found {len(silent_segments)} silent segments:")
    
    total_silence_ms = 0
    for i, (start, end) in enumerate(silent_segments, 1):
        duration = end - start
        total_silence_ms += duration
        
        start_time = skipper.format_timestamp(start)
        end_time = skipper.format_timestamp(end)
        
        print(f"{i}. {start_time} - {end_time} ({duration/1000:.2f}s)")
        
        # You could implement custom logic here, e.g.:
        # - Generate video player seek points
        # - Create a trimmed version without silence
        # - Generate chapter markers
        # etc.
    
    print(f"\nTotal silence: {total_silence_ms/1000:.2f}s")
    
    # Save to custom format
    output_data = {
        'video': info['title'],
        'skip_segments': [
            {'from': start/1000, 'to': end/1000}
            for start, end in silent_segments
        ]
    }
    
    with open('custom_output.json', 'w') as f:
        json.dump(output_data, f, indent=2)


def example_batch_processing():
    """Example of processing multiple videos."""
    print("\n=== BATCH PROCESSING ===\n")
    
    skipper = YouTubeSilenceSkipper(output_dir="batch_downloads")
    
    video_urls = [
        "https://www.youtube.com/watch?v=VIDEO_ID_1",
        "https://www.youtube.com/watch?v=VIDEO_ID_2",
        "https://www.youtube.com/watch?v=VIDEO_ID_3",
    ]
    
    results = []
    
    for url in video_urls:
        try:
            print(f"\nProcessing: {url}")
            filepath, report_path, report = skipper.process_video(
                url,
                min_silence_len=1000,
                silence_thresh=-40
            )
            
            results.append({
                'url': url,
                'success': True,
                'silence_percentage': report['silence_percentage']
            })
            
        except Exception as e:
            print(f"Error processing {url}: {e}")
            results.append({
                'url': url,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print("\n=== BATCH SUMMARY ===")
    for result in results:
        if result['success']:
            print(f"✓ {result['url']}: {result['silence_percentage']:.1f}% silence")
        else:
            print(f"✗ {result['url']}: {result['error']}")


def example_video_editor_integration():
    """Example showing how to use timestamps for video editing."""
    print("\n=== VIDEO EDITOR INTEGRATION ===\n")
    
    skipper = YouTubeSilenceSkipper()
    
    # Assume we already have a report
    with open('downloads/video_silence_report.json') as f:
        report = json.load(f)
    
    # Generate ffmpeg trim commands
    print("FFmpeg commands to remove silence:")
    print("\nOption 1: Complex filter (keeps all non-silent parts)")
    
    segments = report['silence_segments']
    duration = report['duration_seconds']
    
    # Build list of segments to keep (non-silent parts)
    keep_segments = []
    last_end = 0
    
    for seg in segments:
        start_s = seg['start_ms'] / 1000
        if start_s > last_end:
            keep_segments.append((last_end, start_s))
        last_end = seg['end_ms'] / 1000
    
    # Add final segment if needed
    if last_end < duration:
        keep_segments.append((last_end, duration))
    
    # Generate ffmpeg command
    if keep_segments:
        filter_parts = []
        for i, (start, end) in enumerate(keep_segments):
            filter_parts.append(f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{i}];")
            filter_parts.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}];")
        
        concat_v = ''.join(f"[v{i}]" for i in range(len(keep_segments)))
        concat_a = ''.join(f"[a{i}]" for i in range(len(keep_segments)))
        
        print(f"\nffmpeg -i input.mp4 -filter_complex \"")
        print(''.join(filter_parts))
        print(f"{concat_v}{concat_a}concat=n={len(keep_segments)}:v=1:a=1[outv][outa]\" -map \"[outv]\" -map \"[outa]\" output.mp4")
    
    print("\n\nOption 2: Simple skip segments (for player integration)")
    print("Skip these time ranges:")
    for seg in segments[:5]:  # Show first 5
        print(f"  {seg['start_time']} to {seg['end_time']}")
    if len(segments) > 5:
        print(f"  ... and {len(segments) - 5} more")


if __name__ == '__main__':
    print("YouTube Silence Skipper - Usage Examples\n")
    print("=" * 60)
    
    # Uncomment the example you want to run:
    
    # example_basic()
    # example_custom_settings()
    # example_programmatic_access()
    # example_batch_processing()
    # example_video_editor_integration()
    
    print("\nNote: Replace VIDEO_ID with actual YouTube video IDs")
    print("Uncomment the example function you want to run in the script")