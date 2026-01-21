# Quick Reference: HuggingFace Model Pull

## Web UI Quick Start

**Access Web UI:**
```
http://localhost:7860
```

**Pull a Model:**
1. Right sidebar → **"📥 Pull from HF"** section
2. Enter URL: `RockchipAI/Qwen-7B`
3. Optionally enter custom name
4. Click **"🔽 Pull"** button
5. Wait for status message
6. New model appears in **"Model Selection"** dropdown

## URL Formats

```bash
# Short format (recommended)
RockchipAI/Qwen-7B

# Full URL format
https://huggingface.co/RockchipAI/Qwen-7B
```

## Popular Models

```bash
RockchipAI/Qwen-1.5B
RockchipAI/Qwen-7B
RockchipAI/Qwen-7B-Chat
RockchipAI/DeepSeek-R1-Distill
RockchipAI/Llama-2-7B
```

## Python Usage

```python
from rkllm_server.model_manager import ModelPuller

puller = ModelPuller('~/models')
success, msg = puller.pull_model('RockchipAI/Qwen-7B', 'my-model')
print(msg)
```

## cURL Command

```bash
curl -X POST http://localhost:8080/api/models/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "RockchipAI/Qwen-7B"}'
```

## Status Messages

| Status | Meaning |
|--------|---------|
| `✅ Model pulled successfully` | Download complete, ready to use |
| `❌ Invalid HuggingFace URL` | Check URL format |
| `❌ Model not found in repository` | Verify repo exists |
| `❌ No .rkllm files found` | Repo has no RKLLM models |

## Troubleshooting

### "Model not found"
- Check URL spelling
- Verify repo is public
- Check repo has `.rkllm` files

### "Network error"
- Check internet connection
- Try full URL format
- Check HF Hub status

### "Disk space"
- Free up disk: `df -h`
- Delete old models: `rm -r ~/models/old-model`

## Load Pulled Model

1. Model auto-appears in dropdown
2. Select from **"Switch Model"** dropdown
3. Click **"🔀 Load Model"** button
4. Model is now active

## File Location

```bash
# Models stored in
~/models/

# View downloaded models
ls ~/models/
```

## Documentation

- Full Guide: [HF_PULL_GUIDE.md](HF_PULL_GUIDE.md)
- Main README: [README.md](../README.md)
- Gradio Docs: [UI_DESIGN_VERIFICATION.md](UI_DESIGN_VERIFICATION.md)
