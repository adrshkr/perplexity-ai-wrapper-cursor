"""
ABOUTME: Platform abstraction layer for unified cross-platform support.
ABOUTME: Handles Windows, Linux, and WSL2 detection and optimization.
"""
import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, List


class PlatformManager:
    """Unified platform detection and utilities for Windows, Linux, and WSL2"""
    
    def __init__(self):
        self._is_windows = platform.system() == 'Windows'
        self._is_linux = platform.system() == 'Linux'
        self._is_wsl2 = self._detect_wsl2()
    
    def _detect_wsl2(self) -> bool:
        """Detect if running in WSL2 environment"""
        if not self._is_linux:
            return False
        try:
            with open('/proc/version', 'r') as f:
                version = f.read().lower()
                return 'microsoft' in version and 'wsl' in version
        except:
            return False
    
    @property
    def is_windows(self) -> bool:
        """True if running on native Windows"""
        return self._is_windows
    
    @property
    def is_wsl2(self) -> bool:
        """True if running in WSL2"""
        return self._is_wsl2
    
    @property
    def is_linux(self) -> bool:
        """True if running on native Linux (not WSL2)"""
        return self._is_linux and not self._is_wsl2
    
    def get_chrome_executable(self) -> Optional[str]:
        """
        Get best Chrome executable for current platform.
        For WSL2, returns Windows Chrome path (much faster).
        For other platforms, returns None to use Playwright default.
        """
        if self._is_wsl2:
            # Try Windows Chrome first (3-4x faster startup from WSL2)
            return self._find_windows_chrome_from_wsl2()
        return None  # Use Playwright's default Chrome/Chromium
    
    def _find_windows_chrome_from_wsl2(self) -> Optional[str]:
        """
        Find Windows Chrome executable from WSL2 environment.
        Tries multiple detection methods for robustness.
        """
        # Method 1: Try with detected Windows username
        username = self._get_windows_username()
        if username and username != 'Unknown':
            user_path = f'/mnt/c/Users/{username}/AppData/Local/Google/Chrome/Application/chrome.exe'
            if os.path.exists(user_path):
                return user_path
        
        # Method 2: Try common installation paths
        common_paths = [
            '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe',
            '/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe',
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Method 3: Try to find via Windows 'where' command
        try:
            result = subprocess.run(
                ['cmd.exe', '/c', 'where', 'chrome.exe'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                # Convert Windows path to WSL2 path
                win_path = result.stdout.strip().split('\n')[0]
                if win_path.startswith('C:\\'):
                    wsl_path = '/mnt/c' + win_path[2:].replace('\\', '/')
                    if os.path.exists(wsl_path):
                        return wsl_path
        except:
            pass
        
        return None  # Fallback to Linux Chrome
    
    def _get_windows_username(self) -> str:
        """
        Get Windows username from WSL2 environment.
        Tries multiple detection methods.
        """
        # Method 1: USERPROFILE environment variable
        userprofile = os.getenv('USERPROFILE', '')
        if userprofile:
            # Extract username from path like C:\Users\username
            return userprofile.replace('C:\\Users\\', '').replace('\\', '').split('\\')[0]
        
        # Method 2: WSLENV or USER environment variables
        wsl_user = os.getenv('USER', '')
        if wsl_user:
            return wsl_user
        
        # Method 3: List /mnt/c/Users directory
        users_dir = '/mnt/c/Users'
        if os.path.exists(users_dir):
            try:
                for item in os.listdir(users_dir):
                    # Skip system directories
                    if item not in ['Public', 'Default', 'All Users', 'Default User']:
                        item_path = os.path.join(users_dir, item)
                        if os.path.isdir(item_path):
                            return item
            except:
                pass
        
        return 'Unknown'
    
    def get_script_launcher(self) -> str:
        """Get appropriate launcher script for current platform"""
        if self._is_windows:
            return 'perplexity.bat'
        return './perplexity.sh'
    
    def get_venv_python(self) -> str:
        """Get path to venv Python executable"""
        if self._is_windows:
            return 'venv\\Scripts\\python.exe'
        return 'venv/bin/python'
    
    def get_venv_activate_script(self) -> str:
        """Get path to venv activation script"""
        if self._is_windows:
            return 'venv\\Scripts\\activate.bat'
        return 'venv/bin/activate'
    
    def get_display_info(self) -> dict:
        """Get display environment information (useful for WSL2)"""
        display = os.environ.get('DISPLAY', '')
        has_display = bool(display and ':' in display)
        
        return {
            'has_display': has_display,
            'display': display,
            'can_show_ui': has_display or self._is_windows
        }
    
    def get_chrome_launch_args(self) -> List[str]:
        """Get platform-specific Chrome launch arguments"""
        base_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--no-first-run',
            '--no-default-browser-check',
            '--window-size=1280,720',
            '--start-maximized'
        ]
        
        display_info = self.get_display_info()
        
        # WSL2-specific optimizations
        if self._is_wsl2:
            # Check if using Windows Chrome (common rendering issues)
            chrome_path = self.get_chrome_executable()
            using_windows_chrome = chrome_path and '/mnt/c' in chrome_path
            
            if not display_info['has_display'] or using_windows_chrome:
                # No X11 display OR using Windows Chrome - force compatible settings
                # Windows Chrome from WSL2 often has blank/transparent rendering, disable GPU
                base_args.extend([
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-software-gpu',
                    '--disable-gpu-frontend-software',
                    '--no-gpu',
                    '--disable-gpu-sandbox',
                    '--disable-gpu-compositing',
                    '--disable-dev-shm-usage',  # Critical for WSL2
                ])
            else:
                # Has X11 display and using Linux Chrome - enable GPU
                base_args.extend([
                    '--enable-gpu',
                    '--disable-gpu-sandbox',
                    '--force-device-scale-factor=1',
                ])
        
        # Linux-specific optimizations
        elif self._is_linux:
            base_args.extend([
                '--enable-gpu',
                '--disable-gpu-sandbox',
            ])
        
        return base_args
    
    def __repr__(self):
        return (f"PlatformManager(windows={self._is_windows}, "
                f"linux={self._is_linux and not self._is_wsl2}, "
                f"wsl2={self._is_wsl2})")


# Global singleton instance
platform_manager = PlatformManager()
