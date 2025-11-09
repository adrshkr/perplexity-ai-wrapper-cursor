"""
Centralized import handling for the Perplexity AI Wrapper.
Handles both installed package and development mode imports.
"""
import sys
from pathlib import Path


def setup_imports():
    """
    Setup import paths for both installed and development modes.
    This ensures imports work whether the package is installed via pip
    or run directly from the source directory.
    """
    # Get the project root directory
    cli_file = Path(__file__).resolve()
    
    # Navigate to project root (from src/utils/imports.py -> project root)
    if 'src' in str(cli_file.parent):
        project_root = cli_file.parent.parent.parent
    else:
        # Try current working directory as fallback
        project_root = Path.cwd()
    
    # Add project root to path if it exists and has src directory
    if project_root.exists() and (project_root / 'src').exists():
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))


def import_module(module_path, package_name=None):
    """
    Import a module with fallback handling for installed vs development mode.
    
    Args:
        module_path: Full module path (e.g., 'src.core.client')
        package_name: Optional package name for installed mode (e.g., 'core.client')
    
    Returns:
        The imported module
    
    Raises:
        ImportError: If module cannot be imported in any mode
    """
    # Try installed package first (if package_name provided)
    if package_name:
        try:
            return __import__(package_name, fromlist=[''])
        except ImportError:
            pass
    
    # Try development mode (src.*)
    try:
        return __import__(module_path, fromlist=[''])
    except ImportError:
        pass
    
    # Last resort: try without src prefix
    if module_path.startswith('src.'):
        try:
            return __import__(module_path[4:], fromlist=[''])
        except ImportError:
            pass
    
    raise ImportError(f"Could not import {module_path} in any mode")


# Setup imports when this module is imported
setup_imports()

