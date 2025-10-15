"""
Main entry point for Claude Browser Agent
Runs WebSocket server and handles communication with Chrome Extension
"""
import asyncio
import json
import websockets
from typing import Optional

import config
from claude_orchestrator import ClaudeOrchestrator
from chrome_adapter import ChromeAdapter


class BrowserAgentServer:
    """WebSocket server that connects Chrome Extension with Claude"""
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.chrome_adapter = ChromeAdapter()
        self.orchestrator = ClaudeOrchestrator(self.chrome_adapter)
        
    async def handle_client(self, websocket):
        """Handle incoming WebSocket connection from Chrome Extension"""
        self.websocket = websocket
        self.chrome_adapter.set_websocket(websocket)
        
        print("✅ Chrome Extension connected!")
        
        try:
            async for message in websocket:
                await self.handle_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            print("❌ Chrome Extension disconnected")
        except Exception as e:
            print(f"❌ Error handling client: {e}")
        finally:
            self.websocket = None
            
    async def handle_message(self, message: str):
        """Process incoming message from Chrome Extension"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            print(f"\n📥 Received from Extension: {message_type}")
            print(f"   Full message: {data}")
            if message_type == "task":
                print("🔗 Connection test successful")
                # Send response back
                await self.websocket.send(json.dumps({
                    "type": "response",
                    "message": "Connection OK!"
                }))
            
            elif message_type == "task":
                # New task from user
                task = data.get("task")
                print(f"📋 Task: {task}")
                await self.orchestrator.execute_task(task)
                
            elif message_type == "screenshot":
                # Screenshot response from extension
                screenshot_data = data.get("data")
                print(f"📸 Screenshot received ({len(screenshot_data)} bytes)")
                self.chrome_adapter.set_last_screenshot(screenshot_data)
                
            elif message_type == "action_result":
                # Result of action execution
                success = data.get("success")
                result_data = data.get("data")
                print(f"✅ Action result: success={success}")
                self.chrome_adapter.set_last_action_result(success, result_data)
                
            elif message_type == "error":
                # Error from extension
                error_msg = data.get("message")
                print(f"❌ Extension error: {error_msg}")
                
            else:
                print(f"⚠️ Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON received: {message}")
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            
    async def start(self):
        """Start the WebSocket server"""
        print(f"\n🚀 Starting WebSocket server on ws://{config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT}")
        print("⏳ Waiting for Chrome Extension to connect...")
        print("   (Click the extension icon in Chrome to connect)\n")
        
        async with websockets.serve(
            self.handle_client,
            config.WEBSOCKET_HOST,
            config.WEBSOCKET_PORT
        ):
            await asyncio.Future()  # Run forever


async def main():
    """Main entry point"""
    try:
        # Validate configuration
        config.validate_config()
        
        # Start server
        server = BrowserAgentServer()
        await server.start()
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease create a .env file with your API key:")
        print("   ANTHROPIC_API_KEY=your_api_key_here\n")
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())