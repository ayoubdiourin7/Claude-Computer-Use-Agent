"""
Configuration for Claude Browser Agent
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Anthropic API Configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Claude Model
CLAUDE_MODEL = "claude-sonnet-4.5-20250929"

# WebSocket Server Configuration
WEBSOCKET_HOST = "localhost"
WEBSOCKET_PORT = 8765

# Computer Use Configuration
MAX_TOKENS = 4096
SCREENSHOT_WIDTH = 1280  # Default screenshot width
SCREENSHOT_HEIGHT = 800  # Default screenshot height

# Logging
DEBUG = True

def validate_config():
    """Validate that required configuration is present"""
    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY not found")
        '''raise ValueError(
            "ANTHROPIC_API_KEY not found. "
            "Please set it in .env file or environment variables."
        )'''
    else:
        print("✅ ANTHROPIC_API_KEY found")
    
    print("✅ Configuration loaded successfully")
    #print(f"   Model: {CLAUDE_MODEL}")
    print(f"   WebSocket: {WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    return True