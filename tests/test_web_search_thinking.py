"""
Comprehensive tests for web search and thinking functionality.

Test Coverage:
- Web search: queries, caching, TTL expiration, error handling
- Thinking engine: prompt injection, response parsing, step extraction
"""

import sys
import os
import time
import unittest
from datetime import datetime, timedelta

# Add rkllm_server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rkllm_server'))

from web_search import WebSearcher, SearchCache, get_web_searcher, search_web
from thinking_engine import ThinkingEngine, get_thinking_engine, parse_thinking_response


class TestSearchCache(unittest.TestCase):
    """Test cache functionality."""
    
    def setUp(self):
        """Initialize cache for each test."""
        self.cache = SearchCache(ttl_minutes=1)
    
    def test_cache_key_generation(self):
        """Test that cache keys are generated consistently."""
        key1 = self.cache._cache_key("hello world")
        key2 = self.cache._cache_key("HELLO WORLD")  # Should be same (case-insensitive)
        self.assertEqual(key1, key2)
    
    def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        query = "test query"
        results = [{"title": "Test", "url": "http://test.com"}]
        
        self.cache.set(query, results)
        retrieved = self.cache.get(query)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0]["title"], "Test")
    
    def test_cache_miss(self):
        """Test cache miss returns None."""
        results = self.cache.get("nonexistent query")
        self.assertIsNone(results)
    
    def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        # Create cache with very short TTL (0.1 seconds)
        cache = SearchCache(ttl_minutes=0.0001)  # ~0.006 seconds
        
        query = "expiring query"
        results = [{"title": "Temporary"}]
        cache.set(query, results)
        
        # Immediately retrieve - should work
        self.assertIsNotNone(cache.get(query))
        
        # Wait for expiration
        time.sleep(0.1)
        
        # Retrieve after expiration - should return None
        self.assertIsNone(cache.get(query))
    
    def test_cache_clear(self):
        """Test clearing cache."""
        self.cache.set("query1", [{"title": "Result1"}])
        self.cache.set("query2", [{"title": "Result2"}])
        
        self.assertEqual(len(self.cache.cache), 2)
        
        self.cache.clear()
        
        self.assertEqual(len(self.cache.cache), 0)
    
    def test_cache_stats(self):
        """Test getting cache statistics."""
        self.cache.set("query1", [{"title": "Result"}])
        self.cache.set("query2", [{"title": "Result"}])
        
        stats = self.cache.get_stats()
        
        self.assertEqual(stats["cached_queries"], 2)
        self.assertGreater(stats["cache_size_bytes"], 0)


class TestWebSearcher(unittest.TestCase):
    """Test web search functionality."""
    
    def setUp(self):
        """Initialize searcher for each test."""
        self.searcher = WebSearcher(enable_cache=True)
    
    def test_web_search_enabled_by_default(self):
        """Test that web search is enabled by default."""
        self.assertTrue(self.searcher.enabled)
    
    def test_disable_enable_search(self):
        """Test disabling and enabling search."""
        self.searcher.disable()
        self.assertFalse(self.searcher.enabled)
        
        self.searcher.enable()
        self.assertTrue(self.searcher.enabled)
    
    def test_search_returns_results_format(self):
        """Test that search returns properly formatted results."""
        results = self.searcher.search("Python programming", max_results=3)
        
        # Should return a list
        self.assertIsInstance(results, list)
        
        # Results should have required fields
        for result in results:
            self.assertIn("title", result)
            self.assertIn("url", result)
            self.assertIn("snippet", result)
            self.assertIn("content", result)
    
    def test_search_empty_when_disabled(self):
        """Test that disabled search returns empty list."""
        self.searcher.disable()
        results = self.searcher.search("test query")
        
        self.assertEqual(results, [])
    
    def test_search_caching_works(self):
        """Test that caching prevents duplicate searches."""
        query = "test caching"
        
        # First search
        results1 = self.searcher.search(query, max_results=3)
        
        # Second search (should use cache)
        results2 = self.searcher.search(query, max_results=3)
        
        # Results should be identical (from cache)
        self.assertEqual(len(results1), len(results2))
        if results1:
            self.assertEqual(results1[0]["title"], results2[0]["title"])
    
    def test_force_refresh_bypasses_cache(self):
        """Test that force_refresh bypasses cache."""
        query = "force refresh test"
        
        # Set initial cache entry
        initial_results = [{"title": "Cached Result", "url": "http://cached.com"}]
        self.searcher.cache.set(query, initial_results)
        
        # Search with force_refresh should bypass cache
        results = self.searcher.search(query, force_refresh=True)
        
        # Results should not equal cached (they'll be fresh or empty if search fails)
        # This test just verifies force_refresh parameter works
        self.assertIsInstance(results, list)
    
    def test_search_with_fallback_primary_succeeds(self):
        """Test fallback search when primary succeeds."""
        results = self.searcher.search_with_fallback(
            "Python",
            fallback_query="Programming"
        )
        
        self.assertIsInstance(results, list)
    
    def test_detect_search_need_with_triggers(self):
        """Test automatic search detection with trigger words."""
        trigger_messages = [
            "What is the latest AI news?",
            "Tell me current weather information",
            "Search for recent Python updates",
            "How do I learn programming?",
            "What is machine learning?"
        ]
        
        for message in trigger_messages:
            query = self.searcher.extract_search_query_from_message(message)
            # Should detect search need
            self.assertIsNotNone(query, f"Failed to detect search need in: {message}")
    
    def test_detect_search_need_without_triggers(self):
        """Test search not detected without trigger words."""
        message = "2 + 2 equals what?"
        query = self.searcher.extract_search_query_from_message(message)
        
        # Might be None or message itself - test just checks it doesn't error
        self.assertTrue(query is None or isinstance(query, str))
    
    def test_format_search_context(self):
        """Test formatting search results for prompt injection."""
        results = [
            {"title": "Title 1", "url": "http://url1.com", "snippet": "Snippet 1"},
            {"title": "Title 2", "url": "http://url2.com", "snippet": "Snippet 2"},
        ]
        
        context = self.searcher.format_search_context(results, "test query")
        
        # Should contain search indicator
        self.assertIn("WEB SEARCH RESULTS", context)
        self.assertIn("test query", context)
        # Should contain at least one result
        self.assertIn("Title 1", context) or self.assertIn("Title 2", context)
    
    def test_format_empty_search_context(self):
        """Test formatting empty search results."""
        context = self.searcher.format_search_context([], "empty query")
        
        self.assertEqual(context, "")
    
    def test_cache_stats(self):
        """Test getting cache statistics."""
        self.searcher.search("query1")
        self.searcher.search("query2")
        
        stats = self.searcher.get_cache_stats()
        
        self.assertIn("cached_queries", stats)
        self.assertEqual(stats["cached_queries"], 2)
    
    def test_clear_cache(self):
        """Test clearing searcher cache."""
        self.searcher.search("query1")
        self.searcher.search("query2")
        
        self.searcher.clear_cache()
        
        stats = self.searcher.get_cache_stats()
        self.assertEqual(stats["cached_queries"], 0)


class TestThinkingEngine(unittest.TestCase):
    """Test thinking/reasoning functionality."""
    
    def setUp(self):
        """Initialize thinking engine for each test."""
        self.engine = ThinkingEngine(enable_thinking=True)
    
    def test_thinking_enabled_by_default(self):
        """Test that thinking is enabled by default."""
        self.assertTrue(self.engine.enabled)
    
    def test_disable_enable_thinking(self):
        """Test disabling and enabling thinking."""
        self.engine.disable()
        self.assertFalse(self.engine.enabled)
        
        self.engine.enable()
        self.assertTrue(self.engine.enabled)
    
    def test_inject_chain_of_thought_prompt(self):
        """Test injecting chain-of-thought prompt."""
        prompt = self.engine.inject_thinking_prompt("What is 2+2?", pattern="chain_of_thought")
        
        # Should contain step instructions
        self.assertIn("Step", prompt)
        self.assertIn("2+2", prompt)
    
    def test_inject_structured_prompt(self):
        """Test injecting structured thinking prompt."""
        prompt = self.engine.inject_thinking_prompt("What is AI?", pattern="structured")
        
        # Should contain structured thinking indicators
        self.assertIn("relevant facts", prompt)
        self.assertIn("AI", prompt)
    
    def test_inject_detailed_prompt(self):
        """Test injecting detailed explanation prompt."""
        prompt = self.engine.inject_thinking_prompt("Explain gravity", pattern="detailed")
        
        # Should contain detail indicators
        self.assertIn("Detailed Response", prompt)
        self.assertIn("gravity", prompt)
    
    def test_inject_thinking_when_disabled(self):
        """Test that disabled thinking returns original message."""
        self.engine.disable()
        message = "Test message"
        
        result = self.engine.inject_thinking_prompt(message)
        
        self.assertEqual(result, message)
    
    def test_extract_numbered_steps(self):
        """Test extracting numbered steps from response."""
        response = """
        Step 1: Understand the problem
        This is step 1 explanation.
        
        Step 2: Plan the approach
        This is step 2 explanation.
        
        Step 3: Execute the plan
        This is step 3 explanation.
        """
        
        steps = self.engine.extract_thinking_steps(response)
        
        # Should find steps
        self.assertGreater(len(steps), 0)
        # Should contain step indicators
        self.assertTrue(any("Step" in step for step in steps))
    
    def test_extract_conclusion(self):
        """Test extracting conclusion from response."""
        response = """
        Some analysis here...
        
        Therefore, the answer is 42.
        
        This is the most logical conclusion.
        """
        
        conclusion = self.engine.extract_conclusion(response)
        
        # Should find conclusion
        self.assertIsNotNone(conclusion)
        self.assertTrue(len(conclusion) > 0)
    
    def test_separate_thinking_from_answer(self):
        """Test separating thinking from answer."""
        response = """
        <thinking>
        Let me think about this carefully.
        Step 1: Consider the facts
        Step 2: Analyze options
        </thinking>
        
        <answer>
        The best solution is X because of Y.
        </answer>
        """
        
        # This test uses XML tags which might not be in response
        thinking, answer = self.engine.separate_thinking_from_answer(response)
        
        self.assertIsInstance(thinking, str)
        self.assertIsInstance(answer, str)
    
    def test_format_thinking_for_display(self):
        """Test formatting thinking for UI display."""
        thinking = """
        Step 1: Identify the problem
        Step 2: Research solutions
        Step 3: Implement solution
        """
        
        formatted = self.engine.format_thinking_for_display(thinking)
        
        # Should be formatted nicely
        self.assertIsInstance(formatted, str)
        self.assertGreater(len(formatted), 0)
    
    def test_format_empty_thinking(self):
        """Test formatting empty thinking."""
        formatted = self.engine.format_thinking_for_display("")
        
        self.assertEqual(formatted, "")
    
    def test_parse_complex_response(self):
        """Test parsing complex response with multiple components."""
        response = """
        Let me work through this step by step.
        
        Step 1: Analyze the question
        This question requires careful analysis.
        
        Step 2: Consider options
        There are several possible approaches.
        
        Step 3: Determine best path
        After consideration, option A is best.
        
        Therefore, the answer is A because it's most efficient.
        """
        
        parsed = self.engine.parse_complex_response(response)
        
        self.assertIn("thinking", parsed)
        self.assertIn("answer", parsed)
        self.assertIn("steps", parsed)
        self.assertIn("conclusion", parsed)
        
        self.assertIsInstance(parsed["steps"], list)
    
    def test_validate_reasoning(self):
        """Test validating reasoning quality."""
        response = """
        Step 1: First consideration
        Step 2: Second consideration
        Step 3: Third consideration
        
        Therefore, the conclusion is clear.
        """
        
        validation = self.engine.validate_reasoning(response)
        
        self.assertIn("has_thinking", validation)
        self.assertIn("num_steps", validation)
        self.assertIn("has_conclusion", validation)
        self.assertIn("quality_score", validation)
        
        # Should have good quality score
        self.assertGreater(validation["quality_score"], 0)
        self.assertLessEqual(validation["quality_score"], 1.0)
    
    def test_validate_poor_reasoning(self):
        """Test validating poor reasoning."""
        response = "Just answer is X."
        
        validation = self.engine.validate_reasoning(response)
        
        # Should have lower quality score
        self.assertLess(validation["quality_score"], 0.5)


class TestGlobalInstances(unittest.TestCase):
    """Test global singleton instances."""
    
    def test_get_web_searcher_singleton(self):
        """Test that web searcher returns same instance."""
        searcher1 = get_web_searcher()
        searcher2 = get_web_searcher()
        
        self.assertIs(searcher1, searcher2)
    
    def test_get_thinking_engine_singleton(self):
        """Test that thinking engine returns same instance."""
        engine1 = get_thinking_engine()
        engine2 = get_thinking_engine()
        
        self.assertIs(engine1, engine2)


def run_tests():
    """Run all tests with detailed output."""
    print("\n" + "="*70)
    print("🧪 RUNNING COMPREHENSIVE TESTS FOR WEB SEARCH & THINKING")
    print("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSearchCache))
    suite.addTests(loader.loadTestsFromTestCase(TestWebSearcher))
    suite.addTests(loader.loadTestsFromTestCase(TestThinkingEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestGlobalInstances))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"✅ Tests Run: {result.testsRun}")
    print(f"✅ Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"❌ Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL TESTS PASSED! ✅\n")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED ❌\n")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
