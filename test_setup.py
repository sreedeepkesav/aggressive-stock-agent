#!/usr/bin/env python3
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_setup():
    print("🧪 Testing Setup...")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print("=" * 60)

    # Test API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key and api_key.startswith('sk-ant-'):
        print("✅ Anthropic API Key: Found and valid format")
    else:
        print("❌ Anthropic API Key: Missing or invalid format")
        print("   Make sure it starts with 'sk-ant-'")

    # Test Avanza credentials
    username = os.getenv('AVANZA_USERNAME')
    password = os.getenv('AVANZA_PASSWORD')

    if username and password:
        print("✅ Avanza Credentials: Found")
        print("   Auto-trading will be available")
    else:
        print("⚠️  Avanza Credentials: Missing")
        print("   Will run in analysis-only mode")

    # Test critical imports
    failed_imports = []
    
    try:
        import numpy as np
        print(f"✅ NumPy: {np.__version__}")
    except ImportError as e:
        print("❌ NumPy: Import failed")
        failed_imports.append("numpy")

    try:
        import pandas as pd
        print(f"✅ Pandas: {pd.__version__}")
    except ImportError:
        print("❌ Pandas: Import failed")
        failed_imports.append("pandas")

    try:
        import requests
        print("✅ Requests: Available")
    except ImportError:
        print("❌ Requests: Import failed")
        failed_imports.append("requests")

    try:
        import yfinance as yf
        print("✅ YFinance: Available")
    except ImportError:
        print("❌ YFinance: Import failed")
        failed_imports.append("yfinance")
        
    try:
        import anthropic
        print(f"✅ Anthropic: {anthropic.__version__}")
    except ImportError:
        print("❌ Anthropic: Import failed")
        failed_imports.append("anthropic")

    try:
        import feedparser
        print("✅ Feedparser: Available")
    except ImportError:
        print("❌ Feedparser: Import failed")
        failed_imports.append("feedparser")

    print("=" * 60)
    
    if failed_imports:
        print(f"❌ Setup incomplete. Failed imports: {', '.join(failed_imports)}")
        print("Run the installation commands again for failed packages")
        return False
    else:
        print("🚀 Setup test complete! All packages imported successfully!")
        print("You're ready to run the aggressive stock agent!")
        return True

if __name__ == "__main__":
    test_setup()
