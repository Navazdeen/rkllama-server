#!/usr/bin/env python3
"""
Comprehensive test suite for RKLLM Server and Demo Scripts

This script validates:
1. Build scripts syntax
2. Demo script syntax
3. Server endpoints
4. Chat API functionality
5. Tool calling functionality
"""

import json
import subprocess
import sys
from pathlib import Path

import requests

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

SERVER_URL = "http://localhost:8080"
TESTS_PASSED = 0
TESTS_FAILED = 0


def print_header(text):
    """Print a formatted header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


def test_pass(message):
    """Print passing test."""
    global TESTS_PASSED
    TESTS_PASSED += 1
    print(f"{GREEN}✅ PASS{RESET}: {message}")


def test_fail(message, error=""):
    """Print failing test."""
    global TESTS_FAILED
    TESTS_FAILED += 1
    print(f"{RED}❌ FAIL{RESET}: {message}")
    if error:
        print(f"   {RED}Error: {error}{RESET}")


def run_command(cmd, description=""):
    """Run a shell command and return status."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timeout"
    except Exception as e:
        return False, "", str(e)


def check_file_syntax(filepath, description):
    """Check Python file syntax."""
    success, stdout, stderr = run_command(f"python3 -m py_compile {filepath}")
    if success:
        test_pass(f"Syntax check: {description}")
    else:
        test_fail(f"Syntax check: {description}", stderr)
    return success


def check_server_health():
    """Check if server is running and healthy."""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                test_pass(f"Server health check: {data.get('model')} model running")
                return True
        test_fail("Server health check", f"Unexpected response: {response.text}")
    except requests.exceptions.ConnectionError:
        test_fail("Server health check", "Cannot connect to server")
    except Exception as e:
        test_fail("Server health check", str(e))
    return False


def test_chat_endpoint():
    """Test /api/chat endpoint."""
    try:
        response = requests.post(
            f"{SERVER_URL}/api/chat",
            json={
                "model": "qwen",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False
            },
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            if "message" in data and "content" in data["message"]:
                test_pass("Chat API: Basic chat works")
                return True
        test_fail("Chat API: Basic chat", f"Status {response.status_code}")
    except Exception as e:
        test_fail("Chat API: Basic chat", str(e))
    return False


def test_tools_set_endpoint():
    """Test /api/tools/set endpoint."""
    try:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {
                        "type": "object",
                        "properties": {"param": {"type": "string"}},
                        "required": ["param"]
                    }
                }
            }
        ]
        response = requests.post(
            f"{SERVER_URL}/api/tools/set",
            json={"tools": tools},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                test_pass("Tools API: Tool registration works")
                return True
        test_fail("Tools API: Tool registration", f"Status {response.status_code}")
    except Exception as e:
        test_fail("Tools API: Tool registration", str(e))
    return False


def test_tools_call_endpoint():
    """Test /api/tools/call endpoint."""
    try:
        # First register a tool
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_info",
                    "description": "Get information",
                    "parameters": {
                        "type": "object",
                        "properties": {"topic": {"type": "string"}},
                        "required": ["topic"]
                    }
                }
            }
        ]
        requests.post(f"{SERVER_URL}/api/tools/set", json={"tools": tools}, timeout=30)
        
        # Now call tool
        response = requests.post(
            f"{SERVER_URL}/api/tools/call",
            json={"prompt": "Tell me about weather", "stream": False},
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            if "response" in data:
                test_pass("Tools API: Tool calling works")
                return True
        test_fail("Tools API: Tool calling", f"Status {response.status_code}")
    except Exception as e:
        test_fail("Tools API: Tool calling", str(e))
    return False


def test_generate_endpoint():
    """Test /api/generate endpoint (backward compatibility)."""
    try:
        response = requests.post(
            f"{SERVER_URL}/api/generate",
            json={
                "model": "qwen",
                "prompt": "Hello",
                "stream": False
            },
            timeout=60
        )
        if response.status_code == 200:
            test_pass("API: /api/generate endpoint works (backward compatible)")
            return True
        test_fail("API: /api/generate endpoint", f"Status {response.status_code}")
    except Exception as e:
        test_fail("API: /api/generate endpoint", str(e))
    return False


def test_tags_endpoint():
    """Test /api/tags endpoint."""
    try:
        response = requests.get(f"{SERVER_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "models" in data and isinstance(data["models"], list):
                test_pass("API: /api/tags endpoint works")
                return True
        test_fail("API: /api/tags endpoint", f"Status {response.status_code}")
    except Exception as e:
        test_fail("API: /api/tags endpoint", str(e))
    return False


def main():
    """Run all tests."""
    print_header("🧪 RKLLM Server - Complete Test Suite")
    
    base_dir = Path("/home/navazdeen/rkllama-server")
    
    # Test 1: Build Scripts
    print_header("Build Scripts Validation")
    
    # Check shell script syntax
    success, _, _ = run_command(f"bash -n {base_dir}/build_rkllm_server_flask.sh")
    if success:
        test_pass("Build script syntax: Flask build script")
    else:
        test_fail("Build script syntax: Flask build script")
    
    success, _, _ = run_command(f"bash -n {base_dir}/build_rkllm_server_gradio.sh")
    if success:
        test_pass("Build script syntax: Gradio build script")
    else:
        test_fail("Build script syntax: Gradio build script")
    
    # Verify they're executable
    success, _, _ = run_command(f"test -x {base_dir / 'build_rkllm_server_flask.sh'}")
    if success:
        test_pass("Build scripts: executable permissions")
    else:
        test_fail("Build scripts: executable permissions")
    
    # Test 2: Demo Scripts
    print_header("Demo Scripts Validation")
    check_file_syntax(str(base_dir / "demo/chat_api_flask.py"), "Flask chat API demo")
    check_file_syntax(str(base_dir / "demo/chat_api_gradio.py"), "Gradio chat API demo")
    
    # Test 3: Server Health
    print_header("Server Health & Connectivity")
    if not check_server_health():
        print(f"\n{YELLOW}⚠️  Server not running. Skipping API tests.{RESET}")
        print(f"{YELLOW}Start the server with:{RESET}")
        print(f"  cd {base_dir}/rkllm_server")
        print(f"  python3 flask_server.py --model_path ~/models/qwen.rkllm --platform rk3588")
    else:
        # Test 4: API Endpoints
        print_header("API Endpoints Testing")
        test_tags_endpoint()
        test_generate_endpoint()
        test_chat_endpoint()
        test_tools_set_endpoint()
        test_tools_call_endpoint()
    
    # Test 5: Build Script Help
    print_header("Build Scripts Help & Documentation")
    success, stdout, _ = run_command(f"{base_dir}/build_rkllm_server_flask.sh --help")
    if success and "--model_path" in stdout:
        test_pass("Flask build script: help documentation available")
    else:
        test_fail("Flask build script: help documentation")
    
    success, stdout, _ = run_command(f"{base_dir}/build_rkllm_server_gradio.sh --help")
    if success and "--local" in stdout:
        test_pass("Gradio build script: local mode documented")
    else:
        test_fail("Gradio build script: local mode documentation")
    
    # Summary
    print_header("📊 Test Summary")
    total = TESTS_PASSED + TESTS_FAILED
    print(f"Total Tests: {total}")
    print(f"{GREEN}Passed: {TESTS_PASSED}{RESET}")
    print(f"{RED}Failed: {TESTS_FAILED}{RESET}")
    
    if TESTS_FAILED == 0:
        print(f"\n{GREEN}{'='*60}{RESET}")
        print(f"{GREEN}{'✅ ALL TESTS PASSED!'.center(60)}{RESET}")
        print(f"{GREEN}{'='*60}{RESET}\n")
        return 0
    else:
        print(f"\n{RED}{'='*60}{RESET}")
        print(f"{RED}{f'{TESTS_FAILED} Tests Failed'.center(60)}{RESET}")
        print(f"{RED}{'='*60}{RESET}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())