#!/usr/bin/env python3
"""
Local Context Recorder - Unified CLI for screen recording and transcription using ContextRecorder

This script provides a CLI interface for recording screen content,
transcribing audio, analyzing visual content, and caching the results
in a format accessible by the MCP server, using the ContextRecorder class.
"""

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from inframe import ContextRecorder

async def main_async(args):
    recorder = ContextRecorder(cache_file=args.cache_file)
    
    # Add a recorder (returns recorder_id)
    recorder_id = recorder.add_recorder(
        buffer_duration=args.duration,
        include_apps=args.include_apps,
        recording_mode=args.recording_mode,
        visual_task=args.visual_task
    )
    
    # Start recording
    started = await recorder.start(recorder_id)
    if not started:
        print("Failed to start recording.")
        return
    print(f"Recording started (ID: {recorder_id[:8]}...) for {args.duration} seconds...")
    
    # Wait for the specified duration
    try:
        await asyncio.sleep(args.duration)
    except KeyboardInterrupt:
        print("Interrupted by user.")
    
    # Stop recording
    await recorder.stop(recorder_id)
    print("Recording stopped.")
    
    # Print cache file location
    cache_file = recorder.get_cache_file_path()
    print(f"Context cached at: {cache_file}")
    
    # Optionally print the context
    if args.print_context:
        print("\n--- Cached Context ---\n")
        try:
            if cache_file.exists():
                print(cache_file.read_text())
            else:
                print("⚠️ Cache file not found - no context was generated during recording")
        except Exception as e:
            print(f"❌ Error reading cache file: {e}")


def main():
    parser = argparse.ArgumentParser(description='Local Context Recorder CLI (using ContextRecorder)')
    parser.add_argument('--duration', '-d', type=int, default=30, help='Recording duration in seconds (default: 30)')
    parser.add_argument('--include-apps', nargs='*', default=["Visual Studio Code", "Cursor", "PyCharm", "IntelliJ IDEA"], help='List of app names to include (default: common IDEs)')
    parser.add_argument('--recording-mode', choices=['full_screen', 'window_only'], default='full_screen', help='Recording mode (default: full_screen)')
    parser.add_argument('--visual-task', type=str, default="Describe the screen content focusing on application names, file names, UI elements, and text content.", help='Visual task prompt for the recorder')
    parser.add_argument('--print-context', action='store_true', help='Print the cached context after recording')
    parser.add_argument('--cache-file', type=str, default=str(Path.home() / f".cache/inframe/{datetime.now().strftime('%Y%m%d')}"), help='Path to cache file (default: ~/.cache/inframe)')
    args = parser.parse_args()
    
    asyncio.run(main_async(args))

if __name__ == "__main__":
    main() 