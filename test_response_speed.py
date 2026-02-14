#!/usr/bin/env python3
"""Test response speed and display"""
import requests
import time
import json

BASE_URL = "http://localhost:5000"

print("=" * 60)
print("🔥 RESPONSE SPEED TEST")
print("=" * 60)

# Test 1: Quick response test
print("\n[TEST 1] Send message and measure response time...")
start = time.time()
try:
    response = requests.post(
        f"{BASE_URL}/api/chat",
        json={"message": "Hello", "conversation_id": "test"},
        timeout=10
    )
    elapsed = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Response received in {elapsed:.2f} seconds")
        print(f"   Status: {response.status_code}")
        print(f"   Reply: {data.get('reply', 'NO REPLY')[:100]}...")
        
        if elapsed > 5:
            print(f"⚠️  Response took {elapsed:.1f}s - may feel slow to user")
        else:
            print(f"✅ Response time is good ({elapsed:.2f}s)")
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
except Exception as e:
    elapsed = time.time() - start
    print(f"❌ Error after {elapsed:.2f}s: {e}")

# Test 2: Multiple messages rapidly
print("\n[TEST 2] Send 3 messages rapidly...")
for i in range(1, 4):
    start = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": f"Message {i}", "conversation_id": "test"},
            timeout=10
        )
        elapsed = time.time() - start
        if response.status_code == 200:
            data = response.json()
            reply = data.get('reply', 'NO REPLY')[:50]
            print(f"   [{i}] {elapsed:.2f}s → {reply}...")
        else:
            print(f"   [{i}] Error {response.status_code}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"   [{i}] Error after {elapsed:.2f}s: {e}")

print("\n" + "=" * 60)
print("✅ TEST COMPLETE")
print("=" * 60)
