#!/usr/bin/env python3
"""
Verify Experiment Flow

This script runs a small experiment and verifies that:
1. Each dataset row triggers a complete agent run
2. Agent outputs are captured and returned for evaluation
3. Multiple runs are visible in Galileo Console
"""
import os
from dotenv import load_dotenv, find_dotenv
from run_experiment import run_with_custom_dataset

# Load environment
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
load_dotenv(find_dotenv(usecwd=True), override=True)

def main():
    """Run a small test experiment to verify the flow"""
    
    print("=" * 80)
    print("🔍 EXPERIMENT FLOW VERIFICATION")
    print("=" * 80)
    
    # Create a small test dataset (3 queries)
    test_data = [
        {
            "input": "What was Costco's revenue for Q3 2024?",
            "output": "Costco reported net sales of $62.15 billion for Q3 2024.",
        },
        {
            "input": "How is the S&P 500 performing this year?",
            "output": "The S&P 500 has shown strong performance in 2024.",
        },
        {
            "input": "Can you explain what a 10-Q filing is?",
            "output": "A 10-Q is a quarterly report filed by public companies with the SEC.",
        }
    ]
    
    print(f"\n📊 Test Dataset:")
    print(f"   - {len(test_data)} queries")
    print(f"   - Each should trigger a complete agent run")
    print(f"   - Each agent output should be evaluated\n")
    
    for i, row in enumerate(test_data, 1):
        print(f"   {i}. {row['input'][:60]}...")
    
    print("\n" + "-" * 80)
    input("\nPress ENTER to run the experiment...")
    print("-" * 80)
    
    # Run experiment
    experiment_name = "verification-test"
    print(f"\n🚀 Running experiment: {experiment_name}\n")
    
    results = run_with_custom_dataset(
        experiment_name=experiment_name,
        data=test_data
    )
    
    # Verify results
    print("\n" + "=" * 80)
    print("✅ VERIFICATION RESULTS")
    print("=" * 80)
    
    print(f"\n1. Number of rows processed: {len(results) if results else 0}")
    print(f"   Expected: {len(test_data)}")
    print(f"   Status: {'✓ PASS' if len(results) == len(test_data) else '✗ FAIL'}")
    
    print(f"\n2. Results returned: {'Yes' if results else 'No'}")
    print(f"   Status: {'✓ PASS' if results else '✗ FAIL'}")
    
    if results and len(results) > 0:
        print(f"\n3. Sample result structure:")
        print(f"   Type: {type(results[0])}")
        if isinstance(results[0], dict):
            print(f"   Keys: {list(results[0].keys())}")
    
    print(f"\n{'=' * 80}")
    print("📋 NEXT STEPS:")
    print("=" * 80)
    print("\n1. Check Galileo Console:")
    print(f"   - URL: https://console.galileo.ai")
    print(f"   - Look for experiment: '{experiment_name}'")
    print(f"   - You should see {len(test_data)} separate runs")
    
    print(f"\n2. Verify in Console:")
    print(f"   - Each run should show:")
    print(f"     • Input query from dataset")
    print(f"     • Agent's generated output") 
    print(f"     • Tool calls (if any)")
    print(f"     • RAG retrievals (if any)")
    print(f"     • Metric scores")
    
    print(f"\n3. Check Traces:")
    print(f"   - Navigate to Traces tab")
    print(f"   - You should see {len(test_data)} traces")
    print(f"   - Each trace shows complete agent execution")
    
    print("\n" + "=" * 80)
    print()


if __name__ == "__main__":
    main()

