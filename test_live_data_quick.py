#!/usr/bin/env python3
"""
Quick test to verify live data is working

This script tests if the live data APIs are properly configured and working.
"""
import os
import sys

# Set live data mode
os.environ["USE_LIVE_DATA"] = "true"
os.environ["STOCK_DATA_SOURCE"] = "auto"

print("=" * 80)
print("LIVE DATA QUICK TEST")
print("=" * 80)

# Test 1: Check if dependencies are installed
print("\n✓ Step 1: Checking dependencies...")
try:
    import yfinance
    print("  ✓ yfinance installed")
    YFINANCE_OK = True
except ImportError:
    print("  ✗ yfinance NOT installed - run: pip install yfinance")
    YFINANCE_OK = False

try:
    from alpha_vantage.timeseries import TimeSeries
    print("  ✓ alpha-vantage installed")
    ALPHAVANTAGE_OK = True
except ImportError:
    print("  ✗ alpha-vantage NOT installed - run: pip install alpha-vantage")
    ALPHAVANTAGE_OK = False

# Test 2: Check environment variables
print("\n✓ Step 2: Checking environment...")
print(f"  USE_LIVE_DATA: {os.getenv('USE_LIVE_DATA')}")
print(f"  STOCK_DATA_SOURCE: {os.getenv('STOCK_DATA_SOURCE')}")
print(f"  ALPHA_VANTAGE_API_KEY: {'Set' if os.getenv('ALPHA_VANTAGE_API_KEY') else 'Not set'}")

# Test 3: Test the tool directly
print("\n✓ Step 3: Testing get_stock_price tool...")
try:
    from domains.finance.tools.logic import get_stock_price
    
    print("  Testing AAPL...")
    result = get_stock_price("AAPL")
    
    import json
    data = json.loads(result)
    
    print(f"\n  ✓ SUCCESS! Got data:")
    print(f"    Ticker: {data.get('ticker', 'N/A')}")
    print(f"    Price: ${data.get('price', 'N/A')}")
    print(f"    Source: {data.get('source', 'N/A')}")
    
    if 'source' in data:
        if 'yfinance' in data['source'].lower() or 'yahoo' in data['source'].lower():
            print(f"\n  ✓ Using Yahoo Finance (live data!)")
        elif 'alpha' in data['source'].lower():
            print(f"\n  ✓ Using Alpha Vantage (live data!)")
        else:
            print(f"\n  ⚠️  Source: {data['source']} (check if this is live or mock)")
    
    print("\n" + "=" * 80)
    print("✓ LIVE DATA IS WORKING!")
    print("=" * 80)
    print("\nYou can now:")
    print("  1. Run: streamlit run app.py")
    print("  2. Toggle ON 'Use Live Stock Data' in sidebar")
    print("  3. Ask: 'What's the price of AAPL?'")
    print("  4. Should get live data from", data.get('source', 'API'))
    print()
    
except Exception as e:
    print(f"\n  ✗ ERROR: {e}")
    print(f"\n  Full error:")
    import traceback
    traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("TROUBLESHOOTING")
    print("=" * 80)
    
    if not YFINANCE_OK:
        print("\n1. Install yfinance:")
        print("   pip install yfinance")
    
    print("\n2. Make sure you're in the project directory")
    print("   cd /path/to/galileo-golden-demo")
    
    print("\n3. Try running the app:")
    print("   streamlit run app.py")
    print("   Then toggle live data ON in the sidebar")
    print()
    sys.exit(1)

