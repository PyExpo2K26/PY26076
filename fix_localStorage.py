#!/usr/bin/env python
"""
Utility script to fix localStorage issues by clearing corrupted session data
"""

import json
import os

def clear_session_data():
    """Clear application session data"""
    print("🔧 Clearing session data...\n")
    
    # Files to check
    files = [
        "infini_think_chat_log.json",
        "conversations.json",
        "user_credentials.json"
    ]
    
    # Check if files exist
    for file in files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"✅ Found: {file} ({size} bytes)")
        else:
            print(f"⚠️  Not found: {file}")
    
    print("\n📋 Instructions to clear browser localStorage:")
    print("1. Open browser DevTools (F12)")
    print("2. Go to 'Application' tab")
    print("3. Click 'Local Storage'")
    print("4. Select 'http://localhost:5000' or 'file://...'")
    print("5. Look for 'currentUser' and 'loginTime'")
    print("6. Delete both entries")
    print("7. Refresh page (Ctrl+R)")
    print("\n✅ Login page should now be visible")

if __name__ == "__main__":
    clear_session_data()
