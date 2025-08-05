import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
import tempfile
from dataclasses import dataclass
import uuid

from src.video_stream import VideoStream
from src.transcription_pipeline import create_transcription_pipeline, TranscriptionPipeline
from src.context_integrator import create_context_integrator

RecordingMode = Literal["full_screen", "window_only"]

@dataclass
class RecorderConfig:
    include_apps: Optional[List[str]] = None
    recording_mode: RecordingMode = "full_screen"
    visual_task: Optional[str] = None
    video_stream: Optional[VideoStream] = None
    transcription_pipeline: Optional[TranscriptionPipeline] = None
    is_recording: bool = False

class ContextRecorder:
    def __init__(self, openai_api_key: Optional[str] = None, cache_file: str = str(Path.home() / ".cache/inframe")):
        self.openai_api_key = openai_api_key
        self.is_recording = False
        self.cache_file = Path(cache_file)
        self._id = str(uuid.uuid4())  # Generate unique ID for this instance
        
        # Ensure cache directory exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Set up temporary recordings directory
        self.recordings_dir = Path(tempfile.gettempdir()) / 'screenctx_recordings'
        self.recordings_dir.mkdir(exist_ok=True)
        
        self.recorders = {}
        self.active_recorders = 0
        self.active_queries = {}  # recorder_id -> set of query_ids   
        
        session_title = f"Context Recording Session - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.context_integrator = create_context_integrator(
            session_title=session_title,
            openai_api_key=openai_api_key
        )
        
        # Context export callback
        self.context_integrator.set_callback(self._on_context_update)
    
    def __hash__(self):
        """Make ContextRecorder hashable using its unique ID"""
        return hash(self._id)
    
    def __eq__(self, other):
        """Check equality based on unique ID"""
        if isinstance(other, ContextRecorder):
            return self._id == other._id
        return False
    
    @property
    def id(self):
        """Get the unique ID for this recorder"""
        return self._id
    
    def register_query(self, recorder_id: str, query_id: str):
        """Register a query as active on this recorder"""
        if recorder_id in self.active_queries:
            self.active_queries[recorder_id].add(query_id)
    
    def unregister_query(self, recorder_id: str, query_id: str):
        """Unregister a query from this recorder"""
        if recorder_id in self.active_queries:
            self.active_queries[recorder_id].discard(query_id)
        
    async def _on_context_update(self, context_update):
        """Callback called when context is updated - exports to cache file"""
        try:
            # Get current context and export to cache file
            current_context = await self.context_integrator.get_current_context()
            
            # Ensure we have a string
            if isinstance(current_context, dict):
                # If it's a dict, convert to JSON string
                import json
                current_context = json.dumps(current_context, indent=2)
            elif not isinstance(current_context, str):
                # Convert to string if it's not already
                current_context = str(current_context)
            
            # Write to cache file for compatibility with existing ContextQuery
            self.cache_file.write_text(current_context)
            
        except Exception as e:
            print(f"Error updating context cache: {e}")
            import traceback
            traceback.print_exc()
    
    def add_recorder(self, buffer_duration: int = 30, include_apps: Optional[List[str]] = [],
                 recording_mode: RecordingMode = "full_screen", chunk_duration: float = 5.0, max_clips: int = 20, video_priority: int = 0, context_priority: int = 0, visual_task: Optional[str] = None):

        recorder_id = str(uuid.uuid4())
        video_stream = VideoStream.create(
            chunk_duration=chunk_duration,
            max_clips=max_clips,
            temp_dir=str(self.recordings_dir / recorder_id),
            buffer_duration=buffer_duration,
            priority=video_priority
        )
        
        transcription_pipeline = create_transcription_pipeline(
            openai_api_key=self.openai_api_key,
            use_openai=True,  # Always try to use OpenAI if available
            priority=context_priority
        )

        config = RecorderConfig(
            include_apps=include_apps,
            recording_mode=recording_mode,
            visual_task=visual_task,
            video_stream=video_stream,
            transcription_pipeline=transcription_pipeline
        )

        self.recorders[recorder_id] = config
        self.active_queries[recorder_id] = set()  # Initialize empty query set

        return recorder_id

    
    async def start(self, recorder_id: str) -> bool:
        """Start the recording session"""
            
        if recorder_id not in self.recorders:
            print(f"❌ Recorder {recorder_id} not found")
            return False
        

        try:
            config = self.recorders[recorder_id]
            video_stream = config.video_stream
            recording_mode = config.recording_mode
            transcription_pipeline = config.transcription_pipeline
            visual_task = config.visual_task

            print(f"🎬 Starting context recording in {recording_mode} mode...")
            
            # Start video stream
            success = await video_stream.start_stream(recording_mode=recording_mode)
            if not success:
                print("❌ Failed to start video stream")
                return False
            
            # Start transcription pipeline
            await transcription_pipeline.start_pipeline(video_stream, visual_task)
            
            # Start context integrator
            await self.context_integrator.start_integrator(transcription_pipeline)
            
            config.is_recording = True
            self.is_recording = True
            self.active_recorders += 1
            print(f"✅ Context recording started successfully")
            
            return True
            
        except Exception as e:
            print(f"❌ Error starting recording: {e}")
            return False
    
    async def stop(self, recorder_id: str) -> bool:
        """Stop the recording session"""
        if not self.recorders[recorder_id].is_recording:
            return True  # Already stopped, consider it success
        
        # Check if there are active queries on this recorder
        if recorder_id in self.active_queries and self.active_queries[recorder_id]:
            active_count = len(self.active_queries[recorder_id])
            raise ValueError(f"Cannot stop recorder - it has {active_count} active queries. Stop queries first.")
        
        try:
            config = self.recorders[recorder_id]
            video_stream = config.video_stream
            transcription_pipeline = config.transcription_pipeline


            print("🛑 Stopping context recording...")
            
            # Stop components in reverse order with more aggressive timeouts
            print("📋 Stopping transcription pipeline...")
            try:
                await asyncio.wait_for(transcription_pipeline.stop_pipeline(), timeout=5.0)
                print("✅ Transcription pipeline stopped")
            except asyncio.TimeoutError:
                print("⚠️ Transcription pipeline stop timed out")
            
            print("📹 Stopping video stream...")
            try:
                await asyncio.wait_for(video_stream.stop_stream(), timeout=5.0)
                print("✅ Video stream stopped")
            except asyncio.TimeoutError:
                print("⚠️ Video stream stop timed out")
            
            config.is_recording = False
            self.active_recorders -= 1
            if self.active_recorders == 0:
                self.is_recording = False
            print("✅ Context recording stopped")
            
            return True
            
        except Exception as e:
            print(f"❌ Error stopping recording: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the entire recorder system - stops all recordings and the context integrator"""
        try:
            print("🔄 Shutting down ContextRecorder...")
            
            # Stop all active recordings
            active_recorder_ids = list(self.recorders.keys())
            for recorder_id in active_recorder_ids:
                if self.recorders[recorder_id].is_recording:
                    print(f"Stopping recorder {recorder_id[:8]}...")
                    try:
                        await self.stop(recorder_id)
                    except Exception as e:
                        print(f"❌ Error stopping recorder {recorder_id[:8]}: {e}")
            
            # Stop the shared context integrator
            await self.context_integrator.stop_integrator()
            
            # Clear all state
            self.recorders.clear()
            self.active_queries.clear()
            self.is_recording = False
            self.active_recorders = 0
            
            print("✅ ContextRecorder shutdown complete")
            return True
            
        except Exception as e:
            print(f"❌ Error during shutdown: {e}")
            return False
    
    async def get_status(self, recorder_id) -> Dict[str, Any]:
        """Get current recording status"""

        if recorder_id not in self.recorders:
            print(f"❌ Recorder {recorder_id} not found")
            return {
                'is_recording': False,
                'message': f'Recorder {recorder_id} not found'
            }
        
        
        if not self.recorders[recorder_id].is_recording:
            return {
                'is_recording': False,
                'message': 'Not recording'
            }
        
        try:
            # Get status from all components
            config = self.recorders[recorder_id]
            video_stream = config.video_stream
            transcription_pipeline = config.transcription_pipeline
            context_integrator = self.context_integrator

            video_status = await video_stream.get_buffer_status()
            pipeline_status = await transcription_pipeline.get_pipeline_status()
            integrator_status = await context_integrator.get_context_status()
            
            return {
                'is_recording': True,
                'video_clips': video_status['clip_count'],
                'buffer_duration': video_status['buffer_duration'],
                'processed_clips': pipeline_status['total_clips_processed'],
                'context_clips': integrator_status['total_clips_processed'],
                'session_duration': integrator_status['session_duration_seconds'],
                'speakers_identified': len(integrator_status['speakers_identified'])
            }
            
        except Exception as e:
            return {
                'is_recording': self.is_recording,
                'error': str(e)
            }
    
    async def get_current_context(self) -> str:
        """Get the current integrated context"""
        if not self.is_recording:
            return "No recording in progress"
        
        try:
            return await self.context_integrator.get_current_context()
        except Exception as e:
            return f"Error getting context: {e}"
    
    async def export_session_summary(self) -> str:
        """Export a summary of the current session"""
        if not self.is_recording:
            return "No recording session to export"
        
        try:
            return await self.context_integrator.export_session_summary()
        except Exception as e:
            return f"Error exporting session: {e}"
    
    def get_cache_file_path(self) -> Path:
        """Get the path to the cache file for compatibility"""
        return self.cache_file
    
    
    def start_sync(self, recorder_id: str) -> bool:
        """Legacy sync method to start recording"""
        return asyncio.run(self.start(recorder_id))
    
    def stop_sync(self, recorder_id: str) -> None:
        """Legacy sync method to stop recording"""
        asyncio.run(self.stop(recorder_id))
    
    def get_status_sync(self, recorder_id: str) -> Dict[str, Any]:
        """Legacy sync method to get status"""
        return asyncio.run(self.get_status(recorder_id))