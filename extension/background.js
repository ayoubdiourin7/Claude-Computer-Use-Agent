// Background service worker - WebSocket client and Chrome adapter
console.log('Claude Browser Agent background script loaded');

// WebSocket connection to Python backend
let ws = null;
let isConnecting = false;

// Connect to Python WebSocket server
function connectToPython() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    console.log('Already connected to Python');
    return;
  }
  
  if (isConnecting) {
    console.log('Connection already in progress');
    return;
  }
  
  isConnecting = true;
  console.log('🔌 Connecting to Python backend...');
  
  ws = new WebSocket('ws://localhost:8765');
  
  ws.onopen = () => {
    console.log('✅ Connected to Python backend');
    isConnecting = false;
  };
  
  ws.onmessage = async (event) => {
    console.log('📥 Message from Python:', event.data);
    
    try {
      const command = JSON.parse(event.data);
      await executeCommand(command);
    } catch (e) {
      console.error('Error parsing command:', e);
    }
  };
  
  ws.onerror = (error) => {
    console.error('❌ WebSocket error:', error);
    isConnecting = false;
  };
  
  ws.onclose = () => {
    console.log('❌ Disconnected from Python');
    ws = null;
    isConnecting = false;
    
    // Try to reconnect after 2 seconds
    setTimeout(connectToPython, 2000);
  };
}

// Send message to Python
function sendToPython(data) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.error('❌ Not connected to Python');
    return false;
  }
  
  // If data is too large, log its size
  const jsonData = JSON.stringify(data);
  const sizeInMB = jsonData.length / (1024 * 1024);
  if (sizeInMB > 5) {
    console.warn(`⚠️ Sending large data: ${sizeInMB.toFixed(2)} MB`);
  }
  
  try {
    ws.send(jsonData);
    console.log('📤 Sent to Python:', data.type);
    return true;
  } catch (error) {
    console.error('❌ Error sending data:', error);
    return false;
  }
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('=== MESSAGE FROM POPUP ===');
  console.log('Type:', message.type);
  
  if (message.type === 'EXECUTE_TASK') {
    handleExecuteTask(message, sendResponse);
    return true;
  }
});

// Handle task execution
async function handleExecuteTask(message, sendResponse) {
  const { task, timestamp } = message;
  
  console.log('\n🚀 TASK EXECUTION STARTED');
  console.log('Task:', task);
  
  try {
    // Send task to Python
    const sent = sendToPython({
      type: 'task',
      task: task,
      timestamp: timestamp
    });
    
    if (sent) {
      sendResponse({
        success: true,
        message: 'Task sent to Python backend'
      });
    } else {
      sendResponse({
        success: false,
        error: 'Not connected to Python backend'
      });
    }
    
  } catch (error) {
    console.error('❌ Error:', error);
    sendResponse({
      success: false,
      error: error.message
    });
  }
}

// Execute commands from Python
async function executeCommand(command) {
  const action = command.action;
  console.log(`\n🔧 Executing: ${action}`);
  
  try {
    let result;
    
    switch (action) {
      case 'screenshot':
        result = await takeScreenshot();
        break;
        
      case 'click':
        result = await clickAt(command.x, command.y, command.button);
        break;
        
      case 'type':
        result = await typeText(command.text);
        break;
        
      case 'key':
        result = await pressKey(command.key);
        break;
        
      case 'scroll':
        result = await scroll(command.direction, command.amount);
        break;
        
      case 'navigate':
        result = await navigateToUrl(command.url);
        break;
        
      case 'mouse_move':
        result = await moveMouse(command.x, command.y);
        break;
        
      case 'switch_tab':
        result = await switchTab(command.index);
        break;
        
      case 'download':
        result = await downloadFile(command.url);
        break;
        
      default:
        result = { success: false, error: `Unknown action: ${action}` };
    }
    
    // Send result back to Python
    sendToPython({
      type: 'action_result',
      action: action,
      success: result.success,
      data: result.data || null
    });
    
  } catch (error) {
    console.error(`❌ Error executing ${action}:`, error);
    sendToPython({
      type: 'error',
      action: action,
      message: error.message
    });
  }
}

// Chrome action implementations

async function takeScreenshot() {
  console.log('📸 Taking screenshot...');
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Capture visible tab with JPEG format for smaller size
    const screenshot = await chrome.tabs.captureVisibleTab(null, {
        format: 'jpeg',
        quality: 75
    });
    
    // Remove data URL prefix to get just base64
    const base64Data = screenshot.replace(/^data:image\/jpeg;base64,/, '');
    
    console.log(`✅ Screenshot captured (${base64Data.length} bytes)`);
    
    // Split large screenshots into chunks if necessary (WebSockets have message size limits)
    const maxChunkSize = 5 * 1024 * 1024; // 5MB is a safe limit for most WebSockets
    
    if (base64Data.length < maxChunkSize) {
      // Send screenshot in one piece
      sendToPython({
        type: 'screenshot',
        data: base64Data,
        width: tab.width || 1280,
        height: tab.height || 800
      });
    } else {
      console.warn(`⚠️ Large screenshot (${(base64Data.length / (1024 * 1024)).toFixed(2)}MB), will need to optimize in the backend`);
      
      // Send but log a warning - backend will handle resizing
      sendToPython({
        type: 'screenshot',
        data: base64Data,
        width: tab.width || 1280,
        height: tab.height || 800
      });
    }
    
    return { success: true, data: 'Screenshot sent' };
  } catch (error) {
    console.error('Screenshot error:', error);
    return { success: false, error: error.message };
  }
}

async function clickAt(x, y, button = 'left') {
  console.log(`🖱️ Clicking at (${x}, ${y}) with ${button} button`);
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    const result = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (x, y, button) => {
        let element = document.elementFromPoint(x, y);
        
        // ENHANCED VISUAL DEBUG: Add a much more visible click animation
        function createClickAnimation() {
          // Create container for the animation
          const animContainer = document.createElement('div');
          animContainer.style.position = 'fixed';
          animContainer.style.left = (x - 50) + 'px';
          animContainer.style.top = (y - 50) + 'px';
          animContainer.style.width = '100px';
          animContainer.style.height = '100px';
          animContainer.style.pointerEvents = 'none';
          animContainer.style.zIndex = '2147483647'; // Max z-index
          
          // Create ripple effect
          const ripple = document.createElement('div');
          ripple.style.position = 'absolute';
          ripple.style.width = '30px';
          ripple.style.height = '30px';
          ripple.style.left = '35px';
          ripple.style.top = '35px';
          ripple.style.borderRadius = '50%';
          ripple.style.backgroundColor = 'rgba(255, 0, 0, 0.6)';
          ripple.style.boxShadow = '0 0 10px rgba(255, 0, 0, 0.8)';
          ripple.style.animation = 'claude-click-ripple 1.5s ease-out';
          
          // Create a highlight spot
          const spot = document.createElement('div');
          spot.style.position = 'absolute';
          spot.style.width = '10px';
          spot.style.height = '10px';
          spot.style.left = '45px';
          spot.style.top = '45px';
          spot.style.borderRadius = '50%';
          spot.style.backgroundColor = 'rgba(255, 0, 0, 0.8)';
          spot.style.boxShadow = '0 0 10px rgba(255, 0, 0, 1)';
          
          // Create coordinates text
          const coordsText = document.createElement('div');
          coordsText.textContent = `(${x}, ${y})`;
          coordsText.style.position = 'absolute';
          coordsText.style.width = '100px';
          coordsText.style.textAlign = 'center';
          coordsText.style.left = '0';
          coordsText.style.top = '60px';
          coordsText.style.color = 'white';
          coordsText.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
          coordsText.style.padding = '2px';
          coordsText.style.borderRadius = '3px';
          coordsText.style.fontSize = '12px';
          coordsText.style.fontFamily = 'monospace';
          
          // Add keyframes for the ripple animation
          if (!document.getElementById('claude-click-animation-style')) {
            const styleEl = document.createElement('style');
            styleEl.id = 'claude-click-animation-style';
            styleEl.textContent = `
              @keyframes claude-click-ripple {
                0% {
                  transform: scale(0.3);
                  opacity: 1;
                }
                100% {
                  transform: scale(6);
                  opacity: 0;
                }
              }
            `;
            document.head.appendChild(styleEl);
          }
          
          // Assemble and append to document
          animContainer.appendChild(ripple);
          animContainer.appendChild(spot);
          animContainer.appendChild(coordsText);
          document.body.appendChild(animContainer);
          
          // Remove after animation completes
          setTimeout(() => {
            animContainer.remove();
          }, 3000);
        }
        
        // Create the animation
        createClickAnimation();
        
        if (!element) {
          return { 
            success: false, 
            error: 'No element found at coordinates',
            coordinates: { x, y }
          };
        }
        
        // SMART CLICK: Find the closest clickable element
        let clickableElement = element;
        let depth = 0;
        const maxDepth = 5;
        
        // Check if element itself is clickable
        const isClickable = (el) => {
          return el.onclick !== null || 
                 el.tagName === 'A' || 
                 el.tagName === 'BUTTON' ||
                 el.getAttribute('role') === 'button' ||
                 el.hasAttribute('onclick') ||
                 el.style.cursor === 'pointer';
        };
        
        // Walk up the DOM tree to find clickable parent
        while (!isClickable(clickableElement) && depth < maxDepth && clickableElement.parentElement) {
          clickableElement = clickableElement.parentElement;
          depth++;
        }
        
        // Get element info
        const elementInfo = {
          original: {
            tag: element.tagName,
            id: element.id || 'no-id',
            class: element.className.toString().substring(0, 50) || 'no-class',
            text: (element.innerText || element.textContent || 'no-text').substring(0, 50),
            coordinates: { x, y }
          },
          clicked: {
            tag: clickableElement.tagName,
            id: clickableElement.id || 'no-id',
            class: clickableElement.className.toString().substring(0, 50) || 'no-class',
            text: (clickableElement.innerText || clickableElement.textContent || 'no-text').substring(0, 30),
            isClickable: isClickable(clickableElement),
            depth: depth
          }
        };
        
        // Focus if it's an input
        if (clickableElement.tagName === 'INPUT' || clickableElement.tagName === 'TEXTAREA') {
          clickableElement.focus();
        }
        
        // Perform clicks with multiple methods
        // Method 1: MouseEvent on clickable element
        const clickEvent = new MouseEvent('click', {
          view: window,
          bubbles: true,
          cancelable: true,
          clientX: x,
          clientY: y,
          button: button === 'right' ? 2 : button === 'middle' ? 1 : 0
        });
        clickableElement.dispatchEvent(clickEvent);
        
        // Method 2: Native click
        clickableElement.click();
        
        // Method 3: mousedown + mouseup (more reliable for some sites)
        const mousedown = new MouseEvent('mousedown', {
          view: window,
          bubbles: true,
          cancelable: true,
          clientX: x,
          clientY: y
        });
        const mouseup = new MouseEvent('mouseup', {
          view: window,
          bubbles: true,
          cancelable: true,
          clientX: x,
          clientY: y
        });
        clickableElement.dispatchEvent(mousedown);
        clickableElement.dispatchEvent(mouseup);
        
        // For links
        if (clickableElement.tagName === 'A' && clickableElement.href) {
          return { 
            success: true, 
            elementInfo, 
            isLink: true, 
            href: clickableElement.href 
          };
        }
        
        return { success: true, elementInfo };
      },
      args: [x, y, button]
    });
    
    const scriptResult = result[0]?.result;
    
    // Log detailed info
    if (scriptResult?.elementInfo) {
      console.log('📍 Original element:', scriptResult.elementInfo.original);
      console.log('🎯 Clicked element:', scriptResult.elementInfo.clicked);
      
      if (scriptResult.elementInfo.clicked.depth > 0) {
        console.log(`   ↑ Walked up ${scriptResult.elementInfo.clicked.depth} levels to find clickable element`);
      }
    }
    
    if (scriptResult?.isLink) {
      console.log('🔗 Link clicked:', scriptResult.href);
    }
    
    console.log('✅ Click result:', scriptResult?.success);
    return scriptResult || { success: true };
    
  } catch (error) {
    console.error('❌ Click error:', error);
    return { success: false, error: error.message };
  }
}

async function typeText(text) {
  console.log(`⌨️ Typing: "${text}"`);
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    const result = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (text) => {
        const activeElement = document.activeElement;
        console.log('Typing into:', activeElement);
        
        if (!activeElement) {
          return { success: false, error: 'No active element' };
        }
        
        // Handle different element types
        if (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA') {
          // For input/textarea, set value
          activeElement.value = (activeElement.value || '') + text;
          
          // Trigger events
          activeElement.dispatchEvent(new Event('input', { bubbles: true }));
          activeElement.dispatchEvent(new Event('change', { bubbles: true }));
          
          return { success: true, element: activeElement.tagName };
          
        } else if (activeElement.isContentEditable) {
          // For contentEditable, insert text
          document.execCommand('insertText', false, text);
          return { success: true, element: 'contentEditable' };
          
        } else {
          return { success: false, error: 'Element not editable' };
        }
      },
      args: [text]
    });
    
    const scriptResult = result[0]?.result;
    console.log('✅ Type result:', scriptResult);
    return scriptResult || { success: true };
    
  } catch (error) {
    console.error('Type error:', error);
    return { success: false, error: error.message };
  }
}

async function pressKey(key) {
  console.log(`⌨️ Pressing key: ${key}`);
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    const result = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (key) => {
        const activeElement = document.activeElement;
        console.log('Active element:', activeElement);
        
        if (!activeElement) {
          return { success: false, error: 'No active element' };
        }
        
        // Send multiple key events for better compatibility
        const events = ['keydown', 'keypress', 'keyup'];
        
        events.forEach(eventType => {
          const keyEvent = new KeyboardEvent(eventType, {
            key: key,
            code: key === 'Enter' ? 'Enter' : key === 'Tab' ? 'Tab' : key,
            bubbles: true,
            cancelable: true
          });
          activeElement.dispatchEvent(keyEvent);
        });
        
        // Special handling for Enter
        if (key === 'Enter') {
          if (activeElement.form) {
            activeElement.form.submit();
          }
        }
        
        return { success: true, element: activeElement.tagName };
      },
      args: [key]
    });
    
    const scriptResult = result[0]?.result;
    console.log('✅ Key result:', scriptResult);
    return scriptResult || { success: true };
    
  } catch (error) {
    console.error('Key press error:', error);
    return { success: false, error: error.message };
  }
}

async function scroll(direction, amount = 100) {
  console.log(`📜 Scrolling ${direction} by ${amount}px`);
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (direction, amount) => {
        window.scrollBy({
          top: direction === 'down' ? amount : -amount,
          behavior: 'smooth'
        });
        return true;
      },
      args: [direction, amount]
    });
    
    console.log('✅ Scrolled');
    return { success: true };
  } catch (error) {
    console.error('Scroll error:', error);
    return { success: false, error: error.message };
  }
}

async function navigateToUrl(url) {
  console.log(`🌐 Navigating to: ${url}`);
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    await chrome.tabs.update(tab.id, { url: url });
    
    console.log('✅ Navigation started');
    return { success: true };
  } catch (error) {
    console.error('Navigate error:', error);
    return { success: false, error: error.message };
  }
}

async function moveMouse(x, y) {
  console.log(`🖱️ Moving mouse to (${x}, ${y})`);
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Show visual indicator for mouse position
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (x, y) => {
        // Create a cursor indicator
        const cursor = document.createElement('div');
        cursor.style.position = 'fixed';
        cursor.style.left = (x - 10) + 'px';
        cursor.style.top = (y - 10) + 'px';
        cursor.style.width = '20px';
        cursor.style.height = '20px';
        cursor.style.borderRadius = '50%';
        cursor.style.border = '2px solid rgba(100, 100, 255, 0.8)';
        cursor.style.backgroundColor = 'rgba(100, 100, 255, 0.3)';
        cursor.style.zIndex = '2147483646';
        cursor.style.pointerEvents = 'none';
        
        // Add coordinates
        const coords = document.createElement('div');
        coords.textContent = `(${x},${y})`;
        coords.style.position = 'fixed';
        coords.style.left = (x + 10) + 'px';
        coords.style.top = (y + 10) + 'px';
        coords.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        coords.style.color = 'white';
        coords.style.padding = '2px 5px';
        coords.style.borderRadius = '3px';
        coords.style.fontSize = '11px';
        coords.style.fontFamily = 'monospace';
        coords.style.zIndex = '2147483646';
        coords.style.pointerEvents = 'none';
        
        document.body.appendChild(cursor);
        document.body.appendChild(coords);
        
        setTimeout(() => {
          cursor.remove();
          coords.remove();
        }, 2000);
      },
      args: [x, y]
    });
    
    return { success: true, data: { x, y } };
  } catch (error) {
    console.error('Mouse move error:', error);
    return { success: false, error: error.message };
  }
}

async function switchTab(index) {
  console.log(`🔄 Switching to tab ${index}`);
  
  try {
    const tabs = await chrome.tabs.query({ currentWindow: true });
    if (index >= 0 && index < tabs.length) {
      await chrome.tabs.update(tabs[index].id, { active: true });
      console.log('✅ Tab switched');
      return { success: true };
    }
    return { success: false, error: 'Invalid tab index' };
  } catch (error) {
    console.error('Switch tab error:', error);
    return { success: false, error: error.message };
  }
}

async function downloadFile(url) {
  console.log(`💾 Downloading: ${url}`);
  
  try {
    await chrome.downloads.download({ url: url });
    console.log('✅ Download started');
    return { success: true };
  } catch (error) {
    console.error('Download error:', error);
    return { success: false, error: error.message };
  }
}

// Auto-connect on startup
chrome.runtime.onStartup.addListener(() => {
  console.log('Extension started, connecting to Python...');
  connectToPython();
});

// Connect when extension is installed/updated
chrome.runtime.onInstalled.addListener((details) => {
  console.log('Extension installed/updated:', details.reason);
  connectToPython();
});

// Try to connect immediately
connectToPython();