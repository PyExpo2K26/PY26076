"""
infini_think.tools.system_tools
================================
System-level tool functions for InfiniThink.

These tools interact with the operating system at a lower level than
app or file tools.  They require extra caution and may prompt the user
for confirmation in the GUI before execution.

Available tools
---------------
- ``run_terminal_command(command)`` — run a shell command and return output
- ``execute_powershell(script)``     — run a PowerShell script (Windows only)
- ``take_screenshot()``              — capture and save a screenshot of the desktop
- ``shutdown_pc()``                 — initiate a system shutdown
- ``get_system_info()``             — return hardware/OS information
- ``open_device_settings(section)`` — open specific Windows settings pages
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

from infini_think.config.settings import settings
from infini_think.utils.logger import get_logger

log = get_logger(__name__)


def run_terminal_command(command: str) -> str:
    """Execute a shell command and return its output (stdout + stderr).

    The command runs with a configurable timeout.  Only use this for safe,
    non-destructive commands.  The result is truncated to 2000 characters to
    avoid flooding the chat window.

    Args:
        command: The shell command string to execute.

    Returns:
        Combined stdout/stderr output, or an error message.
    """
    log.info("Running terminal command: %r", command)
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=settings.command_timeout,
        )
        output = (result.stdout + result.stderr).strip()
        if not output:
            output = f"Command completed (exit code {result.returncode})."
        # Truncate very long output
        if len(output) > 2000:
            output = output[:2000] + "\n... (output truncated)"
        log.debug("Command output: %r", output[:200])
        return output
    except subprocess.TimeoutExpired:
        msg = f"Command timed out after {settings.command_timeout}s."
        log.warning(msg)
        return msg
    except Exception as exc:  # noqa: BLE001
        msg = f"Command failed: {exc}"
        log.error(msg)
        return msg


def execute_powershell(script: str) -> str:
    """Execute a PowerShell script and return its output.

    Args:
        script: The PowerShell script content or command.

    Returns:
        The output of the script or an error message.
    """
    log.info("Executing PowerShell script")
    log.debug("Script content: %r", script[:200])
    try:
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=settings.command_timeout,
        )
        output = (result.stdout + result.stderr).strip()
        if not output:
            output = f"Script completed (exit code {result.returncode})."
        if len(output) > 2000:
            output = output[:2000] + "\n... (output truncated)"
        return output
    except subprocess.TimeoutExpired:
        return f"PowerShell script timed out after {settings.command_timeout}s."
    except Exception as exc:
        return f"PowerShell execution failed: {exc}"


def take_screenshot() -> str:
    """Capture a screenshot of the primary monitor and save it to the Desktop.

    Returns:
        A message indicating where the screenshot was saved.
    """
    import datetime
    filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = Path.home() / "Desktop" / filename
    
    log.info("Taking screenshot: %s", filepath)
    
    # PowerShell snippet to capture screen using .NET
    # This avoids adding a heavy dependency like 'pillow' or 'pyautogui' if they aren't there.
    ps_script = f"""
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $Screen = [System.Windows.Forms.Screen]::PrimaryScreen
    $Top    = $Screen.Bounds.Top
    $Left   = $Screen.Bounds.Left
    $Width  = $Screen.Bounds.Width
    $Height = $Screen.Bounds.Height
    $Bitmap = New-Object System.Drawing.Bitmap($Width, $Height)
    $Graphic = [System.Drawing.Graphics]::FromImage($Bitmap)
    $Graphic.CopyFromScreen($Left, $Top, 0, 0, $Bitmap.Size)
    $Bitmap.Save('{str(filepath)}', [System.Drawing.Imaging.ImageFormat]::Png)
    $Graphic.Dispose()
    $Bitmap.Dispose()
    """
    
    try:
        subprocess.run(["powershell", "-Command", ps_script], check=True, capture_output=True)
        return f"Screenshot saved to your Desktop: {filename}"
    except Exception as exc:
        msg = f"Failed to take screenshot: {exc}"
        log.error(msg)
        return msg


def shutdown_pc(delay: int = 60) -> str:
    """Initiate a system shutdown.

    A delay is built in to give the user time to cancel.  The shutdown
    command varies by operating system.

    Args:
        delay: Seconds before shutdown occurs (default 60).  Pass 0 for
               an immediate shutdown (use with caution).

    Returns:
        Human-readable status string.
    """
    system = platform.system()
    log.warning("Shutdown requested — delay=%ds platform=%s", delay, system)

    try:
        if system == "Windows":
            subprocess.run(
                ["shutdown", "/s", "/t", str(delay)],
                check=True,
                capture_output=True,
            )
            return f"Shutdown scheduled in {delay} seconds. Run 'shutdown /a' to cancel."
        elif system == "Darwin":
            subprocess.run(
                ["sudo", "shutdown", "-h", f"+{delay // 60}"],
                check=True,
                capture_output=True,
            )
            return f"Shutdown scheduled in {delay // 60} minute(s)."
        else:
            subprocess.run(
                ["sudo", "shutdown", "-h", f"+{delay // 60}"],
                check=True,
                capture_output=True,
            )
            return f"Shutdown scheduled in {delay // 60} minute(s)."
    except subprocess.CalledProcessError as exc:
        msg = f"Shutdown failed: {exc.stderr.decode().strip()}"
        log.error(msg)
        return msg
    except Exception as exc:  # noqa: BLE001
        return f"Shutdown failed: {exc}"


def get_system_info() -> str:
    """Return a human-readable summary of the current system.

    Gathers platform, Python version, CPU, and memory info without
    requiring ``psutil`` (which is not a required dependency).

    Returns:
        Multi-line string with system details.
    """
    try:
        import os
        uname = platform.uname()
        py_ver = sys.version.split()[0]

        lines: list[str] = [
            f"OS:           {uname.system} {uname.release} ({uname.version[:60]})",
            f"Machine:      {uname.machine}",
            f"Hostname:     {uname.node}",
            f"Processor:    {uname.processor or platform.processor() or 'N/A'}",
            f"Python:       {py_ver}",
            f"CPU count:    {os.cpu_count()} logical core(s)",
        ]

        # Try to get memory without psutil
        system = platform.system()
        if system == "Windows":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
                c_ulong = ctypes.c_ulong

                class _MEMORYSTATUS(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", c_ulong),
                        ("dwMemoryLoad", c_ulong),
                        ("dwTotalPhys", c_ulong),
                        ("dwAvailPhys", c_ulong),
                        ("dwTotalPageFile", c_ulong),
                        ("dwAvailPageFile", c_ulong),
                        ("dwTotalVirtual", c_ulong),
                        ("dwAvailVirtual", c_ulong),
                    ]

                ms = _MEMORYSTATUS()
                ms.dwLength = ctypes.sizeof(_MEMORYSTATUS)
                kernel32.GlobalMemoryStatus(ctypes.byref(ms))
                total_gb = ms.dwTotalPhys / (1024 ** 3)
                avail_gb = ms.dwAvailPhys / (1024 ** 3)
                lines.append(
                    f"RAM:          {total_gb:.1f} GB total, {avail_gb:.1f} GB free"
                )
            except Exception:  # noqa: BLE001
                lines.append("RAM:          (unable to retrieve)")
        elif system == "Linux":
            try:
                with open("/proc/meminfo") as f:
                    mem = {
                        k.strip(): int(v.strip().split()[0])
                        for line in f
                        for k, v in [line.split(":", 1)]
                    }
                total_gb = mem.get("MemTotal", 0) / (1024 ** 2)
                free_gb = mem.get("MemAvailable", 0) / (1024 ** 2)
                lines.append(f"RAM:          {total_gb:.1f} GB total, {free_gb:.1f} GB free")
            except Exception:  # noqa: BLE001
                lines.append("RAM:          (unable to retrieve)")

        log.info("System info retrieved")
        return "\n".join(lines)

    except Exception as exc:  # noqa: BLE001
        return f"Could not retrieve system info: {exc}"


def open_device_settings(section: str = "main", *args) -> str:
    """Open a specific section of the Windows Settings app.
    
    Args:
        section: The settings section to open. Options include: 'main', 'wifi',
                  'bluetooth', 'display', 'sound', 'notifications', 'power',
                  'storage', 'apps', 'accounts', 'time', 'gaming', 'accessibility',
                  'privacy', 'windows-update'.
    """
    if platform.system() != "Windows":
        return "Device settings shortcut is only available on Windows."

    # Map friendly names to Windows ms-settings URIs
    uri_map = {
        "main":             "ms-settings:",
        "wifi":             "ms-settings:network-wifi",
        "bluetooth":        "ms-settings:bluetooth",
        "display":          "ms-settings:display",
        "sound":            "ms-settings:sound",
        "notifications":    "ms-settings:notifications",
        "power":            "ms-settings:powersleep",
        "storage":          "ms-settings:storagesense",
        "apps":             "ms-settings:appsfeatures",
        "accounts":         "ms-settings:yourinfo",
        "time":             "ms-settings:dateandtime",
        "gaming":           "ms-settings:gaming-gamemode",
        "accessibility":    "ms-settings:easeofaccess-display",
        "privacy":          "ms-settings:privacy",
        "windows-update":   "ms-settings:windowsupdate",
        "network":          "ms-settings:network",
        "personalization":  "ms-settings:personalization",
    }

    key = section.lower().strip()
    target_uri = uri_map.get(key, uri_map["main"])
    
    log.info("Opening device settings: %s (%s)", section, target_uri)
    try:
        subprocess.run(f'start {target_uri}', shell=True, check=True)
        return f"Opened Windows Settings: {section}"
    except Exception as exc:
        return f"Failed to open settings: {exc}"


def get_process_list(*args, **kwargs) -> str:
    """List all currently running processes with their IDs and memory usage.
    """
    if platform.system() != "Windows":
        return "Process listing is currently only supported on Windows."

    log.info("Retrieving process list")
    
    # PowerShell command to get process details in a clean format
    ps_script = "(Get-Process | Select-Object -Property Id, ProcessName, @{Name='MemMB';Expression={[math]::Round($_.WorkingSet64 / 1MB, 2)}} | Sort-Object -Property MemMB -Descending | Select-Object -First 30 | Format-Table -HideTableHeaders | Out-String).Trim()"
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        processes = result.stdout.strip()
        if not processes:
            return "No processes found."
            
        header = f"{'PID':<8} {'Name':<20} {'Memory (MB)':<12}\n" + "-"*40
        return f"Top 30 Running Processes (by Memory):\n\n{header}\n{processes}"
    except Exception as exc:
        log.error("Process list failed: %s", exc)
        return f"Error retrieving process list: {exc}"


def kill_process(target: str | int, *args, **kwargs) -> str:
    """Terminate a running process by its name or ID.

    Args:
        target: The name of the process (e.g. 'notepad') or its PID.
    """
    system = platform.system()
    log.info("Killing process: %s", target)
    
    try:
        if system == "Windows":
            if str(target).isdigit():
                cmd = ["taskkill", "/PID", str(target), "/F"]
            else:
                # Add .exe if not present for taskkill
                name = str(target)
                if not name.endswith(".exe") and "." not in name:
                    name += ".exe"
                cmd = ["taskkill", "/IM", name, "/F"]
                
            subprocess.run(cmd, check=True, capture_output=True)
            return f"Successfully terminated process: {target}"
            
        else:
            cmd = ["pkill", "-f", str(target)]
            subprocess.run(cmd, check=True, capture_output=True)
            return f"Successfully terminated process: {target}"
            
    except subprocess.CalledProcessError:
        return f"Could not find or terminate process: {target}. It may not be running or requires elevated privileges."
    except Exception as exc:
        log.error("Kill process failed: %s", exc)
        return f"Error killing process: {exc}"
