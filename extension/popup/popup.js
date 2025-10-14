// Get DOM elements
const taskInput = document.getElementById('task');
const executeButton = document.getElementById('execute');
const statusDiv = document.getElementById('status');

// Function to show status messages
function showStatus(message, type = 'info') {
  statusDiv.textContent = message;
  statusDiv.className = type;
  
  // Auto-hide success messages after 3 seconds
  if (type === 'success') {
    setTimeout(() => {
      statusDiv.style.display = 'none';
    }, 3000);
  }
}

// Handle execute button click
executeButton.addEventListener('click', () => {
  const task = taskInput.value.trim();
  
  // Validate input
  if (!task) {
    showStatus('Please enter a task', 'error');
    return;
  }
  
  console.log('=== TASK RECEIVED ===');
  console.log('Task:', task);
  console.log('Timestamp:', new Date().toISOString());
  console.log('====================');
  
  // Disable button while processing
  executeButton.disabled = true;
  showStatus('Sending task to background script...', 'info');
  
  // Send message to background script
  chrome.runtime.sendMessage(
    {
      type: 'EXECUTE_TASK',
      task: task,
      timestamp: Date.now()
    },
    (response) => {
      // Re-enable button
      executeButton.disabled = false;
      
      // Check for errors
      if (chrome.runtime.lastError) {
        console.error('Chrome runtime error:', chrome.runtime.lastError);
        showStatus('Error: ' + chrome.runtime.lastError.message, 'error');
        return;
      }
      
      // Handle response
      if (response && response.success) {
        console.log('Background script response:', response);
        showStatus('Task received! Check console for logs.', 'success');
      } else {
        console.error('Task execution failed:', response);
        showStatus('Task execution failed', 'error');
      }
    }
  );
});

// Allow Enter key to submit (Ctrl+Enter for new line)
taskInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.ctrlKey) {
    executeButton.click();
  }
});

// Log when popup opens
console.log('Claude Browser Agent popup opened');