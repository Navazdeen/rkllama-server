#!/usr/bin/env python3
# ==========================================================
# RKLLM OpenAI + Ollama Compatible Server (Production Grade)
# ==========================================================

import argparse
import json
import resource
import subprocess
import time
import re
from queue import Queue
from threading import Thread, Event
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# ----------------------------------------------------------
# RKLLM import (from Rockchip demo)
# ----------------------------------------------------------
from rkllm import RKLLM

# ==========================================================
# GLOBAL STATE
# ==========================================================
app = Flask(__name__)
CORS(app)

rkllm = None
request_queue = Queue()
last_request_time = time.time()
KEEP_ALIVE_SECONDS = 300  # default 5 minutes

# ----------------------------------------------------------
# TOOL REGISTRY
# ----------------------------------------------------------
TOOLS = {}

def tool(name, description=""):
    def wrapper(fn):
        TOOLS[name] = {
            "fn": fn,
            "description": description
        }
        return fn
    return wrapper

# Example tools
@tool("get_weather", "Get weather for a city")
def get_weather(city: str):
    return f"The weather in {city} is sunny and 30°C"

@tool("add_numbers", "Add two numbers")
def add_numbers(a: int, b: int):
    return a + b

# ==========================================================
# UTILS
# ==========================================================
def now():
    return int(time.time())

def parse_keep_alive(val):
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        if val.endswith("m"):
            return int(val[:-1]) * 60
        if val.endswith("h"):
            return int(val[:-1]) * 3600
    return 300

def messages_to_prompt(messages, system_extra=""):
    prompt = ""
    if system_extra:
        prompt += f"[SYSTEM]\n{system_extra}\n"

    for m in messages:
        role = m.get("role")
        content = m.get("content", "")
        if role == "system":
            prompt += f"[SYSTEM]\n{content}\n"
        elif role == "user":
            prompt += f"[USER]\n{content}\n"
        elif role == "assistant":
            prompt += f"[ASSISTANT]\n{content}\n"
        elif role == "tool":
            prompt += f"[TOOL]\n{content}\n"

    prompt += "[ASSISTANT]\n"
    return prompt

def build_tool_prompt():
    if not TOOLS:
        return ""
    txt = (
        "You can call tools using the format:\n"
        "TOOL_CALL: <name>(<json_arguments>)\n\n"
        "Available tools:\n"
    )
    for name, meta in TOOLS.items():
        txt += f"- {name}: {meta['description']}\n"
    return txt

TOOL_CALL_RE = re.compile(r"TOOL_CALL:\s*(\w+)\((\{.*?\})\)", re.DOTALL)

def detect_tool_call(text):
    match = TOOL_CALL_RE.search(text)
    if not match:
        return None
    return match.group(1), json.loads(match.group(2))

# ==========================================================
# REQUEST QUEUE (SINGLE NPU FLIGHT)
# ==========================================================
def inference_worker():
    while True:
        item = request_queue.get()
        if item is None:
            break

        prompt, done_event, result = item
        try:
            result["text"] = rkllm.generate(prompt)
        except Exception as e:
            result["error"] = str(e)

        done_event.set()
        request_queue.task_done()

Thread(target=inference_worker, daemon=True).start()

def run_inference(prompt):
    global last_request_time
    last_request_time = time.time()

    done = Event()
    result = {}
    request_queue.put((prompt, done, result))
    done.wait()

    if "error" in result:
        raise RuntimeError(result["error"])
    return result["text"]

# ==========================================================
# KEEP ALIVE REAPER
# ==========================================================
def model_reaper():
    global rkllm
    while True:
        time.sleep(5)
        if rkllm and (time.time() - last_request_time) > KEEP_ALIVE_SECONDS:
            print("[RKLLM] Unloading model (keep_alive expired)")
            rkllm.release()
            rkllm = None

Thread(target=model_reaper, daemon=True).start()

# ==========================================================
# TOOL CALL LOOP
# ==========================================================
def run_with_tools(messages):
    system_tools = build_tool_prompt()
    prompt = messages_to_prompt(messages, system_tools)

    for _ in range(3):  # max recursion depth
        output = run_inference(prompt)
        tool_call = detect_tool_call(output)

        if not tool_call:
            return output

        name, args = tool_call
        if name not in TOOLS:
            return output

        result = TOOLS[name]["fn"](**args)

        messages.append({"role": "assistant", "content": output})
        messages.append({"role": "tool", "name": name, "content": str(result)})
        prompt = messages_to_prompt(messages, system_tools)

    return output

# ==========================================================
# API ENDPOINTS
# ==========================================================

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/api/version")
def version():
    return jsonify({"version": "0.2.5"})

# ---------------- OpenAI Chat ----------------
@app.route("/v1/chat/completions", methods=["POST"])
def openai_chat():
    data = request.get_json(force=True)
    messages = data["messages"]
    keep_alive = data.get("keep_alive")

    global KEEP_ALIVE_SECONDS
    if keep_alive:
        KEEP_ALIVE_SECONDS = parse_keep_alive(keep_alive)

    output = run_with_tools(messages)

    return jsonify({
        "id": "chatcmpl-rkllm",
        "object": "chat.completion",
        "created": now(),
        "model": "rkllm",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": output
            },
            "finish_reason": "stop"
        }]
    })

# ---------------- Ollama Chat ----------------
@app.route("/api/chat", methods=["POST"])
def ollama_chat():
    data = request.get_json(force=True)
    messages = data["messages"]
    stream = data.get("stream", True)
    keep_alive = data.get("keep_alive")

    global KEEP_ALIVE_SECONDS
    if keep_alive:
        KEEP_ALIVE_SECONDS = parse_keep_alive(keep_alive)

    def generate():
        text = run_with_tools(messages)
        for ch in text:
            yield json.dumps({
                "message": {
                    "role": "assistant",
                    "content": ch
                },
                "done": False
            }) + "\n"

        yield json.dumps({
            "message": {
                "role": "assistant",
                "content": ""
            },
            "done": True,
            "done_reason": "stop"
        }) + "\n"

    return Response(generate(), content_type="application/x-ndjson")

# ---------------- Embeddings (stub) ----------------
@app.route("/v1/embeddings", methods=["POST"])
def embeddings():
    data = request.get_json(force=True)
    text = data.get("input", "")

    # Placeholder until RKLLM exposes hidden states
    vector = [0.0] * 384

    return jsonify({
        "object": "list",
        "data": [{
            "object": "embedding",
            "embedding": vector,
            "index": 0
        }],
        "model": data.get("model", "rkllm")
    })

# ==========================================================
# MAIN
# ==========================================================
def main():
    global rkllm

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Path to .rkllm file")
    parser.add_argument("--platform", default="rk3588")
    parser.add_argument("--port", default=11434, type=int)
    args = parser.parse_args()
    
    # Fix frequency
    command = "sudo bash fix_freq_{}.sh".format(args.platform)
    subprocess.run(command, shell=True)

    # Set resource limit
    resource.setrlimit(resource.RLIMIT_NOFILE, (102400, 102400))

    print("[RKLLM] Loading model...")
    rkllm = RKLLM(args.model, args.platform)

    print(f"[RKLLM] Server running on port {args.port}")
    app.run(host="0.0.0.0", port=args.port, threaded=True)

if __name__ == "__main__":
    main()
