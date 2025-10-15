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
  
  ws.send(JSON.stringify(data));
  console.log('📤 Sent to Python:', data.type);
  return true;
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
    
    // FIX: Ne pas passer windowId, juste les options
    const screenshot = await chrome.tabs.captureVisibleTab(null, {
        format: 'jpeg',
        quality: 90
    });
    
    // Remove data URL prefix to get just base64
    const base64Data = screenshot.replace(/^data:image\/png;base64,/, '');
    
    console.log(`✅ Screenshot captured (${base64Data.length} bytes)`);
    
    sendToPython({
      type: 'screenshot',
      data: base64Data,
      width: tab.width || 1280,
      height: tab.height || 800
    });
    
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
        
        // VISUAL DEBUG: Add red circle at click position
        const marker = document.createElement('div');
        marker.style.position = 'fixed';
        marker.style.left = (x - 10) + 'px';
        marker.style.top = (y - 10) + 'px';
        marker.style.width = '20px';
        marker.style.height = '20px';
        marker.style.borderRadius = '50%';
        marker.style.backgroundColor = 'red';
        marker.style.border = '2px solid white';
        marker.style.zIndex = '999999';
        marker.style.pointerEvents = 'none';
        document.body.appendChild(marker);
        setTimeout(() => marker.remove(), 2000);
        
        if (!element) {
          return { success: false, error: 'No element found at coordinates' };
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
            text: (element.innerText || element.textContent || 'no-text').substring(0, 50)
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
  // Note: Actual mouse movement not possible in browser
  // This just tracks position for coordinate reference
  return { success: true, data: { x, y } };
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