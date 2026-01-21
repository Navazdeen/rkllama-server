"""
Ollama-compatible Flask server for RKLLM model inference.

This server exposes the RKLLM model through REST API endpoints that are compatible
with the Ollama API specification. It supports both streaming and non-streaming modes
for text generation and chat completions.

Key Features:
- /api/generate: Text generation endpoint
- /api/chat: Chat completion endpoint
- /api/tags: List available models
- /api/show: Show model details
- /api/models/switch/<name>: Switch to a different model
- /api/models/pull: Pull a model from a remote source
- /api/embeddings: Get embeddings (if supported by model)
- Streaming support (Server-Sent Events)
- Multi-threaded request handling
"""

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Optional

from flask import Flask, Response, jsonify, request, stream_with_context
from model_api import ModelAPI
from model_manager import ModelManager, ModelResourceManager

import rkllm_server.core.rkllm as rkllm_module
from rkllm_server.core.rkllm import RKLLM

app = Flask(__name__)

# Global variables
rkllm_model = None
model_name = None
target_platform = None
lock = threading.Lock()
model_manager: Optional[ModelManager] = None
resource_manager: Optional[ModelResourceManager] = None
model_api: Optional[ModelAPI] = None

# Model state management - use the same global_text from rkllm module
# so the callback can populate it correctly
is_processing = False

# Callback states (from RKLLM library)
LLMCallState_NORMAL = 0
LLMCallState_WAITING = 1
LLMCallState_FINISH = 2
LLMCallState_ERROR = 3


def generate_model_id(model_path):
    """Generate a unique model ID based on model path."""
    return hashlib.md5(model_path.encode()).hexdigest()[:12]


def format_response_model(model_name):
    """Format model name for Ollama compatibility."""
    return {
        "name": model_name,
        "modified_at": datetime.now().isoformat(),
        "size": 0,  # Size would be retrieved from model metadata
        "digest": generate_model_id(model_name)
    }


@app.route('/api/tags', methods=['GET'])
def list_models():
    """
    List available models (Ollama compatible endpoint).
    
    Returns:
        JSON with list of available models
    """
    return jsonify({
        "models": [format_response_model(model_name)]
    })


@app.route('/api/show', methods=['POST'])
def show_model():
    """
    Show model details (Ollama compatible endpoint).
    
    Returns:
        JSON with model information
    """
    data = request.json or {}
    requested_model = data.get('name', model_name)
    
    if requested_model != model_name:
        return jsonify({'error': 'Model not found'}), 404
    
    return jsonify({
        "name": model_name,
        "modified_at": datetime.now().isoformat(),
        "size": 0,
        "digest": generate_model_id(model_name),
        "details": {
            "format": "rkllm",
            "family": "unknown",
            "families": ["unknown"],
            "parameter_size": "unknown",
            "quantization_level": "unknown"
        }
    })


@app.route('/api/generate', methods=['POST'])
def generate():
    """
    Text generation endpoint (Ollama compatible).
    
    Request JSON:
    {
        "model": "model_name",
        "prompt": "text prompt",
        "stream": false,
        "temperature": 0.8,
        "top_p": 0.9,
        "top_k": 1
    }
    
    Returns:
        JSON response with generated text or stream of responses
    """
    global is_processing
    
    if is_processing:
        return jsonify({'error': 'Server is busy, please try again later'}), 503
    
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Validate request
        if 'prompt' not in data:
            return jsonify({'error': 'Missing required field: prompt'}), 400
        
        prompt = data['prompt']
        stream = data.get('stream', False)
        model = data.get('model', model_name)
        
        # Validate model
        if model != model_name:
            return jsonify({'error': f'Model {model} not found'}), 404
        
        # Parameters for model (can be extended based on RKLLM support)
        temperature = data.get('temperature', 0.8)
        top_p = data.get('top_p', 0.9)
        top_k = data.get('top_k', 1)
        
        lock.acquire()
        try:
            is_processing = True
            # Clear state before starting inference
            rkllm_module.global_text = []
            rkllm_module.global_state = -1
            
            if not stream or stream.lower() == 'false':
                # Non-streaming response
                return _generate_non_streaming(prompt, model, temperature, top_p, top_k)
            else:
                # Streaming response
                return Response(
                    _generate_streaming(prompt, model, temperature, top_p, top_k),
                    content_type='application/x-ndjson'
                )
        finally:
            lock.release()
            is_processing = False
            
    except Exception as e:
        print(f"Error in /api/generate: {str(e)}")
        return jsonify({'error': str(e)}), 500


def _generate_non_streaming(prompt, model, temperature, top_p, top_k):
    """Generate response without streaming."""
    try:
        # Clear previous output
        rkllm_module.global_text = []
        rkllm_module.global_state = -1
        
        # Run model inference
        model_thread = threading.Thread(
            target=rkllm_model.run,
            args=('user', False, prompt)
        )
        model_thread.start()
        
        # Collect output
        full_output = ""
        while model_thread.is_alive() or len(rkllm_module.global_text) > 0:
            while len(rkllm_module.global_text) > 0:
                full_output += rkllm_module.global_text.pop(0)
                time.sleep(0.001)
            
            if model_thread.is_alive():
                time.sleep(0.01)
        
        model_thread.join()
        
        response = {
            "model": model,
            "created_at": datetime.now().isoformat(),
            "response": full_output,
            "done": True,
            "context": [],
            "total_duration": 0,
            "load_duration": 0,
            "prompt_eval_count": 0,
            "prompt_eval_duration": 0,
            "eval_count": len(full_output.split()),
            "eval_duration": 0
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error in _generate_non_streaming: {str(e)}")
        return jsonify({'error': str(e)}), 500


def _generate_streaming(prompt, model, temperature, top_p, top_k):
    """Generate response with streaming (Server-Sent Events)."""
    try:
        # Clear previous output
        rkllm_module.global_text = []
        rkllm_module.global_state = -1
        
        model_thread = threading.Thread(
            target=rkllm_model.run,
            args=('user', False, prompt)
        )
        model_thread.start()
        
        # Stream output
        while model_thread.is_alive() or len(rkllm_module.global_text) > 0:
            while len(rkllm_module.global_text) > 0:
                chunk = rkllm_module.global_text.pop(0)
                
                response = {
                    "model": model,
                    "created_at": datetime.now().isoformat(),
                    "response": chunk,
                    "done": False,
                    "context": [],
                    "total_duration": 0,
                    "load_duration": 0,
                    "prompt_eval_count": 0,
                    "prompt_eval_duration": 0,
                    "eval_count": 1,
                    "eval_duration": 0
                }
                
                yield json.dumps(response) + '\n'
                time.sleep(0.001)
            
            if model_thread.is_alive():
                time.sleep(0.01)
        
        model_thread.join()
        
        # Final response indicating completion
        final_response = {
            "model": model,
            "created_at": datetime.now().isoformat(),
            "response": "",
            "done": True,
            "context": [],
            "total_duration": 0,
            "load_duration": 0,
            "prompt_eval_count": 0,
            "prompt_eval_duration": 0,
            "eval_count": 0,
            "eval_duration": 0
        }
        
        yield json.dumps(final_response) + '\n'
        
    except Exception as e:
        print(f"Error in _generate_streaming: {str(e)}")
        error_response = {
            "error": str(e),
            "done": True
        }
        yield json.dumps(error_response) + '\n'


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chat completion endpoint (Ollama compatible).
    
    Request JSON:
    {
        "model": "model_name",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ],
        "stream": false,
        "temperature": 0.8
    }
    
    Returns:
        JSON response with assistant message or stream of responses
    """
    global is_processing
    
    if is_processing:
        return jsonify({'error': 'Server is busy, please try again later'}), 503
    
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400
        
        # Validate request
        if 'messages' not in data:
            return jsonify({'error': 'Missing required field: messages'}), 400
        
        messages = data['messages']
        if not isinstance(messages, list) or len(messages) == 0:
            return jsonify({'error': 'Messages must be a non-empty list'}), 400
        
        stream = data.get('stream', False)
        model = data.get('model', model_name)
        
        # Validate model
        if model != model_name:
            return jsonify({'error': f'Model {model} not found'}), 404
        
        # Build prompt from messages
        prompt = _build_prompt_from_messages(messages)
        
        # Parameters
        temperature = data.get('temperature', 0.8)
        top_p = data.get('top_p', 0.9)
        top_k = data.get('top_k', 1)
        
        lock.acquire()
        try:
            is_processing = True
            # Clear state before starting inference
            rkllm_module.global_text = []
            rkllm_module.global_state = -1
            
            if not stream:
                # Non-streaming response
                return _chat_non_streaming(prompt, model, messages, temperature, top_p, top_k)
            else:
                # Streaming response
                return Response(
                    _chat_streaming(prompt, model, messages, temperature, top_p, top_k),
                    content_type='application/x-ndjson'
                )
        finally:
            lock.release()
            is_processing = False
            
    except Exception as e:
        print(f"Error in /api/chat: {str(e)}")
        return jsonify({'error': str(e)}), 500


def _build_prompt_from_messages(messages):
    """
    Build a prompt string from chat messages.
    
    Supports formats:
    - Simple: concatenation of messages
    - Chat template format (if model has specific template)
    """
    prompt_parts = []
    
    for message in messages:
        role = message.get('role', 'user')
        content = message.get('content', '')
        
        if role == 'system':
            prompt_parts.append(f"System: {content}")
        elif role == 'user':
            prompt_parts.append(f"User: {content}")
        elif role == 'assistant':
            prompt_parts.append(f"Assistant: {content}")
        else:
            prompt_parts.append(content)
    
    return '\n'.join(prompt_parts)


def _chat_non_streaming(prompt, model, messages, temperature, top_p, top_k):
    """Generate chat response without streaming."""
    try:
        # Clear previous output
        rkllm_module.global_text = []
        rkllm_module.global_state = -1
        
        # Run model inference
        last_user_role = 'user'
        for msg in reversed(messages):
            if msg.get('role') in ['user', 'system']:
                last_user_role = msg.get('role', 'user')
                break
        
        model_thread = threading.Thread(
            target=rkllm_model.run,
            args=(last_user_role, False, prompt)
        )
        model_thread.start()
        
        # Collect output
        full_output = ""
        while model_thread.is_alive() or len(rkllm_module.global_text) > 0:
            while len(rkllm_module.global_text) > 0:
                full_output += rkllm_module.global_text.pop(0)
                time.sleep(0.001)
            
            if model_thread.is_alive():
                time.sleep(0.01)
        
        model_thread.join()
        
        response = {
            "model": model,
            "created_at": datetime.now().isoformat(),
            "message": {
                "role": "assistant",
                "content": full_output
            },
            "done": True,
            "total_duration": 0,
            "load_duration": 0,
            "prompt_eval_count": len(prompt.split()),
            "prompt_eval_duration": 0,
            "eval_count": len(full_output.split()),
            "eval_duration": 0
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error in _chat_non_streaming: {str(e)}")
        return jsonify({'error': str(e)}), 500


def _chat_streaming(prompt, model, messages, temperature, top_p, top_k):
    """Generate chat response with streaming (Server-Sent Events)."""
    try:
        # Clear previous output
        rkllm_module.global_text = []
        rkllm_module.global_state = -1
        
        last_user_role = 'user'
        for msg in reversed(messages):
            if msg.get('role') in ['user', 'system']:
                last_user_role = msg.get('role', 'user')
                break
        
        model_thread = threading.Thread(
            target=rkllm_model.run,
            args=(last_user_role, False, prompt)
        )
        model_thread.start()
        
        # Stream output
        while model_thread.is_alive() or len(rkllm_module.global_text) > 0:
            while len(rkllm_module.global_text) > 0:
                chunk = rkllm_module.global_text.pop(0)
                
                response = {
                    "model": model,
                    "created_at": datetime.now().isoformat(),
                    "message": {
                        "role": "assistant",
                        "content": chunk
                    },
                    "done": False
                }
                
                yield json.dumps(response) + '\n'
                time.sleep(0.001)
            
            if model_thread.is_alive():
                time.sleep(0.01)
        
        model_thread.join()
        
        # Final response indicating completion
        final_response = {
            "model": model,
            "created_at": datetime.now().isoformat(),
            "message": {
                "role": "assistant",
                "content": ""
            },
            "done": True,
            "total_duration": 0,
            "load_duration": 0,
            "prompt_eval_count": len(prompt.split()),
            "prompt_eval_duration": 0,
            "eval_count": 0,
            "eval_duration": 0
        }
        
        yield json.dumps(final_response) + '\n'
        
    except Exception as e:
        print(f"Error in _chat_streaming: {str(e)}")
        error_response = {
            "error": str(e),
            "done": True
        }
        yield json.dumps(error_response) + '\n'


@app.route('/api/embeddings', methods=['POST'])
def embeddings():
    """
    Get embeddings endpoint (Ollama compatible).
    Note: Only supported if the RKLLM model supports embeddings mode.
    
    Returns:
        JSON with embeddings or error if not supported
    """
    return jsonify({
        'error': 'Embeddings are not supported by this RKLLM model'
    }), 501


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'model': model_name}), 200


# ==================== MODEL MANAGEMENT ENDPOINTS ====================

@app.route('/api/models', methods=['GET'])
def list_available_models():
    """List all available models"""
    if not model_api:
        return jsonify({'error': 'Model manager not initialized'}), 500
    
    return jsonify(model_api.list_models()), 200


@app.route('/api/models/<model_name>', methods=['GET'])
def get_model_info(model_name: str):
    """Get information about a specific model"""
    if not model_api:
        return jsonify({'error': 'Model manager not initialized'}), 500
    
    return jsonify(model_api.get_model_info(model_name)), 200


@app.route('/api/models/switch/<model_name>', methods=['POST'])
def switch_model(model_name: str):
    """Switch to a different model"""
    global rkllm_model
    
    if not model_manager or not model_api:
        return jsonify({'error': 'Model manager not initialized'}), 500
    
    try:
        model_path = model_manager.get_model_path(model_name)
        if not model_path:
            return jsonify({'error': f'Model not found: {model_name}'}), 404
        
        with lock:
            # Cleanup old model
            old_model = rkllm_model
            
            # Load new model
            rkllm_model = RKLLM(model_path)
            
            # Cleanup old model resources
            if old_model:
                try:
                    if hasattr(old_model, 'release'):
                        old_model.release()
                    if hasattr(old_model, 'destroy'):
                        old_model.destroy()
                except:
                    pass
            
            # Update model manager
            model_manager.set_current_model(model_name)
        
        return jsonify(model_api.switch_model(model_name)), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/pull', methods=['POST'])
def pull_model():
    """Pull a model from HuggingFace"""
    if not model_api:
        return jsonify({'error': 'Model manager not initialized'}), 500
    
    data = request.json or {}
    hf_url = data.get('hf_url')
    model_name = data.get('model_name')
    system_prompt = data.get('system_prompt', 'You are a helpful assistant.')
    metadata = data.get('metadata', {})
    
    if not hf_url:
        return jsonify({'error': 'hf_url is required'}), 400
    
    result = model_api.pull_model(hf_url, model_name, system_prompt, metadata)
    
    return jsonify(result), 200 if result.get('success') else 400


@app.route('/api/models/current', methods=['GET'])
def get_current_model():
    """Get current model information"""
    if not model_api:
        return jsonify({'error': 'Model manager not initialized'}), 500
    
    return jsonify(model_api.get_current_model()), 200


@app.route('/api/models/<model_name>/modelfile', methods=['GET'])
def get_modelfile(model_name: str):
    """Get modelfile for a model"""
    if not model_api:
        return jsonify({'error': 'Model manager not initialized'}), 500
    
    return jsonify(model_api.get_modelfile(model_name)), 200


@app.route('/api/models/<model_name>/modelfile', methods=['POST'])
def set_modelfile(model_name: str):
    """Create or update modelfile for a model"""
    if not model_api:
        return jsonify({'error': 'Model manager not initialized'}), 500
    
    data = request.json or {}
    return jsonify(model_api.create_modelfile(model_name, data)), 200


@app.route('/', methods=['GET'])
def root():
    """Root endpoint with server information."""
    return jsonify({
        'name': 'RKLLM Ollama-Compatible Server',
        'version': '1.0.0',
        'model': model_name,
        'platform': target_platform,
        'endpoints': {
            'generate': '/api/generate (POST)',
            'chat': '/api/chat (POST)',
            'tags': '/api/tags (GET)',
            'show': '/api/show (POST)',
            'embeddings': '/api/embeddings (POST)',
            'health': '/health (GET)',
            'models': '/api/models (GET)',
            'switch_model': '/api/models/switch/<name> (POST)',
            'pull_model': '/api/models/pull (POST)',
            'tools/set': '/api/tools/set (POST)',
            'tools/call': '/api/tools/call (POST)'
        }
    }), 200


# ====================== Tool Calling Endpoints ======================

@app.route('/api/tools/set', methods=['POST'])
def set_tools():
    """
    Set function tools for the model.
    
    Request body:
    {
        "system_prompt": "You are a helpful assistant with tools",
        "tools": [
            {
                "name": "get_weather",
                "description": "Get weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    }
                }
            }
        ],
        "tool_choice": "auto"
    }
    
    Returns:
        JSON with success status
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        system_prompt = data.get('system_prompt', 'You are a helpful assistant with tools.')
        tools = data.get('tools', [])
        tool_choice = data.get('tool_choice', 'auto')
        
        if not tools:
            return jsonify({'error': 'No tools provided'}), 400
        
        # Format tools as JSON schema string for RKLLM
        tools_json = json.dumps(tools)
        tool_response_str = json.dumps({
            "tool_choice": tool_choice,
            "type": "function"
        })
        
        # Set the function tools in the RKLLM model
        with lock:
            rkllm_model.set_function_tools(system_prompt, tools_json, tool_response_str)
        
        return jsonify({
            'status': 'success',
            'system_prompt': system_prompt,
            'tools_count': len(tools),
            'tool_names': [tool.get('name') for tool in tools]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to set tools: {str(e)}'}), 500


@app.route('/api/tools/call', methods=['POST'])
def call_tool():
    """
    Call a tool through the model with function calling.
    
    Request body:
    {
        "prompt": "What's the weather in Paris?",
        "stream": false,
        "temperature": 0.8,
        "top_p": 0.9
    }
    
    Returns:
        JSON with model response and tool calls (if any)
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        if 'prompt' not in data:
            return jsonify({'error': 'Missing required field: prompt'}), 400
        
        prompt = data.get('prompt', '')
        stream = data.get('stream', False)
        
        if stream:
            return Response(
                stream_with_context(_tool_call_streaming(prompt)),
                mimetype='application/x-ndjson'
            ), 200
        else:
            return _tool_call_non_streaming(prompt), 200
            
    except Exception as e:
        return jsonify({'error': f'Tool call failed: {str(e)}'}), 500


def _tool_call_non_streaming(prompt):
    """Execute tool call and return full response."""
    try:
        with lock:
            # Clear global state before inference
            rkllm_module.global_text = []
            rkllm_module.global_state = -1
            
            # Run inference with the prompt
            model_thread = threading.Thread(target=rkllm_model.run, args=('user', False, prompt))
            model_thread.start()
            
            # Wait for inference to complete
            model_thread.join(timeout=300)
            
            if model_thread.is_alive():
                rkllm_model.abort()
                model_thread.join(timeout=5)
                return jsonify({'error': 'Inference timeout'}), 504
        
        # Collect all generated text
        response_text = ''.join(rkllm_module.global_text)
        
        # Try to parse tool calls from response
        tool_calls = _parse_tool_calls(response_text)
        
        response = {
            'model': model_name,
            'created_at': datetime.now().isoformat(),
            'response': response_text,
            'tool_calls': tool_calls,
            'done': True,
            'eval_count': len(response_text.split())
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': str(e), 'done': True}), 500


def _tool_call_streaming(prompt):
    """Stream tool call responses."""
    try:
        with lock:
            # Clear global state before inference
            rkllm_module.global_text = []
            rkllm_module.global_state = -1
            
            # Run inference
            model_thread = threading.Thread(target=rkllm_model.run, args=('user', False, prompt))
            model_thread.start()
            
            # Stream response tokens
            last_len = 0
            timeout_counter = 0
            max_timeout = 600  # 10 minutes max
            
            while model_thread.is_alive() or len(rkllm_module.global_text) > 0:
                current_len = len(rkllm_module.global_text)
                
                if current_len > last_len:
                    new_tokens = rkllm_module.global_text[last_len:]
                    last_len = current_len
                    timeout_counter = 0  # Reset timeout on activity
                    
                    for token in new_tokens:
                        response = {
                            'model': model_name,
                            'created_at': datetime.now().isoformat(),
                            'response': token,
                            'done': False,
                            'eval_count': 1
                        }
                        yield json.dumps(response) + '\n'
                else:
                    timeout_counter += 1
                    if timeout_counter > max_timeout:
                        break
                
                time.sleep(0.01)
            
            # Parse tool calls from final response
            response_text = ''.join(rkllm_module.global_text)
            tool_calls = _parse_tool_calls(response_text)
            
            # Send final response with tool calls
            final_response = {
                'model': model_name,
                'created_at': datetime.now().isoformat(),
                'response': '',
                'tool_calls': tool_calls,
                'done': True,
                'eval_count': len(response_text.split())
            }
            yield json.dumps(final_response) + '\n'
            
    except Exception as e:
        error_response = {
            'error': str(e),
            'done': True
        }
        yield json.dumps(error_response) + '\n'


def _parse_tool_calls(response_text):
    """
    Parse tool calls from model response.
    Looks for patterns like <tool_call>{"name": "function", "arguments": {...}}</tool_call>
    """
    import re
    tool_calls = []
    
    # Pattern 1: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
    pattern1 = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
    matches = re.findall(pattern1, response_text, re.DOTALL)
    
    for match in matches:
        try:
            # Try to parse as JSON
            tool_json = json.loads(match)
            if 'name' in tool_json:
                tool_calls.append({
                    'name': tool_json['name'],
                    'arguments': tool_json.get('arguments', {})
                })
        except json.JSONDecodeError:
            # If not valid JSON, try alternate parsing
            try:
                lines = match.strip().split('\n')
                tool_call = {}
                
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().strip('"').lower()
                        value = value.strip().strip(',').strip('"')
                        
                        if key == 'name':
                            tool_call['name'] = value
                        elif key == 'arguments':
                            try:
                                tool_call['arguments'] = json.loads(value)
                            except:
                                tool_call['arguments'] = value
                
                if tool_call.get('name'):
                    tool_calls.append(tool_call)
            except Exception as e:
                print(f"Error parsing tool call: {e}")
    
    # Pattern 2: function_calls in JSON format
    pattern2 = r'"function_calls":\s*(\[.*?\])'
    json_matches = re.findall(pattern2, response_text, re.DOTALL)
    
    for match in json_matches:
        try:
            funcs = json.loads(match)
            for func in funcs:
                if isinstance(func, dict) and 'name' in func:
                    tool_calls.append({
                        'name': func['name'],
                        'arguments': func.get('arguments', {})
                    })
        except Exception as e:
            print(f"Error parsing JSON tool calls: {e}")
    
    # Pattern 3: tool_call: ... format
    pattern3 = r'tool_call:\s*(\w+)\s*(?:\(|,)\s*(?:args|arguments)?:?\s*(\{.*?\})?'
    matches = re.findall(pattern3, response_text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        try:
            tool_name = match[0].strip()
            args_str = match[1] if match[1] else '{}'
            args = json.loads(args_str)
            tool_calls.append({
                'name': tool_name,
                'arguments': args
            })
        except Exception as e:
            print(f"Error parsing tool_call format: {e}")
    
    return tool_calls


# ====================== End Tool Calling Endpoints ======================


def setup_signal_handlers():
    """Setup handlers for graceful shutdown."""
    import signal
    
    def signal_handler(sig, frame):
        print("\n\nShutting down RKLLM server...")
        if rkllm_model:
            rkllm_model.release()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point."""
    global rkllm_model, model_name, target_platform, model_manager, resource_manager, model_api
    
    parser = argparse.ArgumentParser(
        description='Ollama-compatible RKLLM Flask server with Model Management'
    )
    
    # Model folder or single model path
    parser.add_argument(
        '--model_folder',
        type=str,
        default=None,
        help='Path to folder containing models (recommended)'
    )
    parser.add_argument(
        '--rkllm_model_path',
        type=str,
        default=None,
        help='Absolute path of the converted RKLLM model (deprecated, use --model_folder)'
    )
    parser.add_argument(
        '--target_platform',
        type=str,
        required=True,
        help='Target platform: rk3588/rk3576/rv1126b/rk3562'
    )
    parser.add_argument(
        '--lora_model_path',
        type=str,
        default=None,
        help='Absolute path of the lora_model on the Linux board'
    )
    parser.add_argument(
        '--prompt_cache_path',
        type=str,
        default=None,
        help='Absolute path of the prompt_cache file on the Linux board'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Server host address'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Server port'
    )
    parser.add_argument(
        '--model_name',
        type=str,
        default=None,
        help='Custom model name (defaults to model path basename)'
    )
    
    args = parser.parse_args()
    
    # Validate platform
    if args.target_platform not in ["rk3588", "rk3576", "rv1126b", "rk3562"]:
        print(f"Error: Invalid target platform: {args.target_platform}")
        print("Supported platforms: rk3588, rk3576, rv1126b, rk3562")
        sys.exit(1)
    
    # Set resource limits
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (102400, 102400))
    except Exception as e:
        print(f"Warning: Could not set resource limit: {e}")
    
    # Fix frequency scaling (requires sudo) - skip if no sudo access
    try:
        command = f"sudo -n bash fix_freq_{args.target_platform}.sh"
        subprocess.run(command, shell=True, timeout=10, check=False, 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Note: Could not fix frequency scaling (requires sudo): {e}")
    
    target_platform = args.target_platform
    
    print("=" * 50)
    print("🚀 RKLLM Flask Server Starting")
    print("=" * 50)
    
    # Initialize model manager if folder provided
    if args.model_folder:
        print(f"📁 Using model folder: {args.model_folder}")
        if not os.path.exists(args.model_folder):
            print(f"❌ Model folder not found: {args.model_folder}")
            sys.exit(1)
        
        try:
            model_manager = ModelManager(args.model_folder, args.target_platform)
            resource_manager = ModelResourceManager()
            model_api = ModelAPI(args.model_folder, args.target_platform)
            
            # Discover and load first available model
            models = model_manager.discover_models()
            if not models:
                print("❌ No models found in model folder")
                sys.exit(1)
            
            first_model = list(models.keys())[0]
            first_model_path = models[first_model]
            model_name = first_model
            
            print(f"📦 Loading model: {first_model}")
            rkllm_model = RKLLM(first_model_path, args.lora_model_path, 
                               args.prompt_cache_path, args.target_platform)
            model_manager.set_current_model(first_model)
            
        except Exception as e:
            print(f"❌ Error initializing model manager: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    elif args.rkllm_model_path:
        print(f"⚠️  Using deprecated single model path. Consider using --model_folder")
        
        # Validate arguments
        if not os.path.exists(args.rkllm_model_path):
            print("Error: Please provide the correct rkllm model path.")
            print(f"Path not found: {args.rkllm_model_path}")
            sys.exit(1)
        
        if args.lora_model_path and not os.path.exists(args.lora_model_path):
            print("Error: Lora model path not found.")
            sys.exit(1)
        
        if args.prompt_cache_path and not os.path.exists(args.prompt_cache_path):
            print("Error: Prompt cache path not found.")
            sys.exit(1)
        
        model_name = args.model_name or os.path.basename(args.rkllm_model_path)
        
        print(f"Model path: {args.rkllm_model_path}")
        print(f"Model name: {model_name}")
        
        try:
            rkllm_model = RKLLM(
                args.rkllm_model_path,
                args.lora_model_path,
                args.prompt_cache_path,
                args.target_platform
            )
        except Exception as e:
            print(f"❌ Error: Failed to initialize RKLLM model: {e}")
            sys.exit(1)
    else:
        print("❌ Either --model_folder or --rkllm_model_path must be provided")
        sys.exit(1)
    
    print("=" * 50)
    print("✅ RKLLM model initialized successfully!")
    print("=" * 50)
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    
    # Start Flask app
    print(f"\nStarting Ollama-compatible RKLLM server...")
    print(f"Server running at http://{args.host}:{args.port}")
    print(f"API endpoints:")
    print(f"  - Generate: POST /api/generate")
    print(f"  - Chat: POST /api/chat")
    print(f"  - Tags: GET /api/tags")
    print(f"  - Show: POST /api/show")
    print(f"  - Models: GET /api/models")
    print(f"  - Switch Model: POST /api/models/switch/<name>")
    print(f"  - Pull Model: POST /api/models/pull")
    print(f"  - Health: GET /health")
    print(f"  - Root: GET /")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        app.run(
            host=args.host,
            port=args.port,
            threaded=True,
            debug=False
        )
    finally:
        print("\nShutting down...")
        if rkllm_model:
            print("Releasing RKLLM model resources...")
            try:
                rkllm_model.release()
            except:
                pass

if __name__ == "__main__":
    main()
