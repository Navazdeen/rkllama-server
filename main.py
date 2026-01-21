import argparse
import sys

from rkllm_server.db.chat_database import initChatDatabase
from rkllm_server.servers.gradio import (
    createGradioInterface,
    initializeModel,
    initializeModelManager,
)


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
        help="Path to folder containing models (recommended)",
    )
    parser.add_argument(
        "--rkllm_model_path",
        type=str,
        default=None,
        help="Path to single RKLLM model file (deprecated, use --model_folder)",
    )
    parser.add_argument(
        "--target_platform",
        type=str,
        required=True,
        choices=["rk3588", "rk3576", "rk3562", "rv1126b"],
        help="Target platform",
    )
    parser.add_argument(
        "--model_name", type=str, default="qwen", help="Model name (default: qwen)"
    )
    parser.add_argument(
        "--port", type=int, default=7860, help="Server port (default: 7860)"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Server host (default: 0.0.0.0)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🚀 RKLLM Gradio Server Starting")
    print("=" * 60)

    # Initialize chat database
    print("💾 Initializing chat database...")
    chat_db = initChatDatabase()
    print("✅ Chat database initialized")

    # Initialize model manager if folder provided
    if args.model_folder:
        print(f"📁 Using model folder: {args.model_folder}")
        if not initializeModelManager(args.model_folder, args.target_platform):
            print("❌ Failed to initialize model manager")
            sys.exit(1)
    elif args.rkllm_model_path:
        print(f"⚠️  Using deprecated single model path. Consider using --model_folder")
        if not initializeModel(
            args.rkllm_model_path, args.target_platform, args.model_name
        ):
            print("❌ Failed to initialize model")
            sys.exit(1)
    else:
        print("❌ Either --model_folder or --rkllm_model_path must be provided")
    print(f"📱 Creating Gradio interface...")
    demo = createGradioInterface()

    # Launch server
    print(f"🌐 Launching server on {args.host}:{args.port}")
    print("📖 Access interface at: http://localhost:7860")
    print("=" * 60)

    try:
        demo.launch(
            server_name=args.host, server_port=args.port, share=False, show_error=True
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down server...")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
