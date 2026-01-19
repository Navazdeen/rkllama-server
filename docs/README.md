# RKLLM-Server Demo

## Overview

RKLLM-Server provides three ways to interact with RKLLM models:

1. **Ollama-Compatible Flask Server** (NEW) - REST API fully compatible with Ollama
2. **Flask Demo Server** - Custom Flask server implementation
3. **Gradio Web Interface** - Interactive web UI

## Before Running

Before running the demo, you need to:
- Have a converted RKLLM model file on the board
- Know the IP address of the board (use `ifconfig` command)
- Ensure you have adequate memory and CPU resources

---

## RKLLM-Server-Flask (Ollama-Compatible) - NEW!

### Quick Start

Start the Ollama-compatible server directly:

```bash
cd rkllm_server
python flask_server.py \
  --rkllm_model_path ~/models/Qwen2.5-3B-Instruct-rk3588-w8a8_g128-opt.rkllm \
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

#### Text Generation (cURL)
```bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model_name",
    "prompt": "What is AI?",
    "stream": false
  }'
```

#### Chat Completion (cURL)
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

#### Streaming Generation (Python)
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

### Advanced Options

```bash
python flask_server.py \
  --rkllm_model_path ~/models/model.rkllm \
  --target_platform rk3588 \
  --lora_model_path ~/models/lora_adapter.rkllm \
  --prompt_cache_path ~/models/cache.bin \
  --model_name "my-model" \
  --host 0.0.0.0 \
  --port 8080
```

### Full Documentation

See [OLLAMA_API_GUIDE.md](./OLLAMA_API_GUIDE.md) for complete API documentation, examples in multiple languages, and advanced usage.

---

## RKLLM-Server-Flask Demo (Original)

### Build
You can run the demo with the command:
```bash
# Usage: ./build_rkllm_server_flask.sh --workshop [RKLLM-Server Working Path] --model_path [Absolute Path of Converted RKLLM Model on Board] --platform [Target Platform: rk3588/rk3576] [--lora_model_path [Lora Model Path]] [--prompt_cache_path [Prompt Cache File Path]]
./build_rkllm_server_flask.sh --workshop /user/data --model_path /user/data/model.rkllm --platform rk3588
```

### Access with API 
After building the RKLLM-Server-Flask, you can use `chat_api_flask.py` to access the server.

**Note**: Update the IP address in `chat_api_flask.py` to match your board's IP address (check with `ifconfig`).

---

## RKLLM-Server-Gradio Demo

### Build
You can run the demo with the command:
```bash
# Usage: ./build_rkllm_server_gradio.sh --workshop [RKLLM-Server Working Path] --model_path [Absolute Path of Converted RKLLM Model on Board] --platform [Target Platform: rk3588/rk3576] [--lora_model_path [Lora Model Path]] [--prompt_cache_path [Prompt Cache File Path]]
./build_rkllm_server_gradio.sh --workshop /user/data --model_path /user/data/model.rkllm --platform rk3588
```

### Access the Server
After running the demo, you can access the RKLLM-Server-Gradio in two ways:
1. **Web Interface**: Open your browser and access `http://[board_ip]:8080/`. Chat with the RKLLM models in the visual interface.
2. **API Access**: Use the `chat_api_gradio.py` script (update the IP address in the code first).

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
# Change port
python flask_server.py --rkllm_model_path ~/models/model.rkllm --target_platform rk3588 --port 8081
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
