#!/usr/bin/env python3
"""
CertiSense Demo Server
Simple Flask server to serve the CertiSense demo with RAG integration.
"""

import os
import sys
from flask import Flask, send_from_directory, send_file, jsonify, abort

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

# Resolve demo directory (project root / demo_landing_page)
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DEMO_DIR = os.path.join(PROJECT_ROOT, 'demo_landing_page')

@app.route('/')
def serve_demo():
    """Serve the CertiSense demo page"""
    index_path = os.path.join(DEMO_DIR, 'index.html')
    if not os.path.exists(index_path):
        abort(404)
    # Use send_file with absolute path to avoid path resolution issues
    return send_file(index_path)

@app.route('/index.html')
def serve_index_html():
    index_path = os.path.join(DEMO_DIR, 'index.html')
    if not os.path.exists(index_path):
        abort(404)
    return send_file(index_path)

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS)"""
    path = os.path.join(DEMO_DIR, filename)
    if not os.path.exists(path):
        abort(404)
    return send_from_directory(DEMO_DIR, filename)

@app.route('/api/status')
def demo_status():
    """Demo server status"""
    return jsonify({
        'status': 'running',
        'service': 'CertiSense Demo Server',
        'version': '1.0.0',
        'rag_integration': 'enabled'
    })

def main():
    """Main function to run the demo server"""
    print("🏗️  Starting Albedo Demo Server...")
    print("📱 Demo available at: http://localhost:3000")
    print("🔗 Make sure RAG API is running at: http://localhost:5000")
    print()
    
    port = int(os.environ.get('DEMO_PORT', 3000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == "__main__":
    main()
