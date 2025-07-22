#!/usr/bin/env python3
"""
Context MCP Server - Serves cached screen context via Model Context Protocol

This MCP server makes your cached screen recording context available to 
AI assistants through Cursor's MCP integration.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("screen-context")
ddmmyyyy = datetime.now().strftime('%d%m%Y')
cache_file = Path.home() / f'.cache/inframe/{ddmmyyyy}'

@mcp.tool()
async def get_latest_screen_context() -> str:
    """Get the latest screen recording context and transcription"""
    
    if cache_file.exists():
        content = cache_file.read_text()
        return content
    else:
        return "No screen context available. Run 'python local_context_recorder.py' to record some context."

@mcp.tool()
async def check_screen_context_status() -> str:
    """Check if screen context is available and show basic info"""
    
    if cache_file.exists():
        content = cache_file.read_text()
        lines = content.split('\n')
        # Find the most recent session
        recent_session = None
        for line in lines:
            if line.startswith('NEW RECORDING SESSION'):
                recent_session = line
        
        if recent_session:
            return f"Screen context is available. {recent_session}\nTotal content length: {len(content)} characters"
        else:
            return f"Screen context file exists but no sessions found. Content length: {len(content)} characters"
    else:
        return "No screen context available. Run 'python local_context_recorder.py' to record some context."

async def main():
    """Main async function to run the server"""
    await mcp.run_stdio_async()

if __name__ == "__main__":
    asyncio.run(main()) 