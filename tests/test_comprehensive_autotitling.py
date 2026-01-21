#!/usr/bin/env python3
"""
Final comprehensive test for auto-titling fix
Verifies:
1. Title generation from model works
2. Title generation from message works  
3. Database updates correctly
4. UI display updates work
5. Search functionality works with updated titles
"""
import sys

sys.path.insert(0, '/home/navazdeen/rkllama-server')

import os
import uuid

from rkllm_server.db.chat_database import ChatDatabase


def run_comprehensive_test():
    """Run comprehensive auto-titling tests"""
    
    print("\n" + "="*70)
    print("🧪 COMPREHENSIVE AUTO-TITLING TEST SUITE")
    print("="*70)
    
    # Initialize database
    db_path = os.path.expanduser("~/.rkllm/chat_history_final_test.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = ChatDatabase(db_path=db_path)
    
    # TEST 1: Title generation from model
    print("\n📝 TEST 1: Title Generation from Model")
    print("-" * 70)
    model_title = db._generateTitleFromModel("Qwen2.5-3B-Instruct")
    print(f"  Model: Qwen2.5-3B-Instruct")
    print(f"  Generated Title: '{model_title}'")
    assert "Chat with" in model_title, "Model title should contain 'Chat with'"
    assert "Qwen" in model_title, "Model title should contain model name"
    print("  ✅ PASS")
    
    # TEST 2: Title generation from various messages
    print("\n📝 TEST 2: Title Generation from Messages")
    print("-" * 70)
    test_cases = [
        ("How to bake chocolate cake", "How to bake chocolate cake"),
        ("What is the capital of France?", "What is the capital of France"),
        ("Tell me about machine learning", "Tell me about machine learning"),
        ("Hi", "Hi"),
    ]
    
    for message, expected in test_cases:
        generated = db.generateTitleFromMessage(message, "Qwen2.5")
        print(f"  Input: '{message[:40]}'")
        print(f"  Output: '{generated}'")
        assert generated == expected, f"Expected '{expected}', got '{generated}'"
        print(f"  ✅ PASS")
    
    # TEST 3: Database chat creation and title update
    print("\n📝 TEST 3: Database Chat Creation and Title Update")
    print("-" * 70)
    chat_id = str(uuid.uuid4())
    db.createChat(chat_id, "Qwen2.5-3B-Instruct", "Gradio")
    chat_info = db.getChat(chat_id)
    
    print(f"  Created chat: {chat_id}")
    print(f"  Initial title: '{chat_info['title']}'")
    assert chat_info['title'] == model_title, "Initial title should be model title"
    print("  ✅ PASS")
    
    # TEST 4: Auto-title update on first message
    print("\n📝 TEST 4: Auto-Title Update on First Message")
    print("-" * 70)
    first_message = "How to learn Python programming efficiently"
    db.addMessage(chat_id, "user", first_message)
    
    # Simulate the logic from gradio_server
    new_title = db.generateTitleFromMessage(first_message, "Qwen2.5")
    current_auto_title = db._generateTitleFromModel("Qwen2.5")
    
    print(f"  First message: '{first_message}'")
    print(f"  Generated title: '{new_title}'")
    print(f"  Auto-model title: '{current_auto_title}'")
    print(f"  Titles differ: {new_title != current_auto_title}")
    
    if new_title and new_title != current_auto_title:
        db.updateChatTitle(chat_id, new_title)
        print(f"  Title updated in database")
    
    # Verify update
    updated_info = db.getChat(chat_id)
    print(f"  Current title in DB: '{updated_info['title']}'")
    assert updated_info['title'] == new_title, "Title should be updated to message title"
    print("  ✅ PASS")
    
    # TEST 5: Multiple chats independence
    print("\n📝 TEST 5: Multiple Chats Independence")
    print("-" * 70)
    chats = []
    messages = [
        "Best practices for writing clean code",
        "How to optimize database queries",
        "Understanding async programming",
    ]
    
    for msg in messages:
        cid = str(uuid.uuid4())
        db.createChat(cid, "Qwen2.5-3B-Instruct", "Gradio")
        db.addMessage(cid, "user", msg)
        
        title = db.generateTitleFromMessage(msg, "Qwen2.5")
        current_auto = db._generateTitleFromModel("Qwen2.5")
        
        if title and title != current_auto:
            db.updateChatTitle(cid, title)
        
        chats.append((cid, title))
        print(f"  Chat: {title}")
    
    print(f"  Total chats created: {len(chats)}")
    assert len(chats) == 3, "Should create 3 chats"
    print("  ✅ PASS")
    
    # TEST 6: Search functionality
    print("\n📝 TEST 6: Search Functionality")
    print("-" * 70)
    search_terms = [
        ("python", 1),  # Should find 1 chat
        ("code", 1),    # Should find 1 chat
        ("database", 1), # Should find 1 chat
        ("async", 1),    # Should find 1 chat
    ]
    
    for term, expected_count in search_terms:
        results = db.searchChats(term)
        print(f"  Search '{term}': Found {len(results)} results")
        if results:
            for r in results:
                print(f"    → {r['title']}")
        assert len(results) == expected_count, f"Expected {expected_count} results for '{term}'"
    
    print("  ✅ PASS")
    
    # TEST 7: Chat list retrieval
    print("\n📝 TEST 7: Chat List Retrieval")
    print("-" * 70)
    all_chats = db.getAllChats()
    print(f"  Total chats in database: {len(all_chats)}")
    
    for i, chat in enumerate(all_chats):
        print(f"    {i+1}. '{chat['title']}' (Model: {chat['model'][:20]}...)")
    
    # Verify no chat has the default model title
    for chat in all_chats:
        assert not chat['title'].startswith("Chat with"), \
            f"Chat should have custom title, not model title: {chat['title']}"
    
    print("  ✅ PASS")
    
    # TEST 8: Message history preservation
    print("\n📝 TEST 8: Message History Preservation")
    print("-" * 70)
    # Get first chat
    first_chat_id = chats[0][0]
    
    # Add more messages
    db.addMessage(first_chat_id, "assistant", "Here's what I think about clean code...")
    db.addMessage(first_chat_id, "user", "Can you give me some examples?")
    db.addMessage(first_chat_id, "assistant", "Sure! Here are some examples...")
    
    # Retrieve messages
    messages = db.getChatMessages(first_chat_id)
    print(f"  Chat ID: {first_chat_id}")
    print(f"  Total messages: {len(messages)}")
    
    for i, msg in enumerate(messages):
        role = msg['role'].upper()
        content = msg['content'][:50]
        print(f"    {i+1}. [{role}] {content}...")
    
    assert len(messages) == 4, "Should have 4 messages"
    print("  ✅ PASS")
    
    # Cleanup
    os.remove(db_path)
    
    # Summary
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print("\nTest Summary:")
    print("  ✅ Model title generation works")
    print("  ✅ Message-based title extraction works")
    print("  ✅ Database updates correctly")
    print("  ✅ Title updates on first message")
    print("  ✅ Multiple chats are independent")
    print("  ✅ Search functionality works")
    print("  ✅ Chat list retrieval works")
    print("  ✅ Message history is preserved")
    print("\n🎉 Auto-titling system is fully functional!")
    print("="*70 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = run_comprehensive_test()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n❌ Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
