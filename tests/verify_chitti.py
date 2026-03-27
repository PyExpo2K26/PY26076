import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path.cwd()))

from infini_think.tools.file_tools import list_directory, copy_item, move_item
from infini_think.tools.system_tools import get_process_list, kill_process
from infini_think.tools.intelligence_tools import summarize_active_window

def test_tools():
    print("--- Testing list_directory ---")
    print(list_directory("home"))
    
    print("\n--- Testing get_process_list ---")
    print(get_process_list())
    
    print("\n--- Testing summarize_active_window ---")
    # This might fail if no window is focused or PowerShell UI Automation fails, but let's try
    print(summarize_active_window())

    print("\n--- Testing copy/move ---")
    test_file = Path.home() / "Desktop" / "test_chitti.txt"
    test_file.write_text("Hello Chitti")
    
    print(copy_item(str(test_file), "documents/test_chitti_copy.txt"))
    print(move_item("documents/test_chitti_copy.txt", "desktop/test_chitti_moved.txt"))
    
    # Cleanup
    if test_file.exists(): test_file.unlink()
    moved_file = Path.home() / "Desktop" / "test_chitti_moved.txt"
    if moved_file.exists(): moved_file.unlink()
    print("\nTests completed.")

if __name__ == "__main__":
    try:
        test_tools()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
