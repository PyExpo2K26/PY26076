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

def get_active_window_info(*args, **kwargs) -> str:
    """Return the title of the currently focused window.

    Args:
        *args:    Extra arguments (ignored).
        **kwargs: Extra keyword arguments (ignored).

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


def analyze_active_window(*args, **kwargs) -> str:
    """Read and summarize the text content of the currently focused window.
    
    This tool uses UI Automation to extract names and values of visible 
    elements (buttons, labels, inputs) in the active window.
    """
    if platform.system() != "Windows":
        return "Window content analysis is currently only supported on Windows."

    log.info("Analyzing active window content via UI Automation")
    
    ps_script = """
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
    
    $hWnd = (Add-Type -MemberDefinition '
        [DllImport("user32.dll")]
        public static extern IntPtr GetForegroundWindow();
    ' -Name 'User32Win' -PassThru)::GetForegroundWindow()
    
    try {
        $ae = [System.Windows.Automation.AutomationElement]::FromHandle($hWnd)
        
        # Performance optimization: Only fetch direct children and important subtypes
        # This is much faster than fetching all Descendants for complex apps
        $elements = $ae.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
        
        $content = @()
        foreach ($el in $elements) {
            $name = $el.Current.Name
            $type = $el.Current.ControlType.ProgrammaticName
            $value = ""
            
            # Only process visible/meaningful elements to reduce noise and time
            if ($name -or $el.Current.IsEnabled) {
                try {
                    if ($el.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)) {
                        $value = $el.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value
                    }
                } catch {}
                
                $item = "$name"
                if ($value) { $item += " ($value)" }
                if ($item.Trim()) { $content += $item }
            }
        }
        
        # If too few elements, try one level deeper for buttons/links specifically
        if ($content.Count -lt 5) {
            $subCondition = [System.Windows.Automation.OrCondition]::new(
                [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::IsControlElementProperty, $true),
                [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::IsContentElementProperty, $true)
            )
            $subElements = $ae.FindAll([System.Windows.Automation.TreeScope]::Descendants, $subCondition)
            foreach ($el in $subElements) {
                if ($content.Count -gt 50) { break } # Cap it
                $n = $el.Current.Name
                if ($n -and $content -notcontains $n) { $content += $n }
            }
        }

        $content | Select-Object -Unique | Out-String
    } catch {
        "Failed to access window elements: $_"
    }
    """
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=15
        )
        content = result.stdout.strip()
        if not content:
            return "The active window appears to have no readable text elements."
        
        # Truncate to avoid overloading context
        if len(content) > 3000:
            content = content[:3000] + "... (content truncated)"
            
        return f"Content of the active window:\n\n{content}"
    except Exception as exc:
        log.error("Analysis failed: %s", exc)
        return f"Error analyzing window: {exc}"


def get_taskbar_info(*args, **kwargs) -> str:
    """List all currently open applications that are visible on the taskbar.
    """
    if platform.system() != "Windows":
        return "Taskbar info is currently only supported on Windows."

    log.info("Retrieving running applications (taskbar info)")
    
    ps_script = "(Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -Property ProcessName, MainWindowTitle | Sort-Object -Property ProcessName | Format-Table -HideTableHeaders | Out-String).Trim()"
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        apps = result.stdout.strip()
        if not apps:
            return "No applications with visible windows were found."
            
        return f"Running Applications (Taskbar):\n\n{apps}"
    except Exception as exc:
        log.error("Taskbar info failed: %s", exc)
        return f"Error retrieving taskbar info: {exc}"
