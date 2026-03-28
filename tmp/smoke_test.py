import sys
from pathlib import Path

# Add project root to sys.path
root = Path(r"c:\Users\KiTE\OneDrive\Desktop\PY26076")
sys.path.append(str(root))

try:
    print("Checking Tool Imports...")
    from infini_think.tools import (
        app_tools, 
        file_tools, 
        intelligence_tools, 
        system_tools, 
        web_tools, 
        window_tools
    )
    print("✅ All tool modules imported successfully.")
    
    # Check registration in Executor
    from infini_think.core.executor import Executor
    from infini_think.core.ai_engine import AIEngine
    
    engine = AIEngine()
    ex = Executor() 
    
    # It's _registry, not _tools
    print(f"✅ Executor initialized with {len(ex._registry)} registered tools.")
    
    # Check specific critical tools
    critical_tools = [
        "summarize_active_window", 
        "analyze_active_window", 
        "summarize_content", 
        "run_terminal_command"
    ]
    for ct in critical_tools:
        if ct in ex._registry:
            print(f"✅ Tool '{ct}' is registered.")
        else:
            print(f"❌ Tool '{ct}' is MISSING from registration.")
            
    print("\nVerification Complete.")
except Exception as e:
    print(f"❌ Verification FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
