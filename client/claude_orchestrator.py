
# Add this at the top of claude_orchestrator.py where the other imports are
import base64
from typing import List, Dict, Any, Optional
import asyncio  # Make sure asyncio is imported
import time
import os
import json
import traceback

# Fix PIL imports - make sure to import ImageDraw specifically
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import anthropic
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
        
        # State tracking
        self.action_history = []
        self.last_action_type = None
        self.repeated_action_count = 0
        self.visited_urls = set()
        self.typed_text = []
        
    async def execute_task(self, task: str):
        """Execute a task using Claude Computer Use"""
        print(f"\n{'='*60}")
        print(f"🎯 EXECUTING TASK: {task}")
        print(f"{'='*60}\n")
        
        # Reset state tracking
        self.action_history = []
        self.last_action_type = None
        self.repeated_action_count = 0
        self.visited_urls = set()
        self.typed_text = []
        
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
        stuck_counter = 0
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            current_coordinates = []  # Track coordinates for current iteration
            
            try:
                # Get current screenshot
                print("📸 Taking screenshot...")
                screenshot = await self.chrome_adapter.get_screenshot()
                
                if not screenshot:
                    print("❌ Failed to get screenshot")
                    break
                
                # Save initial screenshot (without coordinates)
                self.save_debug_image(screenshot, None, iteration)
                
                # Create context-aware message for Claude
                context_message = self.create_context_message(task, iteration, stuck_counter)
                
                # Call Claude with Computer Use
                print("🤖 Calling Claude API...")
                
                # Create message with screenshot
                screenshot_message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": screenshot
                            }
                        },
                        {
                            "type": "text",
                            "text": context_message
                        }
                    ]
                }
                
                # Call Claude API with messages and screenshot
                current_messages = self.messages.copy() + [screenshot_message]
                response = await self.call_claude_api(current_messages)
                
                # Check if task is complete
                if response.stop_reason == "end_turn":
                    print("\n✅ Task completed!")
                    final_message = self.extract_final_message(response)
                    if final_message:
                        print(f"💬 Claude says: {final_message}")
                    # Add Claude's final response to conversation history
                    self.messages.append({"role": "assistant", "content": response.content})
                    break
                
                # Get tool uses from response
                tool_uses = [block for block in response.content if block.type == "tool_use"]
                
                if not tool_uses:
                    print("⚠️ No tool use found in response")
                    # Still add Claude's response to conversation history
                    self.messages.append({"role": "assistant", "content": response.content})
                    break
                
                # Add Claude's response (with tool uses) to conversation history
                self.messages.append({"role": "assistant", "content": response.content})
                
               
                
                # Process and execute each tool use
                coordinates_used = []
                tool_results = []
                
                for tool_use in tool_uses:
                    # Execute the action
                    action_result = await self.execute_computer_action(
                        tool_use.name, tool_use.input, coordinates_used
                    )
                    
                    # Record action in history
                    self.record_action(tool_use.name, tool_use.input, action_result)
                    
                    # Create tool result
                    tool_result = {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": action_result
                    }
                    tool_results.append(tool_result)
                
                # Add tool results as a single message to conversation history
                if tool_results:
                    self.messages.append({
                        "role": "user",
                        "content": tool_results
                    })
                
                # Save debug image with coordinates
                if coordinates_used:
                    print(f"🎯 Coordinates used in iteration {iteration}: {coordinates_used}")
                    # Get a fresh screenshot to show the result of actions
                    updated_screenshot = await self.chrome_adapter.get_screenshot()
                    if updated_screenshot:
                        self.save_debug_image(updated_screenshot, coordinates_used, iteration)
                
                # If we've been stuck for too many iterations, break
                if stuck_counter >= 4:
                    print("⚠️ Too many stuck cycles, giving up")
                    break
                
            except Exception as e:
                print(f"❌ Error in iteration {iteration}: {e}")
                import traceback
                print(traceback.format_exc())
                
                # Try to recover from certain errors
                if "ERR_CONNECTION_REFUSED" in str(e) or "WebSocket" in str(e):
                    print("⚠️ Connection error, waiting to recover...")
                    await asyncio.sleep(3)  # Wait for potential reconnection
                    continue
                
                break
        
        if iteration >= max_iterations:
            print(f"\n⚠️ Reached maximum iterations ({max_iterations})")
            
        print(f"\n{'='*60}")
        print("Task execution finished")
        print(f"{'='*60}\n")
    
    def create_context_message(self, task, iteration, stuck_counter):
        """Create a context-rich message for Claude"""
        
        # Basic instruction
        message = f"Here is the current state of the browser. "
        
        # Add task reminder
        message += f"Your task is to: {task}. "
        
        # Add iteration count
        message += f"This is iteration {iteration}. "
        
        # Add history summary if we have some
        if self.action_history:
            message += f"\n\nSo far, you have performed these actions:"
            
            # Only include the last 5 actions to avoid making the message too long
            recent_actions = self.action_history[-5:]
            for i, action in enumerate(recent_actions):
                message += f"\n{len(self.action_history) - len(recent_actions) + i + 1}. {action}"
        
        # Add more context if stuck
        if stuck_counter > 0:
            message += f"\n\nNOTE: You appear to be repeating similar actions without progress. "
            
            if stuck_counter == 1:
                message += "Try a different approach such as:"
                message += "\n- Directly navigate to a URL using left_click on the address bar and typing"
                message += "\n- If trying to search, make sure to type in the search box and press Enter"
                message += "\n- Look for alternative UI elements to interact with"
            
            elif stuck_counter >= 2:
                message += "IMPORTANT: You're still stuck. Try a completely different approach:"
                message += f"\n- Direct URL navigation: Type 'facebook.com' in the address bar"
                message += f"\n- Use key presses like 'Tab' to move between elements"
                message += f"\n- Check if you can use browser shortcuts"
                
            message += "\n\nWhat would you like to do next?"
        else:
            message += "\n\nWhat should I do next?"
        
        return message
    
    def summarize_actions(self, tool_uses):
        """Create a summary key of the actions to detect repetition"""
        if not tool_uses:
            return "no_action"
        
        summary = []
        for tool_use in tool_uses:
            if tool_use.name == "computer":
                action = tool_use.input.get("action", "unknown")
                
                if action in ["left_click", "right_click", "mouse_move"]:
                    coords = tool_use.input.get("coordinate", [0, 0])
                    # Use approximate coordinates (rounded to nearest 10) to detect similar actions
                    rounded_x = round(coords[0] / 10) * 10
                    rounded_y = round(coords[1] / 10) * 10
                    summary.append(f"{action}_{rounded_x}_{rounded_y}")
                elif action == "type":
                    text = tool_use.input.get("text", "")
                    summary.append(f"type_{len(text)}")
                else:
                    summary.append(action)
        
        return "_".join(summary)
    
    def record_action(self, tool_name, tool_input, result):
        """Record action in history for context tracking"""
        if tool_name != "computer":
            return
            
        action = tool_input.get("action", "unknown")
        
        if action == "left_click":
            coords = tool_input.get("coordinate", [0, 0])
            self.action_history.append(f"Clicked at ({coords[0]}, {coords[1]})")
            
        elif action == "right_click":
            coords = tool_input.get("coordinate", [0, 0])
            self.action_history.append(f"Right-clicked at ({coords[0]}, {coords[1]})")
            
        elif action == "type":
            text = tool_input.get("text", "")
            self.action_history.append(f"Typed: '{text}'")
            self.typed_text.append(text)
            
        elif action == "key":
            key = tool_input.get("text", "")
            self.action_history.append(f"Pressed key: {key}")
            
        elif action == "navigate":
            url = tool_input.get("url", "")
            self.action_history.append(f"Navigated to: {url}")
            self.visited_urls.add(url)
    
    async def call_claude_api(self, messages):
        """Call Claude API with proper error handling and retries"""
        try:
            # Add exponential backoff for API calls
            max_retries = 3
            retry_delay = 1  # starting delay in seconds
            
            for retry in range(max_retries):
                try:
                    # Call Claude API
                    thinking = {"type": "enabled", "budget_tokens": 1025}
                    response = self.client.beta.messages.create(
                        model="claude-haiku-4-5",
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
                        print(f"❌ API error: {api_error}")
                        raise
            
        except Exception as e:
            print(f"❌ Error calling Claude API: {e}")
            import traceback
            print(traceback.format_exc())
            raise
    
    async def execute_computer_action(self, tool_name, tool_input, coordinates_list=None):
        """Execute a computer action and track coordinates"""
        
        if tool_name != "computer":
            return f"Unknown tool: {tool_name}"
        
        # Extract action and parameters
        action = tool_input.get("action")
        
        # Track coordinates for debug visualization
        if coordinates_list is not None and action in ["left_click", "right_click", "double_click", "mouse_move"]:
            if "coordinate" in tool_input:
                x, y = tool_input.get("coordinate", [0, 0])
                coordinates_list.append((x, y))
                print(f"📍 Debug: Tracking coordinate ({x}, {y}) for {action}")
        
        # Apply smart action selection
        try:
            if self.repeated_action_count >= 2 and action in ["left_click", "right_click"]:
                # If repeating clicks, try to vary the coordinates slightly
                if "coordinate" in tool_input:
                    x, y = tool_input.get("coordinate", [0, 0])
                    # Add slight variation to avoid exact same spot
                    x_offset = (self.repeated_action_count * 5) % 15
                    y_offset = (self.repeated_action_count * 3) % 10
                    x += x_offset - 7  # -7 to +7 range
                    y += y_offset - 5  # -5 to +5 range
                    tool_input["coordinate"] = [x, y]
                    print(f"🔄 Varying coordinates to avoid loop: ({x}, {y})")
            
            if action == "screenshot":
                await self.chrome_adapter.get_screenshot()
                return "Screenshot taken"
                
            elif action == "mouse_move":
                model_x, model_y = tool_input.get("coordinate", [0, 0])
                real_x, real_y = self.scale_coordinates(model_x, model_y)
                await self.chrome_adapter.mouse_move(real_x, real_y)
                return f"Moved mouse to ({real_x}, {real_y})"
                
            elif action == "left_click":
                model_x, model_y = tool_input.get("coordinate", [0, 0])
                real_x, real_y = self.scale_coordinates(model_x, model_y)
                
                # Enhanced click with fallbacks
                result = await self.enhanced_click(real_x, real_y, "left")
                return result
                
            elif action == "right_click":
                model_x, model_y = tool_input.get("coordinate", [0, 0])
                real_x, real_y = self.scale_coordinates(model_x, model_y)
                await self.chrome_adapter.click(real_x, real_y, "right")
                return f"Right-clicked at ({real_x}, {real_y})"
                
            elif action == "double_click":
                model_x, model_y = tool_input.get("coordinate", [0, 0])
                real_x, real_y = self.scale_coordinates(model_x, model_y)
                await self.chrome_adapter.click(real_x, real_y, "left")
                await asyncio.sleep(0.1)  # Small delay between clicks
                await self.chrome_adapter.click(real_x, real_y, "left")
                return f"Double-clicked at ({real_x}, {real_y})"
                
            elif action == "type":
                text = tool_input.get("text", "")
                await self.chrome_adapter.type_text(text)
                return f"Typed: {text}"
                
            elif action == "key":
                key = tool_input.get("text", "")
                await self.chrome_adapter.key_press(key)
                return f"Pressed key: {key}"
            
            elif action == "navigate":
                url = tool_input.get("url", "")
                # Ensure URL has protocol
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                await self.chrome_adapter.navigate(url)
                return f"Navigated to: {url}"
                
            else:
                return f"Unknown action: {action}"
                
        except Exception as e:
            error_msg = f"Error executing {action}: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            print(traceback.format_exc())
            return error_msg
    
    async def enhanced_click(self, x, y, button="left"):
        """Enhanced click with better error handling and element identification"""
        try:
            # First attempt - regular click
            result = await self.chrome_adapter.click(x, y, button)
            
            if not result.get("success", False):
                # If click failed, try to get information about failure
                error_info = result.get("error", "Unknown error")
                print(f"⚠️ Click failed: {error_info}")
                
                # Try clicking with offset for potential interface elements
                for offset in [(0, -5), (0, 5), (-5, 0), (5, 0)]:
                    print(f"🔄 Retrying click with offset {offset}")
                    retry_result = await self.chrome_adapter.click(
                        x + offset[0], y + offset[1], button
                    )
                    if retry_result.get("success", False):
                        return f"Clicked at ({x + offset[0]}, {y + offset[1]}) after retry with offset"
                
                return f"Click attempt failed at ({x}, {y})"
            
            # Check if clicked element was actually interactable
            element_info = result.get("data", {}).get("elementInfo", {})
            element_tag = element_info.get("clicked", {}).get("tag", "").lower()
            is_clickable = element_info.get("clicked", {}).get("isClickable", False)
            
            # If we clicked on a non-interactable element, log warning
            if not is_clickable:
                print(f"⚠️ Clicked on non-interactable element: {element_tag}")
                if self.repeated_action_count >= 1:
                    # After repeated non-interactable clicks, try pressing Tab
                    print("🔄 Pressing Tab to focus on next interactive element")
                    await self.chrome_adapter.key_press("Tab")
                    return f"Clicked at ({x}, {y}) on non-interactable element, followed by Tab key"
            
            return f"Clicked at ({x}, {y})"
            
        except Exception as e:
            print(f"❌ Enhanced click error: {e}")
            return f"Error during click operation: {str(e)}"
    
    def scale_coordinates(self, x: int, y: int) -> tuple:
        """Scale coordinates from model resolution to real screen resolution"""
        real_x = int(x * (self.real_width / self.target_width))
        real_y = int(y * (self.real_height / self.target_height))
        
        print(f"🔍 Scaling coordinates: ({x},{y}) → ({real_x},{real_y})")
        return (real_x, real_y)
            
    def extract_final_message(self, response) -> str:
        """Extract final text message from Claude response"""
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""
    
    def save_debug_image(self, screenshot_base64: str, coordinates=None, iteration=0):
        """
        Save the screenshot with coordinates marked for debugging purposes.
        
        Args:
            screenshot_base64: Base64 encoded screenshot
            coordinates: List of (x, y) coordinates to mark on the image
            iteration: Current iteration number for filename
        """
        try:
            # Create debug directory if it doesn't exist
            debug_dir = os.path.join(os.path.dirname(__file__), "debug")
            os.makedirs(debug_dir, exist_ok=True)
            
            # Decode base64 image
            image_data = base64.b64decode(screenshot_base64)
            image = Image.open(BytesIO(image_data))
            
            # Draw coordinates on image if provided
            if coordinates and len(coordinates) > 0:
                draw = ImageDraw.Draw(image)
                
                # Try to load a font, use default if not available
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except IOError:
                    font = ImageFont.load_default()
                
                # Draw each coordinate
                for i, (x, y) in enumerate(coordinates):
                    # Draw a red circle at the coordinate
                    draw.ellipse((x-10, y-10, x+10, y+10), outline=(255, 0, 0), width=3)
                    
                    # Draw a cross at the coordinate
                    draw.line((x-15, y, x+15, y), fill=(255, 0, 0), width=3)
                    draw.line((x, y-15, x, y+15), fill=(255, 0, 0), width=3)
                    
                    # Calculate scaled coordinates
                    real_x, real_y = self.scale_coordinates(x, y)
                    
                    # Add text label with both original and scaled coordinates
                    draw.text((x+15, y+15), f"Claude: ({x}, {y})\nScaled: ({real_x}, {real_y})", 
                            fill=(255, 0, 0), font=font)
            
            # Save the image
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(debug_dir, f"iter_{iteration:02d}_{timestamp}.jpg")
            image.save(filename, "JPEG", quality=95)
            print(f"✅ Debug image saved: {filename}")
            
            # Save coordinates to text file
            if coordinates and len(coordinates) > 0:
                coords_file = os.path.join(debug_dir, f"iter_{iteration:02d}_{timestamp}_coords.txt")
                with open(coords_file, "w") as f:
                    for i, (x, y) in enumerate(coordinates):
                        real_x, real_y = self.scale_coordinates(x, y)
                        f.write(f"Coordinate {i+1}: Claude: ({x}, {y}) → Scaled: ({real_x}, {real_y})\n")
                print(f"✅ Coordinates saved: {coords_file}")
                
        except Exception as e:
            print(f"❌ Error saving debug image: {e}")
            import traceback
            print(traceback.format_exc())