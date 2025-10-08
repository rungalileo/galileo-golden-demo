#!/usr/bin/env python3
"""
Diagnose Experiment Output Capture

This script helps diagnose whether agent outputs are being properly
captured and sent to Galileo experiments.
"""
import os
from dotenv import load_dotenv, find_dotenv
from galileo.datasets import get_dataset
from galileo.experiments import run_experiment
from galileo.schema.metrics import GalileoScorers
from agent_factory import AgentFactory

# Load environment
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
load_dotenv(find_dotenv(usecwd=True), override=True)

DOMAIN = "finance"
FRAMEWORK = "LangGraph"
PROJECT_NAME = os.getenv("GALILEO_PROJECT", "finance-agent-experiments")


def main():
    print("=" * 80)
    print("🔍 DIAGNOSING EXPERIMENT OUTPUT CAPTURE")
    print("=" * 80)
    
    # Create a minimal dataset
    test_dataset = [
        {
            "input": "What was Costco's Q3 2024 revenue?",
            "output": "Expected: Costco reported $62.15 billion in Q3 2024"
        }
    ]
    
    print(f"\n📊 Test Dataset:")
    print(f"   Input:  {test_dataset[0]['input']}")
    print(f"   Output: {test_dataset[0]['output']}")
    
    # Initialize agent
    print(f"\n🔧 Initializing agent...")
    factory = AgentFactory()
    agent = factory.create_agent(
        domain=DOMAIN,
        framework=FRAMEWORK,
        session_id="diagnostic-session"
    )
    print("   ✓ Agent initialized")
    
    # Define test function with detailed logging
    def diagnostic_runner(input: str) -> str:
        """Test runner with detailed logging - takes input string directly"""
        print(f"\n{'=' * 80}")
        print(f"PROCESSING INPUT")
        print(f"{'=' * 80}")
        print(f"Input received: {input}")
        print(f"Type: {type(input)}")
        
        # Run agent
        messages = [{"role": "user", "content": input}]
        print(f"\nCalling agent.process_query()...")
        agent_response = agent.process_query(messages)
        
        print(f"\n{'=' * 80}")
        print(f"AGENT RESPONSE")
        print(f"{'=' * 80}")
        print(f"Type: {type(agent_response)}")
        print(f"Length: {len(agent_response) if agent_response else 0}")
        print(f"Content: {agent_response[:200]}...")
        print(f"{'=' * 80}")
        
        print(f"\nReturning to Galileo experiments framework...")
        print(f"Return value type: {type(agent_response)}")
        print(f"Return value: '{agent_response[:100]}...'")
        
        return agent_response
    
    # Run experiment
    print(f"\n🚀 Running diagnostic experiment...")
    print(f"   Experiment: diagnostic-output-test")
    print(f"   Project: {PROJECT_NAME}")
    
    results = run_experiment(
        experiment_name="diagnostic-output-test",
        dataset=test_dataset,
        function=diagnostic_runner,
        metrics=[
            GalileoScorers.correctness,
            GalileoScorers.completeness,
        ],
        project=PROJECT_NAME,
    )
    
    print(f"\n{'=' * 80}")
    print(f"RESULTS")
    print(f"{'=' * 80}")
    print(f"Type: {type(results)}")
    print(f"Length: {len(results) if results else 0}")
    if results:
        print(f"First result: {results[0]}")
    print(f"{'=' * 80}")
    
    print(f"\n✅ Diagnostic complete!")
    print(f"\n📋 NEXT STEPS:")
    print(f"   1. Check Galileo Console:")
    print(f"      https://console.galileo.ai")
    print(f"      Project: {PROJECT_NAME}")
    print(f"      Experiment: diagnostic-output-test")
    print(f"\n   2. In the Console, verify:")
    print(f"      □ Experiment shows 1 row")
    print(f"      □ Input matches: '{test_dataset[0]['input']}'")
    print(f"      □ Output shows agent response (not empty)")
    print(f"      □ Metrics are calculated")
    print(f"\n   3. If output is empty in Console:")
    print(f"      - Check the logs above for the actual agent response")
    print(f"      - The issue is in how Galileo captures the return value")
    print(f"\n   4. If output is present but different:")
    print(f"      - Compare Console output to agent response above")
    print(f"      - Verify they match")
    print()


if __name__ == "__main__":
    main()

