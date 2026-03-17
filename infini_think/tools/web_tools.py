"""
infini_think.tools.web_tools
==============================
Browser automation tools for deeply interacting with websites.
"""

from __future__ import annotations

import time
from playwright.sync_api import sync_playwright, Page, BrowserContext
from infini_think.utils.logger import get_logger

log = get_logger(__name__)

# We must not share the sync_playwright instance across QThreads!
# Each tool call by the AI engine happens in a new or different thread.
# Therefore, we open and close a fresh playwright instance or maintain a thread-local one.
import threading

_thread_local = threading.local()

def _get_page() -> Page:
    """Ensure a browser session is running for the current thread and return the active page."""
    
    # Check if this thread already has a running playwright/page
    if not hasattr(_thread_local, "playwright"):
        _thread_local.playwright = sync_playwright().start()
        
    if not hasattr(_thread_local, "page") or _thread_local.page.is_closed():
        import os
        user_data_dir = os.path.join(os.path.expanduser("~"), ".infini_think", "chrome_data")
        os.makedirs(user_data_dir, exist_ok=True)
        
        try:
            context = _thread_local.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"]
            )
        except Exception:
            context = _thread_local.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
        _thread_local.page = context.pages[0] if context.pages else context.new_page()
        
    return _thread_local.page


def web_navigate(url: str) -> str:
    """Navigate to a URL in the automated browser.
    
    Args:
        url: The website URL to visit.
        
    Returns:
        Result string.
    """
    if not url.startswith("http"):
        url = "https://" + url
        
    try:
        page = _get_page()
        page.bring_to_front()
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        return f"Navigated to {page.url}. Page title: '{page.title()}'"
    except Exception as exc:
        log.error("Failed to navigate: %s", exc)
        return f"Failed to open '{url}': {exc}"


def web_extract_text() -> str:
    """Extract all text from the currently open webpage in the automated browser.
    
    Returns:
        Extracted raw text, truncated to avoid context limits.
    """
    try:
        page = _get_page()
        if page.url == "about:blank":
            return "No webpage is currently open in the automated browser."
            
        # Get readable inner text of the body
        text = page.locator("body").inner_text()
        
        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)
        
        if len(text) > 10000:
            text = text[:10000] + "\n\n... (content truncated for context window limits)"
            
        return f"--- Content of {page.title()} ({page.url}) ---\n\n{text}"
    except Exception as exc:
        return f"Failed to extract text: {exc}"


def web_fill_and_submit(url: str, element_description: str, text: str) -> str:
    """Navigate to a URL (if not already there), find an input box matching a description, fill it, and press Enter.
    
    Args:
        url: URL of the website.
        element_description: CSS selector, or generalized name like "Search bar" or "Message input box".
        text: The text to type into the box.
        
    Returns:
        Status describing the action.
    """
    try:
        page = _get_page()
        
        # Navigate if needed
        if not url.startswith("http"):
            url = "https://" + url
            
        # Simple domain matching
        from urllib.parse import urlparse
        target_domain = urlparse(url).netloc
        current_domain = urlparse(page.url).netloc
        
        if target_domain and target_domain not in current_domain:
            web_navigate(url)
            time.sleep(1) # wait for render
            
        page.bring_to_front()
        
        # Specific robust selectors for notoriously difficult LLM/SPA sites
        site_specific_selectors = []
        if "gemini.google.com" in current_domain:
            site_specific_selectors = [page.locator("rich-textarea"), page.locator(".ql-editor"), page.get_by_role("textbox", name="Enter a prompt here")]
        elif "chatgpt.com" in current_domain or "chat.openai.com" in current_domain:
            site_specific_selectors = [page.locator("#prompt-textarea")]
        elif "youtube.com" in current_domain:
            site_specific_selectors = [page.locator("input#search"), page.get_by_role("combobox", name="Search")]
            
        # We try to use Playwright's get_by_role, get_by_placeholder, and specific CSS heuristics
        locators_to_try = site_specific_selectors + [
            # High precision if they passed a real selector
            page.locator(element_description),
            # General text box fallbacks
            page.get_by_placeholder(element_description, exact=False),
            page.get_by_role("textbox", name=element_description),
            page.get_by_role("searchbox"),
            # Broad fallbacks for SPAs
            page.locator("textarea").last,  # Often the main chat input is the last textarea on the page
            page.locator("input[type='text'], input[type='search']").first,
            page.locator("[contenteditable='true']").last, # Rich text editors (like old Gemini UI)
        ]
        
        found_locator = None
        for loc in locators_to_try:
            try:
                # check if it exists and is visible
                count = loc.count()
                for i in range(count):
                    if loc.nth(i).is_visible():
                        found_locator = loc.nth(i)
                        break
                if found_locator:
                    break
            except Exception:
                continue
                
        if found_locator:
            found_locator.fill(text)
            found_locator.press("Enter")
            # Wait for potential results to render
            time.sleep(2)
            return f"Successfully typed '{text}' and submitted on '{page.url}'."
        else:
            return f"Could not find an input box matching '{element_description}' on {page.url}. The website structure might be too complex."
            
    except Exception as exc:
        return f"Failed to fill and submit on '{url}': {exc}"
