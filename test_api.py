#!/usr/bin/env python
"""Test script to verify the chat API works correctly."""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_health():
    """Test if server is running."""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        return response.status_code == 200
    except:
        return False

def test_chat():
    """Test the chat endpoint."""
    try:
        payload = {"message": "Hello, how are you?"}
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(data, indent=2)}")
        return data.get('success', False)
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_history():
    """Test the history endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/api/history", timeout=5)
        data = response.json()
        print(f"History: {len(data.get('history', []))} items")
        return data.get('success', False)
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    print("Testing Infini Think Chat API...")
    print("-" * 50)
    
    if not test_health():
        print("❌ Server is not running on http://localhost:5000")
        print("Start the server with: python app.py")
        exit(1)
    
    print("✅ Server is running")
    print("-" * 50)
    
    print("\n📨 Testing chat endpoint...")
    if test_chat():
        print("✅ Chat endpoint works")
    else:
        print("❌ Chat endpoint failed")
    
    print("\n📚 Testing history endpoint...")
    if test_history():
        print("✅ History endpoint works")
    else:
        print("❌ History endpoint failed")
    
    print("-" * 50)
    print("✅ All tests completed!")
