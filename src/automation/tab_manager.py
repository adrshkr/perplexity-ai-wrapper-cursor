"""
ABOUTME: Manages a pool of browser tabs for concurrent query execution
ABOUTME: Handles tab lifecycle, reuse, and cleanup for browser automation
"""
import time
import threading
from collections import deque
from typing import TYPE_CHECKING, Deque, Dict

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page


class TabManager:
    """Manages a pool of browser tabs for concurrent queries"""
    
    def __init__(self, context: 'BrowserContext', max_tabs: int = 5):
        """
        Initialize tab manager
        
        Args:
            context: Playwright browser context
            max_tabs: Maximum number of concurrent tabs
        """
        self.context = context
        self.max_tabs = max_tabs
        self.available_tabs: Deque['Page'] = deque()
        self.active_tabs: Dict['Page', Dict] = {}
        self.lock = threading.Lock()
    
    def get_tab(self) -> 'Page':
        """Get an available tab, creating one if needed"""
        with self.lock:
            # Reuse available tab if exists
            if self.available_tabs:
                tab = self.available_tabs.popleft()
                try:
                    if tab.is_closed():
                        tab = self.context.new_page()
                    else:
                        # Clear tab for reuse
                        try:
                            tab.goto("about:blank", wait_until="domcontentloaded", timeout=2000)
                        except Exception:
                            # Tab is broken - close it and create a new one
                            try:
                                if not tab.is_closed():
                                    tab.close()
                            except Exception:
                                pass
                            tab = self.context.new_page()
                except Exception:
                    # Tab is broken - close it and create a new one
                    try:
                        if not tab.is_closed():
                            tab.close()
                    except Exception:
                        pass
                    tab = self.context.new_page()
            else:
                # Create new tab if under limit
                if len(self.active_tabs) < self.max_tabs:
                    tab = self.context.new_page()
                else:
                    # Reuse oldest tab
                    oldest_tab = min(self.active_tabs.items(), key=lambda x: x[1].get('created_at', 0))[0]
                    try:
                        if not oldest_tab.is_closed():
                            oldest_tab.goto("about:blank", wait_until="domcontentloaded", timeout=2000)
                        tab = oldest_tab
                        if tab in self.active_tabs:
                            del self.active_tabs[tab]
                    except Exception:
                        # Remove broken oldest tab from active_tabs before creating new one
                        if oldest_tab in self.active_tabs:
                            del self.active_tabs[oldest_tab]
                        tab = self.context.new_page()
            
            # Mark as active
            self.active_tabs[tab] = {
                'created_at': time.time(),
                'state': 'active'
            }
            
            return tab
    
    def release_tab(self, tab: 'Page', reuse: bool = True) -> None:
        """
        Release a tab back to the pool
        
        Args:
            tab: Page to release
            reuse: If True, keep tab for reuse; otherwise close it
        """
        with self.lock:
            if tab in self.active_tabs:
                del self.active_tabs[tab]
            
            if reuse and not tab.is_closed():
                # Check if tab is already in available_tabs to prevent duplicates
                if tab not in self.available_tabs:
                    self.available_tabs.append(tab)
            else:
                try:
                    if not tab.is_closed():
                        tab.close()
                except Exception:
                    pass
    
    def close_all(self) -> None:
        """Close all tabs in the pool"""
        with self.lock:
            for tab in list(self.available_tabs):
                try:
                    if not tab.is_closed():
                        tab.close()
                except Exception:
                    pass
            self.available_tabs.clear()
            
            for tab in list(self.active_tabs.keys()):
                try:
                    if not tab.is_closed():
                        tab.close()
                except Exception:
                    pass
            self.active_tabs.clear()
