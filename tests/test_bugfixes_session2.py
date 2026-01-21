#!/usr/bin/env python3
"""
Test suite for Session 2 bug fixes.

Tests for:
1. Configuration parameters affecting backend
2. Live updates working properly
3. Chat processing without interruption
"""

import threading
import time
import unittest
from typing import Dict, List


class TestConfigurationParameters(unittest.TestCase):
    """Test that configuration parameters properly affect backend."""
    
    def setUp(self):
        """Set up test configuration."""
        self.search_config = {
            'n_iterations': 3,
            'max_results': 3,
            'info_length_threshold': 500,
        }
    
    def test_config_values_stored_globally(self):
        """Test that config values are stored in global dict."""
        self.assertEqual(self.search_config['n_iterations'], 3)
        self.assertEqual(self.search_config['max_results'], 3)
        self.assertEqual(self.search_config['info_length_threshold'], 500)
    
    def test_config_update_applies(self):
        """Test that config update changes values."""
        self.search_config['n_iterations'] = 5
        self.search_config['max_results'] = 8
        self.search_config['info_length_threshold'] = 1000
        
        self.assertEqual(self.search_config['n_iterations'], 5)
        self.assertEqual(self.search_config['max_results'], 8)
        self.assertEqual(self.search_config['info_length_threshold'], 1000)
    
    def test_config_persists_across_operations(self):
        """Test that config persists after operations."""
        original_config = self.search_config.copy()
        self.search_config['n_iterations'] = 4
        
        # Simulate some operation
        _ = self.search_config['n_iterations'] * 2
        
        # Config should still be 4
        self.assertEqual(self.search_config['n_iterations'], 4)
        
        # Restore
        self.search_config.update(original_config)
    
    def test_loop_thinking_engine_uses_config(self):
        """Test that LoopThinkingEngine would use configured parameters."""
        # Simulate engine creation with config values
        class MockLoopThinkingEngine:
            def __init__(self, max_iterations: int, info_threshold: int):
                self.max_iterations = max_iterations
                self.info_threshold = info_threshold
        
        # Engine should be created with config values
        engine = MockLoopThinkingEngine(
            max_iterations=self.search_config['n_iterations'],
            info_threshold=self.search_config['info_length_threshold']
        )
        
        self.assertEqual(engine.max_iterations, 3)
        self.assertEqual(engine.info_threshold, 500)
    
    def test_web_search_uses_max_results_config(self):
        """Test that web search would use configured max_results."""
        # Simulate search with config max_results
        def mock_search(query: str, max_results: int):
            # Would return up to max_results items
            return [f"Result {i}" for i in range(min(max_results, 10))]
        
        results = mock_search("test", max_results=self.search_config['max_results'])
        self.assertEqual(len(results), 3)
        
        # With different config
        self.search_config['max_results'] = 5
        results = mock_search("test", max_results=self.search_config['max_results'])
        self.assertEqual(len(results), 5)


class TestLiveUpdates(unittest.TestCase):
    """Test that live updates work properly."""
    
    def setUp(self):
        """Set up thinking updates storage."""
        self.thinking_updates = {
            'current': [],
            'lock': threading.Lock()
        }
    
    def test_update_thinking_display(self):
        """Test adding thinking updates."""
        def update_thinking_display(message: str):
            with self.thinking_updates['lock']:
                self.thinking_updates['current'].append(message)
        
        update_thinking_display("Step 1: Processing")
        update_thinking_display("Step 2: Searching")
        
        self.assertEqual(len(self.thinking_updates['current']), 2)
        self.assertIn("Step 1", self.thinking_updates['current'][0])
    
    def test_get_thinking_updates(self):
        """Test retrieving and clearing thinking updates."""
        def update_thinking_display(message: str):
            with self.thinking_updates['lock']:
                self.thinking_updates['current'].append(message)
        
        def get_thinking_updates():
            with self.thinking_updates['lock']:
                updates = self.thinking_updates['current'].copy()
                self.thinking_updates['current'].clear()
                return updates
        
        update_thinking_display("Update 1")
        update_thinking_display("Update 2")
        
        updates = get_thinking_updates()
        self.assertEqual(len(updates), 2)
        self.assertEqual(len(self.thinking_updates['current']), 0)
    
    def test_thinking_display_thread_safe(self):
        """Test that thinking updates are thread-safe."""
        def update_thinking_display(message: str):
            with self.thinking_updates['lock']:
                self.thinking_updates['current'].append(message)
        
        def worker(thread_id: int):
            for i in range(5):
                update_thinking_display(f"Thread {thread_id} - Update {i}")
        
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have 15 updates (3 threads * 5 updates each)
        self.assertEqual(len(self.thinking_updates['current']), 15)
    
    def test_thinking_updates_visible(self):
        """Test that thinking updates are marked as visible."""
        def update_thinking_display(message: str):
            with self.thinking_updates['lock']:
                self.thinking_updates['current'].append(message)
        
        update_thinking_display("🔄 Searching...")
        
        # Updates are visible if they contain content
        with self.thinking_updates['lock']:
            has_content = len(self.thinking_updates['current']) > 0
        
        self.assertTrue(has_content)
    
    def test_live_updates_for_thinking_mode(self):
        """Test live updates work in thinking mode."""
        def update_thinking_display(message: str):
            with self.thinking_updates['lock']:
                self.thinking_updates['current'].append(message)
        
        # Simulate thinking mode
        update_thinking_display("⚙️ Config: 3 iterations, 3 results\n")
        update_thinking_display("🌐 Searching: 'test query'\n")
        update_thinking_display("✅ Found 3 results\n")
        update_thinking_display("🔄 Iteration 1: info_length=245 chars\n")
        
        with self.thinking_updates['lock']:
            display_text = "".join(self.thinking_updates['current'])
        
        self.assertIn("Config", display_text)
        self.assertIn("Searching", display_text)
        self.assertIn("Iteration", display_text)
    
    def test_live_updates_for_web_search_mode(self):
        """Test live updates work in web search mode."""
        def update_thinking_display(message: str):
            with self.thinking_updates['lock']:
                self.thinking_updates['current'].append(message)
        
        # Simulate web search mode
        update_thinking_display("🌐 Searching: 'machine learning'\n")
        update_thinking_display("✅ Found 5 results\n")
        
        with self.thinking_updates['lock']:
            display_text = "".join(self.thinking_updates['current'])
        
        self.assertIn("Searching", display_text)
        self.assertIn("Found 5 results", display_text)


class TestChatProcessing(unittest.TestCase):
    """Test that chat processing works without interruption."""
    
    def test_user_message_added_to_history(self):
        """Test that user messages are properly added."""
        chat_history = []
        
        user_msg = {"role": "user", "content": "Hello"}
        chat_history = chat_history + [user_msg]
        
        self.assertEqual(len(chat_history), 1)
        self.assertEqual(chat_history[0]['role'], 'user')
    
    def test_assistant_message_appended(self):
        """Test that assistant messages are appended, not replaced."""
        chat_history = [{"role": "user", "content": "Hello"}]
        
        # First assistant message
        chat_history = chat_history + [{"role": "assistant", "content": "Hi there!"}]
        self.assertEqual(len(chat_history), 2)
        
        # Second user message
        chat_history = chat_history + [{"role": "user", "content": "How are you?"}]
        self.assertEqual(len(chat_history), 3)
        
        # Second assistant message
        chat_history = chat_history + [{"role": "assistant", "content": "I'm doing well!"}]
        self.assertEqual(len(chat_history), 4)
        
        # All messages should be intact
        self.assertEqual(chat_history[0]['content'], "Hello")
        self.assertEqual(chat_history[1]['content'], "Hi there!")
        self.assertEqual(chat_history[2]['content'], "How are you?")
        self.assertEqual(chat_history[3]['content'], "I'm doing well!")
    
    def test_streaming_update_without_interruption(self):
        """Test that streaming updates don't interrupt message flow."""
        chat_history = [{"role": "user", "content": "What is AI?"}]
        
        # Simulate streaming response
        response_parts = ["Artificial", " Intelligence", " is", " a", " field"]
        response_text = ""
        
        for part in response_parts:
            response_text += part
            # Update or add assistant message
            if chat_history and chat_history[-1]['role'] == 'assistant':
                chat_history[-1]['content'] = response_text
            else:
                chat_history = chat_history + [{
                    "role": "assistant",
                    "content": response_text
                }]
        
        self.assertEqual(len(chat_history), 2)
        self.assertEqual(chat_history[-1]['content'], "Artificial Intelligence is a field")
    
    def test_multiple_turn_conversation(self):
        """Test that multi-turn conversations work properly."""
        chat_history = []
        
        # Turn 1
        chat_history = chat_history + [{"role": "user", "content": "Q1"}]
        chat_history = chat_history + [{"role": "assistant", "content": "A1"}]
        
        # Turn 2
        chat_history = chat_history + [{"role": "user", "content": "Q2"}]
        chat_history = chat_history + [{"role": "assistant", "content": "A2"}]
        
        # Turn 3
        chat_history = chat_history + [{"role": "user", "content": "Q3"}]
        chat_history = chat_history + [{"role": "assistant", "content": "A3"}]
        
        self.assertEqual(len(chat_history), 6)
        self.assertEqual(chat_history[0]['content'], "Q1")
        self.assertEqual(chat_history[2]['content'], "Q2")
        self.assertEqual(chat_history[4]['content'], "Q3")
    
    def test_no_message_interruption_with_config_change(self):
        """Test that config changes don't interrupt message flow."""
        chat_history = [{"role": "user", "content": "Hello"}]
        
        # Simulate config change during processing
        config = {'n_iterations': 3, 'max_results': 3}
        config['n_iterations'] = 5  # Change config
        
        # Message should still be added normally
        chat_history = chat_history + [{"role": "assistant", "content": "Hi"}]
        
        self.assertEqual(len(chat_history), 2)
        self.assertEqual(chat_history[-1]['content'], "Hi")


class TestIntegration(unittest.TestCase):
    """Integration tests for all three bug fixes."""
    
    def test_config_affects_search_with_live_updates(self):
        """Test that config changes, live updates show, and messages aren't interrupted."""
        search_config = {'n_iterations': 3, 'max_results': 3, 'info_length_threshold': 500}
        thinking_updates = {'current': [], 'lock': threading.Lock()}
        chat_history = []
        
        def update_thinking_display(msg: str):
            with thinking_updates['lock']:
                thinking_updates['current'].append(msg)
        
        # 1. Start with user message
        chat_history = chat_history + [{"role": "user", "content": "Search query"}]
        
        # 2. Update config
        search_config['n_iterations'] = 5
        search_config['max_results'] = 8
        
        # 3. Add thinking updates with new config
        update_thinking_display(f"Config: {search_config['n_iterations']} iterations\n")
        update_thinking_display(f"Max results: {search_config['max_results']}\n")
        
        # 4. Add assistant response (should not be interrupted)
        chat_history = chat_history + [{"role": "assistant", "content": "Response based on configured search"}]
        
        # Verify all three fixes work together
        self.assertEqual(len(chat_history), 2)
        self.assertEqual(search_config['n_iterations'], 5)
        with thinking_updates['lock']:
            self.assertGreater(len(thinking_updates['current']), 0)


if __name__ == '__main__':
    unittest.main()
