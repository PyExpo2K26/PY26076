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
- ``shutdown_pc()``                 — initiate a system shutdown
- ``get_system_info()``             — return hardware/OS information
"""

from __future__ import annotations

import platform
import subprocess
import sys

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
