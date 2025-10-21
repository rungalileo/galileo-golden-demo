#!/usr/bin/env python3
"""
Demo script for chaos tools - showcasing Galileo observability value

This script demonstrates how chaos tools create confusion and how
Galileo helps identify the issues.
"""
import os
import sys
import time
import json
from pathlib import Path

# Set up paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_banner(text):
    """Print a nice banner."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def demonstrate_standard_tools():
    """Show standard tools working correctly."""
    print_banner("PART 1: Standard Tools (Clean Baseline)")
    
    # Disable chaos tools
    os.environ["USE_CHAOS_TOOLS"] = "false"
    
    # Import after setting env var
    from domains.finance.tools.logic import TOOLS
    
    print(f"✅ Standard tools loaded: {len(TOOLS)} tools")
    print("\nTools available:")
    for i, tool in enumerate(TOOLS, 1):
        print(f"  {i}. {tool.__name__}()")
    
    # Test a standard tool
    print("\n" + "-"*70)
    print("Testing get_stock_price('AAPL')...")
    print("-"*70)
    
    from domains.finance.tools.logic import get_stock_price
    
    start = time.time()
    result = get_stock_price("AAPL")
    duration = time.time() - start
    
    data = json.loads(result)
    print(f"✅ Success! Price: ${data['price']:.2f}")
    print(f"⏱️  Duration: {duration*1000:.0f}ms")
    print(f"📊 Full response: {json.dumps(data, indent=2)}")

def demonstrate_chaos_tools():
    """Show chaos tools creating confusion."""
    print_banner("PART 2: Chaos Tools (Deliberate Confusion)")
    
    # Enable chaos tools
    os.environ["USE_CHAOS_TOOLS"] = "true"
    
    # Need to reload modules to pick up new env var
    if 'domains.finance.tools.logic' in sys.modules:
        del sys.modules['domains.finance.tools.logic']
    if 'domains.finance.tools.chaos_tools' in sys.modules:
        del sys.modules['domains.finance.tools.chaos_tools']
    
    # Import after setting env var
    from domains.finance.tools.logic import TOOLS
    from domains.finance.tools.chaos_tools import get_chaos_tool_descriptions
    
    print(f"⚠️  Chaos tools loaded: {len(TOOLS)} tools (5 standard + chaos)")
    print("\nAll tools now available:")
    for i, tool in enumerate(TOOLS, 1):
        marker = "✅" if i <= 5 else "⚠️"
        print(f"  {marker} {i}. {tool.__name__}()")
    
    # Show what's wrong with each chaos tool
    print("\n" + "-"*70)
    print("Chaos Tool Issues:")
    print("-"*70)
    descriptions = get_chaos_tool_descriptions()
    for tool_name, issue in descriptions.items():
        print(f"  ⚠️  {tool_name}: {issue}")

def demonstrate_chaos_patterns():
    """Show each chaos pattern in action."""
    print_banner("PART 3: Chaos Patterns in Action")
    
    os.environ["USE_CHAOS_TOOLS"] = "true"
    
    # Need to reload
    if 'domains.finance.tools.chaos_tools' in sys.modules:
        del sys.modules['domains.finance.tools.chaos_tools']
    
    from domains.finance.tools import chaos_tools
    
    # Pattern 1: Minimal data
    print("\n📋 Pattern 1: Minimal/Incomplete Data")
    print("-"*70)
    print("Testing get_stock_price_fast()...")
    try:
        start = time.time()
        result = chaos_tools.get_stock_price_fast("AAPL")
        duration = time.time() - start
        data = json.loads(result)
        print(f"✅ Returns data: {data}")
        print(f"⚠️  BUT: Missing volume, high, low, open! Only has ticker, price, change.")
        print(f"✅ Still logs to Galileo though!")
        print(f"⏱️  Duration: {duration*1000:.0f}ms")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Pattern 2: Wrong format
    print("\n📋 Pattern 2: Different Return Format")
    print("-"*70)
    print("Testing lookup_stock_price()...")
    try:
        start = time.time()
        result = chaos_tools.lookup_stock_price("AAPL")
        duration = time.time() - start
        print(f"✅ Returns: '{result}'")
        print(f"⚠️  BUT: Just a string, not JSON! Lost all metadata.")
        print(f"⏱️  Duration: {duration*1000:.0f}ms")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Pattern 3: Artificial latency
    print("\n📋 Pattern 3: Artificial Latency")
    print("-"*70)
    print("Testing get_current_stock_price() (has 2s delay)...")
    try:
        start = time.time()
        result = chaos_tools.get_current_stock_price("AAPL")
        duration = time.time() - start
        print(f"✅ Returns data: {json.loads(result)['price']}")
        print(f"⚠️  BUT: Took {duration:.1f}s due to artificial delay!")
        print(f"⏱️  Duration: {duration*1000:.0f}ms")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Pattern 4: Subtle bugs
    print("\n📋 Pattern 4: Subtle Bugs (Intermittent)")
    print("-"*70)
    print("Testing retrieve_stock_price() 5 times...")
    print("(10% chance of returning wrong ticker)")
    for i in range(5):
        try:
            result = json.loads(chaos_tools.retrieve_stock_price("AAPL"))
            ticker_returned = result.get('ticker', 'unknown')
            if ticker_returned and ticker_returned != 'AAPL':
                print(f"  ❌ Call {i+1}: Wrong ticker! Got {ticker_returned} instead of AAPL")
            else:
                print(f"  ✅ Call {i+1}: Correct (AAPL)")
        except Exception as e:
            print(f"  ❌ Call {i+1}: Error: {e}")
    
    # Pattern 5: Inefficient
    print("\n📋 Pattern 5: Inefficient Implementation")
    print("-"*70)
    print("Testing get_multiple_stock_prices() for single ticker...")
    try:
        start = time.time()
        result = chaos_tools.get_multiple_stock_prices("AAPL")
        duration = time.time() - start
        data = json.loads(result)
        print(f"✅ Returns: {data['count']} stocks")
        print(f"⚠️  BUT: Added 500ms delay even for single ticker!")
        print(f"⏱️  Duration: {duration*1000:.0f}ms")
    except Exception as e:
        print(f"❌ Error: {e}")

def demonstrate_galileo_value():
    """Explain how Galileo helps."""
    print_banner("PART 4: How Galileo Helps")
    
    print("""
Without Galileo Observability:
  ❌ Can't see which tool was actually called
  ❌ Hard to identify performance bottlenecks
  ❌ Intermittent bugs are nearly impossible to debug
  ❌ Can't correlate user issues with specific tool calls
  ❌ No visibility into tool selection patterns
  ❌ Incomplete data responses go unnoticed

With Galileo Observability:
  ✅ See every tool call with inputs/outputs (all chaos tools log!)
  ✅ Duration tracking shows bottlenecks clearly
  ✅ Can correlate intermittent bugs with specific calls
  ✅ Track which tools are used and their success rates
  ✅ Compare tool selection across different queries
  ✅ Identify suboptimal tool choices by agents
  ✅ Spot incomplete or malformed responses instantly

Key Insights:
  1. Too many similar tools confuse LLM agents
  2. Tool choice directly impacts performance and correctness
  3. Without observability, debugging is guesswork
  4. Galileo makes tool usage patterns visible and actionable
""")

def main():
    """Run the full demonstration."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  🔧 CHAOS TOOLS DEMONSTRATION - Galileo Observability Value".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    try:
        demonstrate_standard_tools()
        time.sleep(1)
        
        demonstrate_chaos_tools()
        time.sleep(1)
        
        demonstrate_chaos_patterns()
        time.sleep(1)
        
        demonstrate_galileo_value()
        
        print_banner("Demo Complete!")
        print("""
Next Steps:
  1. Run experiments with USE_CHAOS_TOOLS=true
  2. Compare traces in Galileo UI
  3. Identify which chaos tools were used
  4. Show how Galileo helps spot the issues

See CHAOS_TOOLS_GUIDE.md for more details.
""")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

