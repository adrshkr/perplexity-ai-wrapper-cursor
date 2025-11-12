#!/usr/bin/env python3
"""
Fix for export_as_markdown function in PerplexityWebDriver
This provides a more robust export mechanism with multiple fallback strategies.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)


def export_as_markdown_fixed(
    page: "Page", output_dir: Optional[Union[str, Path]] = None
) -> Optional[Path]:
    """
    Fixed export_as_markdown function with robust menu detection and fallback approaches.

    Args:
        page: Playwright page instance
        output_dir: Directory to save the markdown file

    Returns:
        Path to exported file or None if failed
    """
    if not page:
        raise Exception("Page not provided")

    logger.info("Starting export with improved detection...")

    # Ensure page is active
    try:
        page.bring_to_front()
        page.wait_for_timeout(1000)
    except Exception:
        pass

    # Setup output directory
    output_dir = Path(output_dir) if output_dir else Path.cwd() / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"perplexity_thread_{timestamp}.md"
    export_path = output_dir / filename

    # Strategy 1: Try to find and click thread actions button with improved detection
    try:
        logger.debug("Strategy 1: Looking for thread actions button...")

        # Wait for page to settle after search completion
        page.wait_for_timeout(2000)

        # Multiple selectors for thread actions button
        button_selectors = [
            'button[aria-label="Thread actions"]',
            'button[title="Thread actions"]',
            'button:has-text("Thread actions")',
            '[data-testid="thread-actions"]',
            'button:has([aria-label*="more"])',
            'button:has([aria-label*="options"])',
            'button[aria-label*="menu"]',
        ]

        thread_button = None
        for selector in button_selectors:
            try:
                buttons = page.query_selector_all(selector)
                for btn in buttons:
                    if btn.is_visible():
                        thread_button = btn
                        logger.debug(
                            f"Found thread actions button with selector: {selector}"
                        )
                        break
                if thread_button:
                    break
            except Exception:
                continue

        if thread_button:
            # Click the button
            thread_button.click()
            page.wait_for_timeout(1000)

            # Look for export options with multiple approaches
            export_selectors = [
                # Text-based selectors
                'button:has-text("Export as Markdown")',
                'button:has-text("Export Markdown")',
                'button:has-text("Download Markdown")',
                'a:has-text("Export as Markdown")',
                'a:has-text("Export Markdown")',
                '[role="menuitem"]:has-text("Export")',
                '[role="menuitem"]:has-text("Markdown")',
                # Attribute-based selectors
                '[data-testid*="export"]',
                '[data-testid*="markdown"]',
                '[aria-label*="export"]',
                '[aria-label*="markdown"]',
            ]

            export_element = None
            for selector in export_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for elem in elements:
                        if elem.is_visible():
                            text = elem.inner_text().lower()
                            if any(
                                word in text
                                for word in ["export", "markdown", "download"]
                            ):
                                export_element = elem
                                logger.debug(
                                    f"Found export element with selector: {selector}"
                                )
                                break
                    if export_element:
                        break
                except Exception:
                    continue

            if export_element:
                try:
                    with page.expect_download(timeout=30000) as download_info:
                        export_element.click()

                    download = download_info.value
                    download.save_as(export_path)
                    logger.info(f"Successfully exported via Strategy 1: {export_path}")
                    return export_path
                except Exception as e:
                    logger.debug(f"Download failed in Strategy 1: {e}")

    except Exception as e:
        logger.debug(f"Strategy 1 failed: {e}")

    # Strategy 2: Try keyboard shortcuts
    try:
        logger.debug("Strategy 2: Trying keyboard shortcuts...")

        # Close any open menus first
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        # Common export shortcuts
        shortcuts = ["Control+Shift+E", "Control+E", "Control+S", "Control+Shift+S"]

        for shortcut in shortcuts:
            try:
                page.keyboard.press(shortcut)
                page.wait_for_timeout(1000)

                # Check if download started
                with page.expect_download(timeout=3000) as download_info:
                    pass

                download = download_info.value
                if download.suggested_filename and ".md" in download.suggested_filename:
                    download.save_as(export_path)
                    logger.info(
                        f"Successfully exported via keyboard shortcut {shortcut}: {export_path}"
                    )
                    return export_path
            except Exception:
                continue

    except Exception as e:
        logger.debug(f"Strategy 2 failed: {e}")

    # Strategy 3: Manual content extraction and markdown creation
    try:
        logger.debug("Strategy 3: Manual content extraction...")

        # Extract conversation content
        content = page.evaluate("""
            () => {
                // Try to find the main conversation area
                const selectors = [
                    '[data-testid="conversation-messages"]',
                    '.conversation-content',
                    '[role="main"] .prose',
                    'main [data-testid*="answer"]',
                    'main .markdown',
                    'main article',
                    'main .thread-content'
                ];

                let container = null;
                for (const selector of selectors) {
                    const elem = document.querySelector(selector);
                    if (elem && elem.innerText && elem.innerText.length > 100) {
                        container = elem;
                        break;
                    }
                }

                // Fallback to main element
                if (!container) {
                    container = document.querySelector('main');
                }

                if (!container) {
                    return null;
                }

                // Extract text with basic formatting
                const extractText = (element) => {
                    let text = '';

                    for (const node of element.childNodes) {
                        if (node.nodeType === Node.TEXT_NODE) {
                            text += node.textContent;
                        } else if (node.nodeType === Node.ELEMENT_NODE) {
                            const tagName = node.tagName.toLowerCase();

                            if (tagName === 'br') {
                                text += '\\n';
                            } else if (tagName === 'p') {
                                text += extractText(node) + '\\n\\n';
                            } else if (tagName.match(/^h[1-6]$/)) {
                                const level = parseInt(tagName[1]);
                                const prefix = '#'.repeat(level);
                                text += prefix + ' ' + extractText(node) + '\\n\\n';
                            } else if (tagName === 'ul' || tagName === 'ol') {
                                text += extractText(node) + '\\n';
                            } else if (tagName === 'li') {
                                text += '- ' + extractText(node) + '\\n';
                            } else if (tagName === 'a') {
                                const href = node.getAttribute('href');
                                const linkText = extractText(node);
                                if (href && href.startsWith('http')) {
                                    text += `[${linkText}](${href})`;
                                } else {
                                    text += linkText;
                                }
                            } else if (tagName === 'strong' || tagName === 'b') {
                                text += '**' + extractText(node) + '**';
                            } else if (tagName === 'em' || tagName === 'i') {
                                text += '*' + extractText(node) + '*';
                            } else {
                                text += extractText(node);
                            }
                        }
                    }

                    return text;
                };

                const fullText = extractText(container);

                // Clean up the text
                return fullText
                    .replace(/\\n{3,}/g, '\\n\\n')  // Reduce multiple newlines
                    .replace(/\\s+$/, '')           // Remove trailing whitespace
                    .trim();
            }
        """)

        if content and len(content) > 200:
            # Create markdown content with header
            markdown_content = f"""# Perplexity Conversation Export

**Exported:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Source:** {page.url}

---

{content}
"""

            # Write to file
            with open(export_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            logger.info(f"Successfully exported via manual extraction: {export_path}")
            return export_path
        else:
            logger.warning("No substantial content found for manual extraction")

    except Exception as e:
        logger.error(f"Strategy 3 failed: {e}")

    # Strategy 4: Page screenshot as fallback
    try:
        logger.debug("Strategy 4: Creating screenshot as fallback...")

        screenshot_path = output_dir / f"perplexity_screenshot_{timestamp}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        logger.info(f"Created screenshot fallback: {screenshot_path}")

        # Also create a minimal markdown file with link to screenshot
        minimal_content = f"""# Perplexity Conversation Export (Screenshot)

**Exported:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Source:** {page.url}

*Note: Direct markdown export failed, screenshot saved as: {screenshot_path.name}*

---

Export failed - please check the screenshot for the conversation content.
"""

        with open(export_path, "w", encoding="utf-8") as f:
            f.write(minimal_content)

        logger.info(
            f"Created minimal markdown with screenshot reference: {export_path}"
        )
        return export_path

    except Exception as e:
        logger.error(f"Strategy 4 failed: {e}")

    # If all strategies fail
    logger.error("All export strategies failed")
    return None


def apply_export_fix(web_driver_instance):
    """
    Apply the fixed export function to a PerplexityWebDriver instance.

    Args:
        web_driver_instance: Instance of PerplexityWebDriver
    """

    def export_as_markdown_wrapper(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        page: Optional["Page"] = None,
    ) -> Optional[Path]:
        target_page = page or self.page
        if not target_page:
            raise Exception("Browser not started")

        return export_as_markdown_fixed(target_page, output_dir)

    # Replace the method
    web_driver_instance.export_as_markdown = export_as_markdown_wrapper.__get__(
        web_driver_instance, web_driver_instance.__class__
    )

    logger.info("Applied export fix to PerplexityWebDriver instance")


if __name__ == "__main__":
    # Test the fix independently
    print("Export fix module loaded successfully")
    print("Use apply_export_fix(driver_instance) to apply the fix")
