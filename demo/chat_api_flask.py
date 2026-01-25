#!/usr/bin/env python3
"""
RKLLM Flask Server - Chat API Demo

This script demonstrates how to interact with the RKLLM Flask server
using the new API endpoints (/api/chat and /api/tools/call).

Usage:
    python3 chat_api_flask.py --mode chat              # Chat mode
    python3 chat_api_flask.py --mode tools              # Tool calling mode
    python3 chat_api_flask.py --url http://127.0.0.1:8080  # Custom URL
"""

import sys
import requests
import json
import re
import argparse
from typing import Optional, Dict, Any, List

# Server configuration
DEFAULT_SERVER_URL = 'http://127.0.0.1:8080'
DEFAULT_MODEL = 'qwen'

# Create a session object
session = requests.Session()
session.keep_alive = False
adapter = requests.adapters.HTTPAdapter(max_retries=5)
session.mount('https://', adapter)
session.mount('http://', adapter)

def demo_chat(server_url: str, is_streaming: bool = True) -> None:
    """
    Interactive chat demo with the RKLLM Flask server.
    Demonstrates /api/chat endpoint functionality.
    """
    print("\n" + "="*50)
    print("🤖 RKLLM Flask Chat Demo")
    print("="*50)
    print(f"📡 Server: {server_url}")
    print(f"🔄 Streaming: {is_streaming}")
    print("Type 'exit' to quit\n")
    
    messages: List[Dict[str, str]] = []
    
    try:
        while True:
            user_input = input("👤 You: ").strip()
            
            if user_input.lower() == 'exit':
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            messages.append({"role": "user", "content": user_input})
            
            try:
                # Call the chat endpoint
                response = session.post(
                    f"{server_url}/api/chat",
                    json={
                        "model": DEFAULT_MODEL,
                        "messages": messages,
                        "stream": is_streaming,
                    },
                    timeout=300,
                    stream=is_streaming
                )
                
                if response.status_code != 200:
                    print(f"❌ Error: {response.status_code} - {response.text}")
                    messages.pop()  # Remove user message on error
                    continue
                
                if not is_streaming:
                    # Non-streaming mode
                    data = response.json()
                    assistant_message = data["message"]["content"]
                    print(f"🤖 Assistant: {assistant_message}\n")
                    messages.append({"role": "assistant", "content": assistant_message})
                else:
                    # Streaming mode
                    print("🤖 Assistant: ", end="", flush=True)
                    assistant_message = ""
                    
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line.decode('utf-8'))
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    print(content, end="", flush=True)
                                    assistant_message += content
                            except json.JSONDecodeError:
                                pass
                    
                    print("\n")
                    messages.append({"role": "assistant", "content": assistant_message})
                    
            except requests.exceptions.Timeout:
                print(f"❌ Error: Request timeout (300s)")
                messages.pop()  # Remove user message on error
            except requests.exceptions.ConnectionError:
                print(f"❌ Error: Cannot connect to server at {server_url}")
                print("💡 Make sure the server is running")
                messages.pop()  # Remove user message on error
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                messages.pop()  # Remove user message on error
                
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")


def demo_tools(server_url: str, is_streaming: bool = False) -> None:
    """
    Tool calling demo with the RKLLM Flask server.
    Demonstrates /api/tools/set and /api/tools/call endpoints.
    """
    print("\n" + "="*50)
    print("🔧 RKLLM Flask Tool Calling Demo")
    print("="*50)
    print(f"📡 Server: {server_url}\n")
    
    # Define tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_temperature",
                "description": "Get current temperature at a location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": 'Location in format "City, Country"',
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature unit (default: celsius)",
                        },
                    },
                    "required": ["location"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_weather_forecast",
                "description": "Get weather forecast for a location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": 'Location in format "City, Country"',
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days to forecast (1-7)",
                        },
                    },
                    "required": ["location"],
                },
            },
        },
    ]
    
    # Mock tool implementations
    def get_current_temperature(location: str, unit: str = "celsius") -> Dict:
        return {
            "temperature": 22.5,
            "location": location,
            "unit": unit,
            "condition": "Partly Cloudy"
        }
    
    def get_weather_forecast(location: str, days: int = 3) -> Dict:
        return {
            "location": location,
            "forecast_days": min(days, 7),
            "data": [{"day": i, "high": 25-i, "low": 18-i} for i in range(min(days, 3))]
        }
    
    def get_tool_function(name: str):
        tools_map = {
            "get_current_temperature": get_current_temperature,
            "get_weather_forecast": get_weather_forecast,
        }
        return tools_map.get(name)
    
    try:
        # Step 1: Register tools
        print("📝 Step 1: Registering tools...")
        register_response = session.post(
            f"{server_url}/api/tools/set",
            json={"tools": tools},
            timeout=30
        )
        
        if register_response.status_code != 200:
            print(f"❌ Failed to register tools: {register_response.text}")
            return
        
        print("✅ Tools registered successfully\n")
        
        # Step 2: Interactive tool calling
        print("🤖 You can now ask questions that require tools:")
        print("   Example: 'What is the temperature in Paris?'")
        print("   Example: 'Give me a 5 day forecast for Tokyo'\n")
        
        while True:
            user_input = input("👤 You: ").strip()
            
            if user_input.lower() == 'exit':
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            try:
                # Call the tool endpoint
                tool_response = session.post(
                    f"{server_url}/api/tools/call",
                    json={
                        "prompt": user_input,
                        "stream": is_streaming,
                    },
                    timeout=300,
                    stream=is_streaming
                )
                
                if tool_response.status_code != 200:
                    print(f"❌ Error: {tool_response.status_code}")
                    continue
                
                response_data = tool_response.json()
                
                # Display response
                print(f"🤖 Assistant: {response_data.get('response', 'No response')}\n")
                
                # Display tool calls if any
                if response_data.get('tool_calls'):
                    print("🔧 Tool Calls:")
                    for tool_call in response_data['tool_calls']:
                        print(f"  - {tool_call['name']}({tool_call['arguments']})")
                    print()
                    
            except requests.exceptions.Timeout:
                print(f"❌ Error: Request timeout")
            except requests.exceptions.ConnectionError:
                print(f"❌ Error: Cannot connect to server at {server_url}")
                print("💡 Make sure the server is running")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    


def main():
    """Main entry point for the demo."""
    parser = argparse.ArgumentParser(
        description="RKLLM Flask Server Chat Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode chat                      # Interactive chat
  %(prog)s --mode tools                     # Tool calling demo
  %(prog)s --url http://localhost:8080      # Custom server URL
  %(prog)s --mode chat --stream             # Streaming chat
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['chat', 'tools'],
        default='chat',
        help='Demo mode: chat or tools (default: chat)'
    )
    parser.add_argument(
        '--url',
        default=DEFAULT_SERVER_URL,
        help=f'Server URL (default: {DEFAULT_SERVER_URL})'
    )
    parser.add_argument(
        '--stream',
        action='store_true',
        help='Enable streaming mode (chat mode only)'
    )
    
    args = parser.parse_args()
    
    # Verify server is reachable
    try:
        response = session.get(f"{args.url}/health", timeout=5)
        if response.status_code != 200:
            print(f"⚠️  Warning: Server returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Cannot connect to server at {args.url}")
        print("💡 Make sure the Flask server is running:")
        print(f"   python3 flask_server.py --model_path <model.rkllm> --platform rk3588")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)
    
    # Run appropriate demo
    if args.mode == 'chat':
        demo_chat(args.url, args.stream)
    elif args.mode == 'tools':
        demo_tools(args.url, args.stream)


if __name__ == '__main__':
    main()
    

