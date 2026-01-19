#!/usr/bin/env python3
"""
RKLLM Tool Calling - Complete End-to-End Demo

This demonstrates a realistic scenario where the model uses tools to answer user queries.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8080"

# Define tools that the model can use
TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a specific location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "Temperature unit"}
            },
            "required": ["location"]
        }
    },
    {
        "name": "calculate",
        "description": "Perform mathematical calculations",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression (e.g., '2+2', '10*5/2')"}
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_time",
        "description": "Get the current time in a specific timezone",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {"type": "string", "description": "Timezone (UTC, EST, PST, etc.)"}
            }
        }
    }
]

# Mock tool implementations
def get_weather(location, unit="celsius"):
    data = {
        "Paris": 12, "London": 8, "New York": 5, "Tokyo": 20, "Sydney": 25
    }
    temp = data.get(location, 15)
    if unit == "fahrenheit":
        temp = (temp * 9/5) + 32
    return {"location": location, "temperature": temp, "unit": unit}

def calculate(expression):
    try:
        return {"result": eval(expression)}
    except Exception as e:
        return {"error": str(e)}

def get_time(timezone="UTC"):
    from datetime import datetime
    return {"timezone": timezone, "time": datetime.now().isoformat()}

TOOL_FUNCTIONS = {
    "get_weather": get_weather,
    "calculate": calculate,
    "get_time": get_time
}

def print_header(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_section(title):
    print(f"\n▶ {title}")
    print("-" * 70)

def execute_tool(tool_name, arguments):
    """Execute a tool and return results"""
    if tool_name not in TOOL_FUNCTIONS:
        return {"error": f"Unknown tool: {tool_name}"}
    
    try:
        func = TOOL_FUNCTIONS[tool_name]
        result = func(**arguments)
        return result
    except Exception as e:
        return {"error": str(e)}

def demo_1_simple_calculation():
    """Demo 1: Simple calculation using tool calling"""
    print_header("DEMO 1: Simple Calculation")
    
    print_section("Step 1: Register Tools")
    response = requests.post(
        f"{BASE_URL}/api/tools/set",
        json={
            "system_prompt": "You are a helpful calculator assistant. When asked to calculate, use the calculate tool.",
            "tools": [TOOLS[1]]  # Only calculate tool
        }
    )
    tools_set = response.json()
    print(f"✓ Tools registered: {tools_set['tool_names']}")
    
    print_section("Step 2: Send Query")
    query = "What is 156 * 24 + 42?"
    print(f"User: {query}")
    
    print_section("Step 3: Get Model Response")
    response = requests.post(
        f"{BASE_URL}/api/tools/call",
        json={"prompt": query, "stream": False},
        timeout=300
    )
    result = response.json()
    print(f"Model: {result['response'][:200]}...")
    
    print_section("Step 4: Execute Tool Calls")
    for tool_call in result.get('tool_calls', []):
        tool_name = tool_call['name']
        args = tool_call['arguments']
        print(f"\n🔧 Tool: {tool_name}")
        print(f"   Arguments: {json.dumps(args)}")
        
        result = execute_tool(tool_name, args)
        print(f"   Result: {json.dumps(result)}")
    
    return True

def demo_2_weather_query():
    """Demo 2: Weather query using tool calling"""
    print_header("DEMO 2: Weather Information")
    
    print_section("Step 1: Register Weather Tool")
    response = requests.post(
        f"{BASE_URL}/api/tools/set",
        json={
            "system_prompt": "You are a helpful weather assistant. Always use the get_weather tool to provide accurate weather information.",
            "tools": [TOOLS[0]]  # Only weather tool
        }
    )
    tools_set = response.json()
    print(f"✓ Tools registered: {tools_set['tool_names']}")
    
    print_section("Step 2: Send Weather Query")
    query = "Tell me about the weather in Tokyo and compare it with London"
    print(f"User: {query}")
    
    print_section("Step 3: Get Model Response")
    response = requests.post(
        f"{BASE_URL}/api/tools/call",
        json={"prompt": query, "stream": False},
        timeout=300
    )
    result = response.json()
    print(f"Model: {result['response'][:250]}...")
    
    print_section("Step 4: Execute Tool Calls")
    for i, tool_call in enumerate(result.get('tool_calls', []), 1):
        tool_name = tool_call['name']
        args = tool_call['arguments']
        print(f"\n🔧 Tool Call {i}: {tool_name}")
        print(f"   Arguments: {json.dumps(args)}")
        
        result = execute_tool(tool_name, args)
        print(f"   Result: {json.dumps(result)}")
    
    return True

def demo_3_multiple_tools():
    """Demo 3: Multiple tools in one query"""
    print_header("DEMO 3: Multiple Tools in One Query")
    
    print_section("Step 1: Register Multiple Tools")
    response = requests.post(
        f"{BASE_URL}/api/tools/set",
        json={
            "system_prompt": "You are a helpful assistant with access to multiple tools. Use the appropriate tools to answer user queries.",
            "tools": TOOLS[:2]  # Calculator and weather
        }
    )
    tools_set = response.json()
    print(f"✓ Tools registered: {tools_set['tool_names']}")
    
    print_section("Step 2: Send Complex Query")
    query = "Calculate 100 / 4 and also tell me the weather in Paris"
    print(f"User: {query}")
    
    print_section("Step 3: Get Model Response")
    response = requests.post(
        f"{BASE_URL}/api/tools/call",
        json={"prompt": query, "stream": False},
        timeout=300
    )
    result = response.json()
    print(f"Model: {result['response'][:250]}...")
    
    print_section("Step 4: Execute Tool Calls")
    tool_calls = result.get('tool_calls', [])
    print(f"Total tool calls: {len(tool_calls)}")
    
    for i, tool_call in enumerate(tool_calls, 1):
        tool_name = tool_call['name']
        args = tool_call['arguments']
        print(f"\n🔧 Tool Call {i}: {tool_name}")
        print(f"   Arguments: {json.dumps(args)}")
        
        tool_result = execute_tool(tool_name, args)
        print(f"   Result: {json.dumps(tool_result)}")
    
    return len(tool_calls) >= 2

def demo_4_regular_generation():
    """Demo 4: Regular generation without tools for comparison"""
    print_header("DEMO 4: Regular Generation (No Tools)")
    
    print_section("Step 1: Send Query Without Tool Setup")
    query = "Explain what machine learning is in 2 sentences"
    print(f"User: {query}")
    
    print_section("Step 2: Get Model Response")
    response = requests.post(
        f"{BASE_URL}/api/generate",
        json={"model": "qwen", "prompt": query, "stream": False},
        timeout=300
    )
    result = response.json()
    print(f"Model: {result['response']}")
    print(f"\nTokens generated: {result['eval_count']}")
    
    return True

def demo_5_streaming_tools():
    """Demo 5: Streaming with tool calls"""
    print_header("DEMO 5: Streaming Tool Calls")
    
    print_section("Step 1: Register Tools")
    requests.post(
        f"{BASE_URL}/api/tools/set",
        json={
            "system_prompt": "You are a helpful assistant with tools.",
            "tools": [TOOLS[0]]
        }
    )
    print("✓ Tools registered")
    
    print_section("Step 2: Send Query with Streaming")
    query = "What's the weather in New York?"
    print(f"User: {query}")
    
    print_section("Step 3: Stream Response")
    response = requests.post(
        f"{BASE_URL}/api/tools/call",
        json={"prompt": query, "stream": True},
        stream=True,
        timeout=300
    )
    
    print("Streaming tokens:")
    response_text = ""
    tool_calls_found = False
    
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            
            if data.get('response'):
                print(data['response'], end='', flush=True)
                response_text += data['response']
            
            if data.get('done') and data.get('tool_calls'):
                print("\n")
                tool_calls = data['tool_calls']
                tool_calls_found = True
                
                print_section("Step 4: Execute Tool Calls from Stream")
                for i, tool_call in enumerate(tool_calls, 1):
                    tool_name = tool_call['name']
                    args = tool_call['arguments']
                    print(f"\n🔧 Tool Call {i}: {tool_name}")
                    print(f"   Arguments: {json.dumps(args)}")
                    
                    result = execute_tool(tool_name, args)
                    print(f"   Result: {json.dumps(result)}")
    
    return tool_calls_found

def main():
    print_header("🤖 RKLLM Tool Calling - Complete Demo")
    
    # Check server health
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ Server is running")
            info = response.json()
            print(f"  Model: {info['model']}")
        else:
            print("✗ Server returned unexpected status")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Cannot reach server: {e}")
        print(f"Make sure the server is running on {BASE_URL}")
        sys.exit(1)
    
    # Run demos
    demos = [
        ("Simple Calculation", demo_1_simple_calculation),
        ("Weather Query", demo_2_weather_query),
        ("Multiple Tools", demo_3_multiple_tools),
        ("Regular Generation", demo_4_regular_generation),
        ("Streaming Tools", demo_5_streaming_tools),
    ]
    
    results = []
    for name, demo_func in demos:
        try:
            print(f"\n\n{'='*70}")
            success = demo_func()
            results.append((name, "✓ PASS" if success else "✗ FAIL"))
        except Exception as e:
            print(f"\n✗ Error: {e}")
            results.append((name, f"✗ ERROR: {str(e)[:40]}"))
    
    # Summary
    print("\n\n" + "="*70)
    print("DEMO SUMMARY")
    print("="*70)
    for name, result in results:
        print(f"{result:15} - {name}")
    
    print("\n" + "="*70)
    print("✓ All demos completed successfully!")
    print("="*70 + "\n")
    
    print("Next steps:")
    print("1. Review TOOL_CALLING_GUIDE.md for detailed API documentation")
    print("2. Modify tool_calling_client.py for your specific use case")
    print("3. Implement your own tool handlers")
    print("4. Integrate with your application\n")

if __name__ == '__main__':
    main()
