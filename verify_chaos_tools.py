#!/usr/bin/env python3
"""
Quick verification script to check if chaos tools are loading correctly.
Run this to verify the fix before running experiments.
"""
import os
import sys

def test_chaos_tools():
    """Test chaos tools loading with both enabled and disabled states."""
    
    print("\n" + "="*70)
    print("CHAOS TOOLS VERIFICATION")
    print("="*70)
    
    # Test 1: Standard mode
    print("\n📋 TEST 1: Standard Mode (chaos tools OFF)")
    print("-"*70)
    os.environ["USE_CHAOS_TOOLS"] = "false"
    
    # Import the tools module directly (simulates what agent does)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "domains/finance/tools"))
    import importlib.util
    
    spec = importlib.util.spec_from_file_location(
        "logic",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "domains/finance/tools/logic.py")
    )
    logic = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logic)
    
    tool_count = len(logic.TOOLS)
    tool_names = [t.__name__ for t in logic.TOOLS]
    
    print(f"✅ Tool count: {tool_count}")
    print(f"📋 Tool names: {tool_names}")
    
    if tool_count == 5:
        print("✅ PASS: Standard tools loaded correctly")
    else:
        print(f"❌ FAIL: Expected 5 tools, got {tool_count}")
        return False
    
    # Test 2: Chaos mode
    print("\n📋 TEST 2: Chaos Mode (chaos tools ON)")
    print("-"*70)
    os.environ["USE_CHAOS_TOOLS"] = "true"
    
    # Clear cached modules to force reload
    for module_name in list(sys.modules.keys()):
        if 'finance.tools' in module_name or module_name in ['logic', 'chaos_tools']:
            del sys.modules[module_name]
    
    # Reload module with chaos tools enabled
    spec = importlib.util.spec_from_file_location(
        "logic_chaos",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "domains/finance/tools/logic.py")
    )
    logic_chaos = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logic_chaos)
    
    tool_count = len(logic_chaos.TOOLS)
    tool_names = [t.__name__ for t in logic_chaos.TOOLS]
    
    print(f"✅ Tool count: {tool_count}")
    
    # Show sample chaos tools
    chaos_stock_tools = [n for n in tool_names if 'stock' in n.lower()]
    standard_tools = [n for n in tool_names if n in ['get_market_news', 'get_account_information', 'purchase_stocks', 'sell_stocks']]
    
    print(f"📋 Sample chaos stock price tools: {chaos_stock_tools[:5]}...")
    print(f"📋 Standard tools: {standard_tools}")
    
    # Verify expected counts
    if tool_count >= 21:
        print(f"✅ PASS: Chaos tools loaded correctly ({tool_count} tools)")
        
        # Verify we have the standard tools
        missing_standard = [t for t in ['get_market_news', 'get_account_information', 'purchase_stocks', 'sell_stocks'] if t not in tool_names]
        if missing_standard:
            print(f"❌ WARNING: Missing standard tools: {missing_standard}")
            return False
        else:
            print("✅ All required standard tools present")
        
        # Verify we have chaos tools
        if len(chaos_stock_tools) >= 15:
            print(f"✅ Found {len(chaos_stock_tools)} chaos stock price tools")
        else:
            print(f"❌ WARNING: Only found {len(chaos_stock_tools)} chaos tools, expected ~17")
            return False
    else:
        print(f"❌ FAIL: Expected at least 21 tools, got {tool_count}")
        return False
    
    print("\n" + "="*70)
    print("🎉 ALL TESTS PASSED!")
    print("="*70)
    print("\nChaos tools are working correctly. You can now:")
    print("1. Enable chaos tools in the Streamlit UI (⚙️ Chaos Controls)")
    print("2. Run experiments with: USE_CHAOS_TOOLS=true python run_experiment.py")
    print("3. Watch Galileo traces to see the agent struggle with tool choices!")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = test_chaos_tools()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

