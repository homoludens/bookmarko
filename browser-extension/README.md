# Flaskmarks Browser Extension

Save all open tabs or the current tab as bookmarks to your Flaskmarks instance.

## Features

- Save current tab with one click
- Save all open tabs in the current window
- Progress indicator for bulk saves
- Duplicate detection
- Works with Chrome, Edge, and Firefox

## Installation

### Chrome / Edge (Developer Mode)

1. Open Chrome/Edge and go to `chrome://extensions/` (or `edge://extensions/`)
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `browser-extension` folder
5. The extension icon will appear in your toolbar

### Firefox (Temporary Installation)

1. Open Firefox and go to `about:debugging`
2. Click "This Firefox" in the left sidebar
3. Click "Load Temporary Add-on"
4. Select any file in the `browser-extension` folder (e.g., `manifest.json`)
5. The extension will be loaded until Firefox restarts

### Firefox (Permanent Installation)

For permanent Firefox installation, the extension needs to be signed by Mozilla or installed in Developer Edition with signing disabled.

## Setup

1. Click the Flaskmarks extension icon in your browser toolbar
2. Enter your Flaskmarks server URL (e.g., `https://your-flaskmarks.com`)
3. Enter your API token (found on your Profile page in Flaskmarks)
4. Click "Save Settings"

## Usage

- **Save Current Tab**: Saves only the currently active tab
- **Save All Tabs**: Saves all tabs in the current window (excludes browser internal pages)

The extension shows:
- Connection status to your Flaskmarks server
- Number of tabs that can be saved
- Progress when saving multiple tabs
- Results showing which bookmarks were saved, already existed, or failed

## API Token

Get your API token from your Flaskmarks profile page:

1. Log in to your Flaskmarks instance
2. Go to Profile (user icon in navbar)
3. Copy the API Token shown on the page

Note: Tokens expire after 24 hours. If you get "Invalid token" errors, refresh your Flaskmarks profile page and copy the new token.

## Permissions

The extension requires:
- `tabs`: To read the URLs and titles of your open tabs
- `storage`: To save your server URL and API token locally
- Host permissions for API calls to your Flaskmarks server

## Troubleshooting

**"Cannot reach server"**
- Check that the server URL is correct
- Ensure your Flaskmarks instance is running and accessible

**"Invalid token"**
- Get a fresh token from your Flaskmarks profile page
- Tokens expire after 24 hours

**Some tabs not saved**
- Browser internal pages (chrome://, about:, etc.) are automatically skipped
- Check the results list for specific error messages
