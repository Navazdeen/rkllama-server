#!/usr/bin/env python3
"""
RKLLM Gradio Server - Chat API Demo

This script demonstrates how to interact with the RKLLM Gradio server.

Usage:
    python3 chat_api_gradio.py --url http://127.0.0.1:7860

Note: Make sure the Gradio server is running before running this script:
    python3 gradio_server.py --model_path <model.rkllm> --platform rk3588
"""

import argparse
import sys
from gradio_client import Client
from typing import List, Tuple


def chat_with_rkllm(client: Client, user_message: str, history: List[Tuple]) -> List[Tuple]:
    """
    Send a message to RKLLM via Gradio client and get response.
    
    Args:
        client: Gradio client instance
        user_message: User input message
        history: Chat history (list of [user_msg, assistant_msg] pairs)
    
    Returns:
        Updated chat history
    """
    try:
        # Call the Gradio interface
        result = client.predict(
            message=user_message,
            history=history,
            api_name="/chat"
        )
        
        # Add to history
        history.append([user_message, result])
        return history
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return history


def main():
    """Main entry point for the Gradio chat demo."""
    parser = argparse.ArgumentParser(
        description="RKLLM Gradio Server Chat Demo"
    )
    parser.add_argument(
        '--url',
        default='http://127.0.0.1:7860',
        help='Gradio server URL (default: http://127.0.0.1:7860)'
    )
    
    args = parser.parse_args()
    
    print("="*50)
    print("🤖 RKLLM Gradio Chat Demo")
    print("="*50)
    print(f"📡 Server: {args.url}")
    print("Type 'exit' or 'quit' to exit\n")
    
    try:
        # Connect to Gradio server
        print("📞 Connecting to Gradio server...")
        client = Client(args.url)
        print("✅ Connected!\n")
        
    except Exception as e:
        print(f"❌ Error: Cannot connect to {args.url}")
        print(f"   Make sure the Gradio server is running:")
        print(f"   python3 gradio_server.py --model_path <model.rkllm> --platform rk3588")
        sys.exit(1)
    
    # Chat loop
    history: List[Tuple] = []
    
    try:
        while True:
            try:
                user_input = input("👤 You: ").strip()
                
                if user_input.lower() in ['exit', 'quit']:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Send message
                print("🤖 Assistant: ", end="", flush=True)
                history = chat_with_rkllm(client, user_input, history)
                
                if history and history[-1][1]:
                    print(f"{history[-1][1]}\n")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
            