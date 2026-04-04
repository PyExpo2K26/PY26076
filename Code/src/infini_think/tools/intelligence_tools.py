"""
infini_think.tools.intelligence_tools
======================================
High-level AI-driven tools for document and text intelligence.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from infini_think.core.ai_engine import AIEngine
from infini_think.tools.file_tools import read_file, search_files
from infini_think.utils.logger import get_logger

log = get_logger(__name__)

def summarize_content(text_or_path: str, *args) -> str:
    """Provide a concise summary of a text string or a file's content.
    """
    content = ""
    # Check if it's a file path
    if len(text_or_path) < 255 and ("/" in text_or_path or "\\" in text_or_path or "." in text_or_path):
        log.info("Summarizing file: %s", text_or_path)
        content = read_file(text_or_path)
        if content.startswith("File not found") or content.startswith("Path is not a file"):
            if not Path(text_or_path).exists():
                content = text_or_path
    else:
        content = text_or_path

    if not content.strip():
        return "Nothing to summarize."

    engine = AIEngine()
    prompt = f"Please provide a concise summary of the following content:\n\n{content}"
    
    try:
        summary = engine.generate(
            prompt,
            system="You are an expert document summarizer.",
            temperature=0.3
        )
        return f"Summary:\n\n{summary}"
    except Exception as exc:
        return f"Failed to summarize: {exc}"


def extract_data(text_or_path: str, query: str, *args) -> str:
    """Extract specific information from a text string or a file.
    """
    content = ""
    if len(text_or_path) < 255 and (os.sep in text_or_path or "." in text_or_path):
        content = read_file(text_or_path)
        if content.startswith("File not found"):
            content = text_or_path
    else:
        content = text_or_path

    if not content.strip():
        return "Nothing to analyze."

    engine = AIEngine()
    prompt = f"From the following content, extract: '{query}'\n\nContent:\n{content}"
    
    try:
        answer = engine.generate(
            prompt,
            system="Provide only the extracted information.",
            temperature=0.1
        )
        return f"Extracted '{query}': {answer}"
    except Exception as exc:
        return f"Failed to extract info: {exc}"


def summarize_active_window(*args, **kwargs) -> str:
    """Read the content of the currently focused window and provide a summary.
    """
    from infini_think.tools.window_tools import analyze_active_window
    
    log.info("Summarizing active window")
    
    # 1. Get window content/title
    raw_window_data = analyze_active_window()
    if raw_window_data.startswith("Error"):
        return raw_window_data

    content = raw_window_data
    file_path_found = None
    
    # 2. Extract Path or Title-based filename
    # We look for a path or a title line like "Window Title: MyFile.pdf"
    lines = content.splitlines()
    window_title = ""
    for line in lines:
        if line.startswith("Window Title:"):
            window_title = line.replace("Window Title:", "").strip()
        if "URL/Path:" in line:
            raw_path = line.split("URL/Path:", 1)[1].strip()
            # Clean up URLs (file:///C:/...)
            if raw_path.startswith("file:///"):
                raw_path = raw_path[8:].replace("/", "\\").replace("%20", " ")
            file_path_found = raw_path
            break

    # 3. PROACTIVE DEEP SCAN: If no direct path, use the title to FIND the file
    if not file_path_found and window_title:
        # Extract filename (e.g. MyPaper.pdf) from possible browser titles (Privacy Assistant (5).pdf - Edge)
        match = re.search(r"([a-zA-Z0-9_\-\s%()]+\.(pdf|docx|txt|md|doc))", window_title, re.IGNORECASE)
        if match:
             fname = match.group(1).strip()
             log.info("System-wide search for potential file: %s", fname)
             # Search in typical folders (downloads, documents, home)
             results = search_files(fname)
             if "Found" in results:
                 # Extract the first matching path
                 paths = results.splitlines()[2:] # Skip "Found X files" header
                 if paths:
                     file_path_found = paths[0].strip()

    # 4. READ AND SUMMARIZE FILE
    if file_path_found:
        p = Path(file_path_found)
        if p.exists() and p.is_file():
            log.info("Deep scanning file for summary: %s", file_path_found)
            text = read_file(str(p))
            if not text.startswith("Error"):
                content = f"FULL FILE CONTENT ({p.name}):\n\n{text}"

    # 5. Summarize via AI
    engine = AIEngine()
    prompt = (
        "You are an expert at analyzing documents. Based on the following Window/File Content, "
        "provide a detailed summary. If you are provided with FULL FILE CONTENT, summarize that "
        "thoroughly. \n\n"
        f"Content:\n{content}"
    )
    
    try:
        summary = engine.generate(
            prompt,
            system="You are a helpful assistant. Provide an accurate and comprehensive summary.",
            temperature=0.3
        )
        return f"Summary of focused document:\n\n{summary}"
    except Exception as exc:
        return f"Failed to summarize: {exc}"

def summarize_project(*args) -> str:
    """Summarize the current project structure and files.
    """
    from infini_think.tools.file_tools import list_directory
    log.info("Summarizing project")
    listing = list_directory(".")
    engine = AIEngine()
    prompt = f"Summarize this project structure:\n\n{listing}"
    try:
        summary = engine.generate(prompt, temperature=0.3)
        return f"Project Summary:\n\n{summary}"
    except Exception as exc:
        return f"Failed to summarize project: {exc}"
