"""
Popup and modal handler utilities for closing advertisements and overlays
"""
from typing import Optional, Dict, Any


def close_popups_js() -> str:
    """
    JavaScript to close various types of popups, modals, and advertisements.
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            const results = {
                closed: false,
                methods: [],
                elementsFound: []
            };
            
            // Strategy 1: Look for close buttons (X buttons) in common locations
            const closeButtonSelectors = [
                'button[aria-label*="close" i]',
                'button[aria-label*="Close" i]',
                'button[aria-label*="dismiss" i]',
                'button[aria-label*="Dismiss" i]',
                '[role="button"][aria-label*="close" i]',
                '[role="button"][aria-label*="Close" i]',
                'button:has(svg[aria-label*="close" i])',
                'button:has(svg[aria-label*="Close" i])',
                // Common close button patterns
                'button.close',
                'button[class*="close"]',
                '[class*="close-button"]',
                '[class*="CloseButton"]',
                // X icon buttons
                'svg[aria-label*="close" i]',
                'svg[aria-label*="Close" i]',
                // Look for buttons with X text or close icon
                'button:has-text("×")',
                'button:has-text("✕")',
                'button:has-text("✖")',
            ];
            
            for (const selector of closeButtonSelectors) {
                try {
                    const buttons = Array.from(document.querySelectorAll(selector));
                    for (const btn of buttons) {
                        const rect = btn.getBoundingClientRect();
                        const style = window.getComputedStyle(btn);
                        // Check if button is visible and in viewport
                        if (rect.width > 0 && rect.height > 0 && 
                            btn.offsetParent !== null &&
                            style.display !== 'none' &&
                            style.visibility !== 'hidden' &&
                            rect.top >= 0 && rect.left >= 0 &&
                            rect.top < window.innerHeight &&
                            rect.left < window.innerWidth) {
                            
                            // Check if it's in a modal/popup (not just any close button)
                            let parent = btn.parentElement;
                            let isInModal = false;
                            let depth = 0;
                            while (parent && depth < 5) {
                                const parentClass = parent.className || '';
                                const parentTag = parent.tagName || '';
                                // Check for modal/popup indicators
                                if (parentClass.includes('modal') ||
                                    parentClass.includes('popup') ||
                                    parentClass.includes('overlay') ||
                                    parentClass.includes('dialog') ||
                                    parentClass.includes('backdrop') ||
                                    parent.getAttribute('role') === 'dialog' ||
                                    parentTag === 'DIALOG') {
                                    isInModal = true;
                                    break;
                                }
                                parent = parent.parentElement;
                                depth++;
                            }
                            
                            // Also check if button is in top-right corner (common for close buttons)
                            const isTopRight = rect.top < 100 && rect.left > window.innerWidth - 150;
                            
                            if (isInModal || isTopRight) {
                                btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                                btn.click();
                                btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                results.closed = true;
                                results.methods.push('close-button-click');
                                results.elementsFound.push({
                                    type: 'close-button',
                                    selector: selector,
                                    position: { top: rect.top, left: rect.left }
                                });
                                return results; // Return immediately after closing
                            }
                        }
                    }
                } catch (e) {
                    // Continue to next selector
                }
            }
            
            // Strategy 2: Look for modal/popup containers and try to close them
            const modalSelectors = [
                '[role="dialog"]',
                'dialog',
                '[class*="modal"]',
                '[class*="Modal"]',
                '[class*="popup"]',
                '[class*="Popup"]',
                '[class*="overlay"]',
                '[class*="Overlay"]',
                '[class*="backdrop"]',
                '[class*="Backdrop"]',
                '[class*="announcement"]',
                '[class*="Announcement"]',
                '[class*="promo"]',
                '[class*="Promo"]',
            ];
            
            for (const selector of modalSelectors) {
                try {
                    const modals = Array.from(document.querySelectorAll(selector));
                    for (const modal of modals) {
                        const rect = modal.getBoundingClientRect();
                        const style = window.getComputedStyle(modal);
                        // Check if modal is visible and covers significant portion of screen
                        if (rect.width > 200 && rect.height > 200 &&
                            modal.offsetParent !== null &&
                            style.display !== 'none' &&
                            style.visibility !== 'hidden' &&
                            (rect.top < window.innerHeight / 2 || 
                             rect.width > window.innerWidth * 0.5)) {
                            
                            // Try to find close button within this modal
                            const closeBtn = modal.querySelector('button[aria-label*="close" i], button[aria-label*="Close" i], [class*="close"]');
                            if (closeBtn) {
                                closeBtn.click();
                                closeBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                results.closed = true;
                                results.methods.push('modal-close-button');
                                results.elementsFound.push({
                                    type: 'modal',
                                    selector: selector,
                                    size: { width: rect.width, height: rect.height }
                                });
                                return results;
                            }
                            
                            // Try pressing Escape key on the modal
                            const escapeEvent = new KeyboardEvent('keydown', {
                                key: 'Escape',
                                code: 'Escape',
                                keyCode: 27,
                                bubbles: true,
                                cancelable: true
                            });
                            modal.dispatchEvent(escapeEvent);
                            results.closed = true;
                            results.methods.push('escape-key');
                            results.elementsFound.push({
                                type: 'modal',
                                selector: selector,
                                method: 'escape'
                            });
                            return results;
                        }
                    }
                } catch (e) {
                    // Continue to next selector
                }
            }
            
            // Strategy 3: Click on backdrop/overlay to close (common pattern)
            const backdropSelectors = [
                '[class*="backdrop"]',
                '[class*="Backdrop"]',
                '[class*="overlay"]',
                '[class*="Overlay"]',
                '[class*="modal-backdrop"]',
            ];
            
            for (const selector of backdropSelectors) {
                try {
                    const backdrops = Array.from(document.querySelectorAll(selector));
                    for (const backdrop of backdrops) {
                        const rect = backdrop.getBoundingClientRect();
                        const style = window.getComputedStyle(backdrop);
                        // Check if backdrop is visible and covers screen
                        if (rect.width > window.innerWidth * 0.8 &&
                            rect.height > window.innerHeight * 0.8 &&
                            backdrop.offsetParent !== null &&
                            style.display !== 'none') {
                            
                            // Click on backdrop (usually closes modal)
                            backdrop.click();
                            backdrop.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                            results.closed = true;
                            results.methods.push('backdrop-click');
                            results.elementsFound.push({
                                type: 'backdrop',
                                selector: selector
                            });
                            return results;
                        }
                    }
                } catch (e) {
                    // Continue
                }
            }
            
            // Strategy 4: Look for elements with "Grok 4.1" or similar announcement text
            // (Based on the popup shown in the image)
            const allElements = Array.from(document.querySelectorAll('*'));
            for (const el of allElements) {
                const text = (el.innerText || el.textContent || '').trim();
                // Look for announcement/promo text
                if (text.includes('Introducing Grok') ||
                    text.includes('Grok 4.1') ||
                    text.includes('Try Now') ||
                    (text.includes('Read full announcement') && text.length < 200)) {
                    
                    // Find parent modal/container
                    let container = el.parentElement;
                    let depth = 0;
                    while (container && depth < 10) {
                        const containerClass = container.className || '';
                        const containerRect = container.getBoundingClientRect();
                        
                        // Check if this looks like a popup container
                        if ((containerClass.includes('modal') ||
                             containerClass.includes('popup') ||
                             containerClass.includes('dialog') ||
                             containerRect.width > 300) &&
                            containerRect.width > 200 && containerRect.height > 200) {
                            
                            // Look for close button in this container
                            const closeBtn = container.querySelector('button[aria-label*="close" i], [class*="close"], svg[aria-label*="close" i]');
                            if (closeBtn) {
                                closeBtn.click();
                                closeBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                results.closed = true;
                                results.methods.push('announcement-close');
                                results.elementsFound.push({
                                    type: 'announcement',
                                    text: text.substring(0, 50)
                                });
                                return results;
                            }
                            
                            // Try Escape key
                            const escapeEvent = new KeyboardEvent('keydown', {
                                key: 'Escape',
                                code: 'Escape',
                                keyCode: 27,
                                bubbles: true,
                                cancelable: true
                            });
                            container.dispatchEvent(escapeEvent);
                            results.closed = true;
                            results.methods.push('announcement-escape');
                            return results;
                        }
                        container = container.parentElement;
                        depth++;
                    }
                }
            }
            
            return results;
        }
    """


def wait_and_close_popups_js() -> str:
    """
    JavaScript to wait for popups to appear and then close them.
    Useful when popups appear after a delay.
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            const maxWait = 2000; // 2 seconds
            const checkInterval = 100; // Check every 100ms
            let elapsed = 0;
            
            while (elapsed < maxWait) {
                const result = (function() {
                    // Use the same logic as close_popups_js
                    const closeButtonSelectors = [
                        'button[aria-label*="close" i]',
                        'button[aria-label*="Close" i]',
                        '[class*="close-button"]',
                        'svg[aria-label*="close" i]',
                    ];
                    
                    for (const selector of closeButtonSelectors) {
                        const buttons = Array.from(document.querySelectorAll(selector));
                        for (const btn of buttons) {
                            const rect = btn.getBoundingClientRect();
                            const style = window.getComputedStyle(btn);
                            if (rect.width > 0 && rect.height > 0 && 
                                btn.offsetParent !== null &&
                                style.display !== 'none' &&
                                rect.top < 100 && rect.left > window.innerWidth - 150) {
                                
                                btn.click();
                                return { closed: true, method: 'close-button' };
                            }
                        }
                    }
                    
                    // Check for modals
                    const modals = Array.from(document.querySelectorAll('[role="dialog"], dialog, [class*="modal"], [class*="popup"]'));
                    for (const modal of modals) {
                        const rect = modal.getBoundingClientRect();
                        if (rect.width > 200 && rect.height > 200) {
                            const closeBtn = modal.querySelector('button[aria-label*="close" i], [class*="close"]');
                            if (closeBtn) {
                                closeBtn.click();
                                return { closed: true, method: 'modal-close' };
                            }
                        }
                    }
                    
                    return { closed: false };
                })();
                
                if (result.closed) {
                    return result;
                }
                
                elapsed += checkInterval;
                // Note: Actual waiting will be done in Python with time.sleep()
            }
            
            return { closed: false, timeout: true };
        }
    """

