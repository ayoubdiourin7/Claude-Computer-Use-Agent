"""
Chrome Adapter - Translates Claude Computer Use actions into Chrome Extension commands
This is the bridge between Claude's abstract actions and browser-specific commands
"""
import asyncio
import json
from typing import Optional, Dict, Any
import websockets


class ChromeAdapter:
    """Adapter that translates Claude actions to Chrome Extension commands"""
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.last_screenshot: Optional[str] = None
        self.last_action_result: Optional[Dict] = None
        self._waiting_for_response = False
        
    def set_websocket(self, websocket):
        """Set the WebSocket connection to Chrome Extension"""
        self.websocket = websocket
        
    def set_last_screenshot(self, screenshot_data: str):
        """Store screenshot received from extension"""
        self.last_screenshot = screenshot_data
        self._waiting_for_response = False
        
    def set_last_action_result(self, success: bool, data: Any):
        """Store result of last action"""
        self.last_action_result = {
            "success": success,
            "data": data
        }
        self._waiting_for_response = False
        
    async def send_command(self, command: Dict) -> Dict:
        """Send command to Chrome Extension and wait for response"""
        if not self.websocket:
            raise Exception("Chrome Extension not connected")
            
        print(f"📤 Sending to Extension: {command.get('action')}")
        
        # Send command
        await self.websocket.send(json.dumps(command))
        
        # Wait for response
        self._waiting_for_response = True
        timeout = 10  # seconds
        
        for _ in range(timeout * 10):
            if not self._waiting_for_response:
                break
            await asyncio.sleep(0.1)
            
        if self._waiting_for_response:
            raise TimeoutError("Extension did not respond in time")
            
        return self.last_action_result or {}
        
    async def get_screenshot(self) -> str:
        """Request screenshot from Chrome Extension"""
        self.last_screenshot = None
        
        await self.send_command({
            "action": "screenshot"
        })
        
        return self.last_screenshot
        
    async def mouse_move(self, x: int, y: int) -> Dict:
        """Move mouse to coordinates"""
        return await self.send_command({
            "action": "mouse_move",
            "x": x,
            "y": y
        })
        
    async def click(self, x: int, y: int, button: str = "left") -> Dict:
        """Click at coordinates"""
        return await self.send_command({
            "action": "click",
            "x": x,
            "y": y,
            "button": button
        })
        
    async def type_text(self, text: str) -> Dict:
        """Type text"""
        return await self.send_command({
            "action": "type",
            "text": text
        })
        
    async def key_press(self, key: str) -> Dict:
        """Press a key (Enter, Tab, Backspace, etc.)"""
        return await self.send_command({
            "action": "key",
            "key": key
        })
        
    async def scroll(self, direction: str, amount: int = 100) -> Dict:
        """Scroll page"""
        return await self.send_command({
            "action": "scroll",
            "direction": direction,  # "up" or "down"
            "amount": amount
        })
        
    async def navigate(self, url: str) -> Dict:
        """Navigate to URL"""
        return await self.send_command({
            "action": "navigate",
            "url": url
        })
        
    # Bonus tools
    async def switch_tab(self, index: int) -> Dict:
        """Switch to tab by index"""
        return await self.send_command({
            "action": "switch_tab",
            "index": index
        })
        
    async def download_file(self, url: str) -> Dict:
        """Download file from URL"""
        return await self.send_command({
            "action": "download",
            "url": url
        })
        
    def translate_computer_action(self, action: str, **params) -> str:
        """
        Translate Claude Computer Use action to Chrome command
        
        Claude actions: mouse_move, left_click, type, key, screenshot
        Chrome commands: click, type, key, scroll, navigate, etc.
        """
        # This method helps map Claude's computer tool actions
        # to our Chrome-specific commands
        
        action_map = {
            "mouse_move": "mouse_move",
            "left_click": "click",
            "left_click_drag": "drag",
            "right_click": lambda: {"action": "click", "button": "right"},
            "middle_click": lambda: {"action": "click", "button": "middle"},
            "double_click": "double_click",
            "type": "type",
            "key": "key",
            "screenshot": "screenshot",
            "cursor_position": "get_cursor_position"
        }
        
        return action_map.get(action, action)