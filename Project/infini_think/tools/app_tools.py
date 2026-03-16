"""
infini_think.tools.app_tools
==============================
Application-launcher tool functions for InfiniThink.

Provides cross-platform application launch utilities.  On Windows the
launcher uses common executable names and the ``start`` shell command.
On Linux/macOS the application name is passed directly to ``subprocess``.

Available tools
---------------
- ``open_app(app_name)`` — launch any app by friendly name
- ``open_vscode(path)``  — open VS Code (optionally at a given path)
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

from infini_think.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Windows-specific alias map: friendly name → executable / start command
# ---------------------------------------------------------------------------

_WIN_APP_MAP: dict[str, str] = {
    # Browsers
    "chrome":           "chrome",
    "google chrome":    "chrome",
    "firefox":          "firefox",
    "mozilla firefox":  "firefox",
    "edge":             "msedge",
    "microsoft edge":   "msedge",
    "brave":            "brave",
    "opera":            "opera",
    # Office / productivity
    "word":             "winword",
    "excel":            "excel",
    "powerpoint":       "powerpnt",
    "outlook":          "outlook",
    "onenote":          "onenote",
    "notepad":          "notepad",
    "notepad++":        "notepad++",
    "calculator":       "calc",
    "paint":            "mspaint",
    "snipping tool":    "snippingtool",
    "task manager":     "taskmgr",
    "control panel":    "control",
    "settings":         "ms-settings:",
    # Dev tools
    "vscode":           "code",
    "vs code":          "code",
    "visual studio code": "code",
    "git bash":         "git-bash",
    "terminal":         "wt",           # Windows Terminal
    "powershell":       "powershell",
    "cmd":              "cmd",
    "command prompt":   "cmd",
    # Media
    "vlc":              "vlc",
    "spotify":          "spotify",
    # Utilities
    "file explorer":    "explorer",
    "explorer":         "explorer",
    "steam":            "steam",
    "discord":          "discord",
    "slack":            "slack",
    "zoom":             "zoom",
    "teams":            "teams",
    "microsoft teams":  "teams",
    "notion":           "notion",
    "obsidian":         "obsidian",
}

# Linux/macOS alias map
_UNIX_APP_MAP: dict[str, str] = {
    "chrome":           "google-chrome",
    "google chrome":    "google-chrome",
    "firefox":          "firefox",
    "vscode":           "code",
    "vs code":          "code",
    "visual studio code": "code",
    "terminal":         "x-terminal-emulator",
    "calculator":       "gnome-calculator",
    "file manager":     "nautilus",
    "files":            "nautilus",
    "text editor":      "gedit",
}


def _resolve_app_name(app_name: str) -> str:
    """Resolve a friendly name to the actual executable.

    Args:
        app_name: User-provided application name (case-insensitive).

    Returns:
        The executable name or command string to launch.
    """
    key = app_name.lower().strip()
    system = platform.system()
    if system == "Windows":
        return _WIN_APP_MAP.get(key, key)
    return _UNIX_APP_MAP.get(key, key)


def open_app(app_name: str) -> str:
    """Launch an application by its friendly name.

    Args:
        app_name: The application name, e.g. ``"chrome"``, ``"notepad"``.

    Returns:
        Human-readable status string.
    """
    executable = _resolve_app_name(app_name)
    system = platform.system()
    log.info("Launching app: %r → executable=%r (platform=%s)", app_name, executable, system)

    try:
        if system == "Windows":
            # ``start`` handles both .exe names and ms- URI schemes
            subprocess.Popen(
                f'start "" "{executable}"',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif system == "Darwin":
            subprocess.Popen(
                ["open", "-a", executable],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                [executable],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return f"Launched: {app_name}"
    except FileNotFoundError:
        msg = (
            f"Could not find '{app_name}'. "
            "Make sure it is installed and on your PATH."
        )
        log.warning(msg)
        return msg
    except Exception as exc:  # noqa: BLE001
        msg = f"Failed to launch '{app_name}': {exc}"
        log.error(msg)
        return msg


def open_vscode(path: str = "") -> str:
    """Open Visual Studio Code, optionally at a specific directory or file.

    Args:
        path: Optional path to open in VS Code.  If empty, opens the last
              workspace or a blank window.

    Returns:
        Human-readable status string.
    """
    cmd: list[str] = ["code"]
    if path:
        resolved = Path(path).expanduser()
        cmd.append(str(resolved))

    log.info("Opening VS Code: %s", " ".join(cmd))
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if path:
            return f"Opened VS Code at: {path}"
        return "Opened VS Code"
    except FileNotFoundError:
        return (
            "VS Code not found. Install it from https://code.visualstudio.com "
            "and ensure 'code' is in your PATH."
        )
    except Exception as exc:  # noqa: BLE001
        return f"Failed to open VS Code: {exc}"
