#!/usr/bin/env python3
"""
Simple Agent Example - Demonstrates basic usage of the inframe package

This example shows how to:
1. Set up a ContextRecorder for screen recording
2. Create ContextQuery for intelligent monitoring
3. Handle callbacks for real-time events
"""

import os
import asyncio
from inframe import ContextRecorder, ContextQuery

class SimpleAgent:
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.recorder = ContextRecorder(openai_api_key=openai_api_key)
        self.query = ContextQuery(openai_api_key=openai_api_key, model="gpt-4o")
        self.recorder_id = None
        self.ide_query_id = None
        self.directory_query_id = None
        self._cleanup_done = False

    async def post_init(self):
        print("🚀 Starting Simple Code Agent")
        
        # First add the recorder with configuration
        self.recorder_id = self.recorder.add_recorder(
            include_apps=["Visual Studio Code", "Cursor", "PyCharm", "IntelliJ IDEA"],
            recording_mode="full_screen",
            visual_task=(
                "Describe the screen content focusing on: "
                "1. Application names and window titles "
                "2. File explorer panels and folder names "
                "3. File names and directory structures "
                "4. UI elements like buttons, tabs, and panels "
                "5. The current file path and file name"
                "Be specific about folder names and project structure."
            )
        )
        # Then start it
        success = await self.recorder.start(self.recorder_id)
        if not success:
            raise Exception("Failed to start recorder")
        
        # Add IDE detection query
        self.ide_query_id = self.query.add_query(
            prompt=(
                "Look at the screen content and determine if a coding IDE (like VS Code, Cursor, PyCharm, "
                "IntelliJ IDEA, Sublime Text, Atom, etc.) is currently visible and being used. "
                "Respond with YES or NO."
            ),
            recorder=self.recorder,
            callback=self.on_ide_detected,
            interval_seconds=3  # Check every 3 seconds
        )

        self.directory_query_id = self.query.add_query(
                    prompt=(
                        "Look at the screen and identify the file the user is working on. "
                        "Look specifically for: "
                        "1. The file name in the file explorer hierarchy "
                        "2. The file name in the window title bar "
                        "DO NOT infer from file names or content - find the actual folder name displayed. "
                        "DO NOT use placeholder text like 'actual_folder_name_here' - use the real folder name you see. "
                        "Respond with the folder name only, no other text."
                    ),
                    recorder=self.recorder,
                    callback=self.on_directory_detected,
                    interval_seconds=3
                )                
        
        await self.query.start(self.ide_query_id)

    async def on_ide_detected(self, result):
        try:
            if not result.answer or result.answer.strip() == "":
                print(f"❌ Empty answer from query (confidence: {result.confidence})")
                return
                
            # The answer is already extracted from JSON, just use it directly
            answer = result.answer.upper()
            confidence = result.confidence
            
            if answer == "YES" and confidence > 0.8:
                print("✅ IDE DETECTED! Starting directory name query...")
                
                await self.query.stop(self.ide_query_id)
                
                await self.query.start(self.directory_query_id)
                
        except Exception as e:
            print(f"❌ Error in IDE detection callback: {e}")

    async def on_directory_detected(self, result):
        try:
            if not result.answer or result.answer.strip() == "":
                print(f"❌ Empty answer from query (confidence: {result.confidence})")
                return
                
            # The answer is already extracted from JSON, just use it directly
            directory_name = result.answer
            confidence = result.confidence
            
            if confidence > 0.6:
                print(f"✅ DIRECTORY DETECTED: {directory_name} (confidence: {confidence})")
                
                await self.graceful_shutdown()
                
        except Exception as e:
            print(f"❌ Error in directory detection callback: {e}")
            print(f"   Answer: '{result.answer}'")
            print(f"   Confidence: {result.confidence}")
            print(f"   Error: {result.error if result.error else 'None'}")

    async def graceful_shutdown(self):
        """Gracefully shutdown all components"""
        if self._cleanup_done:
            return
            
        self._cleanup_done = True
        await self.query.shutdown()
        await self.recorder.shutdown()

    async def stop_session(self):
        """Stop session - just calls graceful_shutdown"""
        await self.graceful_shutdown()

async def main():
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        return
    
    agent = SimpleAgent(openai_api_key)
    
    try:
        await agent.post_init()
        print("⏳ Monitoring for 60 seconds...")
        await asyncio.sleep(60)  # Give enough time for queries to run
        
    except KeyboardInterrupt:
        print("🛑 Keyboard interrupt caught")
        
    except Exception as e:
        print(f"❌ Error in main: {e}")
        
    finally:
        try:
            await agent.graceful_shutdown()
            print("✅ Agent shutdown complete")
        except Exception as e:
            print(f"❌ Error during shutdown: {e}")

def run_with_cleanup():
    """Run the agent with proper task cleanup to prevent recursion errors"""
    try:
        # Run the main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Keyboard interrupt caught")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_with_cleanup() 