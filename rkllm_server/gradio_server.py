"""
Enhanced Gradio interface for RKLLM model inference.

This server exposes the RKLLM model through a Gradio web interface.
It uses the same underlying inference engine as the Flask server.

Features:
- Web-based chat interface with rich history display
- Real-time streaming responses
- Multi-session support (independent chat sessions)
- Conversation context management
- Automatic history summarization when too long
- Enhanced UI elements with better organization
- Model configuration options
"""

import sys
import os
import argparse
import threading
import time
import json
import gradio as gr
from typing import List, Tuple, Optional, Any, Dict
from datetime import datetime
from rkllm import RKLLM
import rkllm as rkllm_module

# Global variables
rkllm_model = None
model_name = None
target_platform = None
lock = threading.Lock()

# Session management
sessions: Dict[str, List[Dict]] = {}
current_session_id = "session_1"
session_counter = 1

# Configuration
MAX_HISTORY_MESSAGES = 20  # Keep last N messages before summarizing
MAX_CONTEXT_LENGTH = 4000  # Max tokens for context to model


def initialize_model(model_path: str, platform: str, model_id: str = "qwen") -> bool:
    """Initialize the RKLLM model."""
    global rkllm_model, model_name, target_platform, sessions, current_session_id
    
    try:
        print(f"🔧 Initializing RKLLM model from {model_path}...")
        print(f"   Platform: {platform}")
        
        rkllm_model = RKLLM(model_path=model_path)
        model_name = model_id
        target_platform = platform
        
        # Initialize default session
        sessions["session_1"] = []
        current_session_id = "session_1"
        
        print("✅ Model initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize model: {str(e)}")
        return False


def create_new_session() -> str:
    """Create a new chat session."""
    global session_counter, current_session_id, sessions
    session_counter += 1
    session_id = f"session_{session_counter}"
    sessions[session_id] = []
    current_session_id = session_id
    return session_id


def get_session_list() -> List[str]:
    """Get list of all session IDs."""
    return list(sessions.keys())


def switch_session(session_id: str) -> Tuple[List[Dict], str]:
    """Switch to a different session."""
    global current_session_id
    if session_id in sessions:
        current_session_id = session_id
        return sessions[session_id], session_id
    return [], current_session_id


def delete_session(session_id: str) -> str:
    """Delete a session."""
    global current_session_id, sessions
    if session_id in sessions and len(sessions) > 1:
        del sessions[session_id]
        if current_session_id == session_id:
            current_session_id = list(sessions.keys())[0]
        return f"✅ Session {session_id} deleted"
    return "❌ Cannot delete session"


def get_current_history() -> List[Dict]:
    """Get current session history."""
    return sessions.get(current_session_id, [])


def build_context_from_history(history: List[Dict], max_messages: int = 10) -> str:
    """Build context string from recent history for model input."""
    if not history:
        return ""
    
    # Use only last N messages to avoid too long context
    recent_messages = history[-max_messages:]
    context = "Recent conversation:\n"
    
    for msg in recent_messages:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = msg.get("content", "")
        # Truncate very long messages
        if len(content) > 200:
            content = content[:200] + "..."
        context += f"{role}: {content}\n"
    
    return context


def summarize_history(history: List[Dict]) -> List[Dict]:
    """Summarize old messages when history gets too long."""
    if len(history) <= MAX_HISTORY_MESSAGES:
        return history
    
    # Keep only recent messages, summarize older ones
    messages_to_keep = history[-10:]  # Keep last 10 messages
    
    # Create a summary message of older conversations
    old_messages = history[:-10]
    summary_text = f"[📝 Conversation Summary: {len(old_messages)} previous messages discussing "
    
    # Extract key topics from old messages
    topics = set()
    for msg in old_messages:
        content = msg.get("content", "")[:50]  # First 50 chars
        if content:
            topics.add(content)
    
    summary_text += ", ".join(list(topics)[:3]) + "]"
    
    summary_msg = {
        "role": "system",
        "content": summary_text,
        "timestamp": datetime.now().isoformat(),
        "is_summary": True
    }
    
    return [summary_msg] + messages_to_keep


def add_message_to_session(role: str, content: str) -> None:
    """Add a message to current session history."""
    global sessions, current_session_id
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    
    sessions[current_session_id].append(message)
    
    # Summarize if too long
    if len(sessions[current_session_id]) > MAX_HISTORY_MESSAGES:
        sessions[current_session_id] = summarize_history(sessions[current_session_id])


def generate_response(prompt: str, history: Optional[List[Dict]] = None, stream: bool = True) -> str:
    """Generate response from the model with conversation context."""
    global rkllm_model, lock
    
    if rkllm_model is None:
        return "❌ Model not initialized"
    
    try:
        with lock:
            # Build context from history
            context = ""
            if history:
                context = build_context_from_history(history)
            
            # Combine context with current prompt
            full_prompt = context + prompt if context else prompt
            
            # Reset global state
            rkllm_module.global_text = []
            rkllm_module.global_state = -1
            
            # Run model inference in a thread
            model_thread = threading.Thread(
                target=rkllm_model.run,
                args=('user', False, full_prompt)
            )
            model_thread.start()
            
            # Collect output with polling
            full_output = ""
            while model_thread.is_alive() or len(rkllm_module.global_text) > 0:
                while len(rkllm_module.global_text) > 0:
                    full_output += rkllm_module.global_text.pop(0)
                    time.sleep(0.001)
                
                if model_thread.is_alive():
                    time.sleep(0.01)
            
            model_thread.join()
            response = full_output
            
        return response
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


def generate_response_streaming(prompt: str, history: Optional[List[Dict]] = None):
    """Generate response with streaming (yields tokens in real-time)."""
    global rkllm_model, lock
    
    if rkllm_model is None:
        yield "❌ Model not initialized"
        return
    
    try:
        with lock:
            # Build context from history
            context = ""
            if history:
                context = build_context_from_history(history)
            
            # Combine context with current prompt
            full_prompt = context + prompt if context else prompt
            
            # Reset global state
            rkllm_module.global_text = []
            rkllm_module.global_state = -1
            
            # Run model inference in a thread
            model_thread = threading.Thread(
                target=rkllm_model.run,
                args=('user', False, full_prompt)
            )
            model_thread.start()
            
            # Stream output token by token
            streamed_output = ""
            while model_thread.is_alive() or len(rkllm_module.global_text) > 0:
                while len(rkllm_module.global_text) > 0:
                    token = rkllm_module.global_text.pop(0)
                    streamed_output += token
                    yield streamed_output
                    time.sleep(0.001)
                
                if model_thread.is_alive():
                    time.sleep(0.01)
            
            model_thread.join()
            
    except Exception as e:
        yield f"❌ Error: {str(e)}"


def create_gradio_interface():
    """Create the enhanced Gradio interface with sessions and history."""
    with gr.Blocks(title=f"RKLLM Chat - {model_name}", theme=gr.themes.Soft()) as demo:
        # Header
        gr.Markdown(f"""
        # 🤖 RKLLM Advanced Chat Interface
        
        **Model:** {model_name} | **Platform:** {target_platform}
        
        Multi-session chat with conversation context, history summarization, and real-time streaming.
        """)
        
        # Session management row
        with gr.Row():
            with gr.Column(scale=2):
                session_dropdown = gr.Dropdown(
                    label="📋 Chat Sessions",
                    choices=["session_1"],
                    value="session_1"
                )
            with gr.Column(scale=1):
                new_session_btn = gr.Button("➕ New Session", scale=1)
            with gr.Column(scale=1):
                delete_session_btn = gr.Button("🗑️ Delete", scale=1)
        
        # Session info
        session_info = gr.Textbox(
            label="📊 Session Info",
            value="Messages: 0 | Last updated: -",
            interactive=False
        )
        
        # Main chat area - Initialize with current session history
        chatbot = gr.Chatbot(
            label="💬 Conversation",
            height=500,
            value=sessions.get(current_session_id, [])
        )
        
        # Input section with improved layout
        with gr.Row():
            msg = gr.Textbox(
                label="📝 Message",
                placeholder="Type your message here...",
                lines=3,
                scale=4,
                show_label=True
            )
            with gr.Column(scale=1):
                submit_btn = gr.Button("📤 Send", scale=1, size="lg")
        
        # Controls section
        with gr.Row():
            stream_toggle = gr.Checkbox(
                label="🌊 Streaming",
                value=True,
                scale=1
            )
            context_toggle = gr.Checkbox(
                label="🧠 Use Context",
                value=True,
                scale=1
            )
            clear_btn = gr.Button("🧹 Clear Chat", scale=1)
            info_btn = gr.Button("ℹ️ Model Info", scale=1)
        
        # Status area
        status_text = gr.Textbox(
            label="Status",
            value="Ready",
            interactive=False,
            lines=1
        )
        
        def update_session_info():
            """Update session information display."""
            history = get_current_history()
            timestamp = datetime.now().strftime("%H:%M:%S")
            return f"Messages: {len(history)} | Last updated: {timestamp}"
        
        def update_session_dropdown():
            """Update the session dropdown options."""
            sessions_list = get_session_list()
            return gr.Dropdown(choices=sessions_list, value=current_session_id)
        
        def on_new_session():
            """Create a new session and update UI."""
            session_id = create_new_session()
            return update_session_dropdown(), [], update_session_info(), f"✅ Created {session_id}"
        
        def on_switch_session(session_id):
            """Switch to selected session."""
            history, _ = switch_session(session_id)
            return history, update_session_info(), f"✅ Switched to {session_id}"
        
        def on_delete_session(session_id):
            """Delete selected session."""
            msg_result = delete_session(session_id)
            sessions_list = get_session_list()
            return gr.Dropdown(choices=sessions_list, value=current_session_id), [], update_session_info(), msg_result
        
        def respond(message: str, chat_history, use_streaming: bool = True, use_context: bool = True):
            """Enhanced response handler with context and sessions."""
            if not message.strip():
                if use_streaming:
                    yield chat_history
                else:
                    return chat_history
                return
            
            # Get current session history
            session_history = get_current_history()
            
            # Add user message to both display and session
            if not chat_history:
                chat_history = []
            
            chat_history = chat_history + [{
                "role": "user",
                "content": message
            }]
            
            add_message_to_session("user", message)
            
            # Generate bot response
            try:
                if use_streaming:
                    # Streaming mode with context - use generator
                    response_text = ""
                    for partial_response in generate_response_streaming(
                        message,
                        history=session_history if use_context else None
                    ):
                        response_text = partial_response
                        updated_history = chat_history[:-1] + [{
                            "role": "assistant",
                            "content": response_text
                        }]
                        yield updated_history
                    
                    chat_history = updated_history
                    add_message_to_session("assistant", response_text)
                    yield chat_history
                else:
                    # Non-streaming mode - return result
                    response = generate_response(
                        message,
                        history=session_history if use_context else None,
                        stream=False
                    )
                    chat_history = chat_history + [{
                        "role": "assistant",
                        "content": response
                    }]
                    add_message_to_session("assistant", response)
                    # Must yield for generator function
                    yield chat_history
                    
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                chat_history = chat_history + [{
                    "role": "assistant",
                    "content": error_msg
                }]
                yield chat_history
        
        def get_model_info():
            """Get detailed model information."""
            return f"""**RKLLM Model Information**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📛 Name: {model_name}
🏗️  Platform: {target_platform}
⚙️  Status: ✅ Running
🌐 Interface: Gradio (Enhanced)
📊 Sessions: {len(sessions)}
💾 Context Length: {MAX_CONTEXT_LENGTH} chars
📝 Max History: {MAX_HISTORY_MESSAGES} messages
            """
        
        # Event handlers
        new_session_btn.click(
            on_new_session,
            outputs=[session_dropdown, chatbot, session_info, status_text]
        )
        
        session_dropdown.change(
            on_switch_session,
            inputs=[session_dropdown],
            outputs=[chatbot, session_info, status_text]
        )
        
        delete_session_btn.click(
            on_delete_session,
            inputs=[session_dropdown],
            outputs=[session_dropdown, chatbot, session_info, status_text]
        )
        
        def clear_input_and_update():
            """Clear input box and update session info."""
            return "", update_session_info()
        
        def reset_chat_and_update():
            """Reset chat and update info."""
            return update_session_info()
        
        def sync_chatbot_with_session():
            """Sync chatbot with current session storage - ensures display matches backend."""
            return get_current_history()
        
        msg.submit(respond, [msg, chatbot, stream_toggle, context_toggle], chatbot).then(
            clear_input_and_update,
            outputs=[msg, session_info]
        ).then(
            sync_chatbot_with_session,
            outputs=[chatbot]
        )
        
        submit_btn.click(respond, [msg, chatbot, stream_toggle, context_toggle], chatbot).then(
            clear_input_and_update,
            outputs=[msg, session_info]
        ).then(
            sync_chatbot_with_session,
            outputs=[chatbot]
        )
        
        clear_btn.click(lambda: [], None, chatbot).then(
            reset_chat_and_update,
            outputs=[session_info]
        )
        
        info_btn.click(get_model_info, outputs=gr.Textbox(label="Model Info", lines=6))
        
        # Load event to refresh UI on page load/refresh
        def load_interface():
            """Load interface with current session data on page load."""
            history = get_current_history()
            sessions_list = get_session_list()
            return (
                gr.Dropdown(choices=sessions_list, value=current_session_id),
                history,
                update_session_info()
            )
        
        demo.load(
            load_interface,
            outputs=[session_dropdown, chatbot, session_info]
        )
    
    return demo


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RKLLM Gradio Server"
    )
    parser.add_argument(
        "--rkllm_model_path",
        type=str,
        required=True,
        help="Path to RKLLM model file"
    )
    parser.add_argument(
        "--target_platform",
        type=str,
        required=True,
        choices=["rk3588", "rk3576", "rk3562", "rv1126b"],
        help="Target platform"
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="qwen",
        help="Model name (default: qwen)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Server port (default: 7860)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Server host (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--lora_model_path",
        type=str,
        default=None,
        help="Path to LoRA model (optional)"
    )
    parser.add_argument(
        "--prompt_cache_path",
        type=str,
        default=None,
        help="Path to prompt cache file (optional)"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 RKLLM Gradio Server Starting")
    print("="*60)
    
    # Initialize model
    if not initialize_model(
        args.rkllm_model_path,
        args.target_platform,
        args.model_name
    ):
        print("❌ Failed to initialize model")
        sys.exit(1)
    
    # Create Gradio interface
    print(f"📱 Creating Gradio interface...")
    demo = create_gradio_interface()
    
    # Launch server
    print(f"🌐 Launching server on {args.host}:{args.port}")
    print("📖 Access interface at: http://localhost:7860")
    print("="*60)
    
    try:
        demo.launch(
            server_name=args.host,
            server_port=args.port,
            share=False,
            show_error=True
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down server...")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
