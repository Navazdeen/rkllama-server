#!/usr/bin/env python3
"""
RKLLM Tool Calling Client

This client demonstrates how to use the tool calling features of the RKLLM server.
It provides example functions and shows how the model can invoke them.

Usage:
    python tool_calling_client.py [--host localhost] [--port 8080]
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List

import requests

# ===================== Tool Definitions =====================

TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a specific location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city name or location"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit"
                }
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
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2+2', '10*5')"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_time",
        "description": "Get the current time",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "Timezone (e.g., 'UTC', 'EST', 'PST')"
                }
            }
        }
    },
    {
        "name": "search_web",
        "description": "Search the web for information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 5)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "convert_units",
        "description": "Convert between different units",
        "parameters": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "number",
                    "description": "The value to convert"
                },
                "from_unit": {
                    "type": "string",
                    "description": "Source unit (e.g., 'kilometers', 'miles', 'celsius', 'fahrenheit')"
                },
                "to_unit": {
                    "type": "string",
                    "description": "Target unit"
                }
            },
            "required": ["value", "from_unit", "to_unit"]
        }
    }
]

# ===================== Mock Tool Implementations =====================

def get_weather(location: str, unit: str = "celsius") -> Dict[str, Any]:
    """Mock weather function"""
    weather_data = {
        "Paris": {"temperature": 12, "condition": "Cloudy", "humidity": 75},
        "New York": {"temperature": 5, "condition": "Sunny", "humidity": 60},
        "London": {"temperature": 8, "condition": "Rainy", "humidity": 85},
        "Tokyo": {"temperature": 20, "condition": "Clear", "humidity": 50},
        "Sydney": {"temperature": 25, "condition": "Sunny", "humidity": 40}
    }
    
    data = weather_data.get(location, {"temperature": 15, "condition": "Unknown", "humidity": 65})
    
    if unit.lower() == "fahrenheit":
        data["temperature"] = (data["temperature"] * 9/5) + 32
    
    return {
        "location": location,
        "temperature": data["temperature"],
        "unit": unit,
        "condition": data["condition"],
        "humidity": data["humidity"]
    }


def calculate(expression: str) -> Dict[str, Any]:
    """Mock calculator function"""
    try:
        # Safe evaluation of mathematical expressions
        import math
        result = eval(expression, {"__builtins__": {}}, {"math": math})
        return {
            "expression": expression,
            "result": result,
            "status": "success"
        }
    except Exception as e:
        return {
            "expression": expression,
            "error": str(e),
            "status": "error"
        }


def get_time(timezone: str = "UTC") -> Dict[str, Any]:
    """Mock time function"""
    return {
        "timezone": timezone,
        "current_time": datetime.now().isoformat(),
        "hour": datetime.now().hour,
        "minute": datetime.now().minute
    }


def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Mock web search function"""
    mock_results = {
        "python": [
            {"title": "Python Official Website", "url": "https://python.org", "snippet": "The Python programming language"},
            {"title": "Python Documentation", "url": "https://docs.python.org", "snippet": "Official Python documentation"}
        ],
        "machine learning": [
            {"title": "ML Basics", "url": "https://ml.example.com", "snippet": "Introduction to machine learning"},
            {"title": "TensorFlow", "url": "https://tensorflow.org", "snippet": "Open source machine learning framework"}
        ],
        "artificial intelligence": [
            {"title": "AI Research", "url": "https://ai.example.com", "snippet": "Latest AI research"},
            {"title": "Deep Learning", "url": "https://deeplearning.example.com", "snippet": "Deep learning models"}
        ]
    }
    
    results = mock_results.get(query.lower(), [
        {"title": f"Result for {query}", "url": f"https://example.com/search?q={query}", "snippet": f"Information about {query}"}
    ])
    
    return {
        "query": query,
        "results_count": min(len(results), max_results),
        "results": results[:max_results]
    }


def convert_units(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """Mock unit converter function"""
    conversions = {
        ("kilometers", "miles"): 0.621371,
        ("miles", "kilometers"): 1.60934,
        ("celsius", "fahrenheit"): lambda v: (v * 9/5) + 32,
        ("fahrenheit", "celsius"): lambda v: (v - 32) * 5/9,
        ("kg", "lbs"): 2.20462,
        ("lbs", "kg"): 0.453592,
    }
    
    key = (from_unit.lower(), to_unit.lower())
    
    if key in conversions:
        factor = conversions[key]
        if callable(factor):
            result = factor(value)
        else:
            result = value * factor
        
        return {
            "value": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "result": round(result, 4),
            "status": "success"
        }
    
    return {
        "error": f"Conversion from {from_unit} to {to_unit} not supported",
        "status": "error"
    }


# ===================== Tool Executor =====================

TOOL_FUNCTIONS = {
    "get_weather": get_weather,
    "calculate": calculate,
    "get_time": get_time,
    "search_web": search_web,
    "convert_units": convert_units
}


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name with given arguments"""
    if tool_name not in TOOL_FUNCTIONS:
        return {
            "error": f"Tool '{tool_name}' not found",
            "available_tools": list(TOOL_FUNCTIONS.keys())
        }
    
    try:
        func = TOOL_FUNCTIONS[tool_name]
        result = func(**arguments)
        return result
    except Exception as e:
        return {
            "error": f"Failed to execute {tool_name}: {str(e)}",
            "tool": tool_name
        }


# ===================== RKLLM Tool Calling Client =====================

class ToolCallingClient:
    """Client for interacting with RKLLM tool calling API"""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
    
    def set_tools(self, tools: List[Dict], system_prompt: str = None) -> Dict[str, Any]:
        """
        Set tools for the model
        
        Args:
            tools: List of tool definitions
            system_prompt: System prompt for the model
        
        Returns:
            API response
        """
        if system_prompt is None:
            system_prompt = (
                "You are a helpful assistant with access to the following tools. "
                "When the user asks you to perform a task that matches one of your tools, "
                "you MUST call the appropriate tool to get accurate information. "
                "Always provide the tool call details in your response."
            )
        
        payload = {
            "system_prompt": system_prompt,
            "tools": tools,
            "tool_choice": "auto"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/tools/set",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def call_tool(self, prompt: str, stream: bool = False) -> Any:
        """
        Call a tool through the model
        
        Args:
            prompt: User prompt
            stream: Whether to stream the response
        
        Returns:
            API response or generator if streaming
        """
        payload = {
            "prompt": prompt,
            "stream": stream,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/tools/call",
                json=payload,
                stream=stream,
                timeout=300  # Increased timeout for long inference
            )
            response.raise_for_status()
            
            if stream:
                return response.iter_lines()
            else:
                return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def process_tool_calls(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process tool calls from model response and execute them
        
        Args:
            response: Model response with tool_calls
        
        Returns:
            Response with tool results
        """
        tool_calls = response.get('tool_calls', [])
        
        if not tool_calls:
            return {
                "response": response.get('response'),
                "tool_calls": [],
                "executed_tools": []
            }
        
        executed_tools = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get('name')
            arguments = tool_call.get('arguments', {})
            
            print(f"\n📞 Calling tool: {tool_name}")
            print(f"   Arguments: {json.dumps(arguments, indent=2)}")
            
            result = execute_tool(tool_name, arguments)
            
            print(f"   Result: {json.dumps(result, indent=2)}")
            
            executed_tools.append({
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result
            })
        
        return {
            "response": response.get('response'),
            "tool_calls": tool_calls,
            "executed_tools": executed_tools
        }


# ===================== Test Scenarios =====================

def test_scenario_1(client: ToolCallingClient):
    """Test weather tool calling"""
    print("\n" + "="*70)
    print("TEST 1: Weather Tool Calling")
    print("="*70)
    
    # Set tools
    print("\n1️⃣ Setting tools for the model...")
    result = client.set_tools(TOOLS)
    print(f"   Status: {result.get('status')}")
    print(f"   Tools: {result.get('tool_names')}")
    
    # Call with weather question
    print("\n2️⃣ Asking model about weather...")
    prompt = "What is the weather like in Paris? Tell me the temperature in both Celsius and Fahrenheit."
    response = client.call_tool(prompt, stream=False)
    
    if 'error' in response:
        print(f"   ❌ Error: {response['error']}")
        return
    
    print(f"   Model response: {response.get('response')[:200]}...")
    
    # Process tool calls
    print("\n3️⃣ Processing tool calls...")
    result = client.process_tool_calls(response)
    print(f"   Executed tools: {len(result['executed_tools'])}")


def test_scenario_2(client: ToolCallingClient):
    """Test calculator tool calling"""
    print("\n" + "="*70)
    print("TEST 2: Calculator Tool Calling")
    print("="*70)
    
    # Call with calculation question
    print("\n1️⃣ Asking model to perform calculations...")
    prompt = "Calculate 25 * 4 + 10 - 3. Also convert 100 kilometers to miles."
    response = client.call_tool(prompt, stream=False)
    
    if 'error' in response:
        print(f"   ❌ Error: {response['error']}")
        return
    
    print(f"   Model response: {response.get('response')[:200]}...")
    
    # Process tool calls
    print("\n2️⃣ Processing tool calls...")
    result = client.process_tool_calls(response)
    print(f"   Executed tools: {len(result['executed_tools'])}")


def test_scenario_3(client: ToolCallingClient):
    """Test streaming tool calling"""
    print("\n" + "="*70)
    print("TEST 3: Streaming Tool Calling")
    print("="*70)
    
    print("\n1️⃣ Asking model (with streaming)...")
    prompt = "What is the current time? Also, what is the weather in London?"
    
    print("   Streaming response:")
    response_text = ""
    
    try:
        for line in client.call_tool(prompt, stream=True):
            if line:
                data = json.loads(line)
                if 'error' in data:
                    print(f"   ❌ Error: {data['error']}")
                    return
                
                token = data.get('response', '')
                if token:
                    print(f"   {token}", end='', flush=True)
                    response_text += token
                
                if data.get('done'):
                    tool_calls = data.get('tool_calls', [])
                    if tool_calls:
                        print(f"\n\n2️⃣ Processing tool calls...")
                        for tool_call in tool_calls:
                            tool_name = tool_call.get('name')
                            arguments = tool_call.get('arguments', {})
                            print(f"   📞 Tool: {tool_name}")
                            print(f"      Args: {json.dumps(arguments, indent=2)}")
                            result = execute_tool(tool_name, arguments)
                            print(f"      Result: {json.dumps(result, indent=2)}")
        
        print("\n")
    except Exception as e:
        print(f"\n   ❌ Error: {e}")


def test_scenario_4(client: ToolCallingClient):
    """Test multiple tool calls in one request"""
    print("\n" + "="*70)
    print("TEST 4: Multiple Tool Calls")
    print("="*70)
    
    print("\n1️⃣ Asking model for multiple operations...")
    prompt = "I need to know: (1) the weather in Tokyo, (2) what is 1024 / 32, (3) the current time, and (4) how many miles is 50 kilometers?"
    response = client.call_tool(prompt, stream=False)
    
    if 'error' in response:
        print(f"   ❌ Error: {response['error']}")
        return
    
    print(f"   Model response: {response.get('response')[:300]}...")
    
    # Process all tool calls
    print("\n2️⃣ Processing all tool calls...")
    result = client.process_tool_calls(response)
    print(f"   Total tool calls identified: {len(result['executed_tools'])}")


def test_scenario_5(client: ToolCallingClient):
    """Test web search tool calling"""
    print("\n" + "="*70)
    print("TEST 5: Web Search Tool Calling")
    print("="*70)
    
    print("\n1️⃣ Asking model to search the web...")
    prompt = "Search for information about 'machine learning' and 'artificial intelligence'. Tell me what you find."
    response = client.call_tool(prompt, stream=False)
    
    if 'error' in response:
        print(f"   ❌ Error: {response['error']}")
        return
    
    print(f"   Model response: {response.get('response')[:300]}...")
    
    # Process tool calls
    print("\n2️⃣ Processing tool calls...")
    result = client.process_tool_calls(response)
    print(f"   Executed tools: {len(result['executed_tools'])}")


# ===================== Main =====================

def main():
    parser = argparse.ArgumentParser(
        description='RKLLM Tool Calling Client - Test tool calling features'
    )
    parser.add_argument('--host', default='localhost', help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=8080, help='Server port (default: 8080)')
    parser.add_argument('--test', type=int, choices=[1, 2, 3, 4, 5, 0], default=0,
                       help='Specific test to run (1-5), or 0 for all (default: 0)')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🤖 RKLLM Tool Calling Client")
    print("="*70)
    print(f"Server: {args.host}:{args.port}")
    
    # Create client
    client = ToolCallingClient(args.host, args.port)
    
    # Test connection
    try:
        response = requests.get(f"http://{args.host}:{args.port}/health", timeout=5)
        response.raise_for_status()
        print("✓ Server connection successful")
    except Exception as e:
        print(f"✗ Failed to connect to server: {e}")
        sys.exit(1)
    
    # Run tests
    tests = {
        1: test_scenario_1,
        2: test_scenario_2,
        3: test_scenario_3,
        4: test_scenario_4,
        5: test_scenario_5
    }
    
    if args.test == 0:
        # Run all tests
        for test_num in sorted(tests.keys()):
            try:
                tests[test_num](client)
            except Exception as e:
                print(f"\n❌ Test {test_num} failed: {e}")
    else:
        # Run specific test
        try:
            tests[args.test](client)
        except Exception as e:
            print(f"\n❌ Test {args.test} failed: {e}")
    
    print("\n" + "="*70)
    print("✓ All tests completed")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
