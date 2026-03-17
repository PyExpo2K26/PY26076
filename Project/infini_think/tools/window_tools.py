"""
infini_think.tools.window_tools
================================
Utilities for interacting with active windows.
"""

from __future__ import annotations

import platform
import subprocess
from infini_think.utils.logger import get_logger

log = get_logger(__name__)

def get_active_window_info() -> str:
    """Return the title of the currently focused window.

    Returns:
        Human-readable window information.
    """
    system = platform.system()
    
    try:
        if system == "Windows":
            # Use PowerShell to get the active window title
            ps_script = (
                "Add-Type '@\n"
                "using System;\n"
                "using System.Runtime.InteropServices;\n"
                "public class User32 {\n"
                "  [DllImport(\"user32.dll\")]\n"
                "  public static extern IntPtr GetForegroundWindow();\n"
                "  [DllImport(\"user32.dll\")]\n"
                "  public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);\n"
                "}\n"
                "@'\n"
                "$hWnd = [User32]::GetForegroundWindow()\n"
                "$Title = New-Object System.Text.StringBuilder 256\n"
                "[User32]::GetWindowText($hWnd, $Title, 256) > $null\n"
                "$Title.ToString()"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                check=True
            )
            title = result.stdout.strip()
            if not title:
                # Fallback if GetWindowText returns empty
                res = subprocess.run(
                    ["powershell", "-Command", "(Get-Process | Where-Object {$_.MainWindowHandle -ne 0} | Sort-Object -Descending StartTime | Select-Object -First 1).MainWindowTitle"],
                    capture_output=True,
                    text=True
                )
                title = res.stdout.strip()
            
            return f"The active window is: {title}" if title else "Could not determine the active window title."
            
        elif system == "Darwin":
            # AppleScript for Mac
            cmd = "osascript -e 'tell application \"System Events\" to get name of first process whose frontmost is true'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return f"The active window belongs to: {result.stdout.strip()}"
            
        else:
            # Linux (xprop)
            result = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"], capture_output=True, text=True)
            if result.returncode == 0:
                win_id = result.stdout.split()[-1]
                title_res = subprocess.run(["xprop", "-id", win_id, "WM_NAME"], capture_output=True, text=True)
                title = title_res.stdout.split(" = ")[-1].strip('"')
                return f"The active window is: {title}"
            return "Active window detection not supported or failed on this Linux setup."
            
    except Exception as exc:
        log.error("Failed to get window info: %s", exc)
        return f"Error retrieving window info: {exc}"
