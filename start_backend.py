#!/usr/bin/env python3
"""
Quick start script for the LEED RAG API backend
Run this to start the backend server for the Albedo frontend
"""

import os
import sys
import subprocess

def main():
    """Start the LEED RAG API server"""
    print("=" * 60)
    print("🚀 Starting Albedo LEED RAG API Backend")
    print("=" * 60)
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('src/leed_rag_api.py'):
        print("❌ Error: src/leed_rag_api.py not found!")
        print("   Make sure you're running this from the project root directory.")
        sys.exit(1)
    
    # Check if models exist
    models_exist = (
        os.path.exists('models/index_all.faiss') or
        os.path.exists('models/index_credits.faiss') or
        os.path.exists('models/leed_knowledge_base.faiss')
    )
    
    if not models_exist:
        print("⚠️  Warning: RAG model files not found!")
        print("   The API will start but won't be able to answer queries.")
        print("   To build the models, run:")
        print("   python src/deploy_rag_system.py")
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    print("📡 Starting Flask server on http://localhost:5000")
    print("   Frontend should connect automatically if running on localhost")
    print()
    print("💡 Tips:")
    print("   - Open http://localhost:5000 in browser for API docs")
    print("   - Open demo_landing_page/index.html for the frontend")
    print("   - Press Ctrl+C to stop the server")
    print()
    print("=" * 60)
    print()
    
    # Start the Flask server
    try:
        # Change to src directory to run the script
        os.chdir('src')
        subprocess.run([sys.executable, 'leed_rag_api.py'], check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()





