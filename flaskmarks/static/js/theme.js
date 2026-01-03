/**
 * Theme Manager - Handles dark/light mode switching
 * Features:
 * - System preference detection via matchMedia
 * - Manual toggle with localStorage persistence
 * - Prevents flash of wrong theme on page load
 */

(function() {
    'use strict';

    const THEME_KEY = 'bookmarko-theme';
    const DARK = 'dark';
    const LIGHT = 'light';

    /**
     * Get the user's preferred theme from localStorage or system preference
     */
    function getPreferredTheme() {
        const storedTheme = localStorage.getItem(THEME_KEY);
        if (storedTheme) {
            return storedTheme;
        }
        // Check system preference
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? DARK : LIGHT;
    }

    /**
     * Apply theme to the document
     */
    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        
        // Update toggle button icon visibility (handled by CSS, but update aria-label)
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.setAttribute('aria-label', 
                theme === DARK ? 'Switch to light mode' : 'Switch to dark mode'
            );
        }
    }

    /**
     * Save theme preference to localStorage
     */
    function saveTheme(theme) {
        localStorage.setItem(THEME_KEY, theme);
    }

    /**
     * Toggle between light and dark themes
     */
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || LIGHT;
        const newTheme = currentTheme === DARK ? LIGHT : DARK;
        setTheme(newTheme);
        saveTheme(newTheme);
    }

    /**
     * Initialize theme on page load
     */
    function initTheme() {
        const theme = getPreferredTheme();
        setTheme(theme);

        // Set up toggle button listener
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleTheme);
        }

        // Listen for system theme changes (only if no manual preference is stored)
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
            if (!localStorage.getItem(THEME_KEY)) {
                setTheme(e.matches ? DARK : LIGHT);
            }
        });
    }

    // Apply theme immediately to prevent flash
    // This runs before DOMContentLoaded
    (function() {
        const theme = getPreferredTheme();
        document.documentElement.setAttribute('data-theme', theme);
    })();

    // Set up event listeners after DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }

    // Expose toggle function globally for potential external use
    window.toggleTheme = toggleTheme;

})();
