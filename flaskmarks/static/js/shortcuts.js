/**
 * Keyboard shortcuts for Flaskmarks
 * 
 * Shortcuts:
 *   j/k     - Navigate down/up through bookmark list
 *   Enter   - Open selected bookmark
 *   e       - Edit selected bookmark
 *   d       - Delete selected bookmark (with confirmation)
 *   /       - Focus search input
 *   ?       - Show/hide help modal
 *   Escape  - Clear selection / close modal
 */

(function() {
    'use strict';

    // Check if shortcuts are enabled (stored in localStorage)
    const STORAGE_KEY = 'flaskmarks_shortcuts_enabled';
    
    function isShortcutsEnabled() {
        const stored = localStorage.getItem(STORAGE_KEY);
        // Default to enabled if not set
        return stored === null ? true : stored === 'true';
    }

    function setShortcutsEnabled(enabled) {
        localStorage.setItem(STORAGE_KEY, enabled.toString());
    }

    // Current selection state
    let currentIndex = -1;
    let items = [];

    // Get all bookmark list items
    function getItems() {
        return Array.from(document.querySelectorAll('.list-group-item'));
    }

    // Update selection visual
    function updateSelection(newIndex) {
        items = getItems();
        
        if (items.length === 0) return;

        // Remove previous selection
        if (currentIndex >= 0 && currentIndex < items.length) {
            items[currentIndex].classList.remove('keyboard-selected');
        }

        // Clamp index to valid range
        if (newIndex < 0) newIndex = 0;
        if (newIndex >= items.length) newIndex = items.length - 1;

        currentIndex = newIndex;

        // Add new selection
        if (currentIndex >= 0 && currentIndex < items.length) {
            items[currentIndex].classList.add('keyboard-selected');
            // Scroll into view if needed
            items[currentIndex].scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest' 
            });
        }
    }

    // Clear selection
    function clearSelection() {
        items = getItems();
        items.forEach(item => item.classList.remove('keyboard-selected'));
        currentIndex = -1;
    }

    // Get the main link from selected item
    function getMainLink(item) {
        return item.querySelector('h4 a.list-group-item-action');
    }

    // Get edit link from selected item
    function getEditLink(item) {
        return item.querySelector('a[href*="/mark/edit/"]');
    }

    // Get delete functionality - need to find delete link or create action
    function deleteSelectedMark(item) {
        // Find the mark ID from the main link
        const mainLink = getMainLink(item);
        if (!mainLink) return;

        const href = mainLink.getAttribute('href');
        // Extract mark ID from various URL patterns
        let markId = null;
        
        // Try to get ID from data attribute
        markId = mainLink.getAttribute('data-id');
        
        if (!markId) {
            // Try to extract from href
            const match = href.match(/\/mark\/(?:redirect|edit|view)\/(\d+)/);
            if (match) {
                markId = match[1];
            }
        }

        if (markId && confirm('Are you sure you want to delete this bookmark?')) {
            window.location.href = '/mark/delete/' + markId;
        }
    }

    // Open selected bookmark
    function openSelectedMark() {
        if (currentIndex < 0 || currentIndex >= items.length) return;
        
        const link = getMainLink(items[currentIndex]);
        if (link) {
            // Simulate click to trigger click increment
            link.click();
        }
    }

    // Edit selected bookmark
    function editSelectedMark() {
        if (currentIndex < 0 || currentIndex >= items.length) return;
        
        const editLink = getEditLink(items[currentIndex]);
        if (editLink) {
            window.location.href = editLink.getAttribute('href');
        }
    }

    // Focus search input
    function focusSearch() {
        const searchInput = document.querySelector('input[name="q"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }

    // Create and show help modal
    function createHelpModal() {
        // Check if modal already exists
        let modal = document.getElementById('shortcuts-help-modal');
        if (modal) {
            return modal;
        }

        modal = document.createElement('div');
        modal.id = 'shortcuts-help-modal';
        modal.className = 'shortcuts-modal';
        modal.innerHTML = `
            <div class="shortcuts-modal-content">
                <div class="shortcuts-modal-header">
                    <h4>Keyboard Shortcuts</h4>
                    <button type="button" class="shortcuts-modal-close" aria-label="Close">&times;</button>
                </div>
                <div class="shortcuts-modal-body">
                    <table class="shortcuts-table">
                        <tbody>
                            <tr>
                                <td><kbd>j</kbd></td>
                                <td>Move down to next bookmark</td>
                            </tr>
                            <tr>
                                <td><kbd>k</kbd></td>
                                <td>Move up to previous bookmark</td>
                            </tr>
                            <tr>
                                <td><kbd>Enter</kbd></td>
                                <td>Open selected bookmark</td>
                            </tr>
                            <tr>
                                <td><kbd>e</kbd></td>
                                <td>Edit selected bookmark</td>
                            </tr>
                            <tr>
                                <td><kbd>d</kbd></td>
                                <td>Delete selected bookmark</td>
                            </tr>
                            <tr>
                                <td><kbd>/</kbd></td>
                                <td>Focus search input</td>
                            </tr>
                            <tr>
                                <td><kbd>?</kbd></td>
                                <td>Show this help</td>
                            </tr>
                            <tr>
                                <td><kbd>Esc</kbd></td>
                                <td>Clear selection / Close modal</td>
                            </tr>
                        </tbody>
                    </table>
                    <div class="shortcuts-toggle">
                        <label>
                            <input type="checkbox" id="shortcuts-enabled-toggle" ${isShortcutsEnabled() ? 'checked' : ''}>
                            Enable keyboard shortcuts
                        </label>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close button handler
        modal.querySelector('.shortcuts-modal-close').addEventListener('click', function() {
            hideHelpModal();
        });

        // Click outside to close
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                hideHelpModal();
            }
        });

        // Toggle handler
        modal.querySelector('#shortcuts-enabled-toggle').addEventListener('change', function(e) {
            setShortcutsEnabled(e.target.checked);
        });

        return modal;
    }

    function showHelpModal() {
        const modal = createHelpModal();
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function hideHelpModal() {
        const modal = document.getElementById('shortcuts-help-modal');
        if (modal) {
            modal.classList.remove('show');
            document.body.style.overflow = '';
        }
    }

    function isHelpModalVisible() {
        const modal = document.getElementById('shortcuts-help-modal');
        return modal && modal.classList.contains('show');
    }

    // Check if we're in an input field
    function isTyping(e) {
        const tagName = e.target.tagName.toLowerCase();
        const isInput = tagName === 'input' || tagName === 'textarea' || tagName === 'select';
        const isEditable = e.target.isContentEditable;
        return isInput || isEditable;
    }

    // Main keyboard handler
    function handleKeydown(e) {
        // Always allow ? for help, even when shortcuts are disabled
        if (e.key === '?' && !isTyping(e)) {
            e.preventDefault();
            if (isHelpModalVisible()) {
                hideHelpModal();
            } else {
                showHelpModal();
            }
            return;
        }

        // Close modal on Escape
        if (e.key === 'Escape') {
            if (isHelpModalVisible()) {
                hideHelpModal();
                return;
            }
            clearSelection();
            return;
        }

        // Don't process other shortcuts if disabled or typing
        if (!isShortcutsEnabled() || isTyping(e)) {
            return;
        }

        switch (e.key) {
            case 'j':
                e.preventDefault();
                updateSelection(currentIndex + 1);
                break;

            case 'k':
                e.preventDefault();
                updateSelection(currentIndex - 1);
                break;

            case 'Enter':
                if (currentIndex >= 0) {
                    e.preventDefault();
                    openSelectedMark();
                }
                break;

            case 'e':
                if (currentIndex >= 0) {
                    e.preventDefault();
                    editSelectedMark();
                }
                break;

            case 'd':
                if (currentIndex >= 0) {
                    e.preventDefault();
                    deleteSelectedMark(items[currentIndex]);
                }
                break;

            case '/':
                e.preventDefault();
                focusSearch();
                break;
        }
    }

    // Initialize
    function init() {
        items = getItems();
        document.addEventListener('keydown', handleKeydown);
        
        // Update items list when DOM changes (for dynamic content)
        const observer = new MutationObserver(function() {
            items = getItems();
        });
        
        const container = document.querySelector('.list-group');
        if (container) {
            observer.observe(container, { childList: true, subtree: true });
        }
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose toggle function globally for potential use
    window.FlaskmarksShortcuts = {
        isEnabled: isShortcutsEnabled,
        setEnabled: setShortcutsEnabled,
        showHelp: showHelpModal,
        hideHelp: hideHelpModal
    };

})();
