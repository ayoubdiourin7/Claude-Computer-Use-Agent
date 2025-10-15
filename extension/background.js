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
  
  ws = new WebSocket('ws://localhost:8765'); // Adjust port if needed with the config port
  
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
    
    const screenshot = await chrome.tabs.captureVisibleTab(tab.windowId, {
      format: 'png'
    });
    
    // Remove data URL prefix to get just base64
    const base64Data = screenshot.replace(/^data:image\/png;base64,/, '');
    
    console.log(`✅ Screenshot captured (${base64Data.length} bytes)`);
    
    sendToPython({
      type: 'screenshot',
      data: base64Data,
      width: tab.width,
      height: tab.height
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
    
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (x, y, button) => {
        const element = document.elementFromPoint(x, y);
        if (element) {
          const event = new MouseEvent('click', {
            view: window,
            bubbles: true,
            cancelable: true,
            button: button === 'right' ? 2 : button === 'middle' ? 1 : 0
          });
          element.dispatchEvent(event);
          return true;
        }
        return false;
      },
      args: [x, y, button]
    });
    
    console.log('✅ Click executed');
    return { success: true };
  } catch (error) {
    console.error('Click error:', error);
    return { success: false, error: error.message };
  }
}

async function typeText(text) {
  console.log(`⌨️ Typing: "${text}"`);
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (text) => {
        const activeElement = document.activeElement;
        if (activeElement && (activeElement.tagName === 'INPUT' || 
                              activeElement.tagName === 'TEXTAREA' ||
                              activeElement.isContentEditable)) {
          activeElement.value = (activeElement.value || '') + text;
          activeElement.dispatchEvent(new Event('input', { bubbles: true }));
          return true;
        }
        return false;
      },
      args: [text]
    });
    
    console.log('✅ Text typed');
    return { success: true };
  } catch (error) {
    console.error('Type error:', error);
    return { success: false, error: error.message };
  }
}

async function pressKey(key) {
  console.log(`⌨️ Pressing key: ${key}`);
  
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (key) => {
        const keyEvent = new KeyboardEvent('keydown', {
          key: key,
          bubbles: true,
          cancelable: true
        });
        document.activeElement?.dispatchEvent(keyEvent);
        return true;
      },
      args: [key]
    });
    
    console.log('✅ Key pressed');
    return { success: true };
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