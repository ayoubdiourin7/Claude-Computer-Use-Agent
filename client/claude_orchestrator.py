"""
Claude Orchestrator - Implements the Computer Use loop with Claude API
This is the brain that uses Claude to understand tasks and decide actions
"""
import anthropic
from typing import List, Dict, Any
import base64

import asyncio
import config
from chrome_adapter import ChromeAdapter


class ClaudeOrchestrator:
    """Orchestrates Computer Use loop with Claude API"""
    
    def __init__(self, chrome_adapter: ChromeAdapter):
        self.chrome_adapter = chrome_adapter
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.messages: List[Dict] = []
        
    async def execute_task(self, task: str):
        """Execute a task using Claude Computer Use"""
        print(f"\n{'='*60}")
        print(f"🎯 TESTING BROWSER CONTROLS: {task}")
        print(f"{'='*60}\n")
        
        try:
            # TEST 1: Initial screenshot
            print("\n--- TEST 1: Screenshot ---")
            screenshot = await self.chrome_adapter.get_screenshot()
            self.save_screenshot(screenshot, "test_1_initial.png")
            print("✅ Initial screenshot saved")
            
            await asyncio.sleep(1)
            
            # TEST 2: Navigate to a test page
            print("\n--- TEST 2: Navigate ---")
            await self.chrome_adapter.navigate("https://www.gmail.com/")
            await asyncio.sleep(2)
            screenshot = await self.chrome_adapter.get_screenshot()
            self.save_screenshot(screenshot, "test_2_navigate.png")
            print("✅ Navigation screenshot saved")
            
            # TEST 3: Click at center of page
            print("\n--- TEST 3: Click (640, 400) ---")
            await self.chrome_adapter.click(640, 400, "left")
            await asyncio.sleep(1)
            screenshot = await self.chrome_adapter.get_screenshot()
            self.save_screenshot(screenshot, "test_3_click.png")
            print("✅ Click screenshot saved")
            
            # TEST 4: Scroll down
            print("\n--- TEST 4: Scroll Down ---")
            await self.chrome_adapter.scroll("down", 200)
            await asyncio.sleep(1)
            screenshot = await self.chrome_adapter.get_screenshot()
            self.save_screenshot(screenshot, "test_4_scroll_down.png")
            print("✅ Scroll down screenshot saved")
            
            # TEST 5: Scroll up
            print("\n--- TEST 5: Scroll Up ---")
            await self.chrome_adapter.scroll("up", 200)
            await asyncio.sleep(1)
            screenshot = await self.chrome_adapter.get_screenshot()
            self.save_screenshot(screenshot, "test_5_scroll_up.png")
            print("✅ Scroll up screenshot saved")
            
            # TEST 6: Navigate to Google
            print("\n--- TEST 6: Navigate to Google ---")
            await self.chrome_adapter.navigate("https://www.google.com")
            await asyncio.sleep(2)
            screenshot = await self.chrome_adapter.get_screenshot()
            self.save_screenshot(screenshot, "test_6_google.png")
            print("✅ Google screenshot saved")
            
            # TEST 7: Click on search box (approximate center)
            print("\n--- TEST 7: Click Search Box ---")
            await self.chrome_adapter.click(640, 400, "left")
            await asyncio.sleep(0.5)
            screenshot = await self.chrome_adapter.get_screenshot()
            self.save_screenshot(screenshot, "test_7_click_search.png")
            print("✅ Click search screenshot saved")
            
            # TEST 8: Type text
            print("\n--- TEST 8: Type Text ---")
            await self.chrome_adapter.type_text("Hello from Claude Agent")
            await asyncio.sleep(1)
            screenshot = await self.chrome_adapter.get_screenshot()
            self.save_screenshot(screenshot, "test_8_type.png")
            print("✅ Type screenshot saved")
            
            # TEST 9: Press Enter
            print("\n--- TEST 9: Press Enter ---")
            await self.chrome_adapter.key_press("Enter")
            await asyncio.sleep(2)
            screenshot = await self.chrome_adapter.get_screenshot()
            self.save_screenshot(screenshot, "test_9_enter.png")
            print("✅ Enter screenshot saved")
            
            # TEST 10: Final scroll
            print("\n--- TEST 10: Final Scroll ---")
            await self.chrome_adapter.scroll("down", 300)
            await asyncio.sleep(1)
            screenshot = await self.chrome_adapter.get_screenshot()
            self.save_screenshot(screenshot, "test_10_final_scroll.png")
            print("✅ Final screenshot saved")
            
            print("\n" + "="*60)
            print("✅ ALL TESTS COMPLETED!")
            print("📁 Check screenshots: test_*.png")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

    def save_screenshot(self, screenshot_base64: str, filename: str):
        """Save screenshot to file for debugging"""
        if screenshot_base64:
            import base64
            with open(filename, "wb") as f:
                f.write(base64.b64decode(screenshot_base64))
            print(f"💾 Saved: {filename}") 
    async def call_claude_with_screenshot(self, screenshot_base64: str):
        """Call Claude API with Computer Use tool and screenshot"""
        
        # Build message with screenshot
        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_base64
                    }
                },
                {
                    "type": "text",
                    "text": "Here is the current state of the browser. What should I do next?"
                }
            ]
        }
        
        # Add to conversation
        messages = self.messages + [user_message]
        
        # Define Computer Use tool
        computer_tool = {
            "type": "computer_20241022",
            "name": "computer",
            "display_width_px": config.SCREENSHOT_WIDTH,
            "display_height_px": config.SCREENSHOT_HEIGHT,
            "display_number": 1
        }
        
        # Call Claude
        response = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=config.MAX_TOKENS,
            messages=messages,
            tools=[computer_tool]
        )
        
        return response
        
    async def execute_tool_use(self, tool_use):
        """Execute a tool use from Claude"""
        tool_name = tool_use.name
        tool_input = tool_use.input
        
        print(f"\n🔧 Tool: {tool_name}")
        print(f"   Input: {tool_input}")
        
        if tool_name != "computer":
            print(f"⚠️ Unknown tool: {tool_name}")
            return
        
        # Extract action and parameters
        action = tool_input.get("action")
        
        # Execute the action
        result = await self.execute_computer_action(action, tool_input)
        
        # Add tool result to messages
        tool_result = {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": str(result)
                }
            ]
        }
        
        self.messages.append(tool_result)
        
    async def execute_computer_action(self, action: str, params: Dict) -> str:
        """Execute a computer action via Chrome Adapter"""
        
        try:
            if action == "screenshot":
                screenshot = await self.chrome_adapter.get_screenshot()
                return "Screenshot taken"
                
            elif action == "mouse_move":
                x, y = params.get("coordinate", [0, 0])
                await self.chrome_adapter.mouse_move(x, y)
                return f"Moved mouse to ({x}, {y})"
                
            elif action == "left_click":
                x, y = params.get("coordinate", [0, 0])
                await self.chrome_adapter.click(x, y, "left")
                return f"Clicked at ({x}, {y})"
                
            elif action == "right_click":
                x, y = params.get("coordinate", [0, 0])
                await self.chrome_adapter.click(x, y, "right")
                return f"Right-clicked at ({x}, {y})"
                
            elif action == "double_click":
                x, y = params.get("coordinate", [0, 0])
                await self.chrome_adapter.click(x, y, "left")
                await self.chrome_adapter.click(x, y, "left")
                return f"Double-clicked at ({x}, {y})"
                
            elif action == "type":
                text = params.get("text", "")
                await self.chrome_adapter.type_text(text)
                return f"Typed: {text}"
                
            elif action == "key":
                key = params.get("text", "")
                await self.chrome_adapter.key_press(key)
                return f"Pressed key: {key}"
                
            else:
                return f"Unknown action: {action}"
                
        except Exception as e:
            return f"Error executing {action}: {str(e)}"
            
    def extract_final_message(self, response) -> str:
        """Extract final text message from Claude response"""
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""