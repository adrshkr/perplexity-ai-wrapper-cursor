"""
ABOUTME: Browser automation package for Perplexity.ai
ABOUTME: Exports main components and utilities for browser-based interactions
"""

# Export main components
from .web_driver import PerplexityWebDriver
from .tab_manager import TabManager
from .cookie_injector import CookieInjector
from .cloudflare_handler import CloudflareHandler

__all__ = [
    'PerplexityWebDriver',
    'TabManager',
    'CookieInjector',
    'CloudflareHandler',
]
