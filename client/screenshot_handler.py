"""
Screenshot handler for Claude Browser Agent
Processes screenshots from Chrome extension and prepares them for Claude API
"""
import base64
import io
from PIL import Image
import traceback

class ScreenshotHandler:
    """Handles screenshot processing from Chrome extension to Claude API"""
    
    def __init__(self, target_width=1024, target_height=768):
        """Initialize with target resolution for Claude"""
        self.target_width = target_width
        self.target_height = target_height
        self.real_width = None
        self.real_height = None
        self._scaling_enabled = True
    
    def process_screenshot(self, screenshot_base64, original_width, original_height):
        """
        Process screenshot from Chrome extension
        
        Args:
            screenshot_base64: Base64 encoded JPEG/PNG from Chrome extension
            original_width: Width of the original screenshot
            original_height: Height of the original screenshot
            
        Returns:
            Base64 encoded JPEG at target resolution
        """
        try:
            # Store original dimensions for coordinate scaling
            self.real_width = original_width
            self.real_height = original_height
            print(f"📐 Original screenshot size: {self.real_width}x{self.real_height}")
            
            # Decode base64 to image
            img_bytes = base64.b64decode(screenshot_base64)
            img_buffer = io.BytesIO(img_bytes)
            img_buffer.seek(0)
            img = Image.open(img_buffer)
            
            # Resize to target resolution for Claude
            resized = img.resize((self.target_width, self.target_height), Image.LANCZOS)
            print(f"📐 Resized screenshot to: {self.target_width}x{self.target_height}")
            
            # Convert to JPEG to reduce size
            buffer = io.BytesIO()
            resized.save(buffer, format="JPEG", quality=75)
            buffer.seek(0)
            
            # Get base64 string
            resized_bytes = buffer.getvalue()
            resized_base64 = base64.b64encode(resized_bytes).decode('utf-8')
            
            # Calculate compression ratio
            original_size = len(screenshot_base64)
            compressed_size = len(resized_base64)
            ratio = (original_size / compressed_size) if compressed_size > 0 else 0
            print(f"🗜️ Compression: {original_size/1024:.1f}KB → {compressed_size/1024:.1f}KB ({ratio:.1f}x)")
            
            return resized_base64
            
        except Exception as e:
            print(f"❌ Screenshot processing error: {e}")
            print(traceback.format_exc())
            # Return original screenshot as fallback if processing fails
            return screenshot_base64
    
    def scale_coordinates(self, x, y):
        """
        Scale coordinates from model resolution to real screen resolution
        
        Args:
            x: X coordinate in model resolution (e.g., 512 in 1024x768)
            y: Y coordinate in model resolution (e.g., 384 in 1024x768)
            
        Returns:
            (real_x, real_y): Coordinates scaled to real screen resolution
        """
        if not self._scaling_enabled:
            return x, y
            
        if not self.real_width or not self.real_height:
            print("⚠️ Warning: No screenshot dimensions, using direct coordinates")
            return x, y
        
        # Calculate scaling factors
        x_scaling_factor = self.real_width / self.target_width
        y_scaling_factor = self.real_height / self.target_height
        
        # Scale the coordinates
        real_x = round(x * x_scaling_factor)
        real_y = round(y * y_scaling_factor)
        
        print(f"🔍 Scaling coordinates: ({x},{y}) → ({real_x},{real_y})")
        return real_x, real_y