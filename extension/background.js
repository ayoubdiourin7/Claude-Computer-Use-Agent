// Background service worker for Chrome extension
console.log('Claude Browser Agent background script loaded');

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('=== MESSAGE RECEIVED IN BACKGROUND ===');
  console.log('Message type:', message.type);
  console.log('Full message:', message);
  console.log('Sender:', sender);
  console.log('====================================');
  
  if (message.type === 'EXECUTE_TASK') {
    handleExecuteTask(message, sendResponse);
    // Return true to indicate async response
    return true;
  }
});

// Handle task execution
async function handleExecuteTask(message, sendResponse) {
  const { task, timestamp } = message;
  
  console.log('\n🚀 TASK EXECUTION STARTED');
  console.log('─────────────────────────');
  console.log('Task:', task);
  console.log('Timestamp:', new Date(timestamp).toISOString());
  console.log('Task length:', task.length, 'characters');
  console.log('─────────────────────────\n');
  
  try {
    // For now, just log the task
    // Later, this will send to Python backend
    
    // Simulate some processing
    await new Promise(resolve => setTimeout(resolve, 500));
    
    console.log('✅ Task logged successfully');
    console.log('Next step: Send to Python backend via WebSocket\n');
    
    // Send success response
    sendResponse({
      success: true,
      message: 'Task logged',
      task: task
    });
    
  } catch (error) {
    console.error('❌ Error processing task:', error);
    
    sendResponse({
      success: false,
      error: error.message
    });
  }
}

// Log extension installation/update
chrome.runtime.onInstalled.addListener((details) => {
  console.log('Extension installed/updated:', details.reason);
});