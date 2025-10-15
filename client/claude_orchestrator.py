"""
Claude Orchestrator - Implements the Computer Use loop with Claude API
This is the brain that uses Claude to understand tasks and decide actions
"""
import anthropic
from typing import List, Dict, Any
import base64

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
                
                # Call Claude with Computer Use
                print("🤖 Calling Claude API...")
                response = await self.call_claude_with_screenshot(screenshot)
                
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
                
                # Execute each tool use
                for tool_use in tool_uses:
                    await self.execute_tool_use(tool_use)
                
                # Add response to messages
                self.messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
            except Exception as e:
                print(f"❌ Error in iteration {iteration}: {e}")
                break
        
        if iteration >= max_iterations:
            print(f"\n⚠️ Reached maximum iterations ({max_iterations})")
            
        print(f"\n{'='*60}")
        print("Task execution finished")
        print(f"{'='*60}\n")
        
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
                        "media_type": "image/jpeg",  # ← CHANGE: jpeg instead of png
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
        '''computer_tool = {
            "type": "computer_20241022",
            "name": "computer",
            "display_width_px": config.SCREENSHOT_WIDTH,
            "display_height_px": config.SCREENSHOT_HEIGHT,
            "display_number": 1
        }
        tools=[
        {
          "type": "computer_20250124",
          "name": "computer",
          "display_width_px": 1024,
          "display_height_px": 768,
          "display_number": 1,
        },
        {
          "type": "text_editor_20250124",
          "name": "str_replace_editor"
        },
        {
          "type": "bash_20250124",
          "name": "bash"
        }
    ]
    # Call Claude with beta API
        response = self.client.beta.messages.create(  # ← .beta est crucial!
            #model=config.CLAUDE_MODEL,
            model="claude-sonnet-4-5",
            max_tokens=config.MAX_TOKENS,
            messages=messages,
            tools=[computer_tool],
            betas=["computer-use-2025-01-24"])'''


        #client = anthropic.Anthropic()

        response = self.client.beta.messages.create(
                model="claude-sonnet-4-5",  # or another compatible model
                max_tokens=1024,
                tools=[
                    {
                    "type": "computer_20250124",
                    "name": "computer",
                    "display_width_px": 1024,
                    "display_height_px": 768,
                    "display_number": 1,
                    },
                    {
                    "type": "text_editor_20250124",
                    "name": "str_replace_editor"
                    },
                    {
                    "type": "bash_20250124",
                    "name": "bash"
                    }
                ],
                messages=[{"role": "user", "content": "Save a picture of a cat to my desktop."}],
                betas=["computer-use-2025-01-24"]
            )
        
        print(response)
        exit()
        
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