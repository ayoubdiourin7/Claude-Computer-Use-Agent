# Claude Browser Agent

A browser automation tool that uses Claude's Computer Use capability to control Chrome through natural language commands.

## Overview

Claude Browser Agent enables autonomous web browsing by connecting Claude AI to a Chrome extension, allowing it to see the browser screen and perform actions like clicking, typing, and navigating based on natural language instructions.

## Architecture

The system consists of two main components:

1. **Chrome Extension**:
   * Captures screenshots
   * Executes browser actions (clicks, typing, navigation)
   * Communicates with backend via WebSocket

2. **Python Backend**:
   * Orchestrates the AI workflow
   * Communicates with Claude API
   * Processes screenshots and coordinates
   * Manages the execution loop

## How It Works

```
User → Chrome Extension → Python Backend → Claude API → Python Backend → Chrome Extension → Browser
```

1. User provides a task via the extension popup
2. Backend captures screenshot and sends to Claude
3. Claude analyzes the screenshot and decides what to do next
4. Backend translates Claude's actions to browser commands
5. Extension executes the commands in the browser
6. Process repeats until task completion

## Installation

### Prerequisites
* Python 3.8+
* Google Chrome browser
* Anthropic API key

### Setup

1. Clone the repository:
```bash
git clone https://github.com/ayoubdiourin7/Claude-Computer-Use-Agent
cd claude-browser-agent
```

2. Install Python dependencies:
```bash
cd client
pip install -r requirements.txt
```

3. Configure API key: Create a `.env` file in the `client` directory:
```
ANTHROPIC_API_KEY=your_api_key_here
```

4. Load Chrome extension:
   * Open Chrome and navigate to `chrome://extensions/`
   * Enable "Developer mode"
   * Click "Load unpacked" and select the `extension` directory

## Configuration

Edit `config.py` to adjust settings:

```python
# Screenshot Configuration
REAL_SCREENSHOT_WIDTH   # Logical browser width
REAL_SCREENSHOT_HEIGHT   # Logical browser height

# Target resolution for Claude
TARGET_SCREENSHOT_WIDTH = 1024
TARGET_SCREENSHOT_HEIGHT = 768

# Other settings
MAX_TOKENS = 4096
WEBSOCKET_PORT = 8765
```

## Usage

1. Start the backend server:
```bash
cd client
python main.py
```

2. Click the extension icon in Chrome's toolbar

3. Enter a task in the popup field, such as:
   * "Search Google for AI news"
   * "Login to my Gmail account"
   * "Find products on Amazon"

4. Click "Execute Task" to start the process

## Debugging

The system includes debugging tools to help understand and fix coordinate scaling issues:

1. **Debug Images**:
   * Saved to `client/debug/` directory
   * Shows both original and Claude's view
   * Marks clicked coordinates in both views

2. **Coordinate Scaling**:
   * Transforms Claude's coordinates (1024×768) to browser coordinates
   * Debug logs show both Claude's coordinates and scaled browser coordinates



## Future Improvements

* Enhanced element detection for more accurate clicking
* State tracking to avoid repeating the same actions
* Direct URL navigation capabilities
* Task-specific strategies

