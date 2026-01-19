#!/usr/bin/env bash

# Quick Reference: RKLLM Server Build & Demo Scripts
# ===================================================

cat << 'EOF'

╔════════════════════════════════════════════════════════════════════════════╗
║                   RKLLM Server - Quick Reference Guide                    ║
╚════════════════════════════════════════════════════════════════════════════╝

📋 TABLE OF CONTENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Build Scripts
  2. Demo Scripts  
  3. Quick Start Examples
  4. Troubleshooting

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ BUILD SCRIPTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 Flask Server Build Script
   File: ./build_rkllm_server_flask.sh
   
   LOCAL MODE (Development):
   $ ./build_rkllm_server_flask.sh \
       --model_path ~/models/qwen.rkllm \
       --platform rk3588 \
       --local
   
   REMOTE MODE (via ADB):
   $ ./build_rkllm_server_flask.sh \
       --model_path /data/qwen.rkllm \
       --platform rk3588 \
       --workshop /data

🔹 Gradio Server Build Script
   File: ./build_rkllm_server_gradio.sh
   
   LOCAL MODE (Development):
   $ ./build_rkllm_server_gradio.sh \
       --model_path ~/models/qwen.rkllm \
       --platform rk3588 \
       --local
   
   REMOTE MODE (via ADB):
   $ ./build_rkllm_server_gradio.sh \
       --model_path /data/qwen.rkllm \
       --platform rk3588 \
       --workshop /data

📌 COMMON OPTIONS:
   --model_path PATH           Path to RKLLM model file (required)
   --platform PLATFORM         Platform: rk3588, rk3576, rk3562, rv1126b
   --local                     Run locally (no ADB needed)
   --workshop PATH             Board working path (for remote mode)
   --port PORT                 Server port (Flask: 8080, Gradio: 7860)
   --lora_model_path PATH      Optional LoRA model path
   --prompt_cache_path PATH    Optional prompt cache path

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣ DEMO SCRIPTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 Flask Chat API Demo
   File: ./demo/chat_api_flask.py
   
   MODES:
   • chat  - Interactive chat with the model
   • tools - Tool calling and registration demo
   
   EXAMPLES:
   $ python3 demo/chat_api_flask.py --mode chat
   $ python3 demo/chat_api_flask.py --mode tools
   $ python3 demo/chat_api_flask.py --mode chat --stream
   $ python3 demo/chat_api_flask.py --url http://localhost:8080

📌 OPTIONS:
   --mode {chat,tools}         Demo mode (default: chat)
   --url URL                   Server URL (default: http://127.0.0.1:8080)
   --stream                    Enable streaming mode (chat only)
   --help                      Show help message

🔹 Gradio Chat API Demo
   File: ./demo/chat_api_gradio.py
   
   EXAMPLES:
   $ python3 demo/chat_api_gradio.py
   $ python3 demo/chat_api_gradio.py --url http://localhost:7860

📌 OPTIONS:
   --url URL                   Server URL (default: http://127.0.0.1:7860)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3️⃣ QUICK START EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 EXAMPLE 1: Basic Chat Setup
   
   Terminal 1 - Start Flask Server:
   $ cd rkllm_server
   $ python3 flask_server.py \
       --rkllm_model_path ~/models/qwen.rkllm \
       --target_platform rk3588 \
       --model_name qwen
   
   Terminal 2 - Chat with Model:
   $ python3 demo/chat_api_flask.py --mode chat

📖 EXAMPLE 2: Tool Calling Demo
   
   Terminal 1 - Start Server:
   $ cd rkllm_server
   $ python3 flask_server.py \
       --rkllm_model_path ~/models/qwen.rkllm \
       --target_platform rk3588 \
       --model_name qwen
   
   Terminal 2 - Run Tool Demo:
   $ python3 demo/chat_api_flask.py --mode tools

📖 EXAMPLE 3: Streaming Chat
   
   Terminal 1 - Start Server:
   $ cd rkllm_server
   $ python3 flask_server.py \
       --rkllm_model_path ~/models/qwen.rkllm \
       --target_platform rk3588 \
       --model_name qwen
   
   Terminal 2 - Stream Responses:
   $ python3 demo/chat_api_flask.py --mode chat --stream

📖 EXAMPLE 4: Use Build Script
   
   Local Development:
   $ ./build_rkllm_server_flask.sh \
       --model_path ~/models/qwen.rkllm \
       --platform rk3588 \
       --local
   
   Then in another terminal:
   $ python3 demo/chat_api_flask.py --mode chat

📖 EXAMPLE 5: Remote Deployment
   
   Deploy to RK3588 board:
   $ ./build_rkllm_server_flask.sh \
       --model_path /data/qwen.rkllm \
       --platform rk3588 \
       --workshop /data
   
   Connect and chat:
   $ python3 demo/chat_api_flask.py --url http://<board_ip>:8080 --mode chat

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4️⃣ TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ "Cannot connect to server"
   ✓ Make sure server is running in another terminal
   ✓ Check server URL with: curl http://localhost:8080/health
   ✓ Use correct port (Flask: 8080, Gradio: 7860)

❓ "Model file not found"
   ✓ Check model path exists: ls -la ~/models/qwen.rkllm
   ✓ Use absolute path if relative path doesn't work
   ✓ Ensure model file has .rkllm extension

❓ "Permission denied" on scripts
   ✓ Make scripts executable: chmod +x build_rkllm_server_*.sh
   ✓ Check directory permissions

❓ "Port already in use"
   ✓ Use custom port: --port 8081
   ✓ Or kill existing process: pkill -f flask_server.py

❓ "adb is not installed" (remote mode)
   ✓ For local development, use --local flag
   ✓ For remote deployment, install ADB:
     Ubuntu: sudo apt install android-tools-adb

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run comprehensive test suite:
$ python3 test_all_fixes.py

Test individual endpoints:
$ curl http://localhost:8080/health
$ curl -X POST http://localhost:8080/api/chat \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen","messages":[{"role":"user","content":"Hi"}]}'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 DOCUMENTATION FILES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Main Documentation:
  • BUILD_SCRIPTS_FIX_SUMMARY.md      - Detailed changes and features
  • docs/TOOL_CALLING_GUIDE.md        - Tool calling API reference
  • docs/TOOL_CALLING_SUMMARY.md      - Implementation overview

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ QUICK COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Check script help
./build_rkllm_server_flask.sh --help
./build_rkllm_server_gradio.sh --help
python3 demo/chat_api_flask.py --help
python3 demo/chat_api_gradio.py --help

# Run tests
python3 test_all_fixes.py

# Make scripts executable
chmod +x build_rkllm_server_*.sh

# Check server health
curl http://localhost:8080/health | jq .

# Kill existing servers
pkill -f flask_server.py
pkill -f gradio_server.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 PLATFORMS SUPPORTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ rk3588   - Rockchip RK3588
✅ rk3576   - Rockchip RK3576
✅ rk3562   - Rockchip RK3562
✅ rv1126b  - Rockchip RV1126B

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generated: 2026-01-19
Status: ✅ ALL TESTS PASSING - PRODUCTION READY

EOF
