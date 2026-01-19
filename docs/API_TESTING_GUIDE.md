# API Testing Guide - Curl Commands

## Quick Reference for Testing All Endpoints

### 1. Health Check
```bash
curl http://localhost:8080/health
```

### 2. Server Info
```bash
curl http://localhost:8080/
```

### 3. List Models
```bash
curl http://localhost:8080/api/tags
```

### 4. Show Model Details
```bash
curl -X POST http://localhost:8080/api/show \
  -H "Content-Type: application/json" \
  -d '{"name":"qwen"}'
```

### 5. Generate Text (Non-Streaming)
```bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "prompt": "What is 2+2?",
    "stream": false
  }'
```

### 6. Generate Text (Streaming)
```bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "prompt": "Tell me a story",
    "stream": true
  }'
```

### 7. Chat Completion (Non-Streaming)
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "stream": false
  }'
```

### 8. Chat Completion (Streaming)
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [
      {"role": "system", "content": "You are helpful"},
      {"role": "user", "content": "Hello!"}
    ],
    "stream": true
  }'
```

### 9. Multi-turn Chat
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "messages": [
      {"role": "user", "content": "What is Python?"},
      {"role": "assistant", "content": "Python is a programming language"},
      {"role": "user", "content": "Is it useful?"}
    ],
    "stream": false
  }'
```

### 10. Embeddings (Not Supported)
```bash
curl -X POST http://localhost:8080/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen",
    "input": "test text"
  }'
```

## Important Notes

1. **Always include** `-H "Content-Type: application/json"` header for POST requests
2. **Model name** must be lowercase and match the deployed model (use `/api/tags` to check)
3. **Streaming**: Set `"stream": true` to get real-time responses (NDJSON format)
4. **Error Responses**:
   - 400: Missing required fields or invalid JSON
   - 404: Model not found
   - 500: Internal server error
   - 503: Server busy (only one request at a time)

## Pretty Print JSON Response

Add `| python -m json.tool` to pretty print responses:

```bash
curl http://localhost:8080/api/tags | python -m json.tool
```

## Save Response to File

```bash
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen","prompt":"test","stream":false}' \
  > response.json
```

## Test Results Summary

All 12 tests passed:
✅ Health check
✅ Server info
✅ List models
✅ Show model details
✅ Generate non-streaming
✅ Chat non-streaming
✅ Generate streaming
✅ Chat streaming
✅ Embeddings (returns 501 - not supported)
✅ Error handling (missing prompt)
✅ Error handling (invalid model)
✅ Error handling (missing messages)

The Ollama-compatible server is working perfectly!
