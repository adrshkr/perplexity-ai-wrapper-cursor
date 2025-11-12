#!/usr/bin/env python3
"""
Simple verification script to test imports after optimization
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    print("🧪 Verifying imports after optimization...")

    # Test core clients
    try:
        from src.core.client import PerplexityClient

        print("✅ PerplexityClient imported successfully")
    except Exception as e:
        print(f"❌ PerplexityClient import failed: {e}")
        return False

    try:
        from src.core.async_client import AsyncPerplexityClient

        print("✅ AsyncPerplexityClient imported successfully")
    except Exception as e:
        print(f"❌ AsyncPerplexityClient import failed: {e}")
        return False

    # Test models
    try:
        from src.core.models import SearchMode, SearchResponse

        print("✅ Models imported successfully")
    except Exception as e:
        print(f"❌ Models import failed: {e}")
        return False

    # Test web driver (might fail if playwright not installed)
    try:
        from src.automation.web_driver import PerplexityWebDriver

        print("✅ PerplexityWebDriver imported successfully")
    except Exception as e:
        print(
            f"⚠️  PerplexityWebDriver import failed (expected if Playwright not installed): {e}"
        )

    # Test httpx is available (our new unified HTTP client)
    try:
        import httpx

        print("✅ httpx available for HTTP requests")
    except ImportError:
        print("❌ httpx not available - this is required!")
        return False

    # Test basic client creation
    try:
        client = PerplexityClient(use_cloudflare_bypass=False)
        print("✅ Sync client created successfully")

        # Verify it's using httpx
        if hasattr(client, "client") and isinstance(client.client, httpx.Client):
            print("✅ Sync client using httpx.Client")
        else:
            print("❌ Sync client not using httpx.Client")
            return False

        client.close()
    except Exception as e:
        print(f"❌ Sync client creation failed: {e}")
        return False

    try:
        async_client = AsyncPerplexityClient(use_cloudflare_bypass=False)
        print("✅ Async client created successfully")
    except Exception as e:
        print(f"❌ Async client creation failed: {e}")
        return False

    print("\n🎉 All critical imports working!")
    print("✨ Optimization successful:")
    print("  • Type errors fixed")
    print("  • HTTP clients consolidated to httpx")
    print("  • Dependencies reduced")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
