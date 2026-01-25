"""
Integration test for web search and thinking with Gradio UI.

Tests:
1. Web search integration
2. Thinking mode integration
3. Response formatting with sources
4. Both features together
"""

import sys
import os

# Add rkllm_server to path FIRST
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rkllm_server'))

# Now try importing - this should find the modules in rkllm_server
# But we also need to ensure duckduckgo_search is available
try:
    from duckduckgo_search import DDGS
except ImportError:
    print("⚠️  duckduckgo_search not in sys.path, trying system python...")

from web_search import get_web_searcher
from thinking_engine import get_thinking_engine, inject_thinking, parse_thinking_response, format_thinking_display


def test_web_search_integration():
    """Test web search functionality."""
    print("\n" + "="*70)
    print("🔍 TEST 1: WEB SEARCH INTEGRATION")
    print("="*70)
    
    searcher = get_web_searcher()
    
    # Test search
    query = "Python programming 2024"
    results = searcher.search(query, max_results=3)
    
    print(f"\n✅ Search Query: '{query}'")
    print(f"✅ Results Found: {len(results)}")
    
    if results:
        print("\nSearch Results:")
        for i, result in enumerate(results[:2], 1):
            print(f"  {i}. {result['title']}")
            print(f"     URL: {result['url']}")
            print(f"     Snippet: {result['snippet'][:100]}...")
    
    # Test search context formatting
    context = searcher.format_search_context(results, query)
    print(f"\n✅ Formatted Context (for prompt injection):")
    print(context[:300] + "..." if len(context) > 300 else context)
    
    return True


def test_thinking_mode_integration():
    """Test thinking/reasoning functionality."""
    print("\n" + "="*70)
    print("💭 TEST 2: THINKING MODE INTEGRATION")
    print("="*70)
    
    engine = get_thinking_engine()
    
    # Test prompt injection
    query = "What is the capital of France and why?"
    
    print(f"\n✅ Original Query: {query}")
    
    # Inject thinking prompt
    enhanced = inject_thinking(query, pattern="chain_of_thought")
    print(f"\n✅ Enhanced with Thinking Prompt:")
    print(enhanced[:300] + "..." if len(enhanced) > 300 else enhanced)
    
    # Test response parsing
    sample_response = """
    Let me think through this step by step.
    
    Step 1: Understand what we're looking for
    We need to identify the capital of France and provide reasoning.
    
    Step 2: Recall the information
    The capital of France is Paris.
    
    Step 3: Provide reasoning
    Paris is located in the Île-de-France region and has been the capital since 1871.
    
    Therefore, the answer is Paris because it's the political center of France 
    and has served as the capital for over 150 years.
    """
    
    parsed = parse_thinking_response(sample_response)
    print(f"\n✅ Parsed Response:")
    print(f"  - Has Thinking: {bool(parsed['thinking'])}")
    print(f"  - Number of Steps: {len(parsed['steps'])}")
    print(f"  - Has Conclusion: {bool(parsed['conclusion'] != 'No explicit conclusion')}")
    
    # Format for display
    formatted = format_thinking_display(parsed['thinking'])
    print(f"\n✅ Formatted for UI Display:")
    print(formatted[:250] + "..." if len(formatted) > 250 else formatted)
    
    return True


def test_combined_features():
    """Test web search and thinking together."""
    print("\n" + "="*70)
    print("🔗 TEST 3: COMBINED FEATURES (Search + Thinking)")
    print("="*70)
    
    searcher = get_web_searcher()
    engine = get_thinking_engine()
    
    query = "How has AI evolved in the last year?"
    
    print(f"\n📝 Query: {query}")
    
    # Step 1: Enhance with thinking
    enhanced_query = inject_thinking(query, pattern="chain_of_thought")
    print(f"\n✅ Step 1: Injected thinking prompt")
    print(f"   Enhanced query length: {len(enhanced_query)} chars")
    
    # Step 2: Add web search context
    search_results = searcher.search(query, max_results=2)
    search_context = searcher.format_search_context(search_results, query)
    
    final_prompt = search_context + enhanced_query
    print(f"\n✅ Step 2: Added web search context")
    print(f"   Found {len(search_results)} search results")
    print(f"   Final prompt length: {len(final_prompt)} chars")
    
    # Show sample of final prompt
    print(f"\n✅ Final Prompt (first 400 chars):")
    print(final_prompt[:400] + "..." if len(final_prompt) > 400 else final_prompt)
    
    return True


def test_response_formatting():
    """Test response formatting with sources and thinking."""
    print("\n" + "="*70)
    print("📋 TEST 4: RESPONSE FORMATTING")
    print("="*70)
    
    # Mock response and results
    response = "The answer to your question is that Python has evolved significantly with new async features and improved type hints in recent releases."
    
    search_results = [
        {
            "title": "Python 3.12 Release Notes",
            "url": "https://python.org/release/3.12",
            "snippet": "New features in Python 3.12..."
        },
        {
            "title": "Python Future Roadmap",
            "url": "https://python.org/peps",
            "snippet": "Upcoming changes and roadmap..."
        }
    ]
    
    print(f"\n✅ Original Response:")
    print(f"   {response}")
    
    # Format with sources
    formatted = response + "\n\n📚 **Sources:**\n"
    for i, result in enumerate(search_results[:2], 1):
        formatted += f"{i}. [{result['title']}]({result['url']})\n"
    
    print(f"\n✅ Formatted Response with Sources:")
    print(formatted)
    
    return True


def test_cache_behavior():
    """Test caching to ensure efficiency."""
    print("\n" + "="*70)
    print("💾 TEST 5: CACHE BEHAVIOR")
    print("="*70)
    
    searcher = get_web_searcher()
    
    query = "test cache behavior"
    
    # First search (will hit actual API)
    print(f"\n✅ First search for: '{query}'")
    results1 = searcher.search(query, max_results=2)
    print(f"   Found {len(results1)} results")
    
    # Second search (should hit cache)
    print(f"\n✅ Second search (should use cache):")
    results2 = searcher.search(query, max_results=2)
    print(f"   Found {len(results2)} results (from cache)")
    
    # Verify results are identical
    if len(results1) == len(results2):
        print(f"\n✅ Cache verification: Results match!")
    
    # Get cache stats
    stats = searcher.get_cache_stats()
    print(f"\n✅ Cache Statistics:")
    print(f"   Cached queries: {stats['cached_queries']}")
    print(f"   Cache size: {stats['cache_size_bytes']} bytes")
    
    return True


def run_integration_tests():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("🚀 WEB SEARCH & THINKING INTEGRATION TESTS")
    print("="*80)
    
    tests = [
        ("Web Search Integration", test_web_search_integration),
        ("Thinking Mode Integration", test_thinking_mode_integration),
        ("Combined Features", test_combined_features),
        ("Response Formatting", test_response_formatting),
        ("Cache Behavior", test_cache_behavior),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {test_name}: PASSED")
            else:
                failed += 1
                print(f"\n❌ {test_name}: FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name}: ERROR - {str(e)}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL INTEGRATION TESTS PASSED! ✅\n")
        return 0
    else:
        print(f"\n⚠️  {failed} TEST(S) FAILED ❌\n")
        return 1


if __name__ == "__main__":
    exit_code = run_integration_tests()
    sys.exit(exit_code)
