# Inframe - Screen Context Recording and Querying SDK

A Python SDK for intelligent screen recording, context analysis, and real-time querying. Inframe captures screen activity, processes audio and visual content, and provides an AI-powered interface for understanding your digital workspace.

## Features

- **Real-time Screen Recording**: Native macOS recording with AVFoundation
- **Context-Aware Analysis**: Combines audio transcription with visual content analysis
- **Intelligent Querying**: Ask questions about your screen activity and get AI-powered answers
- **Rolling Buffer**: Maintains recent context for continuous analysis
- **Modular Architecture**: Separate recorders for different applications and contexts
- **Async Processing**: Non-blocking pipeline for smooth operation
- **Cython Optimized**: High-performance core components

## Quick Start

### 1. Install the Package
```bash
pip install inframe
```

### 2. Set Up Environment Variables
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### 3. Basic Usage
```python
import asyncio
from inframe import ContextRecorder, ContextQuery
import os

# Initialize recorder and query system
recorder = ContextRecorder(openai_api_key=os.getenv("OPENAI_API_KEY"))
query = ContextQuery(openai_api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")

# Set up screen recording
screen_recorder = recorder.add_recorder(
    include_apps=["VS Code", "PyCharm", "Cursor"],
    recording_mode="full_screen",
    visual_task="Describe visible code, terminal output, and development activity."
)

# Set up Slack monitoring
slack_recorder = recorder.add_recorder(
    include_apps=["Slack"],
    recording_mode="full_screen", 
    visual_task="Summarize recent DMs and workspace activity."
)

# Define a query to monitor for specific events
async def on_code_change_requested(result):
    if "code change" in result.answer.lower():
        print("Boss requested a code change!")
        # Handle the request...

query.add_query(
    prompt="Has my boss asked for a code change?",
    recorder=slack_recorder,
    callback=on_code_change_requested,
    interval_seconds=5
)

# Start recording and monitoring
await recorder.start()
await query.start()
```

## Core Components

### ContextRecorder
Manages screen recording and context integration:

```python
from inframe import ContextRecorder

# Create recorder
recorder = ContextRecorder(openai_api_key="your-key")

# Add recorder with configuration
recorder_id = recorder.add_recorder(
    buffer_duration=30,  # seconds to keep in buffer
    include_apps=["VS Code", "PyCharm"],  # apps to monitor
    recording_mode="full_screen", 
    visual_task="Describe code changes and development activity"
)

# Start recording
await recorder.start(recorder_id)

# Stop recording
await recorder.stop(recorder_id)
```

### ContextQuery
Provides intelligent querying capabilities over recorded content:

```python
from inframe import ContextQuery

query = ContextQuery(openai_api_key="your-key", model="gpt-4o-mini")

# Add a query to monitor the recorder
query_id = query.add_query(
    prompt="What was I working on in the last 30 minutes?",
    recorder=recorder,
    interval_seconds=30
)

# Start monitoring
await query.start(query_id)
```

## Installation

### Prerequisites
- **macOS** (for native screen recording with AVFoundation)
- **Python 3.8+**
- **Screen Recording Permissions** - Grant in System Preferences > Security & Privacy > Privacy > Screen Recording

### Quick Install
```bash
pip install inframe
```

### Development Install
```bash
# For development access, contact the maintainer
# Private repository - requires access permissions

# Create conda environment (recommended)
conda env create -f environment.yml
conda activate inframe
```

## Dependencies
Core dependencies (automatically installed):
- `opencv-python>=4.5.0,<4.9.0` - Video processing
- `numpy>=1.21.0,<2.0.0` - Numerical computing
- `openai>=1.0.0` - AI analysis
- `faster-whisper>=0.7.0` - Speech recognition
- `pyobjc-framework-*` - macOS integration
- `mcp` and `fastmcp` - Model Context Protocol

## Advanced Usage

### Local Context Recording
Use the included CLI tool for quick testing:

```bash
# Record for 30 seconds and print context
python local-inframe/local_context_recorder.py --duration 30 --print-context

# Record with specific apps
python local-inframe/local_context_recorder.py --duration 60 --include-apps "Visual Studio Code" "Cursor" --print-context
```

### Custom Visual Tasks
Define specific analysis tasks for different applications:

```python
# Code review assistant
recorder_id = recorder.add_recorder(
    include_apps=["VS Code", "GitHub"],
    visual_task="Identify code changes, review comments, and pull request status"
)

# Meeting summarizer  
recorder_id = recorder.add_recorder(
    include_apps=["Zoom", "Teams"],
    visual_task="Summarize meeting topics, participants, and action items"
)
```

### Real-time Monitoring
Set up continuous monitoring with callbacks:

```python
async def on_urgent_message(result):
    if "urgent" in result.answer.lower():
        print("Urgent message detected!")
        # Handle the urgent message

query.add_query(
    prompt="Is there an urgent or important message?",
    recorder=recorder,
    callback=on_urgent_message,
    interval_seconds=10
)
```

## Project Structure

```
inframe/
├── inframe/                    # Main package
│   ├── __init__.py            # Package exports
│   ├── recorder.py            # ContextRecorder class
│   └── query.py               # ContextQuery class
├── inframe/_src/              # Cython-optimized core (compiled)
│   ├── video_stream.cpython-*.so
│   ├── transcription_pipeline.cpython-*.so
│   ├── context_integrator.cpython-*.so
│   ├── context_querier.cpython-*.so
│   └── tldw_utils.cpython-*.so
└── examples/                  # Example implementations
    └── simple_agent.py        # Basic usage example
```

## Configuration

### Environment Variables
```bash
export OPENAI_API_KEY="your-api-key"
export KMP_DUPLICATE_LIB_OK="TRUE"  # For macOS compatibility
```

### Recording Settings
- `buffer_duration`: Seconds to keep in rolling buffer (default: 30)
- `recording_mode`: "full_screen" or "window_only"
- `include_apps`: List of applications to monitor
- `visual_task`: Specific analysis instructions
- `interval_seconds`: Query frequency for monitoring

## Troubleshooting

### Common Issues

1. **Screen Recording Permission Error**
   ```
   ❌ Screen recording permission not granted
   ```
   **Solution**: Go to System Preferences > Security & Privacy > Privacy > Screen Recording and add your terminal/IDE.

2. **Import Errors**
   ```
   ModuleNotFoundError: No module named 'src'
   ```
   **Solution**: Install the package properly with `pip install inframe` or `pip install -e .`

3. **OpenAI API Errors**
   ```
   ⚠️ No OpenAI API key provided
   ```
   **Solution**: Set your OpenAI API key: `export OPENAI_API_KEY="your-key"`

4. **Recording Stops Unexpectedly**
   ```
   ❌ Recording error: Error Domain=AVFoundationErrorDomain
   ```
   **Solution**: Restart your terminal/IDE after granting permissions.

### Debug Mode
Enable verbose logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Considerations

- **Memory Usage**: Rolling buffers prevent memory accumulation
- **API Costs**: Configurable intervals control OpenAI usage
- **Processing**: Async pipeline ensures non-blocking operation
- **Storage**: Temporary files are automatically cleaned up
- **Cython**: Core components are compiled for performance

## License

This software is proprietary and not open source. For commercial licensing, please contact Ben Geist at bendgeist99@gmail.com. 