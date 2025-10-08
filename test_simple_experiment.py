#!/usr/bin/env python3
"""
Simple test to verify run_experiment works with basic function
"""
import os
from dotenv import load_dotenv, find_dotenv
from galileo.experiments import run_experiment
from galileo.schema.metrics import GalileoScorers

# Load environment
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
load_dotenv(find_dotenv(usecwd=True), override=True)

PROJECT_NAME = os.getenv("GALILEO_PROJECT", "finance-agent-experiments")

def simple_function(input: str) -> str:
    """Simple function that just echoes back with a prefix"""
    output = f"RESPONSE TO: {input}"
    print(f"  Input: {input}")
    print(f"  Output: {output}")
    return output

def main():
    print("=" * 80)
    print("🧪 SIMPLE EXPERIMENT TEST")
    print("=" * 80)
    
    # Simple dataset
    dataset = [
        {"input": "Test query 1", "output": "Expected response 1"},
        {"input": "Test query 2", "output": "Expected response 2"},
    ]
    
    print(f"\n📊 Dataset: {len(dataset)} rows")
    
    # Run experiment
    print(f"\n🚀 Running experiment with simple function...")
    results = run_experiment(
        experiment_name="simple-test",
        dataset=dataset,
        function=simple_function,
        metrics=[GalileoScorers.completeness],
        project=PROJECT_NAME,
    )
    
    print(f"\n✅ Complete!")
    print(f"Results: {results}")
    print(f"\n📋 Check Galileo Console:")
    print(f"   - Experiment: simple-test")
    print(f"   - Should show {len(dataset)} rows")
    print(f"   - Each row should have output: 'RESPONSE TO: ...'")
    print()

if __name__ == "__main__":
    main()

