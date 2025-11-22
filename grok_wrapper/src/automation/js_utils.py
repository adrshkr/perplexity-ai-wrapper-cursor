"""
JavaScript utilities for browser automation
Contains reusable JavaScript code snippets for Playwright page.evaluate()
"""


def find_deepsearch_button_js() -> str:
    """
    JavaScript code to find and click the DeepSearch button.
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            // Search the entire document - DeepSearch button has data-slot="button" and text "DeepSearch"
            const searchArea = document.body;
            
            // Strategy 0: Search for buttons below the chat input (leftmost button below chat box)
            // First, try to find buttons in a toolbar/footer area below the main input
            const mainInput = document.querySelector('textarea[aria-label*="Ask"], textarea, input[type="text"]');
            let searchContainer = document.body;
            
            if (mainInput) {
                // Find the container that holds buttons below the input
                let container = mainInput.closest('form, div[class*="input"], div[class*="chat"], main, [role="main"]');
                if (container) {
                    // Look for sibling containers or parent containers that might have buttons
                    let parent = container.parentElement;
                    while (parent && parent !== document.body) {
                        const buttons = parent.querySelectorAll('button');
                        if (buttons.length > 0) {
                            searchContainer = parent;
                            break;
                        }
                        parent = parent.parentElement;
                    }
                }
            }
            
            // Now search for DeepSearch button in the relevant area
            const buttonsInArea = Array.from(searchContainer.querySelectorAll('button, [role="button"], [data-slot="button"]'));
            
            // Sort by position (leftmost = smallest x)
            const buttonsWithPos = buttonsInArea.map(btn => {
                const rect = btn.getBoundingClientRect();
                const text = (btn.innerText || btn.textContent || '').trim();
                return { button: btn, text: text, x: rect.x, y: rect.y, rect: rect };
            }).filter(b => {
                const style = window.getComputedStyle(b.button);
                return b.rect.width > 0 && b.rect.height > 0 && style.display !== 'none';
            });
            
            // Look for DeepSearch button
            for (const btnInfo of buttonsWithPos) {
                const text = btnInfo.text;
                if (text === 'DeepSearch' || text.toLowerCase() === 'deepsearch') {
                    const btn = btnInfo.button;
                    btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                    btn.click();
                    btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    btn.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerId: 1 }));
                    btn.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true, pointerId: 1 }));
                    return { clicked: true, text: text, method: 'below-chat-box', x: btnInfo.x, y: btnInfo.y };
                }
            }
            
            // Fallback: Search ALL elements for text "DeepSearch" (most aggressive)
            const allElements = Array.from(searchArea.querySelectorAll('*'));
            for (const el of allElements) {
                const text = (el.innerText || el.textContent || '').trim();
                if (text === 'DeepSearch' || text.toLowerCase() === 'deepsearch') {
                    // Found element with DeepSearch text - try to click it
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    const isInDOM = el.offsetParent !== null || style.display !== 'none';
                    
                    if (isInDOM) {
                        el.scrollIntoView({ behavior: 'instant', block: 'center' });
                        
                        // Try clicking the element or find its parent button
                        let clickTarget = el;
                        if (el.tagName !== 'BUTTON' && el.tagName !== 'A') {
                            // If it's not a button, find the nearest button parent
                            let parent = el.parentElement;
                            while (parent && parent !== document.body) {
                                if (parent.tagName === 'BUTTON' || parent.tagName === 'A' || parent.getAttribute('role') === 'button') {
                                    clickTarget = parent;
                                    break;
                                }
                                parent = parent.parentElement;
                            }
                        }
                        
                        clickTarget.click();
                        clickTarget.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                        clickTarget.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerId: 1 }));
                        clickTarget.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true, pointerId: 1 }));
                        return { clicked: true, text: text, method: 'text-search-all', tag: el.tagName, clickTarget: clickTarget.tagName };
                    }
                }
            }
            
            // Strategy 1: Look for button[data-slot="button"] with text "DeepSearch" (exact match)
            // Check both visible and potentially hidden buttons (they might be off-screen)
            const dataSlotBtns = Array.from(searchArea.querySelectorAll('button[data-slot="button"]'));
            for (const button of dataSlotBtns) {
                const text = (button.innerText || button.textContent || '').trim();
                if (text === 'DeepSearch' || text.toLowerCase() === 'deepsearch') {
                    // Check if button exists (even if not visible)
                    const rect = button.getBoundingClientRect();
                    const style = window.getComputedStyle(button);
                    const isInDOM = button.offsetParent !== null || style.display !== 'none';
                    
                    // Try to make it visible by scrolling
                    if (isInDOM) {
                        button.scrollIntoView({ behavior: 'instant', block: 'center' });
                        
                        // Check visibility again after scroll
                        const rectAfter = button.getBoundingClientRect();
                        const isVisible = rectAfter.width > 0 && rectAfter.height > 0 && 
                                         !button.hasAttribute('hidden') &&
                                         style.display !== 'none' &&
                                         style.visibility !== 'hidden';
                        
                        if (isVisible || isInDOM) {  // Try clicking even if not fully visible
                            button.click();
                            button.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                            button.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerId: 1 }));
                            button.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true, pointerId: 1 }));
                            return { clicked: true, text: text, method: 'data-slot-exact', visible: isVisible };
                        }
                    }
                }
            }
            
            // Strategy 2: Find all buttons and check text content
            const allButtons = Array.from(searchArea.querySelectorAll('button'));
            
            // Look for DeepSearch button - case insensitive and check all text
            for (const button of allButtons) {
                // Get all text from button and its children
                const text = (button.innerText || button.textContent || '').trim();
                const lowerText = text.toLowerCase();
                
                // Check aria-label and title attributes
                const ariaLabel = (button.getAttribute('aria-label') || '').toLowerCase();
                const title = (button.getAttribute('title') || '').toLowerCase();
                const id = (button.id || '').toLowerCase();
                const testId = (button.getAttribute('data-testid') || '').toLowerCase();
                
                // Check for DeepSearch (case insensitive) or variations
                if (lowerText.includes('deepsearch') || 
                    lowerText.includes('deep search') ||
                    lowerText === 'deepsearch' ||
                    text === 'DeepSearch' ||
                    ariaLabel.includes('deepsearch') ||
                    ariaLabel.includes('deep search') ||
                    title.includes('deepsearch') ||
                    title.includes('deep search') ||
                    id.includes('deepsearch') ||
                    testId.includes('deepsearch')) {
                    
                    // Make sure button is visible
                    const rect = button.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0 && 
                                     button.offsetParent !== null && 
                                     !button.hasAttribute('hidden') &&
                                     window.getComputedStyle(button).display !== 'none';
                    
                    if (!isVisible) {
                        continue; // Skip hidden buttons
                    }
                    
                    // Scroll into view if needed
                    button.scrollIntoView({ behavior: 'instant', block: 'center' });
                    
                    // Try multiple click methods
                    button.click();
                    // Also dispatch events to ensure it's registered
                    button.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    button.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerId: 1 }));
                    button.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true, pointerId: 1 }));
                    
                    return { clicked: true, text: text, ariaLabel: button.getAttribute('aria-label'), visible: isVisible, method: 'text-match' };
                }
            }
            
            // Debug: return info about ALL buttons found (more details) - including those with empty text
            // Focus on buttons with data-slot="button" first
            const dataSlotBtnsForDebug = Array.from(searchArea.querySelectorAll('button[data-slot="button"]'));
            const allButtonInfo = dataSlotBtnsForDebug.slice(0, 20).map(b => {
                const txt = (b.innerText || b.textContent || '').trim();
                const aria = b.getAttribute('aria-label') || '';
                const title = b.getAttribute('title') || '';
                const id = b.id || '';
                const className = b.className || '';
                const dataSlot = b.getAttribute('data-slot') || '';
                const dataTestId = b.getAttribute('data-testid') || '';
                return { 
                    text: txt, 
                    ariaLabel: aria, 
                    title: title, 
                    tag: b.tagName,
                    id: id,
                    className: className.substring(0, 50), // First 50 chars
                    dataSlot: dataSlot,
                    dataTestId: dataTestId
                };
            });
            
            // Also include regular buttons for debugging
            const regularButtons = Array.from(searchArea.querySelectorAll('button')).slice(0, 10).map(b => {
                const txt = (b.innerText || b.textContent || '').trim();
                const aria = b.getAttribute('aria-label') || '';
                const dataSlot = b.getAttribute('data-slot') || '';
                return { 
                    text: txt, 
                    ariaLabel: aria, 
                    dataSlot: dataSlot,
                    tag: b.tagName
                };
            }).filter(b => b.text.length > 0 || b.ariaLabel.length > 0);
            
            return { clicked: false, found: allButtons.length, dataSlotButtons: dataSlotBtnsForDebug.length, sampleButtons: allButtonInfo, regularButtons: regularButtons };
        }
    """


def find_deepsearch_button_simple_js() -> str:
    """
    Simplified JavaScript to find DeepSearch button by text.
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            // Find all buttons with "DeepSearch" text
            const buttons = Array.from(document.querySelectorAll('button'));
            for (const btn of buttons) {
                const text = (btn.innerText || btn.textContent || '').trim();
                if (text === 'DeepSearch' || text.toLowerCase() === 'deepsearch') {
                    // Check if it's visible
                    const rect = btn.getBoundingClientRect();
                    const style = window.getComputedStyle(btn);
                    if (rect.width > 0 && rect.height > 0 && style.display !== 'none') {
                        return { found: true, text: text, x: rect.x, y: rect.y };
                    }
                }
            }
            return { found: false };
        }
    """


def verify_deepsearch_enabled_js() -> str:
    """
    JavaScript to verify DeepSearch is enabled by checking for success indicators.
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            // Check for Memo component with DeepSearch text (success indicator)
            const memoElements = Array.from(document.querySelectorAll('*'));
            for (const el of memoElements) {
                const text = (el.innerText || el.textContent || '').trim();
                // Check if it's a Memo component (React component, might have workspaceId prop)
                if (text === 'DeepSearch') {
                    // Check if parent has workspaceId attribute or is a Memo-like component
                    const parent = el.parentElement;
                    if (parent) {
                        const parentText = (parent.innerText || parent.textContent || '').trim();
                        // Look for the chip/div indicator
                        if (parent.classList && (
                            parent.classList.contains('chip') || 
                            parent.className.includes('bg-chip') ||
                            parent.className.includes('text-primary')
                        )) {
                            return { enabled: true, indicator: 'chip-div', element: 'div' };
                        }
                    }
                }
            }
            
            // Check for div with DeepSearch text and chip styling
            const divs = Array.from(document.querySelectorAll('div'));
            for (const div of divs) {
                const text = (div.innerText || div.textContent || '').trim();
                if (text === 'DeepSearch') {
                    const className = div.className || '';
                    // Check for chip styling indicators
                    if (className.includes('bg-chip') || 
                        className.includes('text-primary') || 
                        className.includes('border-border-l1')) {
                        return { enabled: true, indicator: 'chip-div', element: 'div' };
                    }
                }
            }
            
            // Fallback: check if any element contains DeepSearch in a chip-like container
            const allElements = Array.from(document.querySelectorAll('*'));
            for (const el of allElements) {
                const text = (el.innerText || el.textContent || '').trim();
                if (text === 'DeepSearch') {
                    // Check if it's in a styled container (chip-like)
                    let parent = el.parentElement;
                    let depth = 0;
                    while (parent && depth < 3) {
                        const parentClass = parent.className || '';
                        if (parentClass.includes('chip') || 
                            parentClass.includes('bg-chip') ||
                            parentClass.includes('rounded-xl')) {
                            return { enabled: true, indicator: 'parent-chip', element: parent.tagName };
                        }
                        parent = parent.parentElement;
                        depth++;
                    }
                }
            }
            
            return { enabled: false };
        }
    """


def find_deepsearch_button_exact_js() -> str:
    """
    JavaScript to find DeepSearch button using exact selector: button[data-slot="button"] with text "DeepSearch"
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            // Exact match: button[data-slot="button"] with text "DeepSearch"
            const exactButtons = Array.from(document.querySelectorAll('button[data-slot="button"]'));
            
            for (const btn of exactButtons) {
                const text = (btn.innerText || btn.textContent || '').trim();
                if (text === 'DeepSearch' || text.toLowerCase() === 'deepsearch') {
                    const rect = btn.getBoundingClientRect();
                    const style = window.getComputedStyle(btn);
                    const isVisible = rect.width > 0 && rect.height > 0 && 
                                     btn.offsetParent !== null &&
                                     style.display !== 'none' &&
                                     style.visibility !== 'hidden';
                    
                    if (isVisible) {
                        // Scroll into view
                        btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                        
                        // Get button details for logging
                        const className = btn.className || '';
                        const dataSlot = btn.getAttribute('data-slot') || '';
                        
                        return { 
                            found: true, 
                            text: text, 
                            x: rect.x, 
                            y: rect.y,
                            width: rect.width,
                            height: rect.height,
                            className: className.substring(0, 100),
                            dataSlot: dataSlot,
                            isVisible: isVisible
                        };
                    }
                }
            }
            
            // Return debug info
            return { 
                found: false, 
                totalDataSlotButtons: exactButtons.length,
                buttons: exactButtons.slice(0, 10).map(b => ({
                    text: (b.innerText || b.textContent || '').trim(),
                    dataSlot: b.getAttribute('data-slot'),
                    className: (b.className || '').substring(0, 50)
                }))
            };
        }
    """


def find_private_button_js() -> str:
    """
    JavaScript to find the Private chat toggle button/link.
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            // Look for Private button/link by aria-label
            const privateSelectors = [
                'a[aria-label*="Switch to Private Chat" i]',
                'a[aria-label*="Switch to Default Chat" i]',
                'button[aria-label*="Switch to Private Chat" i]',
                'button[aria-label*="Switch to Default Chat" i]',
                'a[href*="#private"]',
            ];
            
            for (const selector of privateSelectors) {
                try {
                    const elements = Array.from(document.querySelectorAll(selector));
                    for (const el of elements) {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text === 'Private' || text.toLowerCase() === 'private') {
                            const rect = el.getBoundingClientRect();
                            const style = window.getComputedStyle(el);
                            const isVisible = rect.width > 0 && rect.height > 0 && 
                                             el.offsetParent !== null &&
                                             style.display !== 'none' &&
                                             style.visibility !== 'hidden';
                            
                            if (isVisible) {
                                const ariaLabel = el.getAttribute('aria-label') || '';
                                const className = el.className || '';
                                const href = el.getAttribute('href') || '';
                                
                                // Check if already in private mode (has purple color classes)
                                const isPrivate = className.includes('text-purple-400') || 
                                                 className.includes('text-purple-300') ||
                                                 ariaLabel.includes('Switch to Default Chat');
                                
                                return {
                                    found: true,
                                    element: el.tagName,
                                    text: text,
                                    ariaLabel: ariaLabel,
                                    href: href,
                                    className: className.substring(0, 100),
                                    isPrivate: isPrivate,
                                    x: rect.x,
                                    y: rect.y,
                                    visible: isVisible
                                };
                            }
                        }
                    }
                } catch (e) {
                    // Continue to next selector
                }
            }
            
            // Fallback: search by text "Private"
            const allElements = Array.from(document.querySelectorAll('a, button'));
            for (const el of allElements) {
                const text = (el.innerText || el.textContent || '').trim();
                if (text === 'Private' || text.toLowerCase() === 'private') {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    const isVisible = rect.width > 0 && rect.height > 0 && 
                                     el.offsetParent !== null &&
                                     style.display !== 'none';
                    
                    if (isVisible) {
                        const ariaLabel = el.getAttribute('aria-label') || '';
                        const className = el.className || '';
                        const isPrivate = className.includes('text-purple-400') || 
                                       className.includes('text-purple-300') ||
                                       ariaLabel.includes('Switch to Default Chat');
                        
                        return {
                            found: true,
                            element: el.tagName,
                            text: text,
                            ariaLabel: ariaLabel,
                            className: className.substring(0, 100),
                            isPrivate: isPrivate,
                            x: rect.x,
                            y: rect.y,
                            visible: isVisible
                        };
                    }
                }
            }
            
            return { found: false };
        }
    """


def verify_private_mode_js() -> str:
    """
    JavaScript to verify if Private mode is currently active.
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            // Look for Private button and check its state
            const privateSelectors = [
                'a[aria-label*="Private Chat" i], a[aria-label*="Default Chat" i]',
                'button[aria-label*="Private Chat" i], button[aria-label*="Default Chat" i]',
            ];
            
            for (const selector of privateSelectors) {
                try {
                    const elements = Array.from(document.querySelectorAll(selector));
                    for (const el of elements) {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text === 'Private' || text.toLowerCase() === 'private') {
                            const ariaLabel = el.getAttribute('aria-label') || '';
                            const className = el.className || '';
                            
                            // Private mode is active if:
                            // 1. Has purple color classes
                            // 2. aria-label says "Switch to Default Chat" (meaning we're in private, can switch to default)
                            const isPrivate = className.includes('text-purple-400') || 
                                           className.includes('text-purple-300') ||
                                           ariaLabel.includes('Switch to Default Chat');
                            
                            return {
                                found: true,
                                isPrivate: isPrivate,
                                ariaLabel: ariaLabel,
                                className: className.substring(0, 100)
                            };
                        }
                    }
                } catch (e) {
                    // Continue
                }
            }
            
            // Fallback: search by text
            const allElements = Array.from(document.querySelectorAll('a, button'));
            for (const el of allElements) {
                const text = (el.innerText || el.textContent || '').trim();
                if (text === 'Private' || text.toLowerCase() === 'private') {
                    const ariaLabel = el.getAttribute('aria-label') || '';
                    const className = el.className || '';
                    const isPrivate = className.includes('text-purple-400') || 
                                   className.includes('text-purple-300') ||
                                   ariaLabel.includes('Switch to Default Chat');
                    
                    return {
                        found: true,
                        isPrivate: isPrivate,
                        ariaLabel: ariaLabel,
                        className: className.substring(0, 100)
                    };
                }
            }
            
            return { found: false, isPrivate: false };
        }
    """


def find_private_button_js() -> str:
    """
    JavaScript to find the Private chat toggle button/link.
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            // Look for Private button/link by aria-label
            const privateSelectors = [
                'a[aria-label*="Switch to Private Chat" i]',
                'a[aria-label*="Switch to Default Chat" i]',
                'button[aria-label*="Switch to Private Chat" i]',
                'button[aria-label*="Switch to Default Chat" i]',
                'a[href*="#private"]',
                'a:has-text("Private")',
                'button:has-text("Private")',
            ];
            
            for (const selector of privateSelectors) {
                try {
                    const elements = Array.from(document.querySelectorAll(selector));
                    for (const el of elements) {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text === 'Private' || text.toLowerCase() === 'private') {
                            const rect = el.getBoundingClientRect();
                            const style = window.getComputedStyle(el);
                            const isVisible = rect.width > 0 && rect.height > 0 && 
                                             el.offsetParent !== null &&
                                             style.display !== 'none' &&
                                             style.visibility !== 'hidden';
                            
                            if (isVisible) {
                                const ariaLabel = el.getAttribute('aria-label') || '';
                                const className = el.className || '';
                                const href = el.getAttribute('href') || '';
                                
                                // Check if already in private mode (has purple color classes)
                                const isPrivate = className.includes('text-purple-400') || 
                                                 className.includes('text-purple-300') ||
                                                 ariaLabel.includes('Switch to Default Chat');
                                
                                return {
                                    found: true,
                                    element: el.tagName,
                                    text: text,
                                    ariaLabel: ariaLabel,
                                    href: href,
                                    className: className.substring(0, 100),
                                    isPrivate: isPrivate,
                                    x: rect.x,
                                    y: rect.y,
                                    visible: isVisible
                                };
                            }
                        }
                    }
                } catch (e) {
                    // Continue to next selector
                }
            }
            
            return { found: false };
        }
    """


def verify_private_mode_js() -> str:
    """
    JavaScript to verify if Private mode is currently active.
    
    Returns:
        JavaScript code as string for use with page.evaluate()
    """
    return """
        () => {
            // Look for Private button and check its state
            const privateSelectors = [
                'a[aria-label*="Private Chat" i], a[aria-label*="Default Chat" i]',
                'button[aria-label*="Private Chat" i], button[aria-label*="Default Chat" i]',
                'a:has-text("Private"), button:has-text("Private")',
            ];
            
            for (const selector of privateSelectors) {
                try {
                    const elements = Array.from(document.querySelectorAll(selector));
                    for (const el of elements) {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text === 'Private' || text.toLowerCase() === 'private') {
                            const ariaLabel = el.getAttribute('aria-label') || '';
                            const className = el.className || '';
                            
                            // Private mode is active if:
                            // 1. Has purple color classes
                            // 2. aria-label says "Switch to Default Chat" (meaning we're in private, can switch to default)
                            const isPrivate = className.includes('text-purple-400') || 
                                           className.includes('text-purple-300') ||
                                           ariaLabel.includes('Switch to Default Chat');
                            
                            return {
                                found: true,
                                isPrivate: isPrivate,
                                ariaLabel: ariaLabel,
                                className: className.substring(0, 100)
                            };
                        }
                    }
                } catch (e) {
                    // Continue
                }
            }
            
            return { found: false, isPrivate: false };
        }
    """
