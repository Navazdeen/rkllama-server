# RKLLM-Server Demo

## Overview

RKLLM-Server provides three ways to interact with RKLLM models:

1. **Ollama-Compatible Flask Server** (NEW) - REST API fully compatible with Ollama
2. **Flask Demo Server** - Custom Flask server implementation
3. **Gradio Web Interface** - Interactive web UI

## Before Running

Before running the demo, you need to:
- Have a **model folder** with RKLLM model files (`.rkllm` files)
- Know the IP address of the board (use `ifconfig` command on the board)
- Ensure you have adequate memory and CPU resources
- For local development: Python 3.7+ with Flask/Gradio installed

---

## RKLLM-Server-Flask (Ollama-Compatible) - NEW!

### Quick Start

**Using Build Script (Recommended):**
```bash
./build_rkllm_server_flask.sh --model_folder ~/models --platform rk3588 --local
```

**Manual Start:**
```bash
cd rkllm_server
python flask_server.py \
  --model_folder ~/models \
  --target_platform rk3588 \
  --host 0.0.0.0 \
  --port 8080
```

### Features

- **Ollama API Compatible**: Works with Ollama clients and compatible tools
- **Streaming Support**: Real-time response streaming with Server-Sent Events
- **Multiple Endpoints**:
  - `/api/generate` - Text generation
  - `/api/chat` - Chat completions
  - `/api/tags` - List models
  - `/api/show` - Model details
  - `/api/embeddings` - Embeddings (if supported)
  - `/health` - Health check
  - `/` - Server info

### Usage Examples

#### 1. Health Check
```bash
curl http://localhost:8080/health
```

**Response:**
```json
{"status": "running"}
```

#### 2. List Models
```bash
curl http://localhost:8080/api/models
```

**Response:**
```json
{
  "models": [
    {"name": "model1", "size": "3B", "modified_at": "2024-01-21T..."}
  ]
}
```

#### 3. Get Current Model
```bash
curl http://localhost:8080/api/models/current
```

**Response:**
```json
{"current_model": "model_name"}
```

#### 4. Switch Model
```bash
curl -X POST http://localhost:8080/api/models/switch/model_name \
  -H "Content-Type: application/json"
```

#### 5. Show Model Details
```bash
curl -X POST http://localhost:8080/api/show \
  -H "Content-Type: application/json" \
  -d '{"model": "model_name"}'
```

**Response:**
```json
{
  "license": "",
  "modelfile": "",
  "parameters": "",
  "template": ""
}
```

#### 6. Text Generation (Non-Streaming)
```bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model_name",
    "prompt": "What is AI?",
    "stream": false,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 50
  }'
```

**Response:**
```json
{
  "response": "AI is artificial intelligence...",
  "model": "model_name",
  "created_at": "2024-01-21T...",
  "done": true,
  "total_duration": 1234567,
  "load_duration": 123,
  "prompt_eval_count": 15,
  "eval_count": 50
}
```

#### 7. Text Generation (Streaming)
```bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model_name",
    "prompt": "What is AI?",
    "stream": true
  }'
```

**Response (SSE):**
```
data: {"response": "AI", "model": "model_name", ...}
data: {"response": " is", "model": "model_name", ...}
data: {"response": " artificial", "model": "model_name", ...}
```

#### 8. Chat Completion (Non-Streaming)
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model_name",
    "messages": [
      {"role": "user", "content": "What is AI?"}
    ],
    "stream": false,
    "temperature": 0.7
  }'
```

**Response:**
```json
{
  "message": {"role": "assistant", "content": "AI is artificial intelligence..."},
  "model": "model_name",
  "created_at": "2024-01-21T...",
  "done": true,
  "total_duration": 1234567,
  "eval_count": 50
}
```

#### 9. Chat Completion (Streaming)
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model_name",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is AI?"}
    ],
    "stream": true
  }'
```

**Response (SSE):**
```
data: {"message": {"role": "assistant", "content": "AI"}, ...}
data: {"message": {"role": "assistant", "content": " is"}, ...}
```

#### 10. Embeddings (if supported)
```bash
curl -X POST http://localhost:8080/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model_name",
    "prompt": "What is AI?"
  }'
```

**Response:**
```json
{
  "embedding": [0.123, 0.456, ...]
}
```

#### 11. Pull Model
```bash
curl -X POST http://localhost:8080/api/models/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "model_name"}'
```

#### Python Examples

**Streaming Generation:**
```python
import requests
import json

response = requests.post('http://localhost:8080/api/generate', json={
    'model': 'model_name',
    'prompt': 'What is AI?',
    'stream': True
}, stream=True)

for line in response.iter_lines():
    if line:
        print(json.loads(line)['response'], end='', flush=True)
```

**Chat with History:**
```python
import requests

messages = []

# First message
response = requests.post('http://localhost:8080/api/chat', json={
    'model': 'model_name',
    'messages': [{'role': 'user', 'content': 'What is AI?'}]
}).json()

assistant_response = response['message']['content']
messages.append({'role': 'user', 'content': 'What is AI?'})
messages.append({'role': 'assistant', 'content': assistant_response})

# Follow-up message
response = requests.post('http://localhost:8080/api/chat', json={
    'model': 'model_name',
    'messages': messages + [{'role': 'user', 'content': 'Tell me more'}]
}).json()

print(response['message']['content'])
```

**Model Management:**
```python
import requests

# List models
response = requests.get('http://localhost:8080/api/models').json()
print("Available models:", response['models'])

# Get current model
response = requests.get('http://localhost:8080/api/models/current').json()
print("Current model:", response['current_model'])

# Switch model
response = requests.post('http://localhost:8080/api/models/switch/new_model')
print("Switched to:", response.json())
```

### Advanced Options

```bash
python flask_server.py \
  --model_folder ~/models \
  --target_platform rk3588 \
  --lora_model_path ~/models/lora_adapter.rkllm \
  --prompt_cache_path ~/models/cache.bin \
  --model_name "my-model" \
  --host 0.0.0.0 \
  --port 8080
```

### Endpoint Reference

| Endpoint | Method | Purpose | Streaming |
|----------|--------|---------|----------|
| `/health` | GET | Health check | No |
| `/api/models` | GET | List all models | No |
| `/api/models/current` | GET | Get current model | No |
| `/api/models/<name>` | GET | Get specific model info | No |
| `/api/models/switch/<name>` | POST | Switch active model | No |
| `/api/models/pull` | POST | Pull/load a model | No |
| `/api/show` | POST | Show model details | No |
| `/api/generate` | POST | Text generation | Yes/No |
| `/api/chat` | POST | Chat completion | Yes/No |
| `/api/embeddings` | POST | Get embeddings | No |

### Full Documentation

See [OLLAMA_API_GUIDE.md](./OLLAMA_API_GUIDE.md) for complete API documentation, examples in multiple languages, and advanced usage.

---

## RKLLM-Server-Flask Demo (Original)

### Build

**Local Development:**
```bash
./build_rkllm_server_flask.sh --model_folder ~/models --platform rk3588 --local
```

**Remote Deployment via ADB:**
```bash
./build_rkllm_server_flask.sh --model_folder /board/data/models --platform rk3588 --workshop /board/data
```

**With Optional Parameters:**
```bash
./build_rkllm_server_flask.sh \
  --model_folder ~/models \
  --platform rk3588 \
  --local \
  --lora_model_path ~/models/lora_adapter.rkllm \
  --prompt_cache_path ~/models/cache.bin \
  --port 8080
```

### Access via API
After starting the Flask server, access it via:

**Direct API:**
```bash
# Check server health
curl http://localhost:8080/health

# Generate text
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "default", "prompt": "Hello"}'
```

**Using Demo Script:**
```bash
python demo/chat_api_flask.py
```

**Note**: Update the IP address in `chat_api_flask.py` to match your board's IP address (check with `ifconfig` on the board).

---

## RKLLM-Server-Gradio Demo

### Build

**Local Development:**
```bash
./build_rkllm_server_gradio.sh --model_folder ~/models --platform rk3588 --local
```

**Remote Deployment via ADB:**
```bash
./build_rkllm_server_gradio.sh --model_folder /board/data/models --platform rk3588 --workshop /board/data
```

**With Optional Parameters:**
```bash
./build_rkllm_server_gradio.sh \
  --model_folder ~/models \
  --platform rk3588 \
  --local \
  --lora_model_path ~/models/lora_adapter.rkllm \
  --prompt_cache_path ~/models/cache.bin \
  --port 7860
```

### Access the Server

**Web Interface:**
- Local: `http://localhost:7860/`
- Remote: `http://[board_ip]:7860/`
- Interactive chat with RKLLM models with live thinking updates
- Real-time streaming responses

**API Access:**
```bash
python demo/chat_api_gradio.py
```
- Update the IP address in the script to match your board
- Supports streaming and real-time updates

**Direct Requests:**
```bash
# Gradio uses internal API, check gradio_server.py for endpoints
curl http://localhost:7860/api/predict -d '{...}' -H "Content-Type: application/json"
```

### Pull Models from HuggingFace

The Gradio server now supports pulling RKLLM models directly from HuggingFace Hub!

**Via Web Interface:**
1. Open the Gradio interface at `http://localhost:7860/`
2. In the right sidebar, look for the **"📥 Pull from HF"** section
3. Enter the HuggingFace repository URL in one of these formats:
   - `owner/repo` (e.g., `RockchipAI/DeepSeek-R1`)
   - `https://huggingface.co/owner/repo`
4. Optionally enter a custom model name (or leave blank for auto-generated)
5. Click the **"🔽 Pull"** button
6. Monitor the status message for progress

**Examples:**
```
Owner/Repo format:
  RockchipAI/DeepSeek-R1
  
Full URL format:
  https://huggingface.co/RockchipAI/DeepSeek-R1
  
With custom name:
  Repo: RockchipAI/Qwen-1.5B
  Name: my-qwen-15b
```

**Command Line Pull:**
```bash
# Using Python directly
python -c "
from rkllm_server.model_manager import ModelPuller
puller = ModelPuller('~/models')
success, msg = puller.pull_model('owner/repo')
print(msg)
"
```

**Model Management:**
- After pulling, the model automatically appears in the model selector
- Switch between models using the **"🔀 Load Model"** button
- View model details with the **"ℹ️ Show Details"** button

---

## Comparison of Servers

| Feature | Ollama-Compatible | Flask Demo | Gradio |
|---------|------------------|-----------|--------|
| API Compatibility | Ollama Standard | Custom | Custom |
| Web Interface | No | No | Yes |
| Streaming Support | Yes | Yes | Yes |
| Text Generation | Yes | Yes | Yes |
| Chat Mode | Yes | Yes | Yes |
| Model Management | Yes | No | No |
| Easy Integration | Yes | Moderate | Moderate |
| Python Clients | Yes | Yes | Yes |

---

## Common Issues

### Port Already in Use
```bash
# Change port (Flask)
python flask_server.py --model_folder ~/models --target_platform rk3588 --port 8081

# Or use build script
./build_rkllm_server_flask.sh --model_folder ~/models --platform rk3588 --local --port 8081
```

### Connection Refused
- Verify the server is running: `curl http://localhost:8080/health`
- Check firewall settings
- Verify correct IP address for remote connections

### Out of Memory
- Use a smaller quantized model
- Reduce max_new_tokens
- Close other applications

### Slow Inference
- Check CPU/memory usage with `top`
- Ensure frequency scaling is set correctly
- Consider using quantized models

---

## Performance Tips

1. **Model Optimization**: Use quantized models (int8, int4) for better performance
2. **Frequency Scaling**: The server automatically runs frequency scaling scripts
3. **Batch Processing**: The original implementation doesn't support batching
4. **Caching**: Use prompt caching for repeated queries
5. **Threading**: The Ollama-compatible server uses thread-safe operations

---

## Requirements

- Python 3.7+
- Flask
- RKLLM library (librkllmrt.so)
- Sufficient board memory for model loading
- (Optional) Ollama client for API testing

---

## Support

For issues and questions:
- Check the API guide: [OLLAMA_API_GUIDE.md](./OLLAMA_API_GUIDE.md)
- Review the original demo implementations
- Check RKLLM documentation

---
