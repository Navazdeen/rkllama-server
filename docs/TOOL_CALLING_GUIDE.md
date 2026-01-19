# RKLLM Tool Calling Implementation Guide

## Overview

Tool calling (also known as function calling) allows the RKLLM model to identify when it needs to use external tools to answer user queries. The model generates structured tool call requests that can be executed by your application.

This implementation provides:
- **API endpoints** for managing tools
- **Automatic tool detection** from model responses
- **Tool execution framework** for integrating external services
- **Streaming support** for real-time tool calls
- **Full Ollama compatibility** with extended tool calling features

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────┐
│         Client Application                           │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. Set Tools ──────→ /api/tools/set               │
│                                                      │
│  2. Call Tool ──────→ /api/tools/call              │
│                      ↓                              │
│                  RKLLM Model                        │
│                      ↓                              │
│                  Parse Tool Calls                   │
│                      ↓                              │
│  3. Execute Tools ←── Tool Definitions             │
│                      ↓                              │
│                  Tool Results                       │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Workflow

1. **Define Tools**: Create tool schemas with name, description, and parameters
2. **Register Tools**: Send tools to `/api/tools/set` endpoint
3. **Make Request**: Send user query to `/api/tools/call` endpoint
4. **Parse Response**: Extract tool calls from model response
5. **Execute Tools**: Run the identified tools with provided arguments
6. **Process Results**: Use tool results in your application

---

## API Endpoints

### 1. Set Tools: `POST /api/tools/set`

Configure which tools the model has access to.

**Request:**
```json
{
  "system_prompt": "You are a helpful assistant with tools",
  "tools": [
    {
      "name": "get_weather",
      "description": "Get weather for a location",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "City name"
          }
        },
        "required": ["location"]
      }
    }
  ],
  "tool_choice": "auto"
}
```

**Response:**
```json
{
  "status": "success",
  "system_prompt": "You are a helpful assistant with tools",
  "tools_count": 1,
  "tool_names": ["get_weather"]
}
```

**Parameters:**
- `system_prompt` (string, optional): System prompt for the model. Default includes tool usage instructions.
- `tools` (array): Tool definitions
  - `name` (string): Function name
  - `description` (string): What the tool does
  - `parameters` (object): JSON Schema for parameters
- `tool_choice` (string): "auto", "required", or specific tool name. Default: "auto"

**Status Codes:**
- `200`: Tools set successfully
- `400`: Missing required fields
- `500`: Server error

---

### 2. Call Tool: `POST /api/tools/call`

Execute a tool-enabled inference request.

**Request:**
```json
{
  "prompt": "What's the weather in Paris?",
  "stream": false,
  "temperature": 0.8,
  "top_p": 0.9
}
```

**Response (Non-Streaming):**
```json
{
  "model": "qwen",
  "created_at": "2026-01-19T15:30:00.123456",
  "response": "<tool_call>\n{\"name\": \"get_weather\", \"arguments\": {\"location\": \"Paris\"}}\n</tool_call>",
  "tool_calls": [
    {
      "name": "get_weather",
      "arguments": {"location": "Paris"}
    }
  ],
  "done": true,
  "eval_count": 25
}
```

**Response (Streaming):**
```
{"model": "qwen", "response": "T", "done": false, "eval_count": 1}
{"model": "qwen", "response": "o", "done": false, "eval_count": 1}
...
{"model": "qwen", "response": "", "done": true, "tool_calls": [...]}
```

**Parameters:**
- `prompt` (string): User query
- `stream` (boolean, optional): Enable streaming. Default: false
- `temperature` (float, optional): Sampling temperature (0-2). Default: 0.8
- `top_p` (float, optional): Nucleus sampling parameter. Default: 0.9

**Status Codes:**
- `200`: Request successful
- `400`: Missing or invalid parameters
- `500`: Inference error
- `504`: Inference timeout

---

## Tool Response Format

The model generates tool calls in JSON format within `<tool_call>` tags:

```
<tool_call>
{"name": "function_name", "arguments": {"param1": "value1", "param2": "value2"}}
</tool_call>
```

The server automatically parses and extracts these into the `tool_calls` array.

---

## Implementation Examples

### Python Client

```python
import requests
import json

# 1. Define tools
tools = [
    {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
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
                "expression": {"type": "string"}
            },
            "required": ["expression"]
        }
    }
]

# 2. Register tools
response = requests.post(
    "http://localhost:8080/api/tools/set",
    json={
        "system_prompt": "You are a helpful assistant. Use tools when needed.",
        "tools": tools
    }
)
print(f"Tools registered: {response.json()['tool_names']}")

# 3. Make tool call request
response = requests.post(
    "http://localhost:8080/api/tools/call",
    json={
        "prompt": "What is 25 * 4? Also, what's the weather in Paris?",
        "stream": False
    }
)

result = response.json()
print(f"Model response: {result['response']}")

# 4. Process tool calls
for tool_call in result.get('tool_calls', []):
    tool_name = tool_call['name']
    arguments = tool_call['arguments']
    print(f"\nTool: {tool_name}")
    print(f"Arguments: {json.dumps(arguments, indent=2)}")
    
    # Execute tool (implement your own tool handlers)
    if tool_name == "calculate":
        try:
            result_value = eval(arguments['expression'])
            print(f"Result: {result_value}")
        except Exception as e:
            print(f"Error: {e}")
    elif tool_name == "get_weather":
        print(f"Getting weather for {arguments['location']}...")
        # Call your weather API
```

### Tool Handler Pattern

```python
def handle_tool_call(tool_name, arguments):
    """Execute a tool and return results"""
    
    if tool_name == "get_weather":
        location = arguments.get("location")
        unit = arguments.get("unit", "celsius")
        # Call weather API
        return get_weather_api(location, unit)
    
    elif tool_name == "calculate":
        expr = arguments.get("expression")
        try:
            return {"result": eval(expr)}
        except Exception as e:
            return {"error": str(e)}
    
    elif tool_name == "search_web":
        query = arguments.get("query")
        # Call search API
        return search_web_api(query)
    
    else:
        return {"error": f"Unknown tool: {tool_name}"}


# Main loop
response = requests.post(
    "http://localhost:8080/api/tools/call",
    json={"prompt": user_query, "stream": False}
)

for tool_call in response.json().get('tool_calls', []):
    result = handle_tool_call(tool_call['name'], tool_call['arguments'])
    print(f"Tool '{tool_call['name']}' result: {result}")
```

### Streaming Tool Calls

```python
import requests
import json

response = requests.post(
    "http://localhost:8080/api/tools/call",
    json={"prompt": "Help me with calculation and weather", "stream": True},
    stream=True
)

for line in response.iter_lines():
    if line:
        data = json.loads(line)
        
        # Stream response text
        if data.get('response'):
            print(data['response'], end='', flush=True)
        
        # Process tool calls when done
        if data.get('done') and data.get('tool_calls'):
            print("\n\nTool Calls:")
            for tool_call in data['tool_calls']:
                print(f"  {tool_call['name']}: {tool_call['arguments']}")
```

---

## Sample Client Application

The repository includes `tool_calling_client.py` with complete examples:

```bash
# Run all tests
python tool_calling_client.py

# Run specific test
python tool_calling_client.py --test 1  # Test 1: Weather
python tool_calling_client.py --test 2  # Test 2: Calculator
python tool_calling_client.py --test 3  # Test 3: Streaming
python tool_calling_client.py --test 4  # Test 4: Multiple calls
python tool_calling_client.py --test 5  # Test 5: Web search
```

---

## Tool Definition Schema

Tool definitions follow JSON Schema specification:

```json
{
  "name": "tool_name",
  "description": "Clear description of what the tool does",
  "parameters": {
    "type": "object",
    "properties": {
      "param1": {
        "type": "string",
        "description": "Parameter description"
      },
      "param2": {
        "type": "number",
        "description": "Another parameter"
      },
      "param3": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Array parameter"
      }
    },
    "required": ["param1", "param2"]
  }
}
```

### Supported Parameter Types:
- `string`: Text input
- `number`: Numeric value
- `integer`: Whole numbers
- `boolean`: True/False
- `array`: List of values
- `object`: Complex nested object

---

## Testing

### Run Test Suite

```bash
# Simple API tests
python tool_calling_test.py

# Comprehensive tool calling tests
python tool_calling_client.py --test 0  # All tests
```

### Expected Output

Test 1 (Weather):
```
📞 Calling tool: get_weather
   Arguments: {"location": "Paris", "unit": "celsius"}
   Result: {"temperature": 12, "condition": "Cloudy", "humidity": 75}
```

Test 2 (Calculator):
```
📞 Calling tool: calculate
   Arguments: {"expression": "25 * 4 + 10 - 3"}
   Result: {"expression": "25 * 4 + 10 - 3", "result": 107}
```

---

## Integration with Your Application

### Step 1: Define Your Tools

```python
MY_TOOLS = [
    {
        "name": "get_user_profile",
        "description": "Get user profile information",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "update_user_status",
        "description": "Update user status",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "inactive", "banned"]}
            },
            "required": ["user_id", "status"]
        }
    }
]
```

### Step 2: Initialize Tools

```python
requests.post(
    "http://localhost:8080/api/tools/set",
    json={
        "system_prompt": "You are a user management assistant.",
        "tools": MY_TOOLS
    }
)
```

### Step 3: Handle User Requests

```python
def process_user_request(user_query):
    # Get model response with tool calls
    response = requests.post(
        "http://localhost:8080/api/tools/call",
        json={"prompt": user_query}
    ).json()
    
    # Execute each tool call
    for tool_call in response.get('tool_calls', []):
        name = tool_call['name']
        args = tool_call['arguments']
        
        if name == "get_user_profile":
            profile = database.get_user(args['user_id'])
            print(f"Profile: {profile}")
        
        elif name == "update_user_status":
            database.update_user_status(args['user_id'], args['status'])
            print(f"Updated user status")
    
    return response['response']
```

---

## Best Practices

### 1. Clear Tool Descriptions
Write descriptive tool descriptions so the model understands when to use them:
```json
{
  "name": "search_products",
  "description": "Search for products in the inventory by name, category, or price range. Use this when the user asks about available products, prices, or product recommendations.",
  "parameters": { ... }
}
```

### 2. Specific System Prompts
Guide the model with task-specific prompts:
```python
system_prompt = """You are a helpful shopping assistant. You have access to:
1. search_products: Find products in our inventory
2. check_inventory: Check stock levels
3. get_price: Get current pricing

When a customer asks about products, ALWAYS search first to get accurate information.
Provide helpful recommendations based on their needs."""
```

### 3. Handle Tool Errors Gracefully
```python
def execute_tool(tool_name, arguments):
    try:
        # Your tool implementation
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### 4. Validate Arguments
```python
def get_weather(location: str, unit: str = "celsius"):
    if not location:
        raise ValueError("Location is required")
    if unit not in ["celsius", "fahrenheit"]:
        raise ValueError(f"Invalid unit: {unit}")
    # Implementation...
```

### 5. Set Reasonable Timeouts
```python
requests.post(
    "http://localhost:8080/api/tools/call",
    json={"prompt": query},
    timeout=300  # 5 minutes for inference
)
```

---

## Troubleshooting

### Model Not Calling Tools

**Problem**: Model response doesn't include tool calls even though tools are registered.

**Solutions**:
1. Check system prompt includes tool usage instructions
2. Verify tools are properly registered with `/api/tools/set`
3. Make query more specific and tool-relevant
4. Increase temperature (0.7-0.9) to encourage more varied outputs

### Tool Parsing Failed

**Problem**: Tool calls aren't extracted from response.

**Solutions**:
1. Check model response contains `<tool_call>...</tool_call>` tags
2. Verify JSON inside tags is valid
3. Check tool names match registered tools
4. Review server logs for parsing errors

### Timeout Errors

**Problem**: Inference takes too long and times out.

**Solutions**:
1. Increase client timeout: `timeout=300`
2. Use streaming mode to get partial results
3. Optimize prompts to be more concise
4. Check system resources (CPU, memory, NPU)

### Tool Execution Errors

**Problem**: Tool execution fails with arguments.

**Solutions**:
1. Validate argument types match schema
2. Add error handling in tool implementations
3. Log arguments for debugging
4. Return detailed error messages

---

## Performance Considerations

### Inference Speed
- First inference: ~15-20 seconds (model loading)
- Subsequent inferences: Real-time token streaming
- Tool calls: Parsed in real-time as tokens arrive

### Memory Usage
- RKLLM Model: ~3GB for Qwen2.5-3B
- Tool definitions: Minimal overhead
- Buffer for inference: ~500MB

### Optimization Tips
1. **Batch Similar Requests**: Process multiple requests sequentially
2. **Use Streaming**: Real-time feedback with streaming mode
3. **Limit Tools**: Fewer tools = faster model decisions
4. **Cache Results**: Store tool results to avoid redundant calls
5. **Profile Performance**: Track inference times

---

## API Response Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad Request | Check parameters |
| 404 | Not Found | Check endpoint |
| 500 | Server Error | Check logs |
| 504 | Timeout | Increase timeout or optimize prompt |

---

## Related Endpoints

### Regular Generation (No Tools)
```
POST /api/generate
{
  "model": "qwen",
  "prompt": "Hello, how are you?",
  "stream": false
}
```

### Chat Interface (No Tools)
```
POST /api/chat
{
  "model": "qwen",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}
```

### Model Information
```
GET /api/tags - List available models
GET /api/show - Get model details
GET /health - Health check
```

---

## Version History

- **v1.0.0** (2026-01-19): Initial tool calling implementation
  - `/api/tools/set` endpoint
  - `/api/tools/call` endpoint
  - Streaming support
  - Multiple tool call parsing
  - Sample client application

---

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review example implementations
3. Check server logs: `tail -f /tmp/server.log`
4. Run test suite: `python tool_calling_test.py`

---

## License

Tool calling implementation is part of the RKLLM Ollama-compatible server project.
