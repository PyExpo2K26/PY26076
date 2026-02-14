#!/usr/bin/env python
"""
Quick test script to verify login system is working
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_login_system():
    print("\n" + "="*60)
    print("🔥 INFINI THINK - LOGIN SYSTEM TEST")
    print("="*60)
    
    time.sleep(2)  # Wait for server to be ready
    
    # Test 1: Check if server is running
    print("\n[TEST 1] Server Connectivity")
    print("-" * 60)
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Server is running (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return False
    
    # Test 2: Login with existing user
    print("\n[TEST 2] Login with Existing User")
    print("-" * 60)
    try:
        response = requests.post(f"{BASE_URL}/api/login", json={
            "username": "TestUser",
            "password": "default123"
        })
        result = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            print("✅ Existing user login SUCCESSFUL!")
        else:
            print("❌ Existing user login FAILED!")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Register a new user
    print("\n[TEST 3] Register New User")
    print("-" * 60)
    try:
        timestamp = str(int(time.time()))
        new_user = {
            "username": f"testuser_{timestamp}",
            "email": f"test_{timestamp}@example.com",
            "password": "TestPass123"
        }
        
        response = requests.post(f"{BASE_URL}/api/register", json=new_user)
        result = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            print("✅ New user registration SUCCESSFUL!")
            
            # Test 4: Login with new user
            print("\n[TEST 4] Login with New User")
            print("-" * 60)
            time.sleep(1)
            response = requests.post(f"{BASE_URL}/api/login", json={
                "username": new_user['username'],
                "password": new_user['password']
            })
            result = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(result, indent=2)}")
            
            if result.get('success'):
                print("✅ New user login SUCCESSFUL!")
            else:
                print("❌ New user login FAILED!")
        else:
            print("❌ New user registration FAILED!")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: Invalid credentials
    print("\n[TEST 5] Invalid Credentials Test")
    print("-" * 60)
    try:
        response = requests.post(f"{BASE_URL}/api/login", json={
            "username": "NonexistentUser",
            "password": "WrongPassword"
        })
        result = response.json()
        print(f"Status Code: {response.status_code}")
        
        if not result.get('success'):
            print("✅ Invalid credentials correctly rejected!")
        else:
            print("❌ Invalid credentials should have been rejected!")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 6: Test chat endpoint with authentication
    print("\n[TEST 6] Chat API Test")
    print("-" * 60)
    try:
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "message": "Hello!",
            "conversation_id": "test-conv"
        })
        result = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Message Response: {result.get('reply', 'N/A')[:100]}...")
        
        if result.get('success'):
            print("✅ Chat API working!")
        else:
            print("⚠️ Chat API response: " + result.get('error', 'Unknown error'))
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*60)
    print("✅ LOGIN SYSTEM TEST COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_login_system()
