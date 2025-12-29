#!/usr/bin/env python3
"""
Quick script to update config.js with ngrok URL
Run this after starting ngrok to automatically update the config
"""

import requests
import re
from pathlib import Path

def get_ngrok_url():
    """Get the public ngrok URL from ngrok API"""
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get('tunnels', [])
            for tunnel in tunnels:
                if tunnel.get('proto') == 'https':
                    return tunnel.get('public_url')
            # Fallback to http
            for tunnel in tunnels:
                if tunnel.get('proto') == 'http':
                    return tunnel.get('public_url')
    except Exception as e:
        print(f"Error getting ngrok URL: {e}")
        print("Make sure ngrok is running on port 4040")
    return None

def update_config(ngrok_url):
    """Update config.js with ngrok URL"""
    config_path = Path('demo_landing_page/config.js')
    if not config_path.exists():
        print(f"❌ config.js not found at {config_path}")
        return False
    
    try:
        content = config_path.read_text()
        # Update production URL
        pattern = r"production:\s*window\.ALBEDO_API_URL\s*\|\|\s*'[^']*'"
        replacement = f"production: window.ALBEDO_API_URL || '{ngrok_url}'"
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            config_path.write_text(new_content)
            print(f"✅ Updated config.js")
            print(f"   Production URL: {ngrok_url}")
            return True
        else:
            print("⚠️  Could not find production URL pattern to update")
            print(f"   Please manually set: production: '{ngrok_url}'")
            return False
    except Exception as e:
        print(f"❌ Error updating config.js: {e}")
        return False

def main():
    print("🔍 Getting ngrok URL...")
    ngrok_url = get_ngrok_url()
    
    if not ngrok_url:
        print("❌ Could not get ngrok URL")
        print("   Make sure ngrok is running: ngrok http 5000")
        print("   Or check: http://localhost:4040")
        return
    
    print(f"📍 Found ngrok URL: {ngrok_url}")
    print()
    
    if update_config(ngrok_url):
        print()
        print("✅ Done! Your frontend will now use this ngrok URL")
        print("   (when not running on localhost)")
    else:
        print()
        print("⚠️  Please manually update demo_landing_page/config.js:")
        print(f"   production: '{ngrok_url}'")

if __name__ == "__main__":
    main()





