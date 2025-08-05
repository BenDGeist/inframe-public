#!/usr/bin/env python3
"""
API Docs Detection Demo - Clean version for demonstrations

This demo shows how the system can:
1. Detect when you're viewing API documentation
2. Extract function names and URLs automatically
3. Present the information in a clean, structured format

Optimized for fast startup and clean demos.
"""

import os
import asyncio
import logging
from inframe import ContextRecorder, ContextQuery

# Suppress all the verbose logging for clean demos
logging.getLogger().setLevel(logging.ERROR)

class CleanAPIDocsDemo:
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        # Defer heavy initialization until needed
        self.recorder = None
        self.query = None
        self.recorder_id = None
        self.detection_query_id = None
        self.details_query_id = None
        self._cleanup_done = False
        

    async def on_docs_detected(self, result):
        try:
            if not result.answer or result.answer.strip() == "":
                return
                
            answer = result.answer.upper()
            confidence = result.confidence
            
            if answer == "YES" and confidence > 0.7:
                print("\n🎯 API DOCUMENTATION DETECTED!")
                print(f"   Confidence: {confidence:.1%}")
                print("   Extracting details...")
                
                await self.query.stop(self.detection_query_id)
                await self.query.start(self.details_query_id)
                
        except Exception as e:
            print(f"❌ Detection error: {e}")

    async def on_details_extracted(self, result):
        try:
            if not result.answer or result.answer.strip() == "":
                return
                
            details = result.answer
            confidence = result.confidence
            
            if confidence > 0.4:
                print("\n📊 EXTRACTION RESULTS")
                print("=" * 50)
                print(f"Confidence: {confidence:.1%}")
                print("-" * 50)
                print(f"📝 {details}")
                print("=" * 50)
                print("✅ Demo completed successfully!")
                
                await self.shutdown()
            else:
                print(f"❌ Confidence too low ({confidence:.3f}) for details extraction")
                
        except Exception as e:
            print(f"❌ Extraction error: {e}")

    async def shutdown(self):
        """Clean shutdown of all components"""
        if self._cleanup_done:
            return
            
        self._cleanup_done = True
        if self.query:
            await self.query.shutdown()
        if self.recorder:
            await self.recorder.shutdown()

async def main():
    print("🚀 API Docs Detection Demo")
    print("=" * 50)
    print("📋 This demo will:")
    print("   1. Monitor your screen for API documentation")
    print("   2. Detect when you're viewing developer docs")
    print("   3. Extract function names and URLs automatically")
    print("   4. Display the results in a structured format")
    print("=" * 50)
    
    # Check for OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    from inframe import ContextRecorder, ContextQuery
    
    # Initialize the demo
    demo = CleanAPIDocsDemo(openai_api_key)
    
    try:
        # Step 1: Initialize components
        print("🔧 Initializing...")
        if demo.recorder is None:
            demo.recorder = ContextRecorder(openai_api_key=demo.openai_api_key)
            demo.query = ContextQuery(openai_api_key=demo.openai_api_key, model="gpt-4o")

        
        # Step 2: Set up screen recording
        print("📹 Setting up screen recording...")
        demo.recorder_id = demo.recorder.add_recorder(
            include_apps=["Chrome", "Safari", "Firefox", "Edge"],
            recording_mode="full_screen",
            visual_task=(
                "Focus on browser content showing API documentation, developer docs, "
                "or technical reference materials. Look for: "
                "- Documentation websites with code examples "
                "- URLS in the browser address bar, write the full URL down"
                "Pay special attention to the browser address bar and any visible code examples."
                "If you see a URL, write it down."
            )
        )
        
        # Step 3: Start recording
        print("🎬 Starting screen recording...")
        success = await demo.recorder.start(demo.recorder_id)
        if not success:
            raise Exception("Failed to start recorder")
        
        print("✅ Screen monitoring started")
        print("🔍 Looking for API documentation...")
        
        # Step 4: Set up detection query
        print("🤖 Setting up detection query...")
        demo.detection_query_id = demo.query.add_query(
            prompt=(
                "Is the user currently viewing API documentation, developer docs, "
                "or technical reference materials? Look for: "
                "- API documentation websites "
                "- Function/method documentation "
                "- Developer portals and reference pages "
                "Respond with YES or NO."
            ),
            recorder=demo.recorder,
            callback=demo.on_docs_detected,
            interval_seconds=2
        )

        # Step 5: Set up details query
        print("🔍 Setting up details extraction query...")
        demo.details_query_id = demo.query.add_query(
            prompt=(
                "Look at the screen and tell me: "
                "1. What website or service is being documented? "
                "2. What is the URL in the browser? "
                "3. Are there any code examples visible? "
                "Answer in simple text format."
            ),
            recorder=demo.recorder,
            callback=demo.on_details_extracted,
            interval_seconds=2
        )                
        
        # Step 6: Start monitoring
        print("🚀 Starting query monitoring...")
        await demo.query.start(demo.detection_query_id)
        
        # Step 7: Run demo
        print("\n⏳ Demo running for 60 seconds...")
        print("   Open any API documentation in your browser to see it in action!")
        await asyncio.sleep(60)
        
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        
    finally:
        # Step 8: Cleanup
        try:
            await demo.shutdown()
            print("✅ Demo shutdown complete")
        except Exception as e:
            print(f"❌ Shutdown error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Demo stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}") 