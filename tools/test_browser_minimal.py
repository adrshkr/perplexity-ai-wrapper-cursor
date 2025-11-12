"""
Minimal test - exactly mimics working CLI browser automation
"""
import sys
from pathlib import Path
import time

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.automation.web_driver import PerplexityWebDriver

# Use persistent profile like the working code does
profile_dir = str(project_root / 'browser_data' / 'test_persistent')

print("Starting browser with persistent profile...")
driver = PerplexityWebDriver(
    headless=False,
    user_data_dir=profile_dir,
    stealth_mode=True
)

try:
    driver.start()
    
    # Navigate - just like main CLI does
    print("Navigating to Perplexity...")
    driver.page.goto('https://www.perplexity.ai/', wait_until='domcontentloaded')
    time.sleep(3)
    
    print("\n" + "="*60)
    print("Browser opened successfully!")
    print("You have 60 seconds to login manually...")
    print("="*60)
    
    # Wait without blocking - check every second
    for i in range(60, 0, -1):
        print(f"\rTime remaining: {i} seconds... ", end='', flush=True)
        time.sleep(1)
    print("\n")
    
    # Check if we can access page
    print(f"\nCurrent URL: {driver.page.url}")
    
    # Try to find buttons
    buttons = driver.page.evaluate("""
        () => {
            const btns = document.querySelectorAll('button');
            return Array.from(btns).slice(0, 10).map(b => ({
                text: b.textContent?.trim().substring(0, 30),
                visible: b.offsetParent !== null
            }));
        }
    """)
    
    print(f"\nFound {len(buttons)} buttons (showing first 10):")
    for btn in buttons:
        if btn['text']:
            print(f"  - {btn['text']} (visible: {btn['visible']})")
    
    print("\n" + "="*60)
    print("Test successful! Press Enter to close...")
    print("="*60)
    input()
    
finally:
    driver.close()
