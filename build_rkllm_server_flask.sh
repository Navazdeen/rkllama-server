#!/bin/bash

#*****************************************************************************************#
# RKLLM-Server-Flask Build Script
# This script builds and runs the Flask-based RKLLM server.
# Works with local development and remote deployment via ADB.
#
# Usage (Local):
#   ./build_rkllm_server_flask.sh --model_path /path/to/model.rkllm --platform rk3588 --local
#
# Usage (Remote via ADB):
#   ./build_rkllm_server_flask.sh --model_path /board/path/model.rkllm --platform rk3588 --workshop /board/workspace
#
# Example:
#   ./build_rkllm_server_flask.sh --model_path ~/models/qwen.rkllm --platform rk3588 --local
#*****************************************************************************************#

set -e

LORA_PATH=""
PROMPT_FILE_PATH=""
WORKING_PATH=""
LOCAL_MODE=false
SERVER_PORT=8080

# Function to display help
function show_help {
    cat << 'HELP'
Usage: ./build_rkllm_server_flask.sh [OPTIONS]

OPTIONS:
  --model_path PATH       Path to RKLLM model file (required)
  --platform PLATFORM     Target platform: rk3588, rk3576, rk3562, rv1126b (required)
  --local                 Run locally instead of via ADB (optional)
  --workshop PATH         Working path on board for ADB deployment (optional)
  --lora_model_path PATH  LoRA model path (optional)
  --prompt_cache_path PATH Prompt cache file path (optional)
  --port PORT             Server port for local mode (default: 8080)
  --help                  Show this help message

Examples:
  # Local development
  ./build_rkllm_server_flask.sh --model_path ~/models/qwen.rkllm --platform rk3588 --local
  
  # Remote deployment via ADB
  ./build_rkllm_server_flask.sh --model_path /data/qwen.rkllm --platform rk3588 --workshop /data
HELP
}

# Parse command-line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model_path)
            MODEL_PATH="$2"
            shift 2
            ;;
        --platform)
            TARGET_PLATFORM="$2"
            shift 2
            ;;
        --workshop)
            WORKING_PATH="$2"
            shift 2
            ;;
        --local)
            LOCAL_MODE=true
            shift
            ;;
        --lora_model_path)
            LORA_PATH="$2"
            shift 2
            ;;
        --prompt_cache_path)
            PROMPT_FILE_PATH="$2"
            shift 2
            ;;
        --port)
            SERVER_PORT="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *) 
            echo "❌ Invalid option: $1" >&2
            show_help
            exit 1
            ;;
    esac
done

# Validate required arguments
if [[ -z "$MODEL_PATH" || -z "$TARGET_PLATFORM" ]]; then
    echo "❌ Error: --model_path and --platform are required" >&2
    show_help
    exit 1
fi

echo "========================================"
echo "RKLLM Flask Server Builder"
echo "========================================"

if [[ "$LOCAL_MODE" == "true" ]]; then
    # LOCAL MODE: Run directly on this machine
    echo "📱 Mode: LOCAL DEVELOPMENT"
    echo "🎯 Model: $MODEL_PATH"
    echo "📍 Platform: $TARGET_PLATFORM"
    echo "🔌 Port: $SERVER_PORT"
    
    # Check if model exists
    if [[ ! -f "$MODEL_PATH" ]]; then
        echo "❌ Error: Model file not found: $MODEL_PATH" >&2
        exit 1
    fi
    
    # Check dependencies
    echo "\n🔍 Checking dependencies..."
    if ! command -v python3 &> /dev/null; then
        echo "❌ Error: python3 is not installed" >&2
        exit 1
    fi
    
    if ! python3 -c "import flask" &> /dev/null; then
        echo "⚠️  Flask not installed. Installing..."
        pip3 install flask==2.2.2 Werkzeug==2.2.2 requests
    else
        echo "✅ Flask is installed"
    fi
    
    # Kill any existing server
    echo "\n🛑 Stopping any running servers..."
    pkill -f "flask_server.py" || true
    sleep 1
    
    # Start the server
    echo "\n🚀 Starting Flask server..."
    echo "========================================"
    
    cd "$(dirname "$0")/rkllm_server"
    
    CMD="python3 flask_server.py --rkllm_model_path $MODEL_PATH --target_platform $TARGET_PLATFORM --port $SERVER_PORT"
    
    if [[ -n "$LORA_PATH" ]]; then
        CMD="$CMD --lora_model_path $LORA_PATH"
    fi
    
    if [[ -n "$PROMPT_FILE_PATH" ]]; then
        CMD="$CMD --prompt_cache_path $PROMPT_FILE_PATH"
    fi
    
    # Run with error handling
    if eval "$CMD"; then
        echo "✅ Server running successfully"
    else
        echo "❌ Server startup failed"
        exit 1
    fi
    
else
    # REMOTE MODE: Deploy via ADB to board
    if [[ -z "$WORKING_PATH" ]]; then
        echo "❌ Error: --workshop is required for remote deployment" >&2
        exit 1
    fi
    
    echo "📱 Mode: REMOTE DEPLOYMENT (via ADB)"
    echo "🎯 Model: $MODEL_PATH (on board)"
    echo "📍 Platform: $TARGET_PLATFORM"
    echo "💾 Workspace: $WORKING_PATH"
    
    # Check if ADB is available
    if ! command -v adb &> /dev/null; then
        echo "❌ Error: adb is not installed" >&2
        exit 1
    fi
    
    # Install dependencies on board
    echo "\n🔧 Installing dependencies on board..."
    adb shell << 'BOARD_EOF'
pkill -f "python3 flask_server.py" || true
pkill -f "python3 gradio_server.py" || true

if ! command -v pip3 &> /dev/null; then
    echo "⚠️  Installing pip3..."
    sudo apt-get update -qq
    sudo apt-get install -y python3-pip > /dev/null 2>&1
fi

if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Installing Flask..."
    pip3 install flask==2.2.2 Werkzeug==2.2.2 -i https://pypi.tuna.tsinghua.edu.cn/simple --break-system-packages 2>/dev/null || pip3 install flask==2.2.2 Werkzeug==2.2.2
else
    echo "✅ Flask is installed"
fi
BOARD_EOF
    
    # Create working directory
    echo "\n📁 Setting up working directory on board..."
    adb shell mkdir -p "$WORKING_PATH" || true
    
    # Push server files
    echo "📤 Pushing server files to board..."
    adb push ./rkllm_server "$WORKING_PATH" > /dev/null 2>&1 || {
        echo "❌ Failed to push files" >&2
        exit 1
    }
    
    # Start the server
    echo "\n🚀 Starting Flask server on board..."
    echo "========================================"
    
    adb shell << BOARD_EOF
cd $WORKING_PATH/rkllm_server/
python3 flask_server.py --rkllm_model_path $MODEL_PATH --target_platform $TARGET_PLATFORM$(if [[ -n "$LORA_PATH" ]]; then echo " --lora_model_path $LORA_PATH"; fi)$(if [[ -n "$PROMPT_FILE_PATH" ]]; then echo " --prompt_cache_path $PROMPT_FILE_PATH"; fi)
BOARD_EOF
fi

echo "========================================"
echo "✅ Done!"
