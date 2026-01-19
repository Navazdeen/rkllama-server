# Ollama-Compatible RKLLM Flask Server API Guide

## Overview

The new `flask_server.py` provides a fully Ollama-compatible REST API for the RKLLM model. This allows you to use RKLLM models with any client that supports the Ollama API specification.

## Features

- **Ollama API Compatible**: Supports all major Ollama endpoints
- **Streaming Support**: Server-Sent Events (SSE) streaming for real-time responses
- **Multi-threaded**: Safe concurrent request handling
- **Text Generation**: Direct text completion API
- **Chat Completions**: Multi-turn conversation support
- **Model Management**: List, show, and manage models

## Quick Start

### Starting the Server

```bash
python flask_server.py \
  --rkllm_model_path ~/models/Qwen2.5-3B-Instruct-rk3588-w8a8_g128-opt-0-hybrid-ratio-0.0/Qwen2.5-3B-Instruct-rk3588-w8a8_g128-opt-0-hybrid-ratio-0.0.rkllm \
  --target_platform rk3588 \
  --host 0.0.0.0 \
  --port 8080
```

### Optional Arguments

- `--lora_model_path`: Path to LoRA adapter model
- `--prompt_cache_path`: Path to prompt cache file
- `--model_name`: Custom model name (defaults to model path basename)
- `--host`: Server host (default: 0.0.0.0)
- `--port`: Server port (default: 8080)

## API Endpoints

### 1. Health Check

Check if the server is running and ready.

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "ok",
  "model": "model_name"
}
```

---

### 2. Server Info

Get server information and available endpoints.

**Endpoint**: `GET /`

**Response**:
```json
{
  "name": "RKLLM Ollama-Compatible Server",
  "version": "1.0.0",
  "model": "model_name",
  "platform": "rk3588",
  "endpoints": {
    "generate": "/api/generate (POST)",
    "chat": "/api/chat (POST)",
    "tags": "/api/tags (GET)",
    "show": "/api/show (POST)",
    "embeddings": "/api/embeddings (POST)",
    "health": "/health (GET)"
  }
}
```

---

### 3. List Models

Get all available models.

**Endpoint**: `GET /api/tags`

**Response**:
```json
{
  "models": [
    {
      "name": "model_name",
      "modified_at": "2024-01-19T10:30:00",
      "size": 0,
      "digest": "abc123def456"
    }
  ]
}
```

---

### 4. Show Model Details

Get detailed information about a specific model.

**Endpoint**: `POST /api/show`

**Request**:
```json
{
  "name": "model_name"
}
```

**Response**:
```json
{
  "name": "model_name",
  "modified_at": "2024-01-19T10:30:00",
  "size": 0,
  "digest": "abc123def456",
  "details": {
    "format": "rkllm",
    "family": "unknown",
    "families": ["unknown"],
    "parameter_size": "unknown",
    "quantization_level": "unknown"
  }
}
```

---

### 5. Text Generation (Non-Streaming)

Generate text from a prompt.

**Endpoint**: `POST /api/generate`

**Request**:
```json
{
  "model": "model_name",
  "prompt": "Write a poem about the moon",
  "stream": false,
  "temperature": 0.8,
  "top_p": 0.9,
  "top_k": 1
}
```

**Response**:
```json
{
  "model": "model_name",
  "created_at": "2024-01-19T10:30:00",
  "response": "The moon shines bright...",
  "done": true,
  "context": [],
  "total_duration": 5000000000,
  "load_duration": 1000000000,
  "prompt_eval_count": 8,
  "prompt_eval_duration": 2000000000,
  "eval_count": 45,
  "eval_duration": 2000000000
}
```

---

### 6. Text Generation (Streaming)

Generate text with streaming responses (Server-Sent Events).

**Endpoint**: `POST /api/generate`

**Request**:
```json
{
  "model": "model_name",
  "prompt": "Write a poem about the moon",
  "stream": true,
  "temperature": 0.8,
  "top_p": 0.9,
  "top_k": 1
}
```

**Response Stream** (newline-delimited JSON):
```
{"model": "model_name", "created_at": "2024-01-19T10:30:00", "response": "The", "done": false, ...}
{"model": "model_name", "created_at": "2024-01-19T10:30:01", "response": " moon", "done": false, ...}
{"model": "model_name", "created_at": "2024-01-19T10:30:02", "response": " shines", "done": false, ...}
...
{"model": "model_name", "created_at": "2024-01-19T10:30:10", "response": "", "done": true, ...}
```

---

### 7. Chat Completions (Non-Streaming)

Have a multi-turn conversation with the model.

**Endpoint**: `POST /api/chat`

**Request**:
```json
{
  "model": "model_name",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "What is 2+2?"
    }
  ],
  "stream": false,
  "temperature": 0.8
}
```

**Response**:
```json
{
  "model": "model_name",
  "created_at": "2024-01-19T10:30:00",
  "message": {
    "role": "assistant",
    "content": "2+2 equals 4."
  },
  "done": true,
  "total_duration": 5000000000,
  "load_duration": 1000000000,
  "prompt_eval_count": 20,
  "prompt_eval_duration": 2000000000,
  "eval_count": 10,
  "eval_duration": 2000000000
}
```

---

### 8. Chat Completions (Streaming)

Have a multi-turn conversation with streaming responses.

**Endpoint**: `POST /api/chat`

**Request**:
```json
{
  "model": "model_name",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "What is 2+2?"
    }
  ],
  "stream": true,
  "temperature": 0.8
}
```

**Response Stream** (newline-delimited JSON):
```
{"model": "model_name", "created_at": "2024-01-19T10:30:00", "message": {"role": "assistant", "content": "2"}, "done": false}
{"model": "model_name", "created_at": "2024-01-19T10:30:01", "message": {"role": "assistant", "content": "+2"}, "done": false}
{"model": "model_name", "created_at": "2024-01-19T10:30:02", "message": {"role": "assistant", "content": " equals 4"}, "done": false}
...
{"model": "model_name", "created_at": "2024-01-19T10:30:05", "message": {"role": "assistant", "content": ""}, "done": true, ...}
```

---

### 9. Embeddings

Get embeddings for input text (if supported by model).

**Endpoint**: `POST /api/embeddings`

**Note**: Currently returns 501 (Not Implemented) as embedding support depends on model capabilities.

---

## Usage Examples

### Using cURL

#### Generate Text
```bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model_name",
    "prompt": "Hello, how are you?",
    "stream": false
  }'
```

#### Stream Text Generation
```bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model_name",
    "prompt": "Hello, how are you?",
    "stream": true
  }'
```

#### Chat Completion
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model_name",
    "messages": [
      {"role": "user", "content": "What is AI?"}
    ],
    "stream": false
  }'
```

### Using Python

```python
import requests
import json

# Non-streaming generation
response = requests.post('http://localhost:8080/api/generate', json={
    'model': 'model_name',
    'prompt': 'What is AI?',
    'stream': False
})
print(response.json()['response'])

# Streaming generation
response = requests.post('http://localhost:8080/api/generate', json={
    'model': 'model_name',
    'prompt': 'What is AI?',
    'stream': True
}, stream=True)

for line in response.iter_lines():
    if line:
        data = json.loads(line)
        print(data['response'], end='', flush=True)
print()

# Chat completion
response = requests.post('http://localhost:8080/api/chat', json={
    'model': 'model_name',
    'messages': [
        {'role': 'user', 'content': 'What is AI?'}
    ],
    'stream': False
})
print(response.json()['message']['content'])
```

### Using JavaScript/Node.js

```javascript
// Non-streaming generation
const response = await fetch('http://localhost:8080/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        model: 'model_name',
        prompt: 'What is AI?',
        stream: false
    })
});
const data = await response.json();
console.log(data.response);

// Streaming generation
const streamResponse = await fetch('http://localhost:8080/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        model: 'model_name',
        prompt: 'What is AI?',
        stream: true
    })
});

const reader = streamResponse.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const lines = decoder.decode(value).split('\n');
    for (const line of lines) {
        if (line) {
            const data = JSON.parse(line);
            process.stdout.write(data.response);
        }
    }
}
```

### Using Ollama Client (if compatible)

```bash
# List models
ollama list

# Generate text
ollama run model_name "What is AI?"

# With parameters
ollama run model_name "What is AI?" --temperature 0.5
```

---

## Message Roles

The `/api/chat` endpoint supports the following message roles:

- **system**: System instructions for the model behavior
- **user**: User input/questions
- **assistant**: Model's previous responses
- **tool**: Tool/function call responses (for function calling support)

### Example Multi-turn Conversation

```json
{
  "model": "model_name",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful coding assistant."
    },
    {
      "role": "user",
      "content": "How do I reverse a string in Python?"
    },
    {
      "role": "assistant",
      "content": "You can reverse a string in Python using slicing: `s[::-1]`"
    },
    {
      "role": "user",
      "content": "Can you show me an example?"
    }
  ],
  "stream": false
}
```

---

## Request Parameters

### Common Parameters

- **model** (string, required): Name of the model to use
- **stream** (boolean, optional): Whether to stream responses (default: false)
- **temperature** (float, optional): Controls randomness (0-1, default: 0.8)
- **top_p** (float, optional): Nucleus sampling threshold (0-1, default: 0.9)
- **top_k** (integer, optional): Top-K sampling (default: 1)

### Generate-Specific Parameters

- **prompt** (string, required): The text prompt for generation

### Chat-Specific Parameters

- **messages** (array, required): Array of message objects with role and content

---

## Response Fields

### Generation Response

- **model**: Model used
- **created_at**: Response creation timestamp
- **response**: Generated text
- **done**: Whether generation is complete
- **context**: Context tokens (for multi-turn)
- **total_duration**: Total inference time (nanoseconds)
- **load_duration**: Model loading time (nanoseconds)
- **prompt_eval_count**: Number of prompt tokens evaluated
- **prompt_eval_duration**: Time to evaluate prompt (nanoseconds)
- **eval_count**: Number of tokens generated
- **eval_duration**: Time to generate tokens (nanoseconds)

### Chat Response

- **model**: Model used
- **created_at**: Response creation timestamp
- **message**: Response message object with role and content
- **done**: Whether generation is complete
- **total_duration**: Total inference time (nanoseconds)
- **prompt_eval_count**: Number of prompt tokens
- **eval_count**: Number of response tokens
- **eval_duration**: Time to generate response (nanoseconds)

---

## Error Handling

### Error Response Format

```json
{
  "error": "Error description"
}
```

### Common Error Codes

- **400**: Bad Request - Invalid JSON or missing required fields
- **404**: Not Found - Model not found
- **500**: Internal Server Error - Server error during processing
- **503**: Service Unavailable - Server is busy processing another request

### Example Error Response

```json
{
  "error": "Model my_model not found"
}
```

---

## Performance Considerations

1. **Concurrency**: The server uses thread locking to ensure only one request is processed at a time. Subsequent requests will receive a 503 error if the server is busy.

2. **Memory**: RKLLM models can be large. Ensure your device has sufficient memory for the model size plus inference overhead.

3. **Streaming**: Streaming responses provide real-time feedback but may have slightly higher overhead due to frequent I/O operations.

4. **Context Length**: The maximum context length is limited by RKLLM configuration (default: 4096 tokens).

---

## Compatibility Notes

- **Ollama Format**: Response format matches Ollama API v1.0
- **Streaming Format**: Uses newline-delimited JSON (NDJSON)
- **Chat Template**: Uses a simple format-based chat template. For model-specific templates, modify `_build_prompt_from_messages()` in `flask_server.py`

---

## Troubleshooting

### Server Won't Start
- Check that the model path exists and is absolute
- Ensure target platform is correctly specified
- Verify resource limits are not exceeded

### Generation Timeout
- Reduce `max_new_tokens` in RKLLM initialization
- Check device resources (CPU, memory)
- Reduce model size or use quantized versions

### 503 Service Unavailable
- Wait for current inference to complete
- Increase timeout in client
- Check for stuck processes

### Streaming Not Working
- Ensure `stream: true` is set in request
- Use a client that supports Server-Sent Events
- Check Content-Type is `application/x-ndjson`

---

## Advanced Configuration

### Custom Chat Templates

Modify the `_build_prompt_from_messages()` function in `flask_server.py` to support model-specific chat templates:

```python
def _build_prompt_from_messages(messages):
    # Example: Qwen chat template
    prompt_parts = []
    for message in messages:
        role = message.get('role')
        content = message.get('content', '')
        
        if role == 'system':
            prompt_parts.append(f"<|im_start|>system\n{content}<|im_end|>")
        elif role == 'user':
            prompt_parts.append(f"<|im_start|>user\n{content}<|im_end|>")
        elif role == 'assistant':
            prompt_parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")
    
    return '\n'.join(prompt_parts) + "\n<|im_start|>assistant\n"
```

### LoRA Adapter Support

Pass `--lora_model_path` to use LoRA adapters:

```bash
python flask_server.py \
  --rkllm_model_path ~/models/base_model.rkllm \
  --lora_model_path ~/models/lora_adapter.rkllm \
  --target_platform rk3588
```

### Prompt Caching

For faster repeated inferences, use prompt caching:

```bash
python flask_server.py \
  --rkllm_model_path ~/models/model.rkllm \
  --prompt_cache_path ~/models/cache.bin \
  --target_platform rk3588
```

---

## References

- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [RKLLM Documentation](https://github.com/RockchipSoftware/rknn-llm)
- [JSON Lines Format](https://jsonlines.org/)

---

## License

Same as the parent RKLLM project.
