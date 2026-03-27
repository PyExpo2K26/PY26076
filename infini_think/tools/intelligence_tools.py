"""
infini_think.tools.intelligence_tools
======================================
High-level AI-driven tools for document and text intelligence.

These tools leverage the local LLM to perform cognitive tasks like 
summarization and data extraction.
"""

from __future__ import annotations

from pathlib import Path
from infini_think.core.ai_engine import AIEngine
from infini_think.tools.file_tools import read_file
from infini_think.utils.logger import get_logger

log = get_logger(__name__)

def summarize_content(text_or_path: str, *args) -> str:
    """Provide a concise summary of a text string or a file's content.

    Args:
        text_or_path: Raw text to summarize, or a path to a file (txt, pdf, docx).
        *args: Extra arguments (ignored).

    Returns:
        A human-readable summary or an error message.
    """
    content = ""
    # Check if it's a file path
    if len(text_or_path) < 255 and ("/" in text_or_path or "\\" in text_or_path or "." in text_or_path):
        log.info("Summarizing file: %s", text_or_path)
        content = read_file(text_or_path)
        if content.startswith("File not found") or content.startswith("Path is not a file"):
            # If read_file fails, maybe it IS just text? Let's check if file exists
            if not Path(text_or_path).exists():
                content = text_or_path
    else:
        content = text_or_path

    if not content.strip():
        return "Nothing to summarize."

    engine = AIEngine()
    prompt = f"Please provide a concise, high-level summary of the following content:\n\n{content}"
    
    try:
        summary = engine.generate(
            prompt, 
            system="You are a helpful assistant that summarizes documents clearly and accurately.",
            temperature=0.3
        )
        return f"Summary:\n\n{summary}"
    except Exception as exc:
        log.error("Summarization failed: %s", exc)
        return f"Failed to summarize: {exc}"


def extract_data(text_or_path: str, query: str, *args) -> str:
    """Extract specific information from a text string or a file.

    Args:
        text_or_path: Raw text or file path to analyze.
        query: What information to look for (e.g. "total amount", "due date").
        *args: Extra arguments (ignored).

    Returns:
        The extracted information or an error message.
    """
    content = ""
    if len(text_or_path) < 255 and ("/" in text_or_path or "\\" in text_or_path or "." in text_or_path):
        content = read_file(text_or_path)
        if content.startswith("File not found"):
            content = text_or_path
    else:
        content = text_or_path

    if not content.strip():
        return "Nothing to analyze."

    engine = AIEngine()
    prompt = f"From the following content, extract the specific information requested: '{query}'\n\nContent:\n{content}"
    
    try:
        answer = engine.generate(
            prompt,
            system="You are an expert data extractor. Provide only the requested information.",
            temperature=0.1
        )
        return f"Extracted '{query}': {answer}"
    except Exception as exc:
        log.error("Extraction failed: %s", exc)
        return f"Failed to extract info: {exc}"


def summarize_active_window(*args, **kwargs) -> str:
    """Read the content of the currently focused window and provide a summary.
    """
    from infini_think.tools.window_tools import analyze_active_window
    
    log.info("Summarizing active window")
    
    # 1. Get window content
    content = analyze_active_window()
    if content.startswith("Error") or "no readable text" in content:
        return content

    # 2. Summarize via AI
    engine = AIEngine()
    prompt = (
        "You are an expert at analyzing computer screens. Based on the following "
        "list of UI elements (names and values) from the active window, provide a "
        "one or two sentence summary of what the user is doing or looking at.\n\n"
        f"UI Content:\n{content}"
    )
    
    try:
        summary = engine.generate(
            prompt,
            system="You are a helpful desktop assistant. Be concise and accurate.",
            temperature=0.3
        )
        return f"Summary of the active window:\n\n{summary}"
    except Exception as exc:
        log.error("Window summarization failed: %s", exc)
        return f"Failed to summarize window: {exc}"
