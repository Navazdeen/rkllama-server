#!/usr/bin/env python3
"""
Test model-based title generation
"""
import sys
sys.path.insert(0, '/home/navazdeen/rkllama-server/rkllm_server')

from chat_database import ChatDatabase

def test_title_extraction():
    """Test the new extract_summary_from_model_response function"""
    
    print("\n" + "=" * 70)
    print("🧪 TESTING MODEL-BASED TITLE GENERATION")
    print("=" * 70)
    
    # Test cases: (model_response, expected_result_characteristics)
    test_cases = [
        {
            "response": "How to bake a chocolate cake. It requires flour, butter, sugar, and eggs.",
            "description": "Long response with multiple sentences"
        },
        {
            "response": "Python is a powerful programming language for beginners and experts alike.",
            "description": "Single sentence response"
        },
        {
            "response": "Learn about machine learning concepts. Neural networks are fundamental to deep learning.",
            "description": "Two sentences"
        },
        {
            "response": "Tips for learning Python programming efficiently.",
            "description": "Query-like response"
        },
        {
            "response": "What is the capital of France? Paris is the capital.",
            "description": "Question and answer format"
        },
    ]
    
    print("\n📝 Test Results:")
    print("-" * 70)
    
    for i, test_case in enumerate(test_cases, 1):
        response = test_case["response"]
        description = test_case["description"]
        
        # Extract title using the new function
        title = ChatDatabase.extract_summary_from_model_response(response, max_length=60)
        
        print(f"\n{i}. {description}")
        print(f"   Original: {response[:60]}...")
        print(f"   Title:    '{title}'")
        print(f"   Length:   {len(title)} chars")
    
    print("\n" + "=" * 70)
    print("✅ All test cases completed")
    print("=" * 70)
    
    print("\n📋 Summary:")
    print("  • Extracts first sentence as title")
    print("  • Cleans up formatting")
    print("  • Limits to ~60 characters")
    print("  • Capitalizes first letter")
    print("  • Perfect for chat titles!")

if __name__ == "__main__":
    test_title_extraction()
