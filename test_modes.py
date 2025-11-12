#!/usr/bin/env python3
"""
Test script for Research and Labs mode functionality in PerplexityWebDriver

This script verifies that the mode selection works correctly for:
- Standard search mode (default)
- Research mode for comprehensive analysis
- Labs mode for experimental features

Usage:
    python test_modes.py
    
Prerequisites:
    - Valid Perplexity login cookies
    - PerplexityWebDriver implementation
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.automation.web_driver import PerplexityWebDriver
except ImportError:
    try:
        from automation.web_driver import PerplexityWebDriver
    except ImportError:
        print("❌ Could not import PerplexityWebDriver")
        print("Make sure you're running this from the project root directory")
        sys.exit(1)

def test_mode_functionality():
    """Test Research and Labs mode functionality"""
    
    print("🧪 Testing PerplexityWebDriver Research and Labs Mode Support")
    print("=" * 60)
    
    # Initialize driver
    print("1. Initializing PerplexityWebDriver...")
    driver = PerplexityWebDriver(headless=True, stealth_mode=True)
    
    try:
        # Start browser
        print("2. Starting browser...")
        driver.start()
        
        # Navigate to Perplexity
        print("3. Navigating to Perplexity...")
        driver.navigate_to_perplexity()
        
        # Test mode selection functionality
        print("\n4. Testing mode selection...")
        
        # Test Research mode
        print("   📚 Testing Research mode...")
        research_success = driver.select_mode('research')
        if research_success:
            print("   ✅ Research mode selected successfully")
            current_mode = getattr(driver, '_current_mode', 'unknown')
            print(f"   📊 Current mode: {current_mode}")
        else:
            print("   ❌ Failed to select Research mode")
        
        # Test Labs mode  
        print("   🔬 Testing Labs mode...")
        labs_success = driver.select_mode('labs')
        if labs_success:
            print("   ✅ Labs mode selected successfully")
            current_mode = getattr(driver, '_current_mode', 'unknown')
            print(f"   📊 Current mode: {current_mode}")
        else:
            print("   ❌ Failed to select Labs mode")
        
        # Test Search mode (default)
        print("   🔍 Testing Search mode...")
        search_success = driver.select_mode('search')
        if search_success:
            print("   ✅ Search mode selected successfully")
            current_mode = getattr(driver, '_current_mode', 'unknown')
            print(f"   📊 Current mode: {current_mode}")
        else:
            print("   ❌ Failed to select Search mode")
        
        # Test search with different modes
        print("\n5. Testing search with different modes...")
        
        test_query = "What is artificial intelligence?"
        
        # Test search mode
        print("   🔍 Testing search with 'search' mode...")
        try:
            search_result = driver.search(test_query, mode='search', wait_for_response=False)
            print("   ✅ Search mode search initiated successfully")
        except Exception as e:
            print(f"   ❌ Search mode search failed: {e}")
        
        # Test research mode
        print("   📚 Testing search with 'research' mode...")
        try:
            research_result = driver.search(test_query, mode='research', wait_for_response=False)
            print("   ✅ Research mode search initiated successfully")
        except Exception as e:
            print(f"   ❌ Research mode search failed: {e}")
        
        # Test labs mode
        print("   🔬 Testing search with 'labs' mode...")
        try:
            labs_result = driver.search(test_query, mode='labs', wait_for_response=False)
            print("   ✅ Labs mode search initiated successfully")
        except Exception as e:
            print(f"   ❌ Labs mode search failed: {e}")
        
        print("\n6. Testing mode button selectors...")
        
        # Check if mode buttons are accessible
        mode_selectors = [
            'button[aria-label="Search"]',
            'button[aria-label="Research"]', 
            'button[aria-label="Labs"]'
        ]
        
        for selector in mode_selectors:
            try:
                element = driver.page.query_selector(selector)
                if element:
                    print(f"   ✅ Found mode button: {selector}")
                else:
                    print(f"   ⚠️  Mode button not found: {selector}")
            except Exception as e:
                print(f"   ❌ Error checking selector {selector}: {e}")
        
        print("\n🎉 Mode functionality test completed!")
        
        # Summary
        print("\n📊 Test Summary:")
        print(f"   Research mode selection: {'✅' if research_success else '❌'}")
        print(f"   Labs mode selection: {'✅' if labs_success else '❌'}")
        print(f"   Search mode selection: {'✅' if search_success else '❌'}")
        
        if research_success and labs_success and search_success:
            print("\n🎉 All mode tests passed! Research and Labs mode support is working correctly.")
        else:
            print("\n⚠️  Some mode tests failed. Check the implementation or account permissions.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        print("\n7. Cleaning up...")
        try:
            driver.close()
            print("   ✅ Browser closed successfully")
        except Exception as e:
            print(f"   ⚠️  Error closing browser: {e}")

def print_usage_examples():
    """Print usage examples for Research and Labs modes"""
    
    print("\n📖 Usage Examples:")
    print("=" * 60)
    
    examples = [
        {
            "mode": "search",
            "description": "Standard search for quick answers",
            "query": "What is the capital of France?"
        },
        {
            "mode": "research", 
            "description": "Comprehensive analysis and deep research",
            "query": "Analyze the impact of AI on healthcare industry trends in 2024"
        },
        {
            "mode": "labs",
            "description": "Experimental features and advanced capabilities",
            "query": "Generate a comprehensive report on renewable energy technologies"
        }
    ]
    
    for example in examples:
        print(f"\n{example['mode'].upper()} MODE:")
        print(f"Description: {example['description']}")
        print(f"Example usage:")
        print(f"""    result = driver.search(
        "{example['query']}",
        mode='{example['mode']}'
    )""")
    
    print(f"\n📋 Method Signatures:")
    print(f"""    # Select mode
    success = driver.select_mode('research')
    
    # Search with mode
    result = driver.search("Your query", mode='labs')
    
    # Get structured response with mode info
    structured_result = driver.search(
        "Your query", 
        mode='research',
        structured=True
    )
    # Returns: {{'query': str, 'answer': str, 'sources': list, 'mode': 'research', ...}}""")

if __name__ == "__main__":
    print_usage_examples()
    print(f"\n{'='*60}")
    print(f"To run the tests, make sure you:")
    print(f"1. Have valid Perplexity login cookies")
    print(f"2. Are logged into Perplexity in your browser")
    print(f"3. Run: python test_modes.py")
    print(f"{'='*60}")
    
    # Only run tests if explicitly requested
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        test_mode_functionality()
    else:
        print(f"\n💡 Run with --run flag to execute the mode tests:")
        print(f"   python test_modes.py --run")
