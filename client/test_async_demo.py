#!/usr/bin/env python3
"""
Demo script showing the difference between async/await and sync operations
and testing the fixed screenshot timing
"""
import asyncio
import time
from chrome_adapter import ChromeAdapter

async def demo_async_vs_sync():
    """Demonstrate the difference between async and sync operations"""
    
    print("🔄 ASYNC vs SYNC DEMONSTRATION")
    print("=" * 50)
    
    # Simulate async operation (like your WebSocket screenshot)
    async def async_operation(duration: float, name: str):
        print(f"🚀 Starting async {name} (will take {duration}s)")
        await asyncio.sleep(duration)  # Non-blocking wait
        print(f"✅ Completed async {name}")
        return f"Result from {name}"
    
    # Simulate sync operation
    def sync_operation(duration: float, name: str):
        print(f"🚀 Starting sync {name} (will take {duration}s)")
        time.sleep(duration)  # Blocking wait
        print(f"✅ Completed sync {name}")
        return f"Result from {name}"
    
    print("\n1️⃣ SYNC OPERATIONS (Sequential - Blocking):")
    start_time = time.time()
    
    result1 = sync_operation(1.0, "Task A")
    result2 = sync_operation(1.0, "Task B")
    
    sync_total = time.time() - start_time
    print(f"⏱️ Sync total time: {sync_total:.2f}s")
    
    print("\n2️⃣ ASYNC OPERATIONS (Concurrent - Non-blocking):")
    start_time = time.time()
    
    # Run both async operations concurrently
    result1, result2 = await asyncio.gather(
        async_operation(1.0, "Task A"),
        async_operation(1.0, "Task B")
    )
    
    async_total = time.time() - start_time
    print(f"⏱️ Async total time: {async_total:.2f}s")
    
    print(f"\n📊 PERFORMANCE COMPARISON:")
    print(f"   Sync: {sync_total:.2f}s")
    print(f"   Async: {async_total:.2f}s")
    print(f"   Speed improvement: {sync_total/async_total:.1f}x faster!")

async def test_chrome_adapter_events():
    """Test the fixed ChromeAdapter event handling"""
    
    print("\n🔧 TESTING CHROME ADAPTER EVENTS")
    print("=" * 50)
    
    adapter = ChromeAdapter()
    
    # Simulate receiving a screenshot
    async def simulate_screenshot_reception():
        await asyncio.sleep(0.5)  # Simulate network delay
        adapter.set_last_screenshot("fake_base64_screenshot_data")
        print("📸 Simulated screenshot received")
    
    # Test the async event mechanism
    print("🚀 Testing async event mechanism...")
    
    # Start the screenshot reception simulation
    screenshot_task = asyncio.create_task(simulate_screenshot_reception())
    
    # This should now work properly with the event system
    try:
        # Simulate the send_command flow
        adapter._screenshot_event.clear()
        adapter.last_screenshot = None
        
        # Start waiting for screenshot
        wait_task = asyncio.create_task(adapter._screenshot_event.wait())
        
        # Wait for both tasks
        await asyncio.gather(screenshot_task, wait_task)
        
        print("✅ Event mechanism working correctly!")
        print(f"📸 Screenshot data: {adapter.last_screenshot[:20]}...")
        
    except Exception as e:
        print(f"❌ Event mechanism failed: {e}")

async def main():
    """Main demo function"""
    await demo_async_vs_sync()
    await test_chrome_adapter_events()
    
    print("\n🎯 KEY TAKEAWAYS:")
    print("   • ASYNC: Non-blocking, concurrent, event-driven")
    print("   • SYNC: Blocking, sequential, immediate return")
    print("   • Your screenshot issue was caused by polling instead of events")
    print("   • Fixed with asyncio.Event() for proper async communication")

if __name__ == "__main__":
    asyncio.run(main())

