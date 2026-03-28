import sys
import os
from pathlib import Path

# Add project root to sys.path
root = Path(r"c:\Users\KiTE\OneDrive\Desktop\PY26076")
sys.path.append(str(root))

from infini_think.core.executor import Executor

def test_crud():
    ex = Executor()
    test_dir = root / "tmp" / "crud_test_root"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    test_file = "test_crud_file.txt"
    test_path = str(test_dir / test_file)
    content = "Hello InfiniThink CRUD Test!"
    
    print(f"--- Starting CRUD Tests in {test_dir} ---")
    
    # 1. CREATE
    print("\n[1/5] Testing CREATE (write_file)...")
    res = ex.execute({"tool": "write_file", "args": [test_path, content]})
    print(f"Result: {res['output']}")
    if not res['success'] or not Path(test_path).exists():
        print("❌ CREATE FAILED")
        return

    # 2. READ
    print("\n[2/5] Testing READ (read_file)...")
    res = ex.execute({"tool": "read_file", "args": [test_path]})
    print(f"Result: {res['output']}")
    if content not in res['output']:
        print("❌ READ FAILED")
        return

    # 3. RENAME
    print("\n[3/5] Testing RENAME (rename_item)...")
    new_name = "renamed_test_crud.txt"
    res = ex.execute({"tool": "rename_item", "args": [test_path, new_name]})
    print(f"Result: {res['output']}")
    renamed_path = test_dir / new_name
    if not renamed_path.exists():
        print("❌ RENAME FAILED")
        return

    # 4. SEARCH
    print("\n[4/5] Testing SEARCH (search_files)...")
    # Search for renamed file
    res = ex.execute({"tool": "search_files", "args": [new_name, str(test_dir)]})
    print(f"Result: {res['output']}")
    if new_name not in res['output']:
        print("❌ SEARCH FAILED")
        return

    # 5. DELETE
    print("\n[5/5] Testing DELETE (delete_file)...")
    res = ex.execute({"tool": "delete_file", "args": [str(renamed_path)]})
    print(f"Result: {res['output']}")
    if renamed_path.exists():
        print("❌ DELETE FAILED")
        return

    print("\n✅ ALL CRUD TESTS PASSED SUCCESSFULLY.")

if __name__ == "__main__":
    try:
        test_crud()
    except Exception as e:
        print(f"❌ TEST CRASHED: {e}")
        import traceback
        traceback.print_exc()
