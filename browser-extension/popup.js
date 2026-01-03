/**
 * Flaskmarks Browser Extension
 * Save tabs as bookmarks to your Flaskmarks instance
 */

// Storage keys
const STORAGE_KEYS = {
  SERVER_URL: 'flaskmarks_server_url',
  API_TOKEN: 'flaskmarks_api_token'
};

// DOM Elements
let elements = {};

// State
let settings = {
  serverUrl: '',
  apiToken: ''
};

/**
 * Initialize the extension popup
 */
async function init() {
  // Cache DOM elements
  elements = {
    settingsSection: document.getElementById('settings-section'),
    mainSection: document.getElementById('main-section'),
    settingsForm: document.getElementById('settings-form'),
    serverUrlInput: document.getElementById('server-url'),
    apiTokenInput: document.getElementById('api-token'),
    statusIndicator: document.getElementById('status-indicator'),
    statusText: document.getElementById('status-text'),
    saveCurrentBtn: document.getElementById('save-current'),
    saveAllBtn: document.getElementById('save-all'),
    tabCount: document.getElementById('tab-count'),
    progressSection: document.getElementById('progress-section'),
    progressFill: document.getElementById('progress-fill'),
    progressText: document.getElementById('progress-text'),
    resultsSection: document.getElementById('results-section'),
    resultsList: document.getElementById('results-list'),
    openSettingsBtn: document.getElementById('open-settings'),
    openFlaskmarksLink: document.getElementById('open-flaskmarks'),
    message: document.getElementById('message')
  };

  // Load saved settings
  await loadSettings();

  // Setup event listeners
  setupEventListeners();

  // Show appropriate section
  if (settings.serverUrl && settings.apiToken) {
    showMainSection();
    checkConnection();
    updateTabCount();
  } else {
    showSettingsSection();
  }
}

/**
 * Load settings from storage
 */
async function loadSettings() {
  return new Promise((resolve) => {
    chrome.storage.local.get([STORAGE_KEYS.SERVER_URL, STORAGE_KEYS.API_TOKEN], (result) => {
      settings.serverUrl = result[STORAGE_KEYS.SERVER_URL] || '';
      settings.apiToken = result[STORAGE_KEYS.API_TOKEN] || '';
      resolve();
    });
  });
}

/**
 * Save settings to storage
 */
async function saveSettings() {
  return new Promise((resolve) => {
    chrome.storage.local.set({
      [STORAGE_KEYS.SERVER_URL]: settings.serverUrl,
      [STORAGE_KEYS.API_TOKEN]: settings.apiToken
    }, resolve);
  });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
  elements.settingsForm.addEventListener('submit', handleSettingsSubmit);
  elements.saveCurrentBtn.addEventListener('click', saveCurrentTab);
  elements.saveAllBtn.addEventListener('click', saveAllTabs);
  elements.openSettingsBtn.addEventListener('click', showSettingsSection);
}

/**
 * Handle settings form submission
 */
async function handleSettingsSubmit(e) {
  e.preventDefault();
  
  settings.serverUrl = elements.serverUrlInput.value.trim().replace(/\/$/, '');
  settings.apiToken = elements.apiTokenInput.value.trim();
  
  await saveSettings();
  
  showMainSection();
  checkConnection();
  updateTabCount();
}

/**
 * Show settings section
 */
function showSettingsSection() {
  elements.settingsSection.classList.remove('hidden');
  elements.mainSection.classList.add('hidden');
  
  // Populate form with current settings
  elements.serverUrlInput.value = settings.serverUrl;
  elements.apiTokenInput.value = settings.apiToken;
}

/**
 * Show main section
 */
function showMainSection() {
  elements.settingsSection.classList.add('hidden');
  elements.mainSection.classList.remove('hidden');
  elements.openFlaskmarksLink.href = settings.serverUrl;
  
  // Reset results
  elements.progressSection.classList.add('hidden');
  elements.resultsSection.classList.add('hidden');
}

/**
 * Check API connection
 */
async function checkConnection() {
  setConnectionStatus('checking', 'Checking connection...');
  
  try {
    const response = await fetch(`${settings.serverUrl}/api/v1/auth/verify`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${settings.apiToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      setConnectionStatus('connected', 'Connected');
    } else if (response.status === 401) {
      setConnectionStatus('error', 'Invalid token');
    } else {
      setConnectionStatus('error', 'Connection failed');
    }
  } catch (error) {
    setConnectionStatus('error', 'Cannot reach server');
  }
}

/**
 * Set connection status indicator
 */
function setConnectionStatus(status, text) {
  elements.statusIndicator.className = 'status-dot ' + status;
  elements.statusText.textContent = text;
}

/**
 * Update tab count display
 */
async function updateTabCount() {
  const tabs = await getAllTabs();
  elements.tabCount.textContent = tabs.length;
}

/**
 * Get all tabs in current window
 */
async function getAllTabs() {
  return new Promise((resolve) => {
    chrome.tabs.query({ currentWindow: true }, (tabs) => {
      // Filter out extension pages and invalid URLs
      const validTabs = tabs.filter(tab => {
        return tab.url && 
               !tab.url.startsWith('chrome://') && 
               !tab.url.startsWith('chrome-extension://') &&
               !tab.url.startsWith('moz-extension://') &&
               !tab.url.startsWith('about:') &&
               !tab.url.startsWith('edge://');
      });
      resolve(validTabs);
    });
  });
}

/**
 * Get current active tab
 */
async function getCurrentTab() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      resolve(tabs[0]);
    });
  });
}

/**
 * Save a single bookmark via API
 */
async function saveBookmark(url, title) {
  const response = await fetch(`${settings.serverUrl}/api/v1/quickadd`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${settings.apiToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      url: url,
      title: title || url
    })
  });
  
  const data = await response.json();
  
  if (!response.ok) {
    throw new Error(data.error || 'Failed to save bookmark');
  }
  
  return data;
}

/**
 * Save current tab as bookmark
 */
async function saveCurrentTab() {
  const tab = await getCurrentTab();
  
  if (!tab || !tab.url) {
    showMessage('No valid tab to save', 'error');
    return;
  }
  
  elements.saveCurrentBtn.disabled = true;
  elements.saveCurrentBtn.textContent = 'Saving...';
  
  try {
    const result = await saveBookmark(tab.url, tab.title);
    
    if (result.success) {
      if (result.data.duplicate) {
        showMessage(`Already exists: ${result.data.title}`, 'warning');
      } else {
        showMessage(`Saved: ${result.data.title}`, 'success');
      }
    } else {
      showMessage(result.error || 'Failed to save', 'error');
    }
  } catch (error) {
    showMessage(error.message, 'error');
  } finally {
    elements.saveCurrentBtn.disabled = false;
    elements.saveCurrentBtn.innerHTML = '<span class="icon">+</span> Save Current Tab';
  }
}

/**
 * Save all tabs as bookmarks
 */
async function saveAllTabs() {
  const tabs = await getAllTabs();
  
  if (tabs.length === 0) {
    showMessage('No valid tabs to save', 'error');
    return;
  }
  
  // Disable buttons
  elements.saveCurrentBtn.disabled = true;
  elements.saveAllBtn.disabled = true;
  
  // Show progress
  elements.progressSection.classList.remove('hidden');
  elements.resultsSection.classList.remove('hidden');
  elements.resultsList.innerHTML = '';
  
  let saved = 0;
  let duplicates = 0;
  let failed = 0;
  
  for (let i = 0; i < tabs.length; i++) {
    const tab = tabs[i];
    const progress = ((i + 1) / tabs.length) * 100;
    
    elements.progressFill.style.width = `${progress}%`;
    elements.progressText.textContent = `Saving ${i + 1} of ${tabs.length}...`;
    
    try {
      const result = await saveBookmark(tab.url, tab.title);
      
      if (result.success) {
        if (result.data.duplicate) {
          duplicates++;
          addResult(tab.title || tab.url, 'duplicate', 'Already exists');
        } else {
          saved++;
          addResult(tab.title || tab.url, 'success', 'Saved');
        }
      } else {
        failed++;
        addResult(tab.title || tab.url, 'error', result.error || 'Failed');
      }
    } catch (error) {
      failed++;
      addResult(tab.title || tab.url, 'error', error.message);
    }
    
    // Small delay to avoid overwhelming the server
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  // Show summary
  elements.progressText.textContent = `Done: ${saved} saved, ${duplicates} duplicates, ${failed} failed`;
  
  // Re-enable buttons
  elements.saveCurrentBtn.disabled = false;
  elements.saveAllBtn.disabled = false;
}

/**
 * Add result item to results list
 */
function addResult(title, status, message) {
  const li = document.createElement('li');
  li.className = `result-item ${status}`;
  li.innerHTML = `
    <span class="result-status">${getStatusIcon(status)}</span>
    <span class="result-title">${escapeHtml(truncate(title, 40))}</span>
    <span class="result-message">${escapeHtml(message)}</span>
  `;
  elements.resultsList.appendChild(li);
  
  // Scroll to bottom
  elements.resultsList.scrollTop = elements.resultsList.scrollHeight;
}

/**
 * Get status icon
 */
function getStatusIcon(status) {
  switch (status) {
    case 'success': return '&#10003;';
    case 'duplicate': return '&#8644;';
    case 'error': return '&#10007;';
    default: return '?';
  }
}

/**
 * Show message
 */
function showMessage(text, type) {
  elements.message.textContent = text;
  elements.message.className = `message ${type}`;
  elements.message.classList.remove('hidden');
  
  setTimeout(() => {
    elements.message.classList.add('hidden');
  }, 3000);
}

/**
 * Truncate string
 */
function truncate(str, length) {
  if (!str) return '';
  return str.length > length ? str.substring(0, length) + '...' : str;
}

/**
 * Escape HTML
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
