/**
 * Foundation Platform - Main JavaScript
 * Handles sidebar navigation, mobile menu, and active states
 */

(function() {
    'use strict';

    // Wait for DOM to be fully loaded
    document.addEventListener('DOMContentLoaded', function() {
        initSidebar();
        initNavigation();
    });

    /**
     * Initialize sidebar toggle functionality for mobile
     */
    function initSidebar() {
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');

        if (!sidebarToggle || !sidebar || !overlay) {
            return;
        }

        // Toggle sidebar when button is clicked
        sidebarToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleSidebar();
        });

        // Close sidebar when overlay is clicked
        overlay.addEventListener('click', function() {
            closeSidebar();
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(e) {
            const isMobile = window.innerWidth <= 768;
            const isClickInsideSidebar = sidebar.contains(e.target);
            const isClickOnToggle = sidebarToggle.contains(e.target);

            if (isMobile && !isClickInsideSidebar && !isClickOnToggle && sidebar.classList.contains('active')) {
                closeSidebar();
            }
        });

        // Close sidebar on window resize if changing from mobile to desktop
        let previousWidth = window.innerWidth;
        window.addEventListener('resize', function() {
            const currentWidth = window.innerWidth;

            // If transitioning from mobile to desktop, close the sidebar
            if (previousWidth <= 768 && currentWidth > 768) {
                closeSidebar();
            }

            previousWidth = currentWidth;
        });
    }

    /**
     * Toggle sidebar open/closed state
     */
    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');

        if (sidebar && overlay) {
            sidebar.classList.toggle('active');
            overlay.classList.toggle('active');
        }
    }

    /**
     * Close sidebar
     */
    function closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');

        if (sidebar && overlay) {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        }
    }

    /**
     * Open sidebar
     */
    function openSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');

        if (sidebar && overlay) {
            sidebar.classList.add('active');
            overlay.classList.add('active');
        }
    }

    /**
     * Initialize navigation active state
     * Highlights the current page in the sidebar navigation
     */
    function initNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        const currentPath = window.location.pathname;

        navLinks.forEach(function(link) {
            const linkPath = link.getAttribute('href');

            // Remove any existing active class
            link.classList.remove('active');

            // Add active class if this is the current page
            // Check for exact match or if current path starts with link path (for sub-pages)
            if (linkPath === currentPath ||
                (linkPath !== '/' && currentPath.startsWith(linkPath))) {
                link.classList.add('active');
            }

            // Special case: if we're on home page, activate home link
            if (currentPath === '/' && linkPath === '/') {
                link.classList.add('active');
            }

            // Close sidebar when clicking a nav link on mobile
            link.addEventListener('click', function() {
                const isMobile = window.innerWidth <= 768;
                if (isMobile) {
                    // Small delay to allow navigation to complete
                    setTimeout(closeSidebar, 150);
                }
            });
        });
    }

    /**
     * Update active navigation link programmatically
     * Useful when using client-side routing
     * @param {string} path - The path to set as active
     */
    function setActiveNavLink(path) {
        const navLinks = document.querySelectorAll('.nav-link');

        navLinks.forEach(function(link) {
            const linkPath = link.getAttribute('href');
            link.classList.remove('active');

            if (linkPath === path ||
                (linkPath !== '/' && path.startsWith(linkPath))) {
                link.classList.add('active');
            }
        });
    }

    // Export functions to global scope for use in other scripts if needed
    window.FoundationPlatform = {
        toggleSidebar: toggleSidebar,
        closeSidebar: closeSidebar,
        openSidebar: openSidebar,
        setActiveNavLink: setActiveNavLink
    };

})();
