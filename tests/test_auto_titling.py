#!/usr/bin/env python3
"""
Test auto-titling functionality end-to-end
"""
import sys
sys.path.insert(0, '/home/navazdeen/rkllama-server')

from rkllm_server.chat_database import ChatDatabase
from datetime import datetime
import os

def test_auto_titling():
    """Test auto-titling from first user message"""
    
    print("🧪 Testing Auto-Titling Functionality")
    print("=" * 50)
    
    # Initialize database
    db_path = os.path.expanduser("~/.rkllm/chat_history_test.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = ChatDatabase(db_path=db_path)
    
    # Test 1: Create a new chat
    print("\n📝 Test 1: Create new chat with model title")
    import uuid
    chat_id = str(uuid.uuid4())
    db.create_chat(chat_id, "Qwen2.5-3B-Instruct", "Gradio")
    print(f"  ✓ Created chat: {chat_id}")
    
    chat_info = db.get_chat(chat_id)
    print(f"  Initial title: '{chat_info['title']}'")
    assert "Chat with" in chat_info['title'], "Initial title should contain 'Chat with'"
    initial_title = chat_info['title']
    
    # Test 2: Add first user message and check if title updates
    print("\n📝 Test 2: Add first user message")
    user_message = "How to bake a chocolate cake with vanilla frosting"
    db.add_message(chat_id, "user", user_message)
    print(f"  ✓ Added user message: '{user_message[:50]}...'")
    
    # Simulate what gradio_server.py does - extract title from message
    new_title = db.generate_title_from_message(user_message, "Qwen2.5")
    print(f"  Generated title from message: '{new_title}'")
    
    # Simulate the auto-titling logic (what we just fixed)
    current_auto_title = db._generate_title_from_model("Qwen2.5")
    print(f"  Current auto-title from model: '{current_auto_title}'")
    
    if new_title and new_title != current_auto_title:
        print(f"  ✓ Title differs from auto-generated - updating...")
        db.update_chat_title(chat_id, new_title)
        print(f"  ✓ Title updated to: '{new_title}'")
    else:
        print(f"  ✗ Title NOT updated (new_title == current_auto_title)")
        return False
    
    # Verify title was updated in database
    chat_info = db.get_chat(chat_id)
    print(f"  Database title now: '{chat_info['title']}'")
    assert chat_info['title'] == new_title, f"Title should be updated to '{new_title}'"
    
    # Test 3: Multiple chats with different messages
    print("\n📝 Test 3: Create multiple chats and verify titles")
    test_messages = [
        "What is the capital of France",
        "How to learn Python programming",
        "Best practices for writing clean code",
    ]
    
    for msg in test_messages:
        chat_id_2 = str(uuid.uuid4())
        db.create_chat(chat_id_2, "Qwen2.5-3B-Instruct", "Gradio")
        db.add_message(chat_id_2, "user", msg)
        
        # Extract title
        extracted_title = db.generate_title_from_message(msg, "Qwen2.5")
        current_model_title = db._generate_title_from_model("Qwen2.5")
        
        if extracted_title and extracted_title != current_model_title:
            db.update_chat_title(chat_id_2, extracted_title)
            print(f"  ✓ '{msg[:40]}...' → '{extracted_title}'")
        else:
            print(f"  ✗ '{msg[:40]}...' - title not updated")
            return False
    
    # Test 4: Verify search works with new titles
    print("\n📝 Test 4: Search for chats by updated titles")
    results = db.search_chats("chocolate cake")
    print(f"  Search 'chocolate cake': Found {len(results)} results")
    if len(results) > 0:
        print(f"  ✓ Found: '{results[0]['title']}'")
    else:
        print(f"  ✗ No results found")
        return False
    
    # Test 5: Get all chats and verify titles
    print("\n📝 Test 5: List all chats and verify titles")
    all_chats = db.get_all_chats()
    print(f"  Total chats: {len(all_chats)}")
    for i, chat in enumerate(all_chats):
        print(f"    {i+1}. {chat['title']} (Model: {chat['model']})")
        # Verify title is not just the default model title
        assert chat['title'] != db._generate_title_from_model(chat['model']), \
            f"Chat {i+1} should have user-generated title, not default"
    
    # Cleanup
    os.remove(db_path)
    
    print("\n" + "=" * 50)
    print("✅ All auto-titling tests PASSED!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    try:
        success = test_auto_titling()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
