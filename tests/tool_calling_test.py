#!/usr/bin/env python3
"""
Tool Calling API Test - Comprehensive Testing

This script demonstrates how to use the tool calling API.
"""

import json

import requests

BASE_URL = "http://localhost:8080"

def test_1_set_tools():
    """Test 1: Set tools for the model"""
    print("\n" + "="*70)
    print("TEST 1: Set Tools")
    print("="*70)
    
    tools = [
        {
            "name": "get_weather",
            "description": "Get the current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }
    ]
    
    payload = {
        "system_prompt": "You are a helpful assistant with access to weather tools. When asked about weather, ALWAYS use the get_weather tool to get accurate information.",
        "tools": tools,
        "tool_choice": "auto"
    }
    
    response = requests.post(f"{BASE_URL}/api/tools/set", json=payload)
    result = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(result, indent=2)}")
    return response.status_code == 200


def test_2_basic_tool_call():
    """Test 2: Basic tool call"""
    print("\n" + "="*70)
    print("TEST 2: Basic Tool Call")
    print("="*70)
    
    payload = {
        "prompt": "What is the weather in Paris?",
        "stream": False
    }
    
    response = requests.post(f"{BASE_URL}/api/tools/call", json=payload, timeout=300)
    result = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {result.get('response', '')[:500]}")
    print(f"Tool Calls Found: {len(result.get('tool_calls', []))}")
    
    if result.get('tool_calls'):
        print("\nTool Calls:")
        for call in result['tool_calls']:
            print(f"  - {call['name']}: {json.dumps(call.get('arguments', {}))}")
    
    return response.status_code == 200


def test_3_regular_generation():
    """Test 3: Regular text generation (no tools)"""
    print("\n" + "="*70)
    print("TEST 3: Regular Text Generation (No Tools)")
    print("="*70)
    
    payload = {
        "model": "qwen",
        "prompt": "Write a short haiku about programming",
        "stream": False
    }
    
    response = requests.post(f"{BASE_URL}/api/generate", json=payload, timeout=300)
    result = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {result.get('response', '')}")
    print(f"Tokens Generated: {result.get('eval_count', 0)}")
    
    return response.status_code == 200


def test_4_chat_interface():
    """Test 4: Chat interface"""
    print("\n" + "="*70)
    print("TEST 4: Chat Interface")
    print("="*70)
    
    payload = {
        "model": "qwen",
        "messages": [
            {"role": "user", "content": "What can you tell me about RKLLM?"}
        ],
        "stream": False
    }
    
    response = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=300)
    result = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {result.get('message', {}).get('content', '')[:300]}...")
    print(f"Tokens Generated: {result.get('eval_count', 0)}")
    
    return response.status_code == 200


def test_5_list_tools():
    """Test 5: Check server endpoints"""
    print("\n" + "="*70)
    print("TEST 5: Server Endpoints")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/")
    result = response.json()
    
    print(f"Status Code: {response.status_code}")
    print(f"Server: {result.get('name')}")
    print(f"Model: {result.get('model')}")
    print(f"\nAvailable Endpoints:")
    for endpoint, description in result.get('endpoints', {}).items():
        print(f"  - {endpoint}: {description}")
    
    return response.status_code == 200


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🤖 RKLLM Tool Calling API Test Suite")
    print("="*70)
    
    # Check server health
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ Server is running")
        else:
            print("✗ Server returned unexpected status")
            exit(1)
    except Exception as e:
        print(f"✗ Cannot reach server: {e}")
        exit(1)
    
    # Run tests
    tests = [
        ("Set Tools", test_1_set_tools),
        ("Basic Tool Call", test_2_basic_tool_call),
        ("Regular Generation", test_3_regular_generation),
        ("Chat Interface", test_4_chat_interface),
        ("Server Endpoints", test_5_list_tools)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "✓ PASS" if result else "✗ FAIL"))
        except Exception as e:
            print(f"\n✗ Error: {e}")
            results.append((name, f"✗ ERROR: {str(e)[:50]}"))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for name, result in results:
        print(f"{result:12} - {name}")
    
    print("="*70 + "\n")
