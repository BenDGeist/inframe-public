# Inframe Examples

This directory contains examples demonstrating how to use the inframe package.

## Examples

### simple_agent.py
A more advanced example showing:
- IDE detection
- Directory name extraction
- Real-time callbacks
- Graceful shutdown

Run with:
```bash
python examples/simple_agent.py
```

Or as a command:
```bash
inframe-agent
```

## Prerequisites

1. Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

2. Grant screen recording permissions to your terminal/IDE in System Preferences > Security & Privacy > Privacy > Screen Recording

## Usage

All examples can be run directly with Python or as installed commands after installing the package:

```bash
# Install in development mode
pip install inframe

# Run examples
inframe-agent
inframe-record --help
``` 