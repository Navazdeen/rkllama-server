#!/usr/bin/env python3
"""
RKLLM Tool Calling - Quick Reference

Copy-paste ready examples for common operations.
"""

# ============================================================
# QUICK START: Tool Calling
# ============================================================

import json

import requests

BASE_URL = "http://localhost:8080"

# ============================================================
# 1. REGISTER TOOLS
# ============================================================

def register_tools():
    """Define and register tools with the model"""
    
    tools = [
        {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["location"]
            }
        },
        {
            "name": "calculate",
            "description": "Perform math calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression"}
                },
                "required": ["expression"]
            }
        }
    ]
    
    response = requests.post(
        f"{BASE_URL}/api/tools/set",
        json={
            "system_prompt": "You are helpful and use tools when needed",
            "tools": tools
        }
    )
    
    return response.json()


# ============================================================
# 2. CALL TOOLS (Simple)
# ============================================================

def call_tool_simple(prompt):
    """Make a simple tool call request"""
    
    response = requests.post(
        f"{BASE_URL}/api/tools/call",
        json={
            "prompt": prompt,
            "stream": False
        }
    ).json()
    
    # Print model response
    print(f"Model: {response.get('response')}")
    
    # Process tool calls
    for tool_call in response.get('tool_calls', []):
        print(f"\n📞 Tool: {tool_call['name']}")
        print(f"   Args: {json.dumps(tool_call['arguments'], indent=2)}")
    
    return response


# ============================================================
# 3. CALL TOOLS (Streaming)
# ============================================================

def call_tool_streaming(prompt):
    """Make a streaming tool call request"""
    
    response = requests.post(
        f"{BASE_URL}/api/tools/call",
        json={
            "prompt": prompt,
            "stream": True
        },
        stream=True
    )
    
    # Stream tokens
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            
            # Print token
            if data.get('response'):
                print(data['response'], end='', flush=True)
            
            # Process tool calls when done
            if data.get('done') and data.get('tool_calls'):
                print("\n\n📞 Tool Calls:")
                for tc in data['tool_calls']:
                    print(f"  - {tc['name']}: {json.dumps(tc['arguments'])}")
    
    print()


# ============================================================
# 4. CUSTOM TOOL EXECUTION
# ============================================================

def execute_tool(tool_name, arguments):
    """Execute a tool and return results"""
    
    if tool_name == "get_weather":
        location = arguments.get("location")
        # Call your weather API here
        return {"location": location, "temperature": 20, "condition": "Sunny"}
    
    elif tool_name == "calculate":
        expr = arguments.get("expression")
        try:
            result = eval(expr)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}
    
    return {"error": f"Unknown tool: {tool_name}"}


# ============================================================
# 5. FULL WORKFLOW
# ============================================================

def full_workflow(user_query):
    """Complete workflow: register, call, and execute tools"""
    
    # Step 1: Register tools (once)
    print("1️⃣ Registering tools...")
    register_tools()
    
    # Step 2: Make tool call
    print(f"2️⃣ Calling model with: {user_query}")
    response = requests.post(
        f"{BASE_URL}/api/tools/call",
        json={"prompt": user_query, "stream": False}
    ).json()
    
    # Step 3: Execute tool calls
    print(f"3️⃣ Processing tool calls...")
    for tool_call in response.get('tool_calls', []):
        tool_name = tool_call['name']
        arguments = tool_call['arguments']
        
        print(f"\n  Tool: {tool_name}")
        print(f"  Args: {json.dumps(arguments)}")
        
        # Execute your tool
        result = execute_tool(tool_name, arguments)
        print(f"  Result: {json.dumps(result)}")
    
    return response


# ============================================================
# 6. USAGE EXAMPLES
# ============================================================

if __name__ == "__main__":
    
    # Example 1: Simple query
    print("=" * 60)
    print("EXAMPLE 1: Simple Tool Call")
    print("=" * 60)
    register_tools()
    result = call_tool_simple("What is 100 * 25?")
    
    # Example 2: Streaming
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Streaming Tool Call")
    print("=" * 60)
    # call_tool_streaming("What is the weather in Tokyo?")
    
    # Example 3: Full workflow
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Full Workflow")
    print("=" * 60)
    full_workflow("Calculate 50 + 30 - 10")

# ============================================================
# API REFERENCE
# ============================================================

"""
SET TOOLS:
  POST /api/tools/set
  {
    "system_prompt": "Optional custom prompt",
    "tools": [ ... ],
    "tool_choice": "auto"
  }

CALL TOOL:
  POST /api/tools/call
  {
    "prompt": "User query",
    "stream": false
  }

RESPONSE:
  {
    "model": "qwen",
    "response": "Model output with tool calls",
    "tool_calls": [
      {
        "name": "tool_name",
        "arguments": {"param": "value"}
      }
    ],
    "done": true
  }
"""

# ============================================================
# COMMON PATTERNS
# ============================================================

"""
WEATHER CHECK:
  tools = [{"name": "get_weather", "description": "Get weather", ...}]
  query = "What's the weather in Paris?"

CALCULATION:
  tools = [{"name": "calculate", "description": "Do math", ...}]
  query = "What is 156 * 24 + 42?"

MULTIPLE TOOLS:
  tools = [weather_tool, calculate_tool, time_tool, ...]
  query = "Calculate 100/4 and tell me the weather"

DATABASE LOOKUP:
  tools = [{"name": "get_user", "description": "Get user info", ...}]
  query = "Get user 12345 details"

API INTEGRATION:
  tools = [{"name": "search", "description": "Search web", ...}]
  query = "Search for Python tutorial"
"""
