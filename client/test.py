#!/usr/bin/env python3
"""
Test script for resolution scaling functionality
"""
import asyncio
import time
import base64
import os
import io
from PIL import Image, ImageDraw

# Mock screenshot dimensions
ORIGINAL_WIDTH = 1920
ORIGINAL_HEIGHT = 1080
TARGET_WIDTH = 1024
TARGET_HEIGHT = 768

def create_test_image(width, height):
    """Create a test image with specified dimensions"""
    # Create blank image with light gray background
    img = Image.new('RGB', (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    
    # Draw grid lines
    for x in range(0, width, 100):
        draw.line([(x, 0), (x, height)], fill=(200, 200, 200), width=1)
    for y in range(0, height, 100):
        draw.line([(0, y), (width, y)], fill=(200, 200, 200), width=1)
    
    # Draw coordinate markers
    for x in range(100, width, 200):
        for y in range(100, height, 200):
            draw.text((x, y), f"({x},{y})", fill=(0, 0, 0))
    
    # Draw browser-like UI elements
    # Address bar
    draw.rectangle([(0, 0), (width, 60)], fill=(230, 230, 230), outline=(200, 200, 200))
    draw.rectangle([(70, 20), (width-100, 40)], fill=(255, 255, 255), outline=(180, 180, 180))
    
    # Buttons
    draw.ellipse([(20, 20), (40, 40)], fill=(255, 0, 0))
    draw.ellipse([(50, 20), (70, 40)], fill=(255, 255, 0))
    draw.ellipse([(80, 20), (100, 40)], fill=(0, 255, 0))
    
    # Add example clickable elements
    button_positions = [
        (300, 200, "Button 1"),
        (600, 400, "Button 2"),
        (900, 600, "Button 3"),
    ]
    
    for x, y, text in button_positions:
        text_width = len(text) * 8
        draw.rectangle([(x-60, y-20), (x+60, y+20)], fill=(70, 130, 180), outline=(40, 80, 120))
        draw.text((x-text_width//2, y-8), text, fill=(255, 255, 255))
    
    return img

def resize_image(img, target_width, target_height):
    """Resize image to target dimensions"""
    return img.resize((target_width, target_height), Image.LANCZOS)

def image_to_base64(img, format="JPEG", quality=75):
    """Convert PIL Image to base64 string"""
    buffer = io.BytesIO()
    img.save(buffer, format=format, quality=quality)
    img_bytes = buffer.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    return img_base64

def scale_coordinates(x, y, orig_width, orig_height, target_width, target_height):
    """Scale coordinates from target to original dimensions"""
    orig_x = int(x * (orig_width / target_width))
    orig_y = int(y * (orig_height / target_height))
    return orig_x, orig_y

async def test_resolution_scaling():
    """Test the resolution scaling functionality"""
    print("\n🔍 RESOLUTION SCALING TEST")
    print("=" * 50)
    
    # Create test images
    print("\n1️⃣ Creating test images...")
    original_img = create_test_image(ORIGINAL_WIDTH, ORIGINAL_HEIGHT)
    original_img.save("test_original.jpg", quality=90)
    print(f"   ✅ Original image created: {ORIGINAL_WIDTH}x{ORIGINAL_HEIGHT}")
    
    # Resize to target dimensions
    print("\n2️⃣ Resizing to target dimensions...")
    resized_img = resize_image(original_img, TARGET_WIDTH, TARGET_HEIGHT)
    resized_img.save("test_resized.jpg", quality=90)
    print(f"   ✅ Resized image created: {TARGET_WIDTH}x{TARGET_HEIGHT}")
    
    # Convert to base64
    print("\n3️⃣ Converting to base64...")
    original_base64 = image_to_base64(original_img)
    resized_base64 = image_to_base64(resized_img)
    
    original_size = len(original_base64)
    resized_size = len(resized_base64)
    
    print(f"   📊 Original image size: {original_size/1024:.1f}KB")
    print(f"   📊 Resized image size: {resized_size/1024:.1f}KB")
    print(f"   📊 Size reduction: {original_size/resized_size:.1f}x")
    
    # Test coordinate scaling
    print("\n4️⃣ Testing coordinate scaling...")
    test_coordinates = [
        (300, 200),  # Button 1
        (600, 400),  # Button 2
        (900, 600),  # Button 3
    ]
    
    print("   Model coordinates → Real screen coordinates:")
    for model_x, model_y in test_coordinates:
        real_x, real_y = scale_coordinates(
            model_x, model_y, 
            ORIGINAL_WIDTH, ORIGINAL_HEIGHT, 
            TARGET_WIDTH, TARGET_HEIGHT
        )
        print(f"   ({model_x}, {model_y}) → ({real_x}, {real_y})")
        
        # Verify by drawing dots on original image
        draw = ImageDraw.Draw(original_img)
        draw.ellipse([(real_x-10, real_y-10), (real_x+10, real_y+10)], 
                    fill=(255, 0, 0), outline=(0, 0, 0))
    
    # Save final image with markers
    original_img.save("test_coordinates.jpg", quality=90)
    print(f"   ✅ Coordinate test image saved: test_coordinates.jpg")
    
    print("\n✅ Resolution scaling test completed successfully!")
    print("   Check the generated images to verify the results.")

if __name__ == "__main__":
    asyncio.run(test_resolution_scaling())