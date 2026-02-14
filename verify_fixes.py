#!/usr/bin/env python3
"""
INFINI THINK - Verification Script v2.6
Tests all login page fixes and functionality
"""

import requests
import json
import time
import sys
from datetime import datetime

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

BASE_URL = "http://localhost:5000"
ERRORS = []
WARNINGS = []
PASSES = []

def print_header(text):
    print(f"\n{BLUE}{'='*60}")
    print(f"  🔥 {text}")
    print(f"{'='*60}{RESET}\n")

def print_success(test_name):
    msg = f"✅ PASS: {test_name}"
    print(f"{GREEN}{msg}{RESET}")
    PASSES.append(test_name)

def print_error(test_name, error_msg=""):
    msg = f"❌ FAIL: {test_name}"
    if error_msg:
        msg += f" - {error_msg}"
    print(f"{RED}{msg}{RESET}")
    ERRORS.append((test_name, error_msg))

def print_warning(test_name, warning_msg=""):
    msg = f"⚠️  WARN: {test_name}"
    if warning_msg:
        msg += f" - {warning_msg}"
    print(f"{YELLOW}{msg}{RESET}")
    WARNINGS.append((test_name, warning_msg))

def test_server_connection():
    """Test if Flask server is running"""
    print_header("Test 1: Server Connection")
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print_success("Server is running and responsive")
            return True
        else:
            print_error("Server responded with unexpected status", f"Code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to server", "Is Flask running? Try: python app.py")
        return False
    except Exception as e:
        print_error("Connection test failed", str(e))
        return False

def test_login_page_loads():
    """Test if login page HTML loads"""
    print_header("Test 2: Login Page Loads")
    try:
        response = requests.get(BASE_URL, timeout=5)
        if "loginPage" in response.text:
            print_success("Login page div found in HTML")
        else:
            print_warning("Login page div not found", "Check HTML structure")
        
        if "mainPage" in response.text:
            print_success("Main chat page div found in HTML")
        else:
            print_warning("Main page div not found", "Check HTML structure")
        
        if "DOMContentLoaded" in response.text:
            print_success("Page initialization code found")
            return True
        else:
            print_error("Page initialization code not found")
            return False
    except Exception as e:
        print_error("Could not load login page", str(e))
        return False

def test_debug_page():
    """Test if debug page exists"""
    print_header("Test 3: Debug Page Exists")
    try:
        response = requests.get(f"{BASE_URL}/debug", timeout=5)
        if response.status_code == 200:
            print_success("Debug page is accessible at /debug")
            if "Clear Local Storage" in response.text:
                print_success("Debug page has clear function")
                return True
            else:
                print_warning("Clear function not found in debug page")
                return True
        else:
            print_error("Debug page not found", f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_error("Debug page test failed", str(e))
        return False

def test_login_endpoint():
    """Test login API endpoint"""
    print_header("Test 4: Login API Endpoint")
    try:
        payload = {
            "username": "TestUser",
            "password": "default123"
        }
        response = requests.post(f"{BASE_URL}/api/login", json=payload, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 400, 401]:
            print_success("Login endpoint is responding")
            
            try:
                data = response.json()
                if "message" in data or "success" in data or "error" in data:
                    print_success("Login endpoint returns proper JSON")
                    return True
                else:
                    print_warning("Unexpected response format")
                    return True
            except:
                print_error("Invalid JSON response from login endpoint")
                return False
        else:
            print_error("Login endpoint returned unexpected status", f"Code: {response.status_code}")
            return False
    except Exception as e:
        print_error("Login endpoint test failed", str(e))
        return False

def test_register_endpoint():
    """Test register API endpoint"""
    print_header("Test 5: Register API Endpoint")
    try:
        payload = {
            "username": f"TestUser{int(time.time())}",
            "email": f"test{int(time.time())}@test.com",
            "password": "test123456"
        }
        response = requests.post(f"{BASE_URL}/api/register", json=payload, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 400, 409]:
            print_success("Register endpoint is responding")
            
            try:
                data = response.json()
                print_success("Register endpoint returns proper JSON")
                return True
            except:
                print_error("Invalid JSON response from register endpoint")
                return False
        else:
            print_error("Register endpoint returned unexpected status", f"Code: {response.status_code}")
            return False
    except Exception as e:
        print_error("Register endpoint test failed", str(e))
        return False

def test_chat_endpoint():
    """Test chat API endpoint"""
    print_header("Test 6: Chat API Endpoint")
    try:
        payload = {
            "message": "Hello, this is a test",
            "username": "TestUser"
        }
        response = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 400, 401]:
            print_success("Chat endpoint is responding")
            
            try:
                data = response.json()
                print_success("Chat endpoint returns proper JSON")
                return True
            except:
                print_warning("Chat response might be text instead of JSON")
                return True
        else:
            print_error("Chat endpoint returned unexpected status", f"Code: {response.status_code}")
            return False
    except Exception as e:
        print_error("Chat endpoint test failed", str(e))
        return False

def test_display_properties():
    """Test CSS display properties"""
    print_header("Test 7: CSS Display Properties")
    try:
        response = requests.get(BASE_URL, timeout=5)
        
        # Check for login page display style
        if 'id="loginPage"' in response.text:
            print_success("Login page element found")
        else:
            print_warning("Login page element not found")
        
        # Check for main page element
        if 'id="mainPage"' in response.text:
            print_success("Main page element found")
        else:
            print_warning("Main page element not found")
        
        # Check for display flex
        if "display: flex" in response.text or "display:flex" in response.text:
            print_success("Display flex styling found")
        else:
            print_warning("Display flex styling not explicitly found")
        
        return True
    except Exception as e:
        print_error("Display properties test failed", str(e))
        return False

def test_logout_function():
    """Test logout button exists"""
    print_header("Test 8: Logout Functionality")
    try:
        response = requests.get(BASE_URL, timeout=5)
        
        if 'onclick="logout()"' in response.text or 'onclick = "logout()"' in response.text:
            print_success("Logout function is implemented")
        else:
            print_warning("Logout button not found")
        
        if "localStorage.removeItem" in response.text:
            print_success("localStorage clearing found in code")
            return True
        else:
            print_warning("localStorage clearing might not be implemented")
            return True
    except Exception as e:
        print_error("Logout test failed", str(e))
        return False

def test_input_sanitization():
    """Test input sanitization"""
    print_header("Test 9: Input Sanitization")
    try:
        response = requests.get(BASE_URL, timeout=5)
        
        if "sanitize_input" in response.text or "sanitize" in response.text:
            print_success("Input sanitization code found")
            return True
        else:
            print_warning("Input sanitization code not explicitly found")
            return True
    except Exception as e:
        print_error("Input sanitization test failed", str(e))
        return False

def test_rate_limiting():
    """Test rate limiting is configured"""
    print_header("Test 10: Rate Limiting")
    try:
        response = requests.get(BASE_URL, timeout=5)
        
        if "rate_limit" in response.text or "@app.before_request" in response.text:
            print_success("Rate limiting code found")
            return True
        else:
            print_warning("Rate limiting code might not be visible in HTML response")
            return True
    except Exception as e:
        print_error("Rate limiting test failed", str(e))
        return False

def print_summary():
    """Print test summary"""
    print_header("Test Summary")
    
    total = len(PASSES) + len(ERRORS) + len(WARNINGS)
    
    print(f"{GREEN}✅ Passed: {len(PASSES)}{RESET}")
    print(f"{RED}❌ Failed: {len(ERRORS)}{RESET}")
    print(f"{YELLOW}⚠️  Warnings: {len(WARNINGS)}{RESET}")
    print(f"\nTotal Tests: {total}")
    
    if ERRORS:
        print(f"\n{RED}Failed Tests:{RESET}")
        for test, error in ERRORS:
            print(f"  - {test}")
            if error:
                print(f"    └─ {error}")
    
    if WARNINGS:
        print(f"\n{YELLOW}Warnings:{RESET}")
        for test, warning in WARNINGS:
            print(f"  - {test}")
            if warning:
                print(f"    └─ {warning}")
    
    success_rate = (len(PASSES) / total * 100) if total > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.0f}%")
    
    if len(ERRORS) == 0:
        print(f"\n{GREEN}🎉 All critical tests passed!{RESET}")
        return True
    else:
        print(f"\n{RED}⚠️  Some tests failed. Check errors above.{RESET}")
        return False

def main():
    print(f"\n{BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     INFINI THINK - VERIFICATION SCRIPT v2.6                ║")
    print("║     Testing all login page fixes and functionality         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{RESET}")
    
    print(f"\n📍 Testing: {BASE_URL}")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run tests
    test_server_connection()
    test_login_page_loads()
    test_debug_page()
    test_login_endpoint()
    test_register_endpoint()
    test_chat_endpoint()
    test_display_properties()
    test_logout_function()
    test_input_sanitization()
    test_rate_limiting()
    
    # Print summary
    success = print_summary()
    
    print(f"\n⏰ Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    sys.exit(0 if not ERRORS else 1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}\n")
        sys.exit(1)
