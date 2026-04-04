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
    """Return the title of the currently focused window."""
    system = platform.system()
    try:
        if system == "Windows":
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
            result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True, check=True)
            return f"Active window: {result.stdout.strip()}"
        return "Not supported."
    except Exception as exc:
        return f"Error: {exc}"


def analyze_active_window(*args, **kwargs) -> str:
    """Extract and summarize contents of the non-AI active window.
    """
    if platform.system() != "Windows":
        return "Window content analysis is only supported on Windows."

    log.info("Analyzing active window content via UI Automation")
    
    ps_script = """
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
    
    Add-Type -MemberDefinition '
        [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr hWnd, uint uCmd);
        [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int nMaxCount);
    ' -Name 'User32Win'
    
    $hWnd = [User32Win]::GetForegroundWindow()
    $sb = New-Object System.Text.StringBuilder 256
    
    # LOOP UNTIL WE FIND A RELEVANT WINDOW (SKIP INFINITHINK AND SHELL)
    while ($true) {
        $sb.Clear()
        $null = [User32Win]::GetWindowText($hWnd, $sb, 256)
        $title = $sb.ToString()
        if ($title -notlike "*InfiniThink*" -and $title -notlike "Program Manager" -and $title -ne "") {
            break
        }
        $hWnd = [User32Win]::GetWindow($hWnd, 2) # GW_HWNDNEXT (get window behind)
        if ($hWnd -eq 0) { break }
    }
    
    try {
        $ae = [System.Windows.Automation.AutomationElement]::FromHandle($hWnd)
        $title = $ae.Current.Name
        $content = @("Window Title: $title")
        
        # 1. DEEP SEARCH for URL/Path
        $edits = $ae.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit))
        foreach ($edge in $edits) {
            try {
                if ($edge.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)) {
                    $v = $edge.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value
                    if ($v -like "*://*" -or $v -like "?:\\*") {
                        $content += "URL/Path: $v"
                        break
                    }
                }
            } catch {}
        }
        
        # 2. UI Elements
        $elements = $ae.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
        foreach ($el in $elements) {
            $n = $el.Current.Name
            if ($n -and $content -notcontains $n) { $content += $n }
        }

        # 3. Final String
        $content | Out-String
    } catch {
        "Error: $_"
    }
    """
    
    try:
        result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True, timeout=20)
        return result.stdout.strip()
    except Exception as exc:
        return f"Error: {exc}"


def get_taskbar_info(*args, **kwargs) -> str:
    """List open applications on the taskbar."""
    ps_script = "[Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -Property MainWindowTitle | Out-String].Trim()"
    try:
        result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as exc:
        return f"Error: {exc}"

