"""
Claude Orchestrator - Implements the Computer Use loop with Claude API
This is the brain that uses Claude to understand tasks and decide actions
"""
import anthropic
from typing import List, Dict, Any, Optional
import base64
from PIL import Image
import io
import traceback
import time

import config
from chrome_adapter import ChromeAdapter


class ClaudeOrchestrator:
    """Orchestrates Computer Use loop with Claude API"""
    
    def __init__(self, chrome_adapter: ChromeAdapter):
        self.chrome_adapter = chrome_adapter
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.messages: List[Dict] = []
        self.real_width = config.REAL_SCREENSHOT_WIDTH
        self.real_height = config.REAL_SCREENSHOT_HEIGHT
        self.target_width = config.TARGET_SCREENSHOT_WIDTH
        self.target_height = config.TARGET_SCREENSHOT_HEIGHT
        self.last_tool_use_id = None  # Track the last tool use ID
        
    async def execute_task(self, task: str):
        """Execute a task using Claude Computer Use"""
        print(f"\n{'='*60}")
        print(f"🎯 EXECUTING TASK: {task}")
        print(f"{'='*60}\n")
        
        # Initialize conversation with the task
        self.messages = [
            {
                "role": "user",
                "content": task
            }
        ]
        
        # Computer Use loop
        max_iterations = 20
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            
            try:
                # Get current screenshot
                print("📸 Taking screenshot...")
                screenshot = await self.chrome_adapter.get_screenshot()
                
                if not screenshot:
                    print("❌ Failed to get screenshot")
                    break
                
                # Check if screenshot is valid base64
                try:
                    # Basic sanity check for base64
                    test_decode = base64.b64decode(screenshot)
                except Exception as e:
                    print(f"❌ Invalid base64 screenshot: {str(e)}")
                    break
                
                # Resize screenshot to XGA resolution (1024x768)
                try:
                    resized_screenshot = self.resize_screenshot(screenshot)
                except Exception as e:
                    print(f"❌ Error resizing screenshot: {str(e)}")
                    print(traceback.format_exc())
                    # Use original screenshot as fallback
                    print("Using original screenshot as fallback")
                    resized_screenshot = screenshot
                
                # Call Claude with Computer Use
                print("🤖 Calling Claude API...")
                response = await self.call_claude_with_screenshot(resized_screenshot)
                
                # Check if task is complete
                if response.stop_reason == "end_turn":
                    print("\n✅ Task completed!")
                    final_message = self.extract_final_message(response)
                    if final_message:
                        print(f"💬 Claude says: {final_message}")
                    break
                
                # Process tool uses
                tool_uses = [
                    block for block in response.content 
                    if block.type == "tool_use"
                ]
                
                if not tool_uses:
                    print("⚠️ No tool use found, ending...")
                    break
                
                # Add response to messages
                self.messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Execute each tool use
                for tool_use in tool_uses:
                    self.last_tool_use_id = tool_use.id  # Store the tool use ID
                    await self.execute_tool_use(tool_use)
                
            except Exception as e:
                print(f"❌ Error in iteration {iteration}: {e}")
                print(traceback.format_exc())
                break
        
        if iteration >= max_iterations:
            print(f"\n⚠️ Reached maximum iterations ({max_iterations})")
            
        print(f"\n{'='*60}")
        print("Task execution finished")
        print(f"{'='*60}\n")
    
    def resize_screenshot(self, screenshot_base64: str) -> str:
        """Resize screenshot to XGA resolution (1024x768)"""
        try:
            # Decode base64 to bytes
            img_bytes = base64.b64decode(screenshot_base64)
            
            # Create a BytesIO object from the bytes
            img_buffer = io.BytesIO(img_bytes)
            img_buffer.seek(0)
            
            # Open the image
            img = Image.open(img_buffer)
            
            # Get original size
            original_width, original_height = img.size
            print(f"📐 Original screenshot size: {original_width}x{original_height}")
            
            # Update real dimensions for coordinate scaling
            self.real_width = original_width
            self.real_height = original_height
            
            # Resize to target resolution
            resized_img = img.resize((self.target_width, self.target_height), Image.LANCZOS)
            print(f"📐 Resized screenshot to: {self.target_width}x{self.target_height}")
            
            # Convert back to base64
            buffer = io.BytesIO()
            resized_img.save(buffer, format="JPEG", quality=75)
            buffer.seek(0)
            resized_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Calculate compression ratio
            original_size = len(screenshot_base64)
            new_size = len(resized_base64)
            ratio = (original_size / new_size) if new_size > 0 else 0
            print(f"🗜️ Compression: {original_size/1024:.1f}KB → {new_size/1024:.1f}KB ({ratio:.1f}x)")
            
            return resized_base64
            
        except Exception as e:
            print(f"❌ Error in resize_screenshot: {e}")
            print(traceback.format_exc())
            raise
        
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
                        "media_type": "image/jpeg",
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
        messages = self.messages.copy()
        messages.append(user_message)

        try:
            # Add exponential backoff for API calls
            max_retries = 3
            retry_delay = 1  # starting delay in seconds
            
            for retry in range(max_retries):
                try:
                    thinking = {"type": "enabled", "budget_tokens": 1025}
                    response = self.client.beta.messages.create(
                            model="claude-haiku-4-5",  # or another compatible model
                            max_tokens=1026,
                            tools=[
                                {
                                "type": "computer_20250124",
                                "name": "computer",
                                "display_width_px": self.target_width,
                                "display_height_px": self.target_height,
                                "display_number": 1,
                                }
                            ],
                            messages=messages,
                            betas=["computer-use-2025-01-24"],
                            thinking=thinking
                            
                        )
                    #print thr the response for debugging
                    print(response.thinking)

                    return response
                except anthropic.APIError as api_error:
                    # Only retry on certain error types
                    if retry < max_retries - 1 and (
                        isinstance(api_error, anthropic.RateLimitError) or
                        "500" in str(api_error) or "503" in str(api_error)
                    ):
                        wait_time = retry_delay * (2 ** retry)
                        print(f"⚠️ API error, retrying in {wait_time} seconds: {api_error}")
                        time.sleep(wait_time)
                    else:
                        # Don't retry for client errors like 400
                        raise
            
        except Exception as e:
            print(f"❌ Error calling Claude API: {e}")
            print(traceback.format_exc())
            raise
        
    async def execute_tool_use(self, tool_use):
        """Execute a tool use from Claude"""
        tool_name = tool_use.name
        tool_input = tool_use.input
        
        print(f"\n🔧 Tool: {tool_name}")
        print(f"   Input: {tool_input}")
        print(f"   Tool ID: {tool_use.id}")
        
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
                    "tool_use_id": tool_use.id,  # Use the exact ID from the tool use
                    "content": str(result)
                }
            ]
        }
        
        self.messages.append(tool_result)
    
    def scale_coordinates(self, x: int, y: int) -> tuple:
        """Scale coordinates from model resolution to real screen resolution"""
        real_x = int(x * (self.real_width / self.target_width))
        real_y = int(y * (self.real_height / self.target_height))
        
        print(f"🔍 Scaling coordinates: ({x},{y}) → ({real_x},{real_y})")
        return (real_x, real_y)
        
    async def execute_computer_action(self, action: str, params: Dict) -> str:
        """Execute a computer action via Chrome Adapter"""
        
        try:
            if action == "screenshot":
                screenshot = await self.chrome_adapter.get_screenshot()
                return "Screenshot taken"
                
            elif action == "mouse_move":
                model_x, model_y = params.get("coordinate", [0, 0])
                real_x, real_y = self.scale_coordinates(model_x, model_y)
                await self.chrome_adapter.mouse_move(real_x, real_y)
                return f"Moved mouse to ({real_x}, {real_y})"
                
            elif action == "left_click":
                model_x, model_y = params.get("coordinate", [0, 0])
                real_x, real_y = self.scale_coordinates(model_x, model_y)
                await self.chrome_adapter.click(real_x, real_y, "left")
                return f"Clicked at ({real_x}, {real_y})"
                
            elif action == "right_click":
                model_x, model_y = params.get("coordinate", [0, 0])
                real_x, real_y = self.scale_coordinates(model_x, model_y)
                await self.chrome_adapter.click(real_x, real_y, "right")
                return f"Right-clicked at ({real_x}, {real_y})"
                
            elif action == "double_click":
                model_x, model_y = params.get("coordinate", [0, 0])
                real_x, real_y = self.scale_coordinates(model_x, model_y)
                await self.chrome_adapter.click(real_x, real_y, "left")
                await self.chrome_adapter.click(real_x, real_y, "left")
                return f"Double-clicked at ({real_x}, {real_y})"
                
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
            error_msg = f"Error executing {action}: {str(e)}"
            print(f"❌ {error_msg}")
            print(traceback.format_exc())
            return error_msg
            
    def extract_final_message(self, response) -> str:
        """Extract final text message from Claude response"""
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""