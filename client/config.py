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
# Screenshot dimensions
REAL_SCREENSHOT_WIDTH = 1200 # Actual browser width
REAL_SCREENSHOT_HEIGHT = 797  # Actual browser height
TARGET_SCREENSHOT_WIDTH = 1024  # What Claude expects
TARGET_SCREENSHOT_HEIGHT = 768  # What Claude expects


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
    print(f"   WebSocket: {WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    print(f"   Target Resolution: {TARGET_SCREENSHOT_WIDTH}x{TARGET_SCREENSHOT_HEIGHT}")
    return True