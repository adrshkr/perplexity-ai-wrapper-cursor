#!/usr/bin/env python3
"""
Update cloudscraper submodule to latest version
"""
import subprocess
import sys
from pathlib import Path

def update_cloudscraper():
    """Update cloudscraper git submodule to latest version"""
    project_root = Path(__file__).parent.parent
    
    print("Updating cloudscraper submodule...")
    print("=" * 50)
    
    # Check if submodule exists
    cloudscraper_dir = project_root / 'cloudscraper'
    if not cloudscraper_dir.exists():
        print("ERROR: cloudscraper submodule not found")
        print("Initialize it first with:")
        print("  git submodule add https://github.com/VeNoMouS/cloudscraper.git cloudscraper")
        return False
    
    try:
        # Update submodule to latest
        print("1. Fetching latest changes...")
        result = subprocess.run(
            ['git', 'submodule', 'update', '--remote', 'cloudscraper'],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"ERROR: {result.stderr}")
            return False
        
        print("✓ Submodule updated")
        
        # Check current commit
        print("\n2. Checking current version...")
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=cloudscraper_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            commit_hash = result.stdout.strip()[:8]
            print(f"✓ Current commit: {commit_hash}")
        
        # Check for breaking changes (simplified check)
        print("\n3. Checking for potential breaking changes...")
        print("   (Review cloudscraper/CHANGELOG.md for details)")
        
        # Run basic import test
        print("\n4. Testing cloudscraper import...")
        try:
            sys.path.insert(0, str(cloudscraper_dir))
            import cloudscraper
            print(f"✓ cloudscraper version: {getattr(cloudscraper, '__version__', 'unknown')}")
            print("✓ Import successful")
        except Exception as e:
            print(f"⚠ WARNING: Import test failed: {e}")
            print("   You may need to reinstall dependencies:")
            print("   pip install -r requirements.txt")
        
        print("\n" + "=" * 50)
        print("Update complete!")
        print("\nNext steps:")
        print("  1. Test the integration: python -m pytest tests/")
        print("  2. Review cloudscraper/CHANGELOG.md for changes")
        print("  3. Update your code if needed")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = update_cloudscraper()
    sys.exit(0 if success else 1)

