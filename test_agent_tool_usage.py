#!/usr/bin/env python3
"""
Test if the agent actually calls tools for stock price queries
"""
import os
import uuid
from dotenv import load_dotenv, find_dotenv

# Load environment
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
load_dotenv(find_dotenv(usecwd=True), override=True)

# Enable live data
os.environ["USE_LIVE_DATA"] = "true"
os.environ["STOCK_DATA_SOURCE"] = "auto"

from agent_factory import AgentFactory

def test_agent_tool_calls():
    """Test if agent calls get_stock_price tool"""
    
    print("=" * 80)
    print("TESTING AGENT TOOL USAGE")
    print("=" * 80)
    
    # Initialize agent
    print("\n🔧 Initializing agent...")
    factory = AgentFactory()
    agent = factory.create_agent(
        domain="finance",
        framework="LangGraph",
        session_id=f"tool-test-{uuid.uuid4().hex[:8]}"
    )
    print("✓ Agent initialized")
    print(f"✓ Agent has {len(agent.tools)} tools loaded")
    
    # Print tool names
    print("\nTools available:")
    for tool in agent.tools:
        print(f"  - {tool.name}")
    
    # Test queries
    test_queries = [
        "What's the price of AAPL?",
        "What is the current price of TSLA?",
        "How much is NVDA?",
        "Get me the price of GOOGL",
    ]
    
    print("\n" + "=" * 80)
    print("TESTING QUERIES")
    print("=" * 80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Test {i}: {query}")
        print(f"{'=' * 80}")
        
        messages = [{"role": "user", "content": query}]
        
        print(f"\nProcessing...")
        response = agent.process_query(messages)
        
        print(f"\nAgent Response:")
        print(f"{response}")
        
        # Check if tool was likely called
        if "get_stock_price" in str(response).lower() or "$" in response or "price" in response.lower():
            # Check if response has structured data (indicates tool was called)
            if any(word in response for word in ["volume", "change", "high", "low", "open"]):
                print("\n✓ LIKELY USED TOOL (response has detailed market data)")
            else:
                print("\n? UNCLEAR - may have used RAG or tool")
        else:
            print("\n✗ LIKELY DID NOT USE TOOL")
        
        print("-" * 80)
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\n💡 To verify tool usage:")
    print("   1. Check Galileo Console traces")
    print("   2. Look for 'Get Stock Price' tool spans")
    print("   3. Check tool call metadata")
    print()

if __name__ == "__main__":
    test_agent_tool_calls()

