#!/usr/bin/env python3
"""
Demo script showing session-based recording and querying with API endpoints.
"""

import asyncio
import os
import sys
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from inframe_v2.recorder import Recorder
from inframe_v2.query import Querier


async def main():
    """Main demo function"""
    print("🎬 Starting Session-Based Recording and Querying Demo")
    print("=" * 60)
    
    # Create a session ID
    session_id = "demo_session_001"
    print(f"📋 Session ID: {session_id}")
    
    # Initialize recorder
    print("\n🎥 Initializing recorder...")
    recorder = Recorder(session_id=session_id)

    # Create querier for this session
    print("🤖 Creating querier for session...")
    querier = Querier(session_id=session_id)
    
    # Start recording
    print("🎬 Starting recording...")
    await recorder.start_recording()
    
    # Wait a bit
    print("⏳ Recording for 10 seconds...")
    await asyncio.sleep(10)
    
    # Stop recording
    print("⏹️ Stopping recording...")
    await recorder.stop_recording()
    
    # Wait for processing to complete
    print("⏳ Waiting for video processing to complete...")
    await asyncio.sleep(20)
    
    # Get recording statistics
    stats = recorder.get_stats()
    print(f"\n📊 Recording Statistics:")
    print(f"   Session ID: {stats.session_id}")
    print(f"   Duration: {stats.recording_duration:.1f}s")
    print(f"   Clips recorded: {stats.total_clips_recorded}")
    print(f"   Clips processed: {stats.total_clips_processed}")
    print(f"   Processing failures: {stats.total_processing_failures}")
    
    # Ask questions using the API-based Querier
    print(f"\n🤖 Asking questions about session: {session_id}")
    

    
    
    # Multiple questions
    questions = [
        "What was on the screen?",
        "What applications were visible?",
        "What colors were prominent?",
        "Was there any text visible?"
    ]
    
    print(f"\n🤖 Asking {len(questions)} questions concurrently...")
    print("   This will send all questions to the API at the same time!")
    results = await querier.ask_multiple_questions(questions)
    
    print(f"\n📋 Results for session: {session_id}")
    for i, result in enumerate(results, 1):
        print(f"\n❓ Question {i}: {result.question}")
        if result.analysis_success:
            print(f"📝 Answer: {result.answer}")
            print(f"🎯 Confidence: {result.confidence:.2f}")
            print(f"📹 Video ID: {result.video_id}")
        else:
            print(f"❌ Failed: {result.error_message}")
    

    # Get query statistics
    print(f"\n📊 Getting query statistics...")
    querier_stats = querier.get_stats()
    print(f"✅ Retrieved query statistics")
    print(f"   Total queries: {querier_stats.total_queries}")
    print(f"   Successful queries: {querier_stats.successful_queries}")
    print(f"   Failed queries: {querier_stats.failed_queries}")
    print(f"   Average confidence: {querier_stats.average_confidence:.3f}")
    
    # Cleanup
    print(f"\n🧹 Cleaning up...")
    await recorder.cleanup()
    await querier.cleanup()
    
    print("✅ Demo completed")


if __name__ == "__main__":
    asyncio.run(main()) 