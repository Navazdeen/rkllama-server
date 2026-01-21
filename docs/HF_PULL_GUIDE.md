# HuggingFace Model Pull Guide

## Overview

The Gradio server now supports pulling RKLLM models directly from HuggingFace Hub! This allows you to easily download and manage pre-converted RKLLM models without manual downloading.

## Features

✅ **Direct HF Integration** - Pull models directly from HuggingFace Hub  
✅ **Web UI Integration** - Pull models through the Gradio interface  
✅ **Auto Model Detection** - Automatically finds `.rkllm` files in repositories  
✅ **Custom Naming** - Optionally specify custom model names  
✅ **Automatic Refresh** - Model selector updates after successful pull  
✅ **Status Feedback** - Real-time feedback during download  

## Web Interface Usage

### Step-by-Step Guide

1. **Start the Gradio Server:**
   ```bash
   ./build_rkllm_server_gradio.sh --model_folder ~/models --platform rk3588 --local
   ```

2. **Open Web Interface:**
   - Navigate to `http://localhost:7860/`

3. **Locate HF Pull Section:**
   - Look at the right sidebar under **"⚙️ Settings"**
   - Find the **"📥 Pull from HF"** section

4. **Enter Repository URL:**
   - Format options:
     - `owner/repo` (e.g., `RockchipAI/Qwen-7B`)
     - `https://huggingface.co/owner/repo` (full URL)

5. **Optional: Custom Model Name:**
   - Leave blank for auto-generated name based on repo
   - Or enter custom name (e.g., "my-model")

6. **Click Pull Button:**
   - Click **"🔽 Pull"** button
   - Watch status box for progress updates

7. **Switch to Downloaded Model:**
   - New model appears in model selector
   - Click **"🔀 Load Model"** to switch to it

## URL Formats

### Valid Repository URLs

**Short Format (Recommended):**
```
owner/repo-name
```

**Full Format:**
```
https://huggingface.co/owner/repo-name
```

### Examples

**Qwen Models:**
```
RockchipAI/Qwen-1.5B
RockchipAI/Qwen-7B-Chat
```

**DeepSeek Models:**
```
RockchipAI/DeepSeek-R1-Distill
RockchipAI/DeepSeek-Coder
```

**Custom Repository:**
```
your-username/your-model
```

## Model Name Options

### Auto-Generated Names
If you don't specify a custom name, the model gets an auto-generated name based on:
- Repository owner: `RockchipAI`
- Repository name: `Qwen-7B`
- Result: `RockchipAI_Qwen-7B` or similar

### Custom Names
Specify a custom name for easier identification:
- Simple: `my-model`
- Descriptive: `qwen-7b-chat-rkllm`
- Project-specific: `project-x-model-v2`

### Name Requirements
- Use alphanumeric characters, hyphens, underscores
- Avoid special characters
- Keep under 50 characters

## HTTP API Usage

### Pull via Python

**Using ModelPuller:**
```python
from rkllm_server.model_manager import ModelPuller

puller = ModelPuller('~/models')

# With short format
success, msg = puller.pull_model('RockchipAI/Qwen-7B')

# With full URL
success, msg = puller.pull_model('https://huggingface.co/RockchipAI/Qwen-7B')

# With custom name
success, msg = puller.pull_model('RockchipAI/Qwen-7B', 'my-custom-qwen')

if success:
    print(f"✅ {msg}")
else:
    print(f"❌ {msg}")
```

**Using Model API:**
```python
from rkllm_server.model_api import ModelAPI

api = ModelAPI('~/models', 'rk3588')
result = api.pull_model('RockchipAI/Qwen-7B', 'my-model')

if result.get('success'):
    print(f"✅ {result['message']}")
else:
    print(f"❌ {result['message']}")
```

### Pull via cURL

**Basic Pull:**
```bash
curl -X POST http://localhost:8080/api/models/pull \
  -H "Content-Type: application/json" \
  -d '{
    "name": "RockchipAI/Qwen-7B"
  }'
```

**With Custom Name:**
```bash
curl -X POST http://localhost:8080/api/models/pull \
  -H "Content-Type: application/json" \
  -d '{
    "name": "RockchipAI/Qwen-7B",
    "custom_name": "my-qwen"
  }'
```

## Status Messages

### Success Messages

| Message | Meaning |
|---------|---------|
| `✅ Model pulled successfully` | Model download and extraction complete |
| `✅ Model already exists locally` | Model already in folder, no re-download |
| `✅ Model ready to use` | Model available and can be loaded |

### Error Messages

| Message | Solution |
|---------|----------|
| `❌ Invalid HuggingFace URL` | Check URL format, use `owner/repo` or full URL |
| `❌ Model not found in repository` | Verify repo name, check it's a public repo |
| `❌ No .rkllm files found` | Repository doesn't contain RKLLM models |
| `❌ Insufficient disk space` | Free up disk space and try again |
| `❌ Network error` | Check internet connection and repo URL |

## Requirements

### Software
- Python 3.7+
- Git (for LFS support)
- Optional: `huggingface-hub` package (auto-installed)

### Hardware
- Sufficient disk space for model (typically 1-20GB)
- Internet connection for downloading

### Permissions
- Read access to model folder
- Write permission for downloads
- Internet access to HuggingFace Hub

## Troubleshooting

### Model Won't Pull

**Issue:** "Model not found in repository"

**Solutions:**
1. Verify repository exists and is public
2. Check spelling of owner/repo names
3. Ensure repository has `.rkllm` files
4. Try full URL format instead of short format

### Slow Download

**Issue:** Pull takes very long time

**Solutions:**
1. Check internet connection bandwidth
2. Verify no other large downloads happening
3. Try smaller model first
4. Check HuggingFace Hub status (occasional outages)

### Disk Space Error

**Issue:** "Insufficient disk space"

**Solutions:**
1. Free up disk space: `df -h` to check
2. Delete unused models: Check `/models` folder
3. Compress or remove old backups
4. Use external storage if available

### Model Appears But Won't Load

**Issue:** Model in selector but fails to load

**Solutions:**
1. Verify model is valid RKLLM format
2. Check platform compatibility (rk3588, rk3576, etc.)
3. Ensure sufficient RAM available
4. Check model file integrity
5. Check console/logs for detailed error

## Best Practices

### 1. Naming Convention
```
# Good
my-project-qwen-7b
customer-x-deepseek
demo-model-v2

# Avoid
Model_123
QwEn (mixed case)
my model (spaces)
```

### 2. Disk Management
- Monitor disk space: `df -h`
- Delete unused models: `rm -r ~/models/old-model`
- Archive old models: `tar -gz old-model.tar.gz old-model`

### 3. Network Optimization
- Pull during off-peak hours
- Use wired connection for large downloads
- Avoid pulling multiple models simultaneously

### 4. Model Organization
```
~/models/
├── qwen-7b/
├── deepseek-r1/
├── my-custom-model/
└── archive/
    └── old-model/
```

## Supported Repositories

### Popular RKLLM Models

**RockchipAI Official:**
- `RockchipAI/Qwen-7B`
- `RockchipAI/Qwen-1.5B`
- `RockchipAI/DeepSeek-R1-Distill`
- `RockchipAI/Llama-2-7B`

**Community Models:**
- Community-contributed RKLLM conversions
- Custom fine-tuned RKLLM models
- Any public repo with `.rkllm` files

### Finding Models

1. **Search HuggingFace Hub:**
   - Go to https://huggingface.co/models
   - Search: "rkllm" or "rk3588"
   - Filter by relevant platform

2. **Check RockchipAI Organization:**
   - https://huggingface.co/RockchipAI
   - All official RKLLM models

3. **Community Collections:**
   - Ask in RKLLM community
   - Check GitHub repositories
   - Check forums and discussions

## Performance Tips

### Download Speed
- Large models (7B+) take 30+ minutes
- Smaller models (1-3B) take 5-15 minutes
- Use `status` command to monitor progress

### Model Selection
- Smaller models: 1B, 3B (faster inference)
- Medium models: 7B (good balance)
- Larger models: 13B+ (better quality, slower)

### Memory Usage
- Allocate adequate RAM for model loading
- Close other applications during loading
- Monitor: `top` or `free -h`

## Limitations

### Current Limitations
- Only downloads from HuggingFace Hub
- Requires `.rkllm` files in repository
- One model at a time per pull operation
- Limited to models on public HF repositories

### Future Enhancements
- Batch pulling of multiple models
- Custom filtering for specific model files
- Pre-download verification
- Automatic version management

## Getting Help

### Documentation
- [Main README](../README.md)
- [Gradio Server Guide](./UI_DESIGN_VERIFICATION.md)
- [Model Management](./MODEL_MANAGEMENT_SYSTEM.md)

### Support
- Check console output for detailed errors
- Review logs in `~/.rkllm_server/logs/`
- Create issue on GitHub with error details
- Ask community on HuggingFace discussions

## Examples

### Example 1: Pull Qwen Model
```bash
# Via Web UI:
1. URL: RockchipAI/Qwen-7B
2. Name: my-qwen
3. Click Pull

# Via Python:
from rkllm_server.model_manager import ModelPuller
puller = ModelPuller('~/models')
success, msg = puller.pull_model('RockchipAI/Qwen-7B', 'my-qwen')
```

### Example 2: Pull and Load Model
```bash
# Start server
./build_rkllm_server_gradio.sh --model_folder ~/models --platform rk3588 --local

# In web UI:
1. Go to "📥 Pull from HF" section
2. Enter: RockchipAI/DeepSeek-R1-Distill
3. Click Pull
4. In "Model Selection" section, select new model
5. Click "🔀 Load Model"
6. Model is now active!
```

### Example 3: Custom Named Model
```
URL: RockchipAI/Qwen-1.5B
Name: qwen-15b-chat-prod
```

Result: Model saved as `qwen-15b-chat-prod` for easy identification

## Version History

### v1.0 (Current)
- ✅ Basic HF pull support
- ✅ Web UI integration
- ✅ Auto model detection
- ✅ Custom naming
- ✅ Status feedback

### v1.1 (Planned)
- ⏳ Batch pulling
- ⏳ Model versioning
- ⏳ Pre-download verification
- ⏳ Progress percentage display

---

**Last Updated:** January 2026  
**Maintained by:** RKLLM Team
