#!/usr/bin/env python3
"""
Start Albedo backend with ngrok tunnel
This exposes your local backend to the internet via ngrok
"""

import os
import sys
import subprocess
import time
import requests
import json
import webbrowser
from pathlib import Path

def check_ngrok():
    """Check if ngrok is installed"""
    try:
        result = subprocess.run(['ngrok', 'version'], 
                              capture_output=True, text=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def get_ngrok_url():
    """Get the public ngrok URL"""
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get('tunnels', [])
            for tunnel in tunnels:
                if tunnel.get('proto') == 'https':
                    return tunnel.get('public_url')
            # Fallback to http if https not available
            for tunnel in tunnels:
                if tunnel.get('proto') == 'http':
                    return tunnel.get('public_url')
    except:
        pass
    return None

def update_config(ngrok_url):
    """Update config.js with ngrok URL"""
    config_path = Path('demo_landing_page/config.js')
    if not config_path.exists():
        print("⚠️  config.js not found, skipping update")
        return
    
    try:
        content = config_path.read_text()
        # Update production URL
        import re
        pattern = r"production:\s*window\.ALBEDO_API_URL\s*\|\|\s*'[^']*'"
        replacement = f"production: window.ALBEDO_API_URL || '{ngrok_url}'"
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            config_path.write_text(new_content)
            print(f"✅ Updated config.js with ngrok URL: {ngrok_url}")
        else:
            print("⚠️  Could not update config.js automatically")
            print(f"   Please manually set production URL to: {ngrok_url}")
    except Exception as e:
        print(f"⚠️  Error updating config.js: {e}")
        print(f"   Please manually set production URL to: {ngrok_url}")

def main():
    """Main function"""
    print("=" * 60)
    print("🚀 Starting Albedo Backend with ngrok Tunnel")
    print("=" * 60)
    print()
    
    # Check ngrok installation
    if not check_ngrok():
        print("❌ ngrok is not installed!")
        print()
        print("📥 Install ngrok:")
        print("   1. Download from: https://ngrok.com/download")
        print("   2. Extract ngrok.exe to a folder in your PATH")
        print("   3. Sign up for free account: https://dashboard.ngrok.com/signup")
        print("   4. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken")
        print("   5. Run: ngrok config add-authtoken YOUR_TOKEN")
        print()
        sys.exit(1)
    
    print("✅ ngrok found")
    print()
    
    # Check if backend models exist
    models_exist = (
        os.path.exists('models/index_all.faiss') or
        os.path.exists('models/index_credits.faiss') or
        os.path.exists('models/leed_knowledge_base.faiss')
    )
    
    if not models_exist:
        print("⚠️  Warning: RAG model files not found!")
        print("   The API will start but won't be able to answer queries.")
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    print("📡 Starting Flask backend on port 5000...")
    print()
    
    # Start Flask backend in background
    backend_process = None
    try:
        backend_process = subprocess.Popen(
            [sys.executable, 'src/leed_rag_api.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd()
        )
        
        # Wait a bit for backend to start
        print("⏳ Waiting for backend to start...")
        time.sleep(3)
        
        # Check if backend is running
        try:
            response = requests.get('http://localhost:5000/api/status', timeout=2)
            if response.status_code == 200:
                print("✅ Backend is running!")
            else:
                print("⚠️  Backend may not be fully ready yet")
        except:
            print("⚠️  Backend is starting... (this may take a moment)")
        
        print()
        print("🌐 Starting ngrok tunnel...")
        print()
        
        # Start ngrok
        ngrok_process = subprocess.Popen(
            ['ngrok', 'http', '5000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for ngrok to start
        time.sleep(3)
        
        # Get ngrok URL
        ngrok_url = None
        max_attempts = 10
        for i in range(max_attempts):
            ngrok_url = get_ngrok_url()
            if ngrok_url:
                break
            time.sleep(1)
        
        if not ngrok_url:
            print("❌ Could not get ngrok URL")
            print("   Check ngrok dashboard: http://localhost:4040")
            ngrok_process.terminate()
            backend_process.terminate()
            sys.exit(1)
        
        print("=" * 60)
        print("🎉 SUCCESS! Your backend is now publicly accessible")
        print("=" * 60)
        print()
        print(f"📍 Public URL: {ngrok_url}")
        print(f"📍 Local URL:  http://localhost:5000")
        print(f"📍 ngrok Dashboard: http://localhost:4040")
        print()
        print("📋 Next steps:")
        print(f"   1. Update config.js production URL to: {ngrok_url}")
        print("   2. Or use this URL directly in your frontend")
        print("   3. Open your frontend and test the connection")
        print()
        print("💡 Tips:")
        print("   - Keep this window open (Ctrl+C to stop)")
        print("   - ngrok URL changes each time you restart")
        print("   - Free ngrok has 40 connections/minute limit")
        print()
        print("=" * 60)
        print()
        
        # Try to update config.js automatically
        update_config(ngrok_url)
        print()
        
        # Open ngrok dashboard
        try:
            webbrowser.open('http://localhost:4040')
        except:
            pass
        
        # Keep processes running
        print("🔄 Backend and ngrok are running...")
        print("   Press Ctrl+C to stop")
        print()
        
        try:
            # Wait for user interrupt
            while True:
                time.sleep(1)
                # Check if processes are still alive
                if backend_process.poll() is not None:
                    print("❌ Backend process stopped unexpectedly")
                    break
                if ngrok_process.poll() is not None:
                    print("❌ ngrok process stopped unexpectedly")
                    break
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping services...")
            backend_process.terminate()
            ngrok_process.terminate()
            print("✅ Stopped")
            print()
            print("💡 To use a permanent URL, consider:")
            print("   - Deploying to Render (free tier)")
            print("   - Using ngrok paid plan for static domains")
            print()
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
        if backend_process:
            backend_process.terminate()
        if 'ngrok_process' in locals():
            ngrok_process.terminate()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if backend_process:
            backend_process.terminate()
        if 'ngrok_process' in locals():
            ngrok_process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()

