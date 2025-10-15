// Content script - Injected into web pages for direct DOM interaction
console.log('Claude Browser Agent content script loaded');

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Content script received:', message.type);
  
  // Handle different types of page interactions
  if (message.type === 'GET_PAGE_INFO') {
    sendResponse(getPageInfo());
  }
  
  return true;
});

// Get information about the current page
function getPageInfo() {
  return {
    url: window.location.href,
    title: document.title,
    dimensions: {
      width: window.innerWidth,
      height: window.innerHeight,
      scrollX: window.scrollX,
      scrollY: window.scrollY
    }
  };
}

// Utility: Highlight element at coordinates (for debugging)
function highlightElement(x, y) {
  const element = document.elementFromPoint(x, y);
  if (element) {
    element.style.outline = '2px solid red';
    setTimeout(() => {
      element.style.outline = '';
    }, 1000);
  }
}