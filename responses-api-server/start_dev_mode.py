#!/usr/bin/env python3
"""
Start the API server in development mode with unlimited queries for testuser
"""

import os
import sys

def start_dev_mode():
    print("🚀 Starting CS 15 Tutor API server in DEVELOPMENT MODE")
    print("=" * 60)
    print("📋 Development mode features:")
    print("   ✅ Unlimited queries for 'testuser'")
    print("   ✅ System prompt reloading")
    print("   ✅ Enhanced debugging")
    print("   ✅ Flask debug mode enabled")
    print()
    print("🔧 Web app will use 'testuser' automatically in development")
    print("🔧 VSCode extension will need manual authentication")
    print("=" * 60)
    print()
    
    # Set development mode environment variable
    os.environ['DEVELOPMENT_MODE'] = 'true'
    
    # Import and run the Flask app
    try:
        from index import app
        print("🎯 Development mode enabled - testuser has unlimited queries!")
        print("🌐 Server starting on http://127.0.0.1:5000")
        print("📱 Web app should be accessible on http://127.0.0.1:3000")
        print()
        app.run(host='127.0.0.1', port=5000, debug=True)
    except ImportError as e:
        print(f"❌ Error importing Flask app: {e}")
        print("💡 Make sure you're in the responses-api-server directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_dev_mode() 