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
import uuid
from typing import List, Tuple, Optional, Any, Dict
from datetime import datetime
from rkllm import RKLLM
import rkllm as rkllm_module
from model_manager import ModelManager, ModelPuller, ModelResourceManager
from model_api import ModelAPI
from chat_database import ChatDatabase, init_chat_database, get_chat_database
from web_search import get_web_searcher, search_web, get_search_context
from thinking_engine import get_thinking_engine, inject_thinking, parse_thinking_response, format_thinking_display

# Global variables
rkllm_model = None
model_name = None
target_platform = None
lock = threading.Lock()
model_manager: Optional[ModelManager] = None
resource_manager: Optional[ModelResourceManager] = None
model_api: Optional[ModelAPI] = None

# Session management with database
sessions: Dict[str, List[Dict]] = {}
current_session_id = None
current_chat_id = None
current_chat_title = None
chat_db: Optional[ChatDatabase] = None
title_updated_for_chat = {}

# Configuration
MAX_HISTORY_MESSAGES = 20  # Keep last N messages before summarizing
MAX_CONTEXT_LENGTH = 4000  # Max tokens for context to model


def initialize_model(model_path: str, platform: str, model_id: str = "qwen") -> bool:
    """Initialize the RKLLM model from model path."""
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


def initialize_model_manager(model_folder: str, platform: str) -> bool:
    """Initialize model manager from folder."""
    global model_manager, resource_manager, model_api, rkllm_model, model_name, target_platform
    
    try:
        print(f"🔧 Initializing Model Manager from {model_folder}...")
        
        model_manager = ModelManager(model_folder, platform)
        resource_manager = ModelResourceManager()
        model_api = ModelAPI(model_folder, platform)
        
        target_platform = platform
        
        # Discover available models
        models = model_manager.discover_models()
        
        if not models:
            print("❌ No models found in model folder")
            return False
        
        # Load first available model
        first_model = list(models.keys())[0]
        first_model_path = models[first_model]
        
        print(f"📦 Loading first available model: {first_model}")
        
        if initialize_model(first_model_path, platform, first_model):
            model_manager.set_current_model(first_model)
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Failed to initialize model manager: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def switch_to_model(model_name_to_load: str) -> Tuple[bool, str]:
    """Switch to a different model"""
    global rkllm_model, model_name, target_platform, resource_manager
    
    if not model_manager:
        return False, "❌ Model manager not initialized"
    
    try:
        model_path = model_manager.get_model_path(model_name_to_load)
        if not model_path:
            return False, f"❌ Model not found: {model_name_to_load}"
        
        print(f"🔄 Switching to model: {model_name_to_load}")
        
        # Cleanup old model
        with lock:
            if resource_manager:
                old_model = rkllm_model
                
                # Create new model
                rkllm_model = RKLLM(model_path=model_path)
                model_name = model_name_to_load
                
                # Cleanup old model
                if old_model:
                    try:
                        if hasattr(old_model, 'release'):
                            old_model.release()
                        if hasattr(old_model, 'destroy'):
                            old_model.destroy()
                    except:
                        pass
                
                print(f"✅ Switched to model: {model_name_to_load}")
                model_manager.set_current_model(model_name_to_load)
                return True, f"✅ Switched to model: {model_name_to_load}"
        
        return False, "❌ Failed to switch model"
        
    except Exception as e:
        print(f"❌ Error switching model: {str(e)}")
        return False, f"❌ Error: {str(e)}"


def pull_model_from_hf(hf_url: str, model_name: Optional[str] = None) -> Tuple[bool, str]:
    """Pull a model from HuggingFace"""
    if not model_api:
        return False, "❌ Model API not initialized"
    
    try:
        print(f"📥 Pulling model from: {hf_url}")
        result = model_api.pull_model(hf_url, model_name)
        
        if result.get("success"):
            return True, result.get("message", "✅ Model pulled successfully")
        else:
            return False, result.get("message", "❌ Failed to pull model")
    
    except Exception as e:
        return False, f"❌ Error pulling model: {str(e)}"


def create_new_session() -> str:
    """Create a new chat session in database."""
    global current_session_id, current_chat_id, current_chat_title, chat_db, sessions
    
    if chat_db is None:
        chat_db = get_chat_database()
    
    chat_id = str(uuid.uuid4())[:8]
    current_chat_id = chat_id
    current_session_id = chat_id
    
    chat_db.create_chat(chat_id, model_name or "RKLLM", target_platform)
    sessions[chat_id] = []
    current_chat_title = chat_db._generate_title_from_model(model_name or "RKLLM")
    # Don't initialize in dict - let it be checked on first message
    
    return chat_id


def get_session_list() -> List[str]:
    """Get list of all chat IDs from database."""
    global chat_db
    if chat_db is None:
        chat_db = get_chat_database()
    
    chats = chat_db.get_all_chats()
    return [chat['id'] for chat in chats] if chats else []


def switch_session(session_id: str) -> Tuple[List[Dict], str]:
    """Switch to a different session from database."""
    global current_session_id, current_chat_id, current_chat_title, chat_db, sessions
    
    if chat_db is None:
        chat_db = get_chat_database()
    
    if not chat_db.chat_exists(session_id):
        return [], current_session_id
    
    current_session_id = session_id
    current_chat_id = session_id
    
    # Load from database
    messages = chat_db.get_chat_messages(session_id)
    chat_info = chat_db.get_chat(session_id)
    current_chat_title = chat_info['title'] if chat_info else session_id
    
    # Convert to Gradio format
    chat_history = []
    for msg in messages:
        chat_history.append({
            "role": msg['role'],
            "content": msg['content']
        })
    
    sessions[session_id] = chat_history
    return chat_history, session_id


def delete_session(session_id: str) -> str:
    """Delete a session from database."""
    global current_session_id, current_chat_id, chat_db, sessions
    
    if chat_db is None:
        chat_db = get_chat_database()
    
    # Delete from database
    if chat_db.delete_chat(session_id):
        # Remove from cache
        if session_id in sessions:
            del sessions[session_id]
        
        # If deleting current session, switch to another or create new
        if current_session_id == session_id:
            remaining_chats = get_session_list()
            if remaining_chats:
                new_session_id = remaining_chats[0]
                switch_session(new_session_id)
            else:
                # No chats left, create new one
                new_session_id = create_new_session()
                current_session_id = new_session_id
        
        return f"✅ Chat deleted"
    return "❌ Cannot delete chat"


def get_current_history() -> List[Dict]:
    """Get current session history."""
    if current_session_id is None:
        return []
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


def generate_title_with_model(user_message: str) -> str:
    """Use the model to generate a concise title/summary from user message."""
    global rkllm_model, lock
    
    if rkllm_model is None or not user_message:
        # Fallback to simple extraction if model not available
        return ChatDatabase.generate_title_from_message(user_message, model_name or "RKLLM")
    
    try:
        with lock:
            # Create a prompt for title generation
            title_prompt = f"""Summarize the following user query in a short title (max 7 words). 
Respond with ONLY the title, no explanation.

User query: {user_message}

Title:"""
            
            # Reset global state
            rkllm_module.global_text = []
            rkllm_module.global_state = -1
            
            # Run model inference
            model_thread = threading.Thread(
                target=rkllm_model.run,
                args=('user', False, title_prompt)
            )
            model_thread.start()
            
            # Collect output with timeout
            title_output = ""
            timeout = 10  # 10 second timeout
            start_time = time.time()
            
            while model_thread.is_alive() and (time.time() - start_time) < timeout:
                while len(rkllm_module.global_text) > 0:
                    title_output += rkllm_module.global_text.pop(0)
                time.sleep(0.01)
            
            model_thread.join(timeout=2)
            
            # Extract and clean the title
            if title_output.strip():
                title = ChatDatabase.extract_summary_from_model_response(title_output.strip())
                if title:
                    print(f"✅ Model-generated title: '{title}'")
                    return title
        
    except Exception as e:
        print(f"⚠️ Error generating title with model: {str(e)}")
    
    # Fallback to simple extraction
    return ChatDatabase.generate_title_from_message(user_message, model_name or "RKLLM")


def add_message_to_session(role: str, content: str) -> None:
    """Add a message to current session history and save to database."""
    global sessions, current_session_id, current_chat_id, chat_db, current_chat_title, title_updated_for_chat
    
    if chat_db is None:
        chat_db = get_chat_database()
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    
    sessions[current_session_id].append(message)
    
    # Save to database
    if current_chat_id:
        chat_db.add_message(current_chat_id, role, content)
        
        # Update chat title from first user message using MODEL-BASED SUMMARIZATION
        if role == "user" and current_chat_id not in title_updated_for_chat:
            # Get fresh chat info from database
            chat_info = chat_db.get_chat(current_chat_id)
            
            if chat_info:
                # Use model to generate concise title from user message
                new_title = generate_title_with_model(content)
                
                if new_title:
                    # Always update if it's not the auto-generated model title
                    current_auto_title = chat_db._generate_title_from_model(model_name or "RKLLM")
                    if new_title != current_auto_title:
                        # Update database with new title
                        chat_db.update_chat_title(current_chat_id, new_title)
                        # Update global variable
                        current_chat_title = new_title
                        print(f"✅ Chat title updated from '{current_auto_title}' to: '{new_title}'")
                    
                    # Mark as updated
                    title_updated_for_chat[current_chat_id] = True
    
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


def get_chat_display_list() -> List[str]:
    """Get list of chat IDs with their titles for display."""
    global chat_db
    if chat_db is None:
        chat_db = get_chat_database()
    
    chats = chat_db.get_all_chats()
    return [chat['id'] for chat in chats] if chats else []


def get_chat_id_by_title_index(index: int) -> Optional[str]:
    """Get chat ID by its index in the list."""
    chat_list = get_chat_display_list()
    if 0 <= index < len(chat_list):
        return chat_list[index]
    return None


def search_chats_by_title(query: str) -> List[str]:
    """Search chats by title or model."""
    global chat_db
    if chat_db is None:
        chat_db = get_chat_database()
    
    if not query:
        return get_chat_display_list()
    
    results = chat_db.search_chats(query)
    return [chat['id'] for chat in results] if results else []


def get_chat_titles_dict() -> Dict[str, str]:
    """Get dictionary of chat IDs to their titles."""
    global chat_db
    if chat_db is None:
        chat_db = get_chat_database()
    
    chats = chat_db.get_all_chats()
    return {chat['id']: chat['title'] for chat in chats} if chats else {}


def create_gradio_interface():
    """Create the enhanced Gradio interface with 3-panel layout."""
    model_display = model_name or "RKLLM"
    platform_display = target_platform or "RK"
    
    with gr.Blocks(title=f"RKLLM Chat - {model_display}", theme=gr.themes.Soft(), css="""
    .session-item { padding: 8px; margin: 4px 0; border-radius: 4px; cursor: pointer; }
    .session-item:hover { background: rgba(0,0,0,0.05); }
    .sidebar { display: flex; flex-direction: column; gap: 10px; }
    .left-sidebar { border-right: 1px solid #e0e0e0; padding-right: 10px; }
    .right-sidebar { border-left: 1px solid #e0e0e0; padding-left: 10px; }
    """) as demo:
        
        # Main header
        gr.Markdown(f"""
        # 🤖 RKLLM Advanced Chat
        **{model_display.upper()}** • {platform_display.upper()}
        """)
        
        # Main layout: Left | Middle | Right
        with gr.Row(equal_height=False):
            # ==================== LEFT SIDEBAR: SESSIONS ====================
            with gr.Column(scale=1, elem_classes="left-sidebar"):
                gr.Markdown("### � Chats")
                
                # Search box
                chat_search = gr.Textbox(
                    label="🔍 Search Chats",
                    placeholder="Search by title or model...",
                    interactive=True,
                    lines=1
                )
                
                # Initialize with chats from database
                initial_chats = get_chat_display_list()
                chat_titles = get_chat_titles_dict()
                display_choices = [f"{cid[:4]}... - {chat_titles.get(cid, 'Chat')}" for cid in initial_chats]
                
                # Session dropdown
                session_dropdown = gr.Dropdown(
                    label="Current Chat",
                    choices=display_choices if display_choices else ["New Chat"],
                    value=display_choices[0] if display_choices else "New Chat",
                    interactive=True
                )
                
                # Hidden component to store actual chat IDs
                hidden_chat_ids = gr.State(value=initial_chats)
                
                # Session management buttons
                with gr.Row():
                    new_session_btn = gr.Button("➕ New", scale=1, size="sm")
                    delete_session_btn = gr.Button("🗑️ Delete", scale=1, size="sm")
                
                # Session info
                session_info = gr.Textbox(
                    label="Chat Info",
                    value="New chat - Ready to start",
                    interactive=False,
                    lines=2
                )
                
                # Divider
                gr.Markdown("---")
                
                # Session list (scrollable)
                gr.Markdown("**Chat History**")
                sessions_list = gr.Textbox(
                    label="Recent Chats",
                    value="\n".join(display_choices) if display_choices else "No chats yet",
                    interactive=False,
                    lines=8
                )
            
            # ==================== MIDDLE: MAIN CHAT ====================
            with gr.Column(scale=3):
                gr.Markdown("### 💬 Conversation")
                
                # Chat display (larger)
                chatbot = gr.Chatbot(
                    label="",
                    height=600,
                    value=sessions.get(current_session_id, []),
                    show_label=False
                )
                
                # Message input area
                with gr.Row():
                    msg = gr.Textbox(
                        label="Message",
                        placeholder="Type your message here...",
                        lines=3,
                        scale=4,
                        show_label=False
                    )
                    with gr.Column(scale=1):
                        submit_btn = gr.Button("📤 Send", scale=1, size="lg")
            
            # ==================== RIGHT SIDEBAR: SETTINGS ====================
            with gr.Column(scale=1, elem_classes="right-sidebar"):
                gr.Markdown("### ⚙️ Settings")
                
                # Model settings
                stream_toggle = gr.Checkbox(
                    label="🌊 Streaming",
                    value=True
                )
                
                context_toggle = gr.Checkbox(
                    label="🧠 Use Context",
                    value=True
                )
                
                # Web Search and Thinking toggles
                search_toggle = gr.Checkbox(
                    label="🔍 Web Search",
                    value=False,
                    info="Augment responses with web search results"
                )
                
                thinking_toggle = gr.Checkbox(
                    label="💭 Thinking Mode",
                    value=False,
                    info="Show model reasoning steps"
                )
                
                # Divider
                gr.Markdown("---")
                
                # Model Selector
                gr.Markdown("**🔄 Model Selection**")
                available_models = []
                if model_manager:
                    models = model_manager.get_available_models()
                    available_models = list(models.keys()) if models else []
                
                model_selector = gr.Dropdown(
                    label="Switch Model",
                    choices=available_models,
                    value=model_name if model_name in available_models else (available_models[0] if available_models else ""),
                    interactive=True
                )
                
                switch_model_btn = gr.Button("🔀 Load Model", scale=1, variant="primary")
                
                # Divider
                gr.Markdown("---")
                
                # Model information
                gr.Markdown("**Model Info**")
                model_info_btn = gr.Button("ℹ️ Show Details", scale=1)
                model_info_display = gr.Textbox(
                    label="",
                    value=f"Model: {model_name}\nPlatform: {target_platform}",
                    interactive=False,
                    lines=6,
                    show_label=False
                )
                
                # Divider
                gr.Markdown("---")
                
                # Actions
                gr.Markdown("**Actions**")
                clear_btn = gr.Button("🧹 Clear Chat", scale=1, variant="secondary")
                
                # Divider
                gr.Markdown("---")
                
                # Status
                gr.Markdown("**Status**")
                status_text = gr.Textbox(
                    label="",
                    value="Ready",
                    interactive=False,
                    lines=2,
                    show_label=False
                )

        
        # ==================== EVENT HANDLERS ====================
        
        def update_session_info():
            """Update session information display with title."""
            global current_chat_title
            history = get_current_history()
            timestamp = datetime.now().strftime("%H:%M:%S")
            msg_count = len(history)
            title_display = current_chat_title or "New Chat"
            return f"📌 {title_display}\nMessages: {msg_count}\nLast: {timestamp}"
        
        def update_session_list_display():
            """Generate formatted list of all chats with titles."""
            chat_ids = get_chat_display_list()
            chat_titles = get_chat_titles_dict()
            
            if not chat_ids:
                return "No chats yet"
            
            list_text = "\n".join([
                f"• {chat_titles.get(cid, 'Chat')}" for cid in chat_ids[:10]
            ])
            return list_text
        
        def get_dropdown_choices():
            """Get formatted dropdown choices with IDs and titles."""
            chat_ids = get_chat_display_list()
            chat_titles = get_chat_titles_dict()
            return [f"{cid[:4]}... - {chat_titles.get(cid, 'Chat')}" for cid in chat_ids]
        
        def on_new_session():
            """Create a new session and update all UI elements."""
            session_id = create_new_session()
            choices = get_dropdown_choices()
            display_value = choices[0] if choices else "New Chat"
            
            return (
                gr.Dropdown(choices=choices, value=display_value),
                [],
                update_session_info(),
                update_session_list_display(),
                f"✅ New chat created",
                get_chat_display_list()
            )
        
        def on_search_chats(query: str):
            """Search chats by title or model."""
            if not query:
                chat_ids = get_chat_display_list()
            else:
                chat_ids = search_chats_by_title(query)
            
            chat_titles = get_chat_titles_dict()
            choices = [f"{cid[:4]}... - {chat_titles.get(cid, 'Chat')}" for cid in chat_ids]
            
            return gr.Dropdown(choices=choices if choices else ["No matches"], value=choices[0] if choices else "No matches")
        
        def on_switch_session_by_display(display_text):
            """Convert display text back to chat ID and switch."""
            if not display_text or display_text == "New Chat":
                return [], update_session_info(), update_session_list_display()
            
            # Extract chat ID from display text (format: "xxxx... - Title")
            try:
                chat_id_prefix = display_text.split(' - ')[0].replace('...', '').strip()
                # Find full chat ID
                all_chats = get_chat_display_list()
                full_chat_id = next((cid for cid in all_chats if cid.startswith(chat_id_prefix)), None)
                
                if full_chat_id:
                    history, _ = switch_session(full_chat_id)
                    return (
                        history,
                        update_session_info(),
                        update_session_list_display()
                    )
            except:
                pass
            
            return [], update_session_info(), update_session_list_display()
        
        def on_delete_session_by_display(display_text):
            """Delete chat by display text."""
            if not display_text or display_text == "New Chat":
                return gr.Dropdown(choices=get_dropdown_choices(), value="New Chat"), [], update_session_info(), update_session_list_display(), "❌ No chat selected"
            
            try:
                chat_id_prefix = display_text.split(' - ')[0].replace('...', '').strip()
                all_chats = get_chat_display_list()
                full_chat_id = next((cid for cid in all_chats if cid.startswith(chat_id_prefix)), None)
                
                if full_chat_id:
                    msg_result = delete_session(full_chat_id)
                    choices = get_dropdown_choices()
                    new_value = choices[0] if choices else "New Chat"
                    
                    return (
                        gr.Dropdown(choices=choices, value=new_value),
                        [],
                        update_session_info(),
                        update_session_list_display(),
                        msg_result
                    )
            except:
                pass
            
            choices = get_dropdown_choices()
            return (
                gr.Dropdown(choices=choices, value=choices[0] if choices else "New Chat"),
                [],
                update_session_info(),
                update_session_list_display(),
                "❌ Error deleting chat"
            )
        
        def format_response_with_search_and_thinking(response: str, search_results: Optional[List[Dict]] = None, use_thinking: bool = False) -> str:
            """Format response with search results and thinking display."""
            formatted = response
            
            # Add thinking display if enabled and model provided reasoning
            if use_thinking:
                try:
                    parsed = parse_thinking_response(response)
                    if parsed.get('thinking'):
                        thinking_display = format_thinking_display(parsed['thinking'])
                        if thinking_display:
                            formatted = thinking_display + "\n\n" + (parsed.get('answer', response) or response)
                except:
                    pass  # If parsing fails, just return original response
            
            # Add search results at the end if available
            if search_results:
                search_section = "\n\n📚 **Sources:**\n"
                for i, result in enumerate(search_results[:3], 1):
                    title = result.get('title', 'Source')
                    url = result.get('url', '#')
                    search_section += f"{i}. [{title}]({url})\n"
                formatted = formatted + search_section
            
            return formatted
        
        def respond(message: str, chat_history, use_streaming: bool = True, use_context: bool = True, use_search: bool = False, use_thinking: bool = False):
            """Enhanced response handler with context, web search, and thinking modes."""
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
            
            # Prepare message with web search and thinking
            augmented_message = message
            search_results = []
            
            # Perform web search if enabled
            print(use_search)
            if use_search:
                try:
                    search_results = search_web(message, max_results=3)
                    if search_results:
                        search_context = get_search_context(message, max_results=3)
                        augmented_message = search_context + augmented_message
                        print(f"🔍 Web search found {len(search_results)} results")
                except Exception as e:
                    print(f"⚠️  Web search error: {str(e)}")
            
            # Inject thinking prompt if enabled
            if use_thinking:
                try:
                    augmented_message = inject_thinking(augmented_message, pattern="chain_of_thought")
                    print(f"💭 Thinking mode enabled")
                except Exception as e:
                    print(f"⚠️  Thinking injection error: {str(e)}")
            
            # Generate bot response
            try:
                if use_streaming:
                    # Streaming mode with context - use generator
                    response_text = ""
                    updated_history = chat_history  # Initialize to avoid unbound variable
                    for partial_response in generate_response_streaming(
                        augmented_message,
                        history=session_history if use_context else None
                    ):
                        response_text = partial_response
                        # Format response with search results and thinking display
                        formatted_response = format_response_with_search_and_thinking(
                            response_text,
                            search_results if search_results else None,
                            use_thinking
                        )
                        updated_history = chat_history[:-1] + [{
                            "role": "assistant",
                            "content": formatted_response
                        }]
                        yield updated_history
                    
                    chat_history = updated_history
                    add_message_to_session("assistant", response_text)
                    yield chat_history
                else:
                    # Non-streaming mode - return result
                    response = generate_response(
                        augmented_message,
                        history=session_history if use_context else None,
                        stream=False
                    )
                    # Format response with search results and thinking display
                    formatted_response = format_response_with_search_and_thinking(
                        response,
                        search_results if search_results else None,
                        use_thinking
                    )
                    chat_history = chat_history + [{
                        "role": "assistant",
                        "content": formatted_response
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
        
        def get_model_info_detailed():
            """Get detailed model information."""
            return f"""**RKLLM Model Information**
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📛 Name: {model_name}
🏗️ Platform: {target_platform}
⚙️ Status: ✅ Running
📊 Sessions: {len(sessions)}
💾 Context: {MAX_CONTEXT_LENGTH} chars
📝 Max History: {MAX_HISTORY_MESSAGES}
🌐 Interface: Gradio v4
"""
        
        def clear_input_and_update():
            """Clear input box and update session info and dropdown."""
            # Get updated dropdown choices (in case title changed from auto-titling)
            choices = get_dropdown_choices()
            # Use current_session_id to find the display value
            display_value = None
            if current_session_id:
                # Find the display label for current session
                chat_info = chat_db.get_chat(current_session_id)
                if chat_info:
                    display_value = f"📝 {chat_info['title'][:50]}"
            # Fallback to first choice if not found
            if not display_value or display_value not in choices:
                display_value = choices[0] if choices else "New Chat"
            return "", update_session_info(), gr.Dropdown(choices=choices, value=display_value)
        
        def reset_chat_and_update():
            """Reset chat and update info."""
            return update_session_info()
        
        def sync_chatbot_with_session():
            """Sync chatbot with current session storage - ensures display matches backend."""
            return get_current_history()
        
        # Event handlers for session management
        new_session_btn.click(
            on_new_session,
            outputs=[session_dropdown, chatbot, session_info, sessions_list, status_text, hidden_chat_ids]
        )
        
        chat_search.change(
            on_search_chats,
            inputs=[chat_search],
            outputs=[session_dropdown]
        )
        
        session_dropdown.change(
            on_switch_session_by_display,
            inputs=[session_dropdown],
            outputs=[chatbot, session_info, sessions_list]
        )
        
        delete_session_btn.click(
            on_delete_session_by_display,
            inputs=[session_dropdown],
            outputs=[session_dropdown, chatbot, session_info, sessions_list, status_text]
        )
        
        # Event handlers for messaging
        msg.submit(
            respond,
            [msg, chatbot, stream_toggle, context_toggle, search_toggle, thinking_toggle],
            chatbot
        ).then(
            clear_input_and_update,
            outputs=[msg, session_info, session_dropdown]
        ).then(
            sync_chatbot_with_session,
            outputs=[chatbot]
        )
        
        submit_btn.click(
            respond,
            [msg, chatbot, stream_toggle, context_toggle, search_toggle, thinking_toggle],
            chatbot
        ).then(
            clear_input_and_update,
            outputs=[msg, session_info, session_dropdown]
        ).then(
            sync_chatbot_with_session,
            outputs=[chatbot]
        )
        
        def on_switch_model(selected_model):
            """Switch to selected model."""
            global rkllm_model, model_name, lock
            
            if not selected_model or not model_manager:
                return "❌ No model selected", get_model_info_detailed()
            
            try:
                print(f"🔄 Switching to model: {selected_model}")
                
                # Get model path
                model_path = model_manager.get_model_path(selected_model)
                if not model_path:
                    return f"❌ Model path not found: {selected_model}", get_model_info_detailed()
                
                # Thread-safe model switch with lock
                with lock:
                    # Release old model
                    if rkllm_model:
                        try:
                            if hasattr(rkllm_model, 'release'):
                                rkllm_model.release()
                            print("✅ Old model resources released")
                        except Exception as e:
                            print(f"⚠️ Warning releasing old model: {str(e)}")
                    
                    # Load new model
                    if initialize_model(model_path, target_platform, selected_model):
                        print(f"✅ Successfully switched to: {selected_model}")
                        return f"✅ Switched to: {selected_model}", get_model_info_detailed()
                    else:
                        return f"❌ Failed to load model: {selected_model}", get_model_info_detailed()
                        
            except Exception as e:
                error_msg = f"❌ Error switching model: {str(e)}"
                print(error_msg)
                return error_msg, get_model_info_detailed()
        
        def refresh_model_selector():
            """Refresh available models in selector."""
            available_models = []
            if model_manager:
                models = model_manager.get_available_models()
                available_models = list(models.keys()) if models else []
            return gr.Dropdown(choices=available_models)
        
        # Event handlers for model switching
        switch_model_btn.click(
            on_switch_model,
            inputs=[model_selector],
            outputs=[status_text, model_info_display]
        )
        
        # Event handler for actions
        clear_btn.click(
            lambda: [],
            None,
            chatbot
        ).then(
            reset_chat_and_update,
            outputs=[session_info]
        )
        
        model_info_btn.click(
            get_model_info_detailed,
            outputs=[model_info_display]
        )
        
        # Load event to refresh UI on page load/refresh
        def load_interface():
            """Load interface with current session data on page load."""
            global current_session_id, current_chat_id, current_chat_title
            
            # Ensure database is initialized
            chat_ids = get_chat_display_list()
            
            # If no chats exist, create one
            if not chat_ids:
                current_session_id = create_new_session()
                current_chat_id = current_session_id
                chat_ids = [current_session_id]
            elif current_session_id is None:
                current_session_id = chat_ids[0]
                current_chat_id = current_session_id
                switch_session(current_session_id)
            
            choices = get_dropdown_choices()
            display_value = choices[0] if choices else "New Chat"
            history = get_current_history()
            
            return (
                gr.Dropdown(choices=choices, value=display_value),
                history,
                update_session_info(),
                update_session_list_display()
            )
        
        demo.load(
            load_interface,
            outputs=[session_dropdown, chatbot, session_info, sessions_list]
        )
    
    return demo


def main():
    """Main entry point."""
    global chat_db
    
    parser = argparse.ArgumentParser(
        description="RKLLM Gradio Server with Model Management"
    )
    
    # Model folder or single model path
    parser.add_argument(
        "--model_folder",
        type=str,
        default=None,
        help="Path to folder containing models (recommended)"
    )
    parser.add_argument(
        "--rkllm_model_path",
        type=str,
        default=None,
        help="Path to single RKLLM model file (deprecated, use --model_folder)"
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
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 RKLLM Gradio Server Starting")
    print("="*60)
    
    # Initialize chat database
    print("💾 Initializing chat database...")
    chat_db = init_chat_database()
    print("✅ Chat database initialized")
    
    # Initialize model manager if folder provided
    if args.model_folder:
        print(f"📁 Using model folder: {args.model_folder}")
        if not initialize_model_manager(args.model_folder, args.target_platform):
            print("❌ Failed to initialize model manager")
            sys.exit(1)
    elif args.rkllm_model_path:
        print(f"⚠️  Using deprecated single model path. Consider using --model_folder")
        if not initialize_model(
            args.rkllm_model_path,
            args.target_platform,
            args.model_name
        ):
            print("❌ Failed to initialize model")
            sys.exit(1)
    else:
        print("❌ Either --model_folder or --rkllm_model_path must be provided")
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
