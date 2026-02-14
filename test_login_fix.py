#!/usr/bin/env python
"""
Test script to verify login functionality works for both new and existing users
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_login_system():
    print("=" * 60)
    print("🔥 INFINI THINK - LOGIN SYSTEM TEST")
    print("=" * 60)
    
    # Test 1: Register a new user
    print("\n[TEST 1] Register New User")
    print("-" * 60)
    new_user = {
        "username": "testuser_" + str(int(__import__('time').time())),
        "email": f"test_{int(__import__('time').time())}@example.com",
        "password": "TestPassword123"
    }
    
    response = requests.post(f"{BASE_URL}/api/register", json=new_user)
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        print("✅ New user registration successful!")
        new_username = new_user['username']
        new_password = new_user['password']
    else:
        print("❌ Registration failed!")
        return False
    
    # Test 2: Login with new user
    print("\n[TEST 2] Login with New User")
    print("-" * 60)
    response = requests.post(f"{BASE_URL}/api/login", json={
        "username": new_username,
        "password": new_password
    })
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        print("✅ New user login successful!")
    else:
        print("❌ New user login failed!")
        return False
    
    # Test 3: Login with existing user (TestUser - legacy user)
    print("\n[TEST 3] Login with Legacy/Existing User (TestUser)")
    print("-" * 60)
    response = requests.post(f"{BASE_URL}/api/login", json={
        "username": "TestUser",
        "password": "default123"
    })
    result = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if result.get('success'):
        print("✅ Legacy user login successful!")
    else:
        print("❌ Legacy user login failed!")
        return False
    
    # Test 4: Email validation
    print("\n[TEST 4] Email Validation Test")
    print("-" * 60)
    
    invalid_emails = [
        {"email": "notanemail", "desc": "No @ symbol"},
        {"email": "user@", "desc": "No domain"},
        {"email": "@example.com", "desc": "No username"},
        {"email": "user@example", "desc": "No extension"}
    ]
    
    for test_case in invalid_emails:
        response = requests.post(f"{BASE_URL}/api/register", json={
            "username": "tempuser",
            "email": test_case['email'],
            "password": "Password123"
        })
        result = response.json()
        status = "✅ Correctly rejected" if not result.get('success') else "❌ Should have been rejected"
        print(f"{test_case['desc']}: {test_case['email']} -> {status}")
    
    # Test 5: Valid email
    print("\n[TEST 5] Valid Email Registration")
    print("-" * 60)
    
    valid_email = {
        "username": "validuser_" + str(int(__import__('time').time())),
        "email": f"valid.user+{int(__import__('time').time())}@company.co.uk",
        "password": "ValidPass123"
    }
    
    response = requests.post(f"{BASE_URL}/api/register", json=valid_email)
    result = response.json()
    status = "✅ Successfully registered" if result.get('success') else "❌ Failed to register"
    print(f"Email: {valid_email['email']} -> {status}")
    
    print("\n" + "=" * 60)
    print("✨ LOGIN SYSTEM TEST COMPLETE ✨")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        test_login_system()
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("Make sure the Flask server is running on http://localhost:5000")
