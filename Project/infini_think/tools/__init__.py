"""infini_think.tools – package init."""
from infini_think.tools.file_tools import (
    create_folder,
    open_file,
    close_file,
    open_folder,
    close_folder,
    organize_downloads,
    search_files,
)
from infini_think.tools.app_tools import open_app, open_vscode, close_app
from infini_think.tools.system_tools import run_terminal_command, shutdown_pc, get_system_info

__all__ = [
    "open_folder",
    # file_tools
    "create_folder",
    "open_file",
    "close_file",
    "open_folder",
    "close_folder",
    "organize_downloads",
    "close_app",
    "run_terminal_command",
    "shutdown_pc",
    "get_system_info",
]
