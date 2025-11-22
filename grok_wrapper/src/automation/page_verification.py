"""
Page verification utilities for ensuring Grok homepage is fully rendered
"""
from typing import Optional, Dict, Any

def verify_grok_homepage_js() -> str:
    """
    JavaScript to verify that the Grok homepage is fully rendered.
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            const verification = {
                pageLoaded: false,
                mainInputVisible: false,
                buttonsVisible: false,
                deepsearchButtonVisible: false,
                issues: []
            };
            
            // Check if page is loaded
            if (document.readyState === 'complete') {
                verification.pageLoaded = true;
            } else {
                verification.issues.push('Page readyState is not complete: ' + document.readyState);
            }
            
            // Check for main input field
            const mainInput = document.querySelector('textarea[aria-label*="Ask"], textarea, input[type="text"]');
            if (mainInput) {
                const rect = mainInput.getBoundingClientRect();
                const style = window.getComputedStyle(mainInput);
                if (rect.width > 0 && rect.height > 0 && 
                    mainInput.offsetParent !== null &&
                    style.display !== 'none' &&
                    style.visibility !== 'hidden') {
                    verification.mainInputVisible = true;
                } else {
                    verification.issues.push('Main input exists but is not visible');
                }
            } else {
                verification.issues.push('Main input field not found');
            }
            
            // Check for buttons (should have multiple buttons including DeepSearch)
            const allButtons = Array.from(document.querySelectorAll('button'));
            if (allButtons.length > 0) {
                const visibleButtons = allButtons.filter(btn => {
                    const rect = btn.getBoundingClientRect();
                    const style = window.getComputedStyle(btn);
                    return rect.width > 0 && rect.height > 0 && 
                           btn.offsetParent !== null &&
                           style.display !== 'none';
                });
                
                if (visibleButtons.length > 0) {
                    verification.buttonsVisible = true;
                    verification.visibleButtonCount = visibleButtons.length;
                } else {
                    verification.issues.push('Buttons found but none are visible');
                }
            } else {
                verification.issues.push('No buttons found on page');
            }
            
            // Specifically check for DeepSearch button
            for (const btn of allButtons) {
                const text = (btn.innerText || btn.textContent || '').trim();
                if (text === 'DeepSearch' || text.toLowerCase() === 'deepsearch') {
                    const rect = btn.getBoundingClientRect();
                    const style = window.getComputedStyle(btn);
                    if (rect.width > 0 && rect.height > 0 && 
                        btn.offsetParent !== null &&
                        style.display !== 'none' &&
                        style.visibility !== 'hidden') {
                        verification.deepsearchButtonVisible = true;
                        verification.deepsearchButtonInfo = {
                            text: text,
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height,
                            dataSlot: btn.getAttribute('data-slot'),
                            className: (btn.className || '').substring(0, 100)
                        };
                        break;
                    }
                }
            }
            
            if (!verification.deepsearchButtonVisible) {
                verification.issues.push('DeepSearch button not found or not visible');
            }
            
            // Check if we're on the right page (not redirected to login)
            const currentUrl = window.location.href;
            if (currentUrl.includes('sign-in') || currentUrl.includes('sign-up') || currentUrl.includes('accounts.x.ai')) {
                verification.issues.push('Redirected to login page: ' + currentUrl);
            }
            
            // Check for common Grok UI elements
            verification.hasMainElement = document.querySelector('main') !== null;
            verification.hasFormElement = document.querySelector('form') !== null;
            
            // Overall status
            verification.isFullyRendered = (
                verification.pageLoaded &&
                verification.mainInputVisible &&
                verification.buttonsVisible &&
                verification.deepsearchButtonVisible &&
                !currentUrl.includes('sign-in') &&
                !currentUrl.includes('sign-up')
            );
            
            return verification;
        }
    """


def wait_for_grok_homepage_js() -> str:
    """
    JavaScript to wait for Grok homepage to be fully rendered.
    Polls until all elements are visible.
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            const maxAttempts = 20; // 10 seconds max (0.5s intervals)
            let attempts = 0;
            
            while (attempts < maxAttempts) {
                const mainInput = document.querySelector('textarea[aria-label*="Ask"], textarea, input[type="text"]');
                const allButtons = Array.from(document.querySelectorAll('button'));
                
                let deepsearchFound = false;
                for (const btn of allButtons) {
                    const text = (btn.innerText || btn.textContent || '').trim();
                    if (text === 'DeepSearch' || text.toLowerCase() === 'deepsearch') {
                        const rect = btn.getBoundingClientRect();
                        const style = window.getComputedStyle(btn);
                        if (rect.width > 0 && rect.height > 0 && 
                            btn.offsetParent !== null &&
                            style.display !== 'none') {
                            deepsearchFound = true;
                            break;
                        }
                    }
                }
                
                if (mainInput && allButtons.length > 0 && deepsearchFound) {
                    return { ready: true, attempts: attempts + 1 };
                }
                
                attempts++;
                // Wait 0.5 seconds (this will be done in Python)
            }
            
            return { ready: false, attempts: maxAttempts };
        }
    """

