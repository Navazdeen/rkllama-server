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

import argparse
import os
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import gradio as gr
from model_api import ModelAPI
from model_manager import ModelManager, ModelResourceManager
from thinking_engine import (
    format_thinking_display,
    inject_thinking,
    parse_thinking_response,
)
from web_search import ContentExtractor, QueryOptimizer, search_web

import rkllm_server.core.rkllm as rkllm_module
from rkllm_server.core.rkllm import RKLLM
from rkllm_server.db.chat_database import (
    ChatDatabase,
    getChatDatabase,
    initChatDatabase,
)

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

# Configuration parameters for web search and thinking
search_config = {
    'n_iterations': 3,           # Default iterations
    'max_results': 3,            # Default max results per search
    'info_length_threshold': 500, # Default info threshold
}

# Thinking phase updates storage (for live updates)
thinking_updates = {
    'current': [],  # Current thinking updates
    'lock': threading.Lock()
}

def update_thinking_display(message: str):
    """Add a thinking update message for UI display."""
    with thinking_updates['lock']:
        thinking_updates['current'].append(message)

def get_thinking_updates() -> List[str]:
    """Get current thinking updates and clear them."""
    with thinking_updates['lock']:
        updates = thinking_updates['current'].copy()
        thinking_updates['current'].clear()
        return updates

# Helper function for human-readable file size formatting
def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format (B, KB, MB, GB, TB)"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f}TB"

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
        chat_db = getChatDatabase()
    
    chat_id = str(uuid.uuid4())[:8]
    current_chat_id = chat_id
    current_session_id = chat_id
    
    chat_db.createChat(chat_id, model_name or "RKLLM", target_platform)
    sessions[chat_id] = []
    current_chat_title = chat_db._generateTitleFromModel(model_name or "RKLLM")
    # Don't initialize in dict - let it be checked on first message
    
    return chat_id


def get_session_list() -> List[str]:
    """Get list of all chat IDs from database."""
    global chat_db
    if chat_db is None:
        chat_db = getChatDatabase()
    
    chats = chat_db.getAllChats()
    return [chat['id'] for chat in chats] if chats else []


def switch_session(session_id: str) -> Tuple[List[Dict], str]:
    """Switch to a different session from database."""
    global current_session_id, current_chat_id, current_chat_title, chat_db, sessions
    
    if chat_db is None:
        chat_db = getChatDatabase()
    
    if not chat_db.chatExists(session_id):
        return [], current_session_id
    
    current_session_id = session_id
    current_chat_id = session_id
    
    # Load from database
    messages = chat_db.getChatMessages(session_id)
    chat_info = chat_db.getChat(session_id)
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
        chat_db = getChatDatabase()
    
    # Delete from database
    if chat_db.deleteChat(session_id):
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
        return ChatDatabase.generateTitleFromMessage(user_message, model_name or "RKLLM")
    
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
                title = ChatDatabase.extractSummaryFromModelResponse(title_output.strip())
                if title:
                    print(f"✅ Model-generated title: '{title}'")
                    return title
        
    except Exception as e:
        print(f"⚠️ Error generating title with model: {str(e)}")
    
    # Fallback to simple extraction
    return ChatDatabase.generateTitleFromMessage(user_message, model_name or "RKLLM")


def add_message_to_session(role: str, content: str) -> None:
    """Add a message to current session history and save to database."""
    global sessions, current_session_id, current_chat_id, chat_db, current_chat_title, title_updated_for_chat
    
    if chat_db is None:
        chat_db = getChatDatabase()
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    
    sessions[current_session_id].append(message)
    
    # Save to database
    if current_chat_id:
        chat_db.addMessage(current_chat_id, role, content)
        
        # Update chat title from first user message using MODEL-BASED SUMMARIZATION
        if role == "user" and current_chat_id not in title_updated_for_chat:
            # Get fresh chat info from database
            chat_info = chat_db.getChat(current_chat_id)
            
            if chat_info:
                # Use model to generate concise title from user message
                new_title = generate_title_with_model(content)
                
                if new_title:
                    # Always update if it's not the auto-generated model title
                    current_auto_title = chat_db._generateTitleFromModel(model_name or "RKLLM")
                    if new_title != current_auto_title:
                        # Update database with new title
                        chat_db.updateChatTitle(current_chat_id, new_title)
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
        chat_db = getChatDatabase()
    
    chats = chat_db.getAllChats()
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
        chat_db = getChatDatabase()
    
    if not query:
        return get_chat_display_list()
    
    results = chat_db.searchChats(query)
    return [chat['id'] for chat in results] if results else []


def get_chat_titles_dict() -> Dict[str, str]:
    """Get dictionary of chat IDs to their titles."""
    global chat_db
    if chat_db is None:
        chat_db = getChatDatabase()
    
    chats = chat_db.getAllChats()
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
    .right-sidebar { 
        border-left: 1px solid #e0e0e0; 
        padding-left: 10px;
        max-height: 100vh;
        overflow-y: auto;
        overflow-x: hidden;
    }
    .right-sidebar::-webkit-scrollbar {
        width: 8px;
    }
    .right-sidebar::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    .right-sidebar::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 10px;
    }
    .right-sidebar::-webkit-scrollbar-thumb:hover {
        background: #a1a1a1;
    }
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
                    height=500,
                    value=sessions.get(current_session_id, []),
                    show_label=False
                )
                
                # Live thinking updates display - ALWAYS visible for live updates
                thinking_display = gr.Markdown(
                    value="",
                    label="🧠 Live Thinking Updates",
                    visible=True,
                    elem_classes="thinking-display-box"
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
                
                # Web Search & Thinking Configuration
                gr.Markdown("**🎛️ Configuration**")
                
                with gr.Group():
                    n_iterations = gr.Slider(
                        label="Max Iterations",
                        minimum=1,
                        maximum=5,
                        value=search_config['n_iterations'],
                        step=1,
                        info="Max loop iterations for gathering info"
                    )
                    
                    max_results = gr.Slider(
                        label="Max Results",
                        minimum=1,
                        maximum=10,
                        value=search_config['max_results'],
                        step=1,
                        info="Search results per query"
                    )
                    
                    info_threshold = gr.Slider(
                        label="Info Length",
                        minimum=100,
                        maximum=2000,
                        value=search_config['info_length_threshold'],
                        step=100,
                        info="Min chars for completeness"
                    )
                
                # Apply config button
                apply_config_btn = gr.Button("💾 Save Config", scale=1, size="sm", variant="secondary")
                
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
                
                # HuggingFace Model Pull
                gr.Markdown("**📥 Pull from HF**")
                
                hf_url_input = gr.Textbox(
                    label="HF Repo URL",
                    placeholder="owner/repo or https://huggingface.co/owner/repo",
                    lines=1,
                    interactive=True
                )
                
                with gr.Row():
                    hf_model_name = gr.Textbox(
                        label="Model Name",
                        placeholder="Optional custom name",
                        lines=1,
                        scale=2,
                        interactive=True
                    )
                    hf_pull_btn = gr.Button("🔽 Pull", scale=1, variant="primary", size="sm")
                
                # Progress bar
                hf_progress = gr.Slider(0, 100, label="Download Progress", value=None)
                
                # Status display with size info
                hf_status = gr.Textbox(
                    label="Status",
                    value="Ready",
                    interactive=False,
                    lines=3,
                    show_label=False
                )
                
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
            create_new_session()
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
            """Enhanced response handler with context, web search, thinking modes, and loop-based gathering."""
            if not message.strip():
                yield chat_history, ""
                return
            
            # Get current session history
            session_history = get_current_history()
            
            # Add user message to both display and session
            if not chat_history:
                chat_history = []
            
            # BUG FIX: Append user message properly instead of replacing
            user_msg = {
                "role": "user",
                "content": message
            }
            chat_history = chat_history + [user_msg]
            
            add_message_to_session("user", message)
            
            # Clear thinking updates from previous responses
            with thinking_updates['lock']:
                thinking_updates['current'].clear()
            
            # Yield updated history with user message and initial thinking display
            thinking_display_text = "🤔 Starting processing...\n"
            yield chat_history, thinking_display_text
            
            # Prepare message with web search and thinking
            augmented_message = message
            search_results = []
            loop_thinking_results = None
            
            # Enhanced Web Search with Loop Thinking - USE CONFIGURED PARAMETERS
            if use_search or use_thinking:
                try:
                    # Step 1: Optimize search query
                    optimized_query = QueryOptimizer.optimize_query(message)
                    print(f"🔍 Original: '{message}'")
                    print(f"🔍 Optimized: '{optimized_query}'")
                    
                    # Step 2: Perform loop-based gathering if thinking enabled
                    if use_thinking:
                        print(f"💭 Starting loop-based gathering...")
                        print(f"   Config: iterations={search_config['n_iterations']}, max_results={search_config['max_results']}, threshold={search_config['info_length_threshold']}")
                        
                        # Update thinking display with configuration
                        update_thinking_display(f"🔄 Starting information gathering...\n⚙️ Config: {search_config['n_iterations']} iterations, {search_config['max_results']} results/iter, {search_config['info_length_threshold']} char threshold\n")
                        
                        # Yield thinking updates during search phase - FIX for live updates
                        thinking_display_text = "".join(get_thinking_updates())
                        yield chat_history, thinking_display_text
                        
                        # Import LoopThinkingEngine to create with configured parameters
                        from thinking_engine import LoopThinkingEngine

                        # Define search function for loop with CONFIGURED max_results
                        def loop_search(query: str, max_results: int = None):
                            if max_results is None:
                                max_results = search_config['max_results']
                            update_thinking_display(f"🌐 Searching: '{query}' (max {max_results} results)\n")
                            results = search_web(query, max_results=max_results)
                            # Enhance with content extraction
                            extracted = ContentExtractor.extract_from_results(results)
                            update_thinking_display(f"✅ Found {len(extracted)} results, extracting content...\n")
                            return extracted
                        
                        # Create loop engine with CONFIGURED parameters (THIS WAS THE BUG)
                        loop_engine = LoopThinkingEngine(
                            max_iterations=search_config['n_iterations'],
                            info_threshold=search_config['info_length_threshold']
                        )
                        
                        loop_thinking_results = loop_engine.gather_information_loop(
                            query=optimized_query,
                            search_func=loop_search
                        )
                        
                        # Yield thinking updates after search - FIX for live updates
                        thinking_display_text = "".join(get_thinking_updates())
                        yield chat_history, thinking_display_text
                        
                        # Use gathered info as augmented message
                        if loop_thinking_results['gathered_info']:
                            update_thinking_display(f"✅ Information gathering complete in {loop_thinking_results['iterations']} iterations\n")
                            search_context = f"📚 **Gathered Information** ({loop_thinking_results['iterations']} iterations):\n"
                            search_context += loop_thinking_results['gathered_info']
                            augmented_message = search_context + "\n\n" + message
                            search_results = []  # Results embedded in augmented message
                            
                            # Yield final thinking updates - FIX for live updates
                            thinking_display_text = "".join(get_thinking_updates())
                            yield chat_history, thinking_display_text
                            
                            print(f"✅ Gathered info in {loop_thinking_results['iterations']} iterations")
                    
                    # Step 3: Regular search if not using loop thinking
                    elif use_search:
                        print(f"   Config: max_results={search_config['max_results']}")
                        update_thinking_display(f"🌐 Searching: '{optimized_query}' (max {search_config['max_results']} results)\n")
                        search_results = search_web(optimized_query, max_results=search_config['max_results'])
                        if search_results:
                            # Enhance results with content extraction
                            search_results = ContentExtractor.extract_from_results(search_results)
                            search_context = f"🔍 **Web Search Results** ({len(search_results)} found):\n"
                            for i, result in enumerate(search_results, 1):
                                content = result.get('full_content') or result.get('snippet', '')
                                search_context += f"\n{i}. [{result.get('title', 'Source')}]({result.get('url', '#')})\n   {content[:200]}..."
                            update_thinking_display(f"✅ Web search complete: {len(search_results)} results found\n")
                            augmented_message = search_context + "\n\n" + message
                            
                            # Yield thinking updates during web search - FIX for live updates
                            thinking_display_text = "".join(get_thinking_updates())
                            yield chat_history, thinking_display_text
                            
                            print(f"🔍 Web search found {len(search_results)} results with content")

                
                except Exception as e:
                    print(f"⚠️  Search/thinking error: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # Inject thinking prompt if enabled (and not already using loop thinking)
            if use_thinking and not loop_thinking_results:
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
                    # BUG FIX: Properly append assistant message instead of replacing
                    for partial_response in generate_response_streaming(
                        augmented_message,
                        history=session_history if use_context else None
                    ):
                        response_text = partial_response
                        
                        # Get latest thinking updates
                        latest_thinking_updates = get_thinking_updates()
                        thinking_display_text = "".join(latest_thinking_updates)
                        
                        # Format response with thinking steps if available
                        formatted_response = response_text
                        if loop_thinking_results:
                            thinking_steps = "\n".join([f"  • {s}" for s in loop_thinking_results['thinking_steps']])
                            formatted_response = f"**🔄 Gathering Steps:**\n{thinking_steps}\n\n**Response:**\n{response_text}"
                        
                        # BUG FIX: Append assistant message to existing history properly
                        # Don't replace, just append to the end
                        updated_history = list(chat_history)
                        if updated_history and updated_history[-1]['role'] == 'assistant':
                            # Update existing assistant message
                            updated_history[-1]['content'] = formatted_response
                        else:
                            # Add new assistant message
                            updated_history.append({
                                "role": "assistant",
                                "content": formatted_response
                            })
                        # FIX: Yield both chatbot history and thinking display updates
                        yield updated_history, thinking_display_text
                    
                    # Final update to session
                    add_message_to_session("assistant", response_text)
                else:
                    # Non-streaming mode - return result
                    response = generate_response(
                        augmented_message,
                        history=session_history if use_context else None,
                        stream=False
                    )
                    
                    # Get all thinking updates
                    latest_thinking_updates = get_thinking_updates()
                    thinking_display_text = "".join(latest_thinking_updates)
                    
                    # Format response with thinking steps if available
                    formatted_response = response
                    if loop_thinking_results:
                        thinking_steps = "\n".join([f"  • {s}" for s in loop_thinking_results['thinking_steps']])
                        formatted_response = f"**🔄 Gathering Steps:**\n{thinking_steps}\n\n**Response:**\n{response}"
                    
                    # BUG FIX: Append new assistant message to existing chat history
                    chat_history = list(chat_history) + [{
                        "role": "assistant",
                        "content": formatted_response
                    }]
                    add_message_to_session("assistant", response)
                    # Must yield for generator function - FIX: include thinking display
                    yield chat_history, thinking_display_text
                    
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                # BUG FIX: Append error message properly
                chat_history = list(chat_history) + [{
                    "role": "assistant",
                    "content": error_msg
                }]
                # FIX: Yield with thinking display on error too
                yield chat_history, f"❌ Error occurred: {error_msg}"
        
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
                chat_info = chat_db.getChat(current_session_id)
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
        
        def apply_search_config(n_iter: int, max_res: int, info_len: int):
            """Apply search configuration settings."""
            global search_config
            search_config['n_iterations'] = n_iter
            search_config['max_results'] = max_res
            search_config['info_length_threshold'] = info_len
            
            msg = f"✅ Config saved:\n• Max iterations: {n_iter}\n• Max results: {max_res}\n• Info threshold: {info_len}"
            return msg
        
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
        
        # Event handler for configuration - update global search_config and show confirmation
        def apply_config_and_update(n_iter: int, max_res: int, info_len: int):
            """Apply configuration and return confirmation message."""
            global search_config
            # Update global configuration
            search_config['n_iterations'] = int(n_iter)
            search_config['max_results'] = int(max_res)
            search_config['info_length_threshold'] = int(info_len)
            print(f"✅ Configuration updated: iterations={n_iter}, results={max_res}, threshold={info_len}")
            return f"✅ Config applied:\n• Iterations: {n_iter}\n• Max Results: {max_res}\n• Info Threshold: {info_len} chars"
        
        apply_config_btn.click(
            apply_config_and_update,
            inputs=[n_iterations, max_results, info_threshold],
            outputs=[status_text]
        )
        
        # Event handlers for messaging - SIMPLIFIED to avoid interruption
        msg.submit(
            respond,
            [msg, chatbot, stream_toggle, context_toggle, search_toggle, thinking_toggle],
            [chatbot, thinking_display]
        ).then(
            clear_input_and_update,
            outputs=[msg, session_info, session_dropdown],
            queue=False
        )
        
        submit_btn.click(
            respond,
            [msg, chatbot, stream_toggle, context_toggle, search_toggle, thinking_toggle],
            [chatbot, thinking_display]
        ).then(
            clear_input_and_update,
            outputs=[msg, session_info, session_dropdown],
            queue=False
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
        
        # Event handler for HuggingFace model pull with progress tracking
        def on_hf_pull(hf_url: str, custom_name: str):
            """Handle HuggingFace model pull with real-time progress updates."""
            if not hf_url or not hf_url.strip():
                yield "❌ Please enter a HuggingFace repository URL", 0
                return
            
            try:
                import subprocess

                from model_manager import ModelPuller

                # Use custom name if provided, otherwise None to auto-generate
                model_name_for_pull = custom_name if custom_name and custom_name.strip() else None
                
                print(f"📥 Starting HF pull: {hf_url}")
                yield f"🔍 Verifying repository: {hf_url}", 5
                
                # Get model folder path
                if model_manager:
                    model_folder = model_manager.model_folder
                else:
                    model_folder = os.path.expanduser("~/models")
                
                os.makedirs(model_folder, exist_ok=True)
                
                # Parse HF URL
                puller = ModelPuller(model_folder)
                owner, repo = puller.parse_hf_url(hf_url)
                
                if not owner or not repo:
                    yield "❌ Invalid HuggingFace repository URL format", 0
                    return
                
                hf_full_url = f"https://huggingface.co/{owner}/{repo}"
                yield f"📡 Connecting to: {hf_full_url}", 10
                
                # Create target directory
                repo_name = model_name_for_pull or f"{owner}_{repo}"
                target_dir = os.path.join(model_folder, repo_name)
                os.makedirs(target_dir, exist_ok=True)
                
                print(f"📂 Target directory: {target_dir}")
                yield f"📂 Target directory: {target_dir}\n", 15
                
                # Use git clone with LFS for downloading
                print(f"📥 Cloning repository with Git LFS...")
                yield f"📥 Cloning repository (this may take a while)...", 20
                
                git_clone_success = False
                try:
                    # First, ensure git LFS is installed and working
                    lfs_check = subprocess.run(["git", "lfs", "version"], capture_output=True, text=True)
                    has_lfs = lfs_check.returncode == 0
                    print(f"Git LFS available: {has_lfs}")
                    if not has_lfs:
                        yield "⚠️ Git LFS not found. Please install Git LFS for large file support.", 0
                        raise Exception("Git LFS not installed")
                    
                    # Clone with both stdout and stderr captured
                    cmd = ["git", "clone", f"{hf_full_url}.git", target_dir]
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1
                    )
                    
                    # Track output for progress estimation
                    output_lines = 0
                    for line in process.stdout:
                        output_lines += 1
                        line_strip = line.strip()
                        # Estimate progress based on output lines
                        progress = min(20 + (output_lines * 0.5), 85)
                        if line_strip and any(x in line_strip for x in ["Receiving", "Resolving", "Unpacking", "objects"]):
                            yield f"📥 {line_strip}", progress
                        elif output_lines % 10 == 0:
                            yield f"📥 Downloading... ({output_lines} updates)", progress
                        print(f"Git output: {line_strip}")
                    
                    returncode = process.wait()
                    
                    if returncode == 0:
                        print(f"✅ Git clone completed successfully")
                        git_clone_success = True
                        yield f"✅ Git clone completed", 85
                    else:
                        print(f"⚠️  Git clone returned code {returncode}")
                        yield f"⚠️  Git clone returned code {returncode}, checking downloaded files...", 50
                
                except Exception as e:
                    print(f"⚠️  Git clone exception: {str(e)}")
                    git_clone_success = False
                
                # If git clone didn't work, try huggingface_hub
                if not git_clone_success:
                    print(f"📥 Falling back to huggingface_hub for download...")
                    yield f"📥 Using alternative download method...", 30
                    
                    try:
                        import shutil

                        from huggingface_hub import snapshot_download

                        # Clean target directory before fallback download
                        if os.path.exists(target_dir):
                            shutil.rmtree(target_dir)
                        os.makedirs(target_dir, exist_ok=True)
                        
                        print(f"📥 Using huggingface_hub for complete download...")
                        yield f"📥 Downloading model from HuggingFace (this may take a while)...", 35
                        
                        # Download all files including LFS pointers
                        result_dir = snapshot_download(
                            f"{owner}/{repo}",
                            local_dir=target_dir,
                            local_dir_use_symlinks=False,
                            resume_download=True
                        )
                        
                        print(f"✅ HuggingFace download completed to: {result_dir}")
                        yield f"✅ Download completed successfully", 85
                        
                    except Exception as hf_error:
                        print(f"❌ Download failed: {str(hf_error)}")
                        import traceback
                        traceback.print_exc()
                        yield f"❌ Download failed: {str(hf_error)}", 0
                        return
                
                # Find RKLLM files
                yield f"🔍 Scanning for .rkllm files...", 88
                
                # Wait a moment to ensure all files are fully written
                time.sleep(2)
                
                rkllm_files = list(Path(target_dir).rglob("*.rkllm"))
                
                # Also check for .rkllm files that might be LFS pointers
                if not rkllm_files:
                    # List all files in target directory for debugging
                    all_files = list(Path(target_dir).rglob("*"))
                    file_types = {}
                    for f in all_files:
                        if f.is_file():
                            ext = f.suffix or "no_ext"
                            file_types[ext] = file_types.get(ext, 0) + 1
                    
                    print(f"❌ No .rkllm files found. Files in directory: {file_types}")
                    yield f"❌ No .rkllm files found in repository. Available: {file_types}", 0
                    return
                
                print(f"✅ Found {len(rkllm_files)} RKLLM file(s)")
                yield f"✅ Found {len(rkllm_files)} RKLLM model file(s)", 95
                
                # List files
                file_info = "📋 Models found:\n"
                total_size = 0
                for rkllm_file in rkllm_files:
                    file_size = rkllm_file.stat().st_size
                    total_size += file_size
                    file_size_str = format_file_size(file_size)
                    file_info += f"  • {rkllm_file.name} ({file_size_str})\n"
                
                total_size_str = format_file_size(total_size)
                file_info += f"\n✅ Total size: {total_size_str}"
                file_info += f"\n✅ Model ready to use!"
                
                yield file_info, 100
                print(f"✅ Model pull completed successfully!")
                
            except Exception as e:
                print(f"❌ Error during pull: {str(e)}")
                import traceback
                traceback.print_exc()
                yield f"❌ Error: {str(e)}", 0
        
        hf_pull_btn.click(
            on_hf_pull,
            inputs=[hf_url_input, hf_model_name],
            outputs=[hf_status, hf_progress]
        ).then(
            refresh_model_selector,
            outputs=[model_selector]
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
            
            # BUG FIX: Preserve selected conversation on server restart
            # If no current session set, get the most recently modified chat
            if not chat_ids:
                current_session_id = create_new_session()
                current_chat_id = current_session_id
                chat_ids = [current_session_id]
            elif current_session_id is None or current_session_id not in chat_ids:
                # BUG FIX: Load most recently modified chat instead of first one
                # This preserves user's last active conversation
                if chat_db:
                    chats = chat_db.getAllChats()
                    if chats:
                        # Get most recently modified (should be first in list if db sorts correctly)
                        current_session_id = chats[0]['id']
                        current_chat_id = current_session_id
                        switch_session(current_session_id)
                    else:
                        current_session_id = chat_ids[0] if chat_ids else create_new_session()
                        current_chat_id = current_session_id
                else:
                    current_session_id = chat_ids[0] if chat_ids else create_new_session()
                    current_chat_id = current_session_id
            
            choices = get_dropdown_choices()
            # Get display value for current session
            display_value = None
            if current_session_id:
                chat_titles = get_chat_titles_dict()
                display_value = f"{current_session_id[:4]}... - {chat_titles.get(current_session_id, 'Chat')}"
            
            display_value = display_value or (choices[0] if choices else "New Chat")
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
    chat_db = initChatDatabase()
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
