"""
infini_think.tools.file_tools
==============================
File-system tool functions for InfiniThink.

All functions return a human-readable result string that is displayed in the
chat window and optionally spoken by the TTS engine.

Available tools
---------------
- ``open_folder(path)`` — open a folder in the native file explorer
- ``open_file(path)`` — open a file using the system default application
- ``organize_downloads()`` — sort Downloads into sub-folders by type
- ``create_folder(name)`` — create a new folder in the current user home
- ``search_files(query)`` — find files matching a name pattern
- ``write_file(path, content)`` — create or overwrite a file with text content
- ``delete_file(path)`` — delete a file or folder (use with caution)
- ``rename_item(path, new_name)`` — rename a file or folder
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from infini_think.config.settings import settings
from infini_think.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# File-type → subfolder mapping used by organize_downloads()
# ---------------------------------------------------------------------------

_CATEGORY_MAP: dict[str, list[str]] = {
    "Images":     [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico"],
    "Videos":     [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "Audio":      [".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".wma"],
    "Documents":  [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".rtf"],
    "Archives":   [".zip", ".rar", ".tar", ".gz", ".7z", ".bz2", ".xz"],
    "Code":       [".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".h", ".json",
                   ".xml", ".yaml", ".yml", ".sh", ".bat", ".ps1", ".rs", ".go", ".rb"],
    "Executables":[".exe", ".msi", ".dmg", ".deb", ".rpm", ".apk"],
    "Data":       [".csv", ".xlsx", ".db", ".sqlite", ".sql", ".parquet"],
}


def _ext_to_category(extension: str) -> str:
    """Map a file extension to a category folder name."""
    ext = extension.lower()
    for category, exts in _CATEGORY_MAP.items():
        if ext in exts:
            return category
    return "Others"


def _open_path_in_explorer(path: Path) -> None:
    """Open *path* in the OS native file manager."""
    system = platform.system()
    if system == "Windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


def _smart_find(path_str: str, find_dir: bool = False) -> Path | None:
    """Attempt to resolve a path, falling back to a recursive search in common folders."""
    # 0. Strip file:/// prefix and handle common URL encoding
    if path_str.startswith("file:///"):
        path_str = path_str[8:]
    elif path_str.startswith("file://"):
        path_str = path_str[7:]
    
    # Simple URL decoding check (just for spaces for now)
    path_str = path_str.replace("%20", " ")

    shortcuts: dict[str, Path] = {
        "downloads": Path.home() / "Downloads",
        "desktop":   Path.home() / "Desktop",
        "documents": Path.home() / "Documents",
        "pictures":  Path.home() / "Pictures",
        "music":     Path.home() / "Music",
        "videos":    Path.home() / "Videos",
    }

    # 1. Exact resolution attempt
    parts = path_str.replace("\\", "/").split("/")
    base_shortcut = parts[0].lower()
    
    if base_shortcut in shortcuts:
        resolved = shortcuts[base_shortcut].joinpath(*parts[1:])
    elif base_shortcut == "home":
        resolved = Path.home().joinpath(*parts[1:])
    else:
        resolved = Path(path_str)

    if resolved.exists():
        return resolved

    # 2. Deep search fallback (highly localized to prevent hangs)
    if "/" in path_str or "\\" in path_str:
        return None # Don't deep search if user provided a specific (but wrong) path

    query = Path(path_str).name.lower()
    log.info("Path %r not found. Quick-searching common folders for: %r", path_str, query)
    
    # Only search in Desktop and Documents by default for speed
    search_dirs = [shortcuts["desktop"], shortcuts["documents"]]
            
    max_depth = 1 # Reduced from 2 for speed
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        try:
            for root, dirs, files in os.walk(str(search_dir)):
                # Skip hidden folders
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                
                if find_dir:
                    for d in dirs:
                        if query in d.lower():
                            return Path(root) / d
                else:
                    for f in files:
                        if query in f.lower():
                            return Path(root) / f
                            res = Path(root) / f
                            log.info("Deep search matched file: %s", res)
                            return res
                
                # Manual depth control since we only want depth 1
                break 
        except (PermissionError, OSError):
            continue

    return None

def open_folder(path: str, *args) -> str:
    """Open a folder in the native file explorer.

    Accepts friendly names such as ``"downloads"``, ``"desktop"``,
    ``"documents"``, ``"home"`` or any absolute / relative path.

    Args:
        path: Folder path or friendly shorthand.
        *args: Extra arguments (ignored).

    Returns:
        Human-readable status string.
    """
    resolved = _smart_find(path, find_dir=True)

    if not resolved:
        msg = f"Folder not found during search: {path}"
        log.warning(msg)
        return msg

    log.info("Opening folder: %s", resolved)
    _open_path_in_explorer(resolved)
    return f"Opened folder: {resolved}"


def open_file(path: str, *args) -> str:
    """Open a file using the system's default application.

    Accepts absolute paths or paths relative to the home directory.
    Uses the same shortcut resolution as `open_folder` (e.g. "downloads/image.png").

    Args:
        path: File path or friendly shorthand.
        *args: Extra arguments (ignored).

    Returns:
        Human-readable status string.
    """
    resolved = _smart_find(path, find_dir=False)

    if not resolved:
        msg = f"File not found during search: {path}"
        log.warning(msg)
        return msg

    if resolved.is_dir():
        return open_folder(str(resolved))

    log.info("Opening file: %s", resolved)
    _open_path_in_explorer(resolved)
    return f"Opened file: {resolved.name}"


def close_folder(path: str, *args) -> str:
    """Close a specific folder window in the file explorer.
    
    Args:
        path: Folder path or friendly shorthand.
        *args: Extra arguments (ignored).
        
    Returns:
        Human-readable status string.
    """
    resolved = _smart_find(path, find_dir=True)
    if not resolved:
        msg = f"Could not find folder to close: {path}"
        log.warning(msg)
        return msg
        
    system = platform.system()
    try:
        if system == "Windows":
            # Safely close only the specific Explorer window using a PowerShell COM Object
            # We match the window's LocationName broadly against the resolved folder's name
            folder_name = resolved.name.replace("'", "''")
            ps_script = f"""
            $Shell = New-Object -ComObject Shell.Application
            foreach ($window in $Shell.Windows()) {{
                if ($window.LocationName -match '{folder_name}') {{
                    $window.Quit()
                }}
            }}
            """
            subprocess.run(
                ["powershell", "-Command", ps_script],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            # On Unix/Mac, closing specific Finder/Nautilus tabs automatically is complex,
            # so we fall back to a generic warning or attempt a soft kill.
            return f"Closed folder functionality is currently tailored for Windows. Please close '{resolved.name}' manually."
            
        return f"Closed folder: {resolved.name}"
    except Exception as exc:  # noqa: BLE001
        msg = f"Failed to close folder '{resolved.name}': {exc}"
        log.error(msg)
        return msg


def close_file(path: str, *args) -> str:
    """Attempt to close a file by terminating its host application.
    
    Because files do not run as independent processes, this uses a heuristic
    to map the file extension to the likely host program (e.g., .txt -> notepad.exe),
    and terminates that program.
    
    Args:
        path: File path or friendly shorthand.
        *args: Extra arguments (ignored).
        
    Returns:
        Human-readable status string.
    """
    resolved = _smart_find(path, find_dir=False)
    if not resolved:
        # If we can't find it, we might just have a random filename. We can still try to derive extension
        resolved = Path(path)
        
    if resolved.is_dir():
        return close_folder(str(resolved))

    ext = resolved.suffix.lower()
    
    # Heuristic mapping for common file extensions to their typical host application executables
    ext_to_app = {
        ".txt": "notepad.exe",
        ".md": "code.exe",
        ".py": "code.exe",
        ".js": "code.exe",
        ".json": "code.exe",
        ".ppt": "powerpnt.exe",
        ".pptx": "powerpnt.exe",
        ".doc": "winword.exe",
        ".docx": "winword.exe",
        ".xls": "excel.exe",
        ".xlsx": "excel.exe",
        ".pdf": "msedge.exe", # Default for many Windows users
        ".jpg": "PhotosApp.exe",
        ".jpeg": "PhotosApp.exe",
        ".png": "PhotosApp.exe",
        ".gif": "PhotosApp.exe",
        ".mp4": "vlc.exe",
        ".mp3": "vlc.exe",
    }
    
    host_app = ext_to_app.get(ext)
    
    if not host_app:
        return (
            f"I cannot safely determine which application is hosting '{resolved.name}'. "
            f"Please use the 'close_app' command with the application's name instead (e.g. 'close powerpoint')."
        )
        
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(
                ["taskkill", "/IM", host_app, "/F"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            clean_app = host_app.replace(".exe", "")
            subprocess.run(
                ["pkill", "-f", clean_app],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return f"Closed file host ({host_app}) for: {resolved.name}"
    except subprocess.CalledProcessError:
        return f"Could not find a running '{host_app}' to close."
    except Exception as exc:  # noqa: BLE001
        return f"Failed to close file '{resolved.name}': {exc}"


def organize_downloads() -> str:
    """Sort the Downloads folder into sub-folders by file type.

    Creates category sub-folders (Images, Videos, Documents, …) and moves
    each file into the appropriate one.  Existing sub-folders and files that
    are already in a sub-folder are left untouched.

    Returns:
        Summary string listing how many files were moved.
    """
    downloads: Path = settings.downloads_dir
    if not downloads.exists():
        return f"Downloads folder not found: {downloads}"

    moved = 0
    skipped = 0

    for item in list(downloads.iterdir()):
        # Skip sub-directories and hidden files
        if item.is_dir() or item.name.startswith("."):
            skipped += 1
            continue

        category = _ext_to_category(item.suffix)
        target_dir = downloads / category
        target_dir.mkdir(exist_ok=True)

        dest = target_dir / item.name
        # Avoid overwriting – append a counter if necessary
        counter = 1
        while dest.exists():
            dest = target_dir / f"{item.stem}_{counter}{item.suffix}"
            counter += 1

        shutil.move(str(item), str(dest))
        log.debug("Moved %s → %s/%s", item.name, category, dest.name)
        moved += 1

    msg = (
        f"Downloads organised: {moved} file(s) moved into category folders. "
        f"{skipped} item(s) skipped."
    )
    log.info(msg)
    return msg


def create_folder(name: str, parent: str | None = None, *args) -> str:
    """Create a new folder.

    Args:
        name: Folder name (may include nested paths, e.g. ``"Work/2024"``).
        parent: Parent directory path.  Defaults to the user's home directory.
        *args: Extra arguments (ignored).

    Returns:
        Human-readable status string.
    """
    base: Path = Path(parent) if parent else Path.home()
    target: Path = base / name

    if target.exists():
        return f"Folder already exists: {target}"

    target.mkdir(parents=True, exist_ok=True)
    log.info("Created folder: %s", target)
    return f"Created folder: {target}"


def read_file(path: str, *args) -> str:
    """Read the text content of a file.

    Accepts absolute paths or paths relative to the home directory.
    Uses shortcut resolution (e.g. "downloads/notes.txt").

    Args:
        path: File path or friendly shorthand.
        *args: Extra arguments (ignored).

    Returns:
        The content of the file (truncated if too long), or an error message.
    """
    resolved = _smart_find(path, find_dir=False)

    if not resolved:
        return f"File not found: {path}"

    if not resolved.is_file():
        return f"Path is not a file: {resolved}"

    try:
        ext = resolved.suffix.lower()
        content = ""
        
        if ext == ".pdf":
            import fitz
            doc = fitz.open(resolved)
            for page in doc:
                content += page.get_text() + "\n"
            doc.close()
        elif ext == ".docx":
            import docx
            doc = docx.Document(resolved)
            content = "\n".join([para.text for para in doc.paragraphs])
        else:
            # Fallback for txt, md, py, etc.
            content = resolved.read_text(encoding="utf-8", errors="replace")
            
        if len(content) > 10000:
            content = content[:10000] + "\n... (content truncated for context window limits)"
        
        log.info("Read file contents: %s", resolved)
        return f"Contents of {resolved.name}:\n\n{content}"
    except Exception as exc:
        return f"Failed to read file: {exc}"


def write_file(path: str, content: str, *args) -> str:
    """Create a new file or overwrite an existing one with text content.

    Args:
        path: File path or friendly shorthand (e.g. "desktop/notes.txt").
        content: The text to write into the file.
        *args: Extra arguments (ignored).

    Returns:
        Human-readable status string.
    """
    # Resolve path, but don't require it to exist yet
    parts = path.replace("\\", "/").split("/")
    base_shortcut = parts[0].lower()
    shortcuts: dict[str, Path] = {
        "downloads": Path.home() / "Downloads",
        "desktop":   Path.home() / "Desktop",
        "documents": Path.home() / "Documents",
    }
    
    if base_shortcut in shortcuts:
        resolved = shortcuts[base_shortcut].joinpath(*parts[1:])
    elif base_shortcut == "home":
        resolved = Path.home().joinpath(*parts[1:])
    else:
        resolved = Path(path)

    try:
        # Create parent directories if they don't exist
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        log.info("Wrote file: %s", resolved)
        return f"File written successfully: {resolved}"
    except Exception as exc:
        msg = f"Failed to write file '{path}': {exc}"
        log.error(msg)
        return msg


def delete_file(path: str, *args) -> str:
    """Delete a file or folder. Use with caution.

    Args:
        path: Path or shorthand to the item to delete.
        *args: Extra arguments (ignored).

    Returns:
        Human-readable status string.
    """
    resolved = _smart_find(path, find_dir=True) # Check both files and dirs
    if not resolved:
        return f"Item not found to delete: {path}"

    try:
        if resolved.is_dir():
            shutil.rmtree(resolved)
            log.info("Deleted folder: %s", resolved)
            return f"Deleted folder: {resolved.name}"
        else:
            resolved.unlink()
            log.info("Deleted file: %s", resolved)
            return f"Deleted file: {resolved.name}"
    except Exception as exc:
        msg = f"Failed to delete '{path}': {exc}"
        log.error(msg)
        return msg


def rename_item(path: str, new_name: str, *args) -> str:
    """Rename a file or folder.

    Args:
        path: Current path or shorthand.
        new_name: The new filename or folder name (not a full path).
        *args: Extra arguments (ignored).

    Returns:
        Human-readable status string.
    """
    resolved = _smart_find(path, find_dir=True)
    if not resolved:
        return f"Item not found to rename: {path}"

    try:
        target = resolved.parent / new_name
        if target.exists():
            return f"Cannot rename: an item named '{new_name}' already exists in {resolved.parent}"
        
        resolved.rename(target)
        log.info("Renamed %s → %s", resolved, target.name)
        return f"Renamed '{resolved.name}' to '{new_name}'"
    except Exception as exc:
        msg = f"Failed to rename '{path}': {exc}"
        log.error(msg)
        return msg


def search_files(query: str, root: str | None = None, *args) -> str:
    """Recursively search for files whose names contain *query*.

    Args:
        query: Case-insensitive substring to search for.
        root: Directory to start the search from.  Defaults to user home.
        *args: Extra arguments (ignored).

    Returns:
        Comma-separated list of matching paths (max 20), or a "not found" msg.
    """
    base: Path = Path(root) if root else Path.home()
    query_lower = query.lower()
    matches: list[str] = []
    max_results = 20

    try:
        for path in base.rglob("*"):
            if path.is_file() and query_lower in path.name.lower():
                matches.append(str(path))
                if len(matches) >= max_results:
                    break
    except PermissionError:
        pass

    if not matches:
        return f"No files found matching '{query}' under {base}"

    result_str = "\n".join(matches)
    log.info("search_files('%s'): %d results", query, len(matches))
    return f"Found {len(matches)} file(s):\n{result_str}"


def list_directory(path: str = "home", *args) -> str:
    """List the contents of a directory.

    Args:
        path: Directory path or shorthand (e.g. "downloads", "desktop"). 
              Defaults to the user's home directory.
        *args: Extra arguments (ignored).

    Returns:
        A list of files and folders in the directory.
    """
    resolved = _smart_find(path, find_dir=True)
    if not resolved:
        # Try direct resolution if smart find fails (for non-standard paths)
        resolved = Path(path).expanduser()
        if not resolved.exists():
            return f"Directory not found: {path}"

    if not resolved.is_dir():
        return f"Path is not a directory: {resolved}"

    try:
        items = []
        for item in resolved.iterdir():
            prefix = "📁 " if item.is_dir() else "📄 "
            items.append(f"{prefix}{item.name}")
        
        if not items:
            return f"The directory '{resolved}' is empty."
            
        # Sort folders first, then files
        items.sort()
        content = "\n".join(items)
        
        # Truncate if too many items
        if len(items) > 100:
            content = "\n".join(items[:100]) + f"\n... (and {len(items)-100} more)"
            
        log.info("Listed directory: %s", resolved)
        return f"Contents of {resolved}:\n\n{content}"
    except Exception as exc:
        return f"Failed to list directory: {exc}"


def copy_item(source: str, destination: str, *args) -> str:
    """Copy a file or directory to a new location.

    Args:
        source: Source path or shorthand.
        destination: Destination path or shorthand.
        *args: Extra arguments (ignored).

    Returns:
        Human-readable status string.
    """
    src = _smart_find(source, find_dir=True)
    if not src:
        src = Path(source).expanduser()
        if not src.exists():
            return f"Source not found: {source}"

    # For destination, we resolve it as a path
    dst = Path(destination).expanduser()
    if not dst.is_absolute():
        # Heuristic: if it's not absolute, try to resolve it relative to home or as a shortcut
        resolved_dst = _smart_find(destination, find_dir=True)
        if resolved_dst:
            dst = resolved_dst
        else:
            dst = Path.home() / destination

    try:
        # If destination is a directory, copy INTO it
        if dst.is_dir():
            dst = dst / src.name

        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
            
        log.info("Copied %s to %s", src, dst)
        return f"Successfully copied '{src.name}' to '{dst}'"
    except Exception as exc:
        msg = f"Failed to copy '{source}': {exc}"
        log.error(msg)
        return msg


def move_item(source: str, destination: str, *args) -> str:
    """Move (or rename) a file or directory to a new location.

    Args:
        source: Source path or shorthand.
        destination: Destination path or shorthand.
        *args: Extra arguments (ignored).

    Returns:
        Human-readable status string.
    """
    src = _smart_find(source, find_dir=True)
    if not src:
        src = Path(source).expanduser()
        if not src.exists():
            return f"Source not found: {source}"

    dst = Path(destination).expanduser()
    if not dst.is_absolute():
        resolved_dst = _smart_find(destination, find_dir=True)
        if resolved_dst:
            dst = resolved_dst
        else:
            dst = Path.home() / destination

    try:
        if dst.is_dir():
            dst = dst / src.name

        shutil.move(str(src), str(dst))
        log.info("Moved %s to %s", src, dst)
        return f"Successfully moved '{src.name}' to '{dst}'"
    except Exception as exc:
        msg = f"Failed to move '{source}': {exc}"
        log.error(msg)
        return msg
