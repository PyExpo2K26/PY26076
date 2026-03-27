import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path.cwd()))

from infini_think.tools.file_tools import list_directory, copy_item, move_item
from infini_think.tools.system_tools import get_process_list

def test_core_tools():
    print("--- Testing list_directory ---")
    print(list_directory("home"))
    
    print("\n--- Testing get_process_list ---")
    print(get_process_list())
    
    print("\n--- Testing copy/move ---")
    # Use project-local tmp for testing
    tmp_file = Path.cwd() / "test_simple.txt"
    tmp_file.write_text("Test Content")
    
    print(copy_item(str(tmp_file), "test_simple_copy.txt"))
    print(move_item("test_simple_copy.txt", "test_simple_moved.txt"))
    
    # Cleanup
    if tmp_file.exists(): tmp_file.unlink()
    moved_file = Path.cwd() / "test_simple_moved.txt"
    if moved_file.exists(): moved_file.unlink()
    print("\nCore tests completed.")

if __name__ == "__main__":
    test_core_tools()
