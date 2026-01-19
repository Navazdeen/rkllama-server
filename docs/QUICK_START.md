# Quick Start Guide - Ollama-Compatible RKLLM Server

## Getting Started in 5 Minutes

### Step 1: Start the Server

```bash
cd rkllm_server
python flask_server.py \
  --rkllm_model_path ~/models/your_model.rkllm \
  --target_platform rk3588 \
  --port 8080
```

You should see output like:
```
==================================================
Initializing RKLLM model...
Model path: ~/models/your_model.rkllm
Target platform: rk3588
Model name: your_model
==================================================

rkllm init success!

==================================================
RKLLM model initialized successfully!
==================================================

Starting Ollama-compatible RKLLM server...
Server running at http://0.0.0.0:8080
API endpoints:
  - Generate: POST /api/generate
  - Chat: POST /api/chat
  - Tags: GET /api/tags
  - Show: POST /api/show
  - Health: GET /health
  - Root: GET /

Press Ctrl+C to stop the server
```

### Step 2: Test the Server

#### Option A: Using cURL

**Health Check:**
```bash
curl http://localhost:8080/health
```

**List Models:**
```bash
curl http://localhost:8080/api/tags
```

**Generate Text:**
```bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your_model",
    "prompt": "What is artificial intelligence?",
    "stream": false
  }'
```

**Chat:**
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your_model",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "stream": false
  }'
```

#### Option B: Using Python

```python
import requests
import json

# Check health
response = requests.get('http://localhost:8080/health')
print("Health:", response.json())

# List models
response = requests.get('http://localhost:8080/api/tags')
print("Available models:", response.json())

# Generate text
response = requests.post('http://localhost:8080/api/generate', json={
    'model': 'your_model',
    'prompt': 'What is AI?',
    'stream': False
})
print("Generated:", response.json()['response'])

# Chat
response = requests.post('http://localhost:8080/api/chat', json={
    'model': 'your_model',
    'messages': [
        {'role': 'user', 'content': 'Hello!'}
    ],
    'stream': False
})
print("Assistant:", response.json()['message']['content'])
```

#### Option C: Using Ollama CLI (if installed)

```bash
# Generate text
ollama run your_model "What is AI?"

# Note: May need to configure Ollama to point to your server
```

### Step 3: Test Streaming

#### Streaming with cURL
```bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your_model",
    "prompt": "Tell me about quantum computing",
    "stream": true
  }'
```

#### Streaming with Python
```python
import requests
import json

response = requests.post('http://localhost:8080/api/generate', json={
    'model': 'your_model',
    'prompt': 'Tell me about quantum computing',
    'stream': True
}, stream=True)

print("Streaming response:")
for line in response.iter_lines():
    if line:
        data = json.loads(line)
        if data.get('response'):
            print(data['response'], end='', flush=True)
print()
```

---

## Common Tasks

### Change Port
```bash
python flask_server.py \
  --rkllm_model_path ~/models/your_model.rkllm \
  --target_platform rk3588 \
  --port 8081
```

### Use LoRA Adapter
```bash
python flask_server.py \
  --rkllm_model_path ~/models/your_model.rkllm \
  --target_platform rk3588 \
  --lora_model_path ~/models/lora_adapter.rkllm
```

### Custom Model Name
```bash
python flask_server.py \
  --rkllm_model_path ~/models/your_model.rkllm \
  --target_platform rk3588 \
  --model_name "my-awesome-model"
```

### Allow Remote Connections
```bash
python flask_server.py \
  --rkllm_model_path ~/models/your_model.rkllm \
  --target_platform rk3588 \
  --host 0.0.0.0  # Listen on all interfaces
```

---

## Chat Examples

### Simple Chat
```python
response = requests.post('http://localhost:8080/api/chat', json={
    'model': 'your_model',
    'messages': [
        {'role': 'user', 'content': 'What is Python?'}
    ]
})
print(response.json()['message']['content'])
```

### Multi-turn Conversation
```python
messages = [
    {'role': 'system', 'content': 'You are a helpful coding assistant.'},
    {'role': 'user', 'content': 'How do I read a file in Python?'},
    {'role': 'assistant', 'content': 'You can use the `open()` function...'},
    {'role': 'user', 'content': 'Can you show me an example?'}
]

response = requests.post('http://localhost:8080/api/chat', json={
    'model': 'your_model',
    'messages': messages
})
print(response.json()['message']['content'])
```

### With System Prompt
```python
response = requests.post('http://localhost:8080/api/chat', json={
    'model': 'your_model',
    'messages': [
        {
            'role': 'system',
            'content': 'You are an expert in astronomy. Always provide accurate and detailed information.'
        },
        {
            'role': 'user',
            'content': 'Tell me about black holes.'
        }
    ]
})
print(response.json()['message']['content'])
```

---

## Response Examples

### Generation Response
```json
{
  "model": "your_model",
  "created_at": "2024-01-19T10:30:00",
  "response": "Artificial intelligence is the simulation of human intelligence processes by computer systems...",
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

### Chat Response
```json
{
  "model": "your_model",
  "created_at": "2024-01-19T10:30:00",
  "message": {
    "role": "assistant",
    "content": "Hello! I'm here to help. What can I assist you with?"
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

## Troubleshooting

### "Connection Refused"
- Ensure server is running: `curl http://localhost:8080/health`
- Check if port is in use: `lsof -i :8080`
- Try a different port: `--port 8081`

### "Model not found"
- Check model name matches exactly
- Use `/api/tags` to see available models
- Verify model path exists

### "Server is busy"
- Wait for current request to complete
- RKLLM server processes one request at a time
- Increase timeout in client code

### "Out of Memory"
- Use a smaller model
- Close other applications
- Reduce context length or max_new_tokens

### Slow Response
- Check CPU load: `top`
- Check memory usage: `free -h`
- Verify frequency scaling is enabled
- Use quantized models (int8, int4)

---

## Next Steps

- Read full API documentation: [OLLAMA_API_GUIDE.md](../OLLAMA_API_GUIDE.md)
- Integrate with your application
- Explore advanced features like function calling
- Set up monitoring and logging

---

## Support

For detailed information on all endpoints and parameters, see:
- **Complete API Guide**: [OLLAMA_API_GUIDE.md](../OLLAMA_API_GUIDE.md)
- **Main README**: [README.md](../README.md)

---
