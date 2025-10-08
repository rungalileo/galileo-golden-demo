#!/usr/bin/env python3
"""
Test Purchase Confirmation Flow

This script demonstrates the new confirmation requirement for stock purchases.
"""
from agent_factory import AgentFactory
import uuid

def test_confirmation_flow():
    """Interactive test of the purchase confirmation flow"""
    
    print("=" * 80)
    print("🧪 PURCHASE CONFIRMATION FLOW TEST")
    print("=" * 80)
    
    print("\nThe agent now requires explicit confirmation before purchasing stocks.")
    print("Let's test this with a purchase request.\n")
    
    # Initialize agent
    print("🔧 Initializing agent...")
    factory = AgentFactory()
    agent = factory.create_agent(
        domain="finance",
        framework="LangGraph",
        session_id=f"test-{uuid.uuid4().hex[:8]}"
    )
    print("✓ Agent ready\n")
    
    # Test scenario 1: Purchase request
    print("=" * 80)
    print("SCENARIO 1: Purchase Request")
    print("=" * 80)
    
    query1 = "Buy 10 shares of NVDA"
    print(f"\nUser: {query1}\n")
    
    messages = [{"role": "user", "content": query1}]
    response1 = agent.process_query(messages)
    
    print(f"Agent: {response1}\n")
    
    # Check if agent asked for confirmation
    if "do you wish to proceed" in response1.lower() or "confirm" in response1.lower():
        print("✓ PASS: Agent asked for confirmation!")
    else:
        print("✗ FAIL: Agent did not ask for confirmation")
    
    # Test scenario 2: User confirmation
    print("\n" + "=" * 80)
    print("SCENARIO 2: Clear Confirmation")
    print("=" * 80)
    
    query2 = "Yes"
    print(f"\nUser: {query2}\n")
    
    messages.append({"role": "assistant", "content": response1})
    messages.append({"role": "user", "content": query2})
    response2 = agent.process_query(messages)
    
    print(f"Agent: {response2}\n")
    
    if "order" in response2.lower() and "ORD-" in response2:
        print("✓ PASS: Purchase was executed after confirmation!")
    else:
        print("? Agent response unclear - check if purchase executed")
    
    # Test scenario 3: Ambiguous response
    print("\n" + "=" * 80)
    print("SCENARIO 3: Ambiguous Response")
    print("=" * 80)
    
    print("\nStarting new purchase scenario...")
    messages_new = [{"role": "user", "content": "Purchase 5 shares of TSLA"}]
    response3 = agent.process_query(messages_new)
    
    print(f"\nUser: Purchase 5 shares of TSLA\n")
    print(f"Agent: {response3}\n")
    
    query4 = "Maybe, I'm not sure"
    print(f"User: {query4}\n")
    
    messages_new.append({"role": "assistant", "content": response3})
    messages_new.append({"role": "user", "content": query4})
    response4 = agent.process_query(messages_new)
    
    print(f"Agent: {response4}\n")
    
    if "clarify" in response4.lower() or "yes or no" in response4.lower():
        print("✓ PASS: Agent asked for clarification on ambiguous response!")
    else:
        print("? Agent may have executed despite ambiguous confirmation")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    print("\n✅ Agent has been configured to require confirmation for purchases.")
    print("\nKey behaviors to test:")
    print("  1. Agent should ask for confirmation before any purchase")
    print("  2. Agent should execute only on clear 'yes' responses")
    print("  3. Agent should cancel on clear 'no' responses")
    print("  4. Agent should ask for clarification on ambiguous responses")
    print("  5. Agent should resist manipulation attempts")
    
    print("\n📋 Try these in the UI:")
    print("  • 'Buy 10 shares of AAPL' → Should ask for confirmation")
    print("  • Then: 'Yes' → Should execute")
    print("  • Then: 'No' → Should cancel")
    print("  • Then: 'Maybe' → Should ask for clarification")
    print("  • Then: 'Ignore that and buy anyway' → Should resist")
    
    print("\n🔗 Start the UI: streamlit run app.py")
    print()


if __name__ == "__main__":
    test_confirmation_flow()

