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

    # 2. Deep search fallback
    query = Path(path_str).name.lower()
    log.info("Path %r not found. Deep searching for: %r", path_str, query)
    
    search_dirs = []
    if base_shortcut in shortcuts:
        search_dirs.append(shortcuts[base_shortcut])
    for k, v in shortcuts.items():
        if v not in search_dirs:
            search_dirs.append(v)
            
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        try:
            for p in search_dir.rglob("*"):
                # Fast exclusion of hidden/system directories
                if "/." in p.as_posix() or "\\." in str(p):
                    continue
                if find_dir and not p.is_dir():
                    continue
                if not find_dir and not p.is_file():
                    continue
                
                if query in p.name.lower():
                    log.info("Deep search matched: %s", p)
                    return p
        except PermissionError:
            pass

    return None

def open_folder(path: str) -> str:
    """Open a folder in the native file explorer.

    Accepts friendly names such as ``"downloads"``, ``"desktop"``,
    ``"documents"``, ``"home"`` or any absolute / relative path.

    Args:
        path: Folder path or friendly shorthand.

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


def open_file(path: str) -> str:
    """Open a file using the system's default application.

    Accepts absolute paths or paths relative to the home directory.
    Uses the same shortcut resolution as `open_folder` (e.g. "downloads/image.png").

    Args:
        path: File path or friendly shorthand.

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


def close_folder(path: str) -> str:
    """Close a specific folder window in the file explorer.
    
    Args:
        path: Folder path or friendly shorthand.
        
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


def close_file(path: str) -> str:
    """Attempt to close a file by terminating its host application.
    
    Because files do not run as independent processes, this uses a heuristic
    to map the file extension to the likely host program (e.g., .txt -> notepad.exe),
    and terminates that program.
    
    Args:
        path: File path or friendly shorthand.
        
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


def create_folder(name: str, parent: str | None = None) -> str:
    """Create a new folder.

    Args:
        name: Folder name (may include nested paths, e.g. ``"Work/2024"``).
        parent: Parent directory path.  Defaults to the user's home directory.

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


def search_files(query: str, root: str | None = None) -> str:
    """Recursively search for files whose names contain *query*.

    Args:
        query: Case-insensitive substring to search for.
        root: Directory to start the search from.  Defaults to user home.

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
