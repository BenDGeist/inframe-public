#!/usr/bin/env python3
"""
Recorder class that handles video recording and sends clips to Modal API for processing.
Provides a simple start/stop interface for recording with automatic clip processing.
"""

import asyncio
import base64
import os
import tempfile
import uuid
import httpx
from typing import Optional, Dict, Any
from dataclasses import dataclass

from src.video_stream import VideoStream


@dataclass
class RecordingStats:
    """Statistics about a recording session"""
    session_id: str
    total_clips_recorded: int
    total_clips_processed: int
    total_processing_failures: int
    recording_duration: float
    is_running: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'session_id': self.session_id,
            'total_clips_recorded': self.total_clips_recorded,
            'total_clips_processed': self.total_clips_processed,
            'total_processing_failures': self.total_processing_failures,
            'recording_duration': self.recording_duration,
            'is_running': self.is_running
        }


class Recorder:
    """Video recorder that sends clips to Modal API for processing"""
    
    def __init__(self, 
                 session_id: Optional[str] = None,
                 temp_dir: Optional[str] = None,
                 max_clips: int = 50):
        """Initialize the recorder
        
        Args:
            session_id: Unique session identifier (auto-generated if None)
            temp_dir: Directory for temporary video files (default: system temp)
            max_clips: Maximum number of clips to keep in memory
        """
        # Generate session ID if not provided
        self.session_id = session_id or str(uuid.uuid4())
        
        # Set up temp directory with session subfolder
        base_temp_dir = temp_dir or tempfile.gettempdir()
        self.temp_dir = os.path.join(base_temp_dir, f"recorder_{self.session_id}")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Initialize video stream
        self.video_stream = VideoStream.create(
            temp_dir=self.temp_dir,
            max_clips=max_clips
        )
        
        # State tracking
        self.is_recording = False
        self.start_time: Optional[float] = None
        self.recording_stats = RecordingStats(
            session_id=self.session_id,
            total_clips_recorded=0,
            total_clips_processed=0,
            total_processing_failures=0,
            recording_duration=0.0,
            is_running=False
        )
        
        print("✅ Recorder initialized")
        print(f"   Session ID: {self.session_id}")
        print(f"   Temp directory: {self.temp_dir}")
    
    def get_session_id(self) -> str:
        """Get the session ID for this recorder"""
        return self.session_id
    
    def get_session_dir(self) -> str:
        """Get the session-specific directory"""
        return self.temp_dir
    
    async def _process_clip_callback(self, clip):
        """Callback function to process new video clips via HTTP API"""
        print(f"🔔 CALLBACK EXECUTED: Processing clip {clip.file_path}")
        try:
            import httpx
            import json
            import base64
            import modal
            
            # Get the processing URL from environment
            processing_url = os.environ.get("PROCESSING_URL", "https://adscope--processing-service.modal.run")
            endpoint_url = processing_url.replace(".modal.run", "-process-v1.modal.run")
            
            print(f"📡 Making HTTP request to: {endpoint_url}")
            print(f"📡 Session ID: {self.session_id}")
            
            # Read video file and encode
            with open(clip.file_path, 'rb') as f:
                video_data = f.read()
            
            print(f"📡 Video data size: {len(video_data)} bytes")
            video_data_b64 = base64.b64encode(video_data).decode('utf-8')
            
            # Prepare clip data as JSON string (including video data)
            clip_json = json.dumps({
                "start_time": clip.start_time,
                "end_time": clip.end_time,
                "video_data_b64": video_data_b64
            })
            
            print(f"📡 About to make HTTP request...")
            
            # Make HTTP POST request with relaxed SSL settings
            async with httpx.AsyncClient(
                timeout=120.0,  # Much longer timeout for video processing (up to 2 minutes)
                verify=False,  # Disable SSL verification for testing
                http2=False    # Disable HTTP/2 to avoid compatibility issues
            ) as client:
                response = await client.post(
                    endpoint_url,
                    params={
                        "session_id": self.session_id,
                        "num_frames": 4
                    },
                    json={"clip_json": clip_json}
                )
                
                print(f"📡 HTTP Response: {response.status_code}")
                print(f"📡 Response body: {response.text[:500]}")
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Update stats
                    self.recording_stats.total_clips_recorded += 1
                    if result.get("success"):
                        result_data = result.get("result", {})
                        frames_embedded = result_data.get("successful_frame_count", 0)
                        self.recording_stats.total_clips_processed += 1
                        print(f"✅ Processed clip: {os.path.basename(clip.file_path)} ({frames_embedded} frames embedded)")
                    else:
                        self.recording_stats.total_processing_failures += 1
                        print(f"❌ Failed to process clip: {result.get('error', 'Unknown error')}")
                else:
                    self.recording_stats.total_processing_failures += 1
                    print(f"❌ HTTP error {response.status_code}: {response.text}")
                    
        except Exception as e:
            self.recording_stats.total_processing_failures += 1
            print(f"❌ Error processing clip: {e}")
    
    async def start_recording(self) -> None:
        """Start video recording with automatic clip processing via Modal API"""
        if self.is_recording:
            print("⚠️ Recording already in progress")
            return
        
        try:
            print(f"🎬 Starting recording for session: {self.session_id}")
            
            # Start video stream
            await self.video_stream.start_stream()
            
            # Set callback for clip processing
            self.video_stream.set_callback(self._process_clip_callback)
            
            # Update state
            self.is_recording = True
            self.start_time = asyncio.get_event_loop().time()
            self.recording_stats.is_running = True
            
            print("✅ Recording started successfully!")
            print(f"   Session ID: {self.session_id}")
            print("   Video stream: Active")
            print("   Clip processing: Via Modal API")
            
        except Exception as e:
            print(f"❌ Failed to start recording: {e}")
            await self._cleanup_on_error()
            raise
    
    async def stop_recording(self) -> None:
        """Stop video recording"""
        if not self.is_recording:
            print("⚠️ No recording in progress")
            return
        
        try:
            print(f"⏹️ Stopping recording for session: {self.session_id}")
            
            # Stop video stream
            await self.video_stream.stop_stream()
            
            # Update state and stats
            self.is_recording = False
            if self.start_time:
                self.recording_stats.recording_duration = asyncio.get_event_loop().time() - self.start_time
            self.recording_stats.is_running = False
            
            print("✅ Recording stopped successfully!")
            print(f"   Session ID: {self.session_id}")
            print(f"   Duration: {self.recording_stats.recording_duration:.1f}s")
            print(f"   Clips recorded: {self.recording_stats.total_clips_recorded}")
            print(f"   Clips processed: {self.recording_stats.total_clips_processed}")
            print(f"   Processing failures: {self.recording_stats.total_processing_failures}")
            
        except Exception as e:
            print(f"❌ Error stopping recording: {e}")
            await self._cleanup_on_error()
            raise
    
    async def _cleanup_on_error(self) -> None:
        """Clean up resources when an error occurs"""
        try:
            if self.video_stream:
                await self.video_stream.stop_stream()
        except:
            pass
        
        self.is_recording = False
        self.recording_stats.is_running = False
    
    def get_stats(self) -> RecordingStats:
        """Get current recording statistics"""
        return self.recording_stats
    
    async def cleanup(self) -> None:
        """Clean up all resources"""
        print(f"🧹 Cleaning up recorder for session: {self.session_id}")
        
        if self.is_recording:
            await self.stop_recording()
        
        if self.video_stream:
            try:
                await self.video_stream.stop_stream()
            except:
                pass
        
        print("✅ Recorder cleanup completed")


# Factory function for easy creation
def create_recorder(session_id: Optional[str] = None,
                   temp_dir: Optional[str] = None,
                   max_clips: int = 50) -> Recorder:
    """Create a recorder for video recording with automatic clip processing via Modal API
    
    Args:
        session_id: Unique session identifier (auto-generated if None)
        temp_dir: Directory for temporary video files
        max_clips: Maximum number of clips to keep in memory
        
    Returns:
        Recorder instance
    """
    return Recorder(
        session_id=session_id,
        temp_dir=temp_dir,
        max_clips=max_clips
    ) 