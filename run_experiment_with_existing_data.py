#!/usr/bin/env python3
"""
Run Experiment with Existing CSV Dataset

This script demonstrates how to use your existing dataset.csv file
to run experiments without creating synthetic data.
"""
import os
import pandas as pd
from dotenv import load_dotenv, find_dotenv
from run_experiment import run_with_custom_dataset

# Load environment variables
# 1) load global/shared first
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
# 2) then load per-app .env (if present) to override selectively
load_dotenv(find_dotenv(usecwd=True), override=True)

# Configuration
DOMAIN = "finance"
DATASET_PATH = f"domains/{DOMAIN}/dataset.csv"


def load_existing_dataset(csv_path: str):
    """
    Load dataset from CSV file
    
    The CSV should have columns:
    - input: User query (required)
    - output: Expected answer (optional, enables correctness metrics)
    - context: Relevant context (optional, enables context adherence)
    """
    print(f"📂 Loading dataset from: {csv_path}")
    
    # Read CSV
    df = pd.read_csv(csv_path)
    
    print(f"✓ Loaded {len(df)} rows")
    print(f"📋 Columns: {', '.join(df.columns.tolist())}")
    
    # Convert to list of dicts
    dataset = df.to_dict('records')
    
    # Show sample
    if dataset:
        print(f"\n📝 Sample row:")
        sample = dataset[0]
        for key, value in sample.items():
            preview = str(value)[:80] + "..." if len(str(value)) > 80 else str(value)
            print(f"   {key}: {preview}")
    
    return dataset


def run_experiment_with_csv(
    csv_path: str,
    experiment_name: str,
    limit: int = None
):
    """
    Run experiment with CSV dataset
    
    Args:
        csv_path: Path to CSV file
        experiment_name: Name for the experiment
        limit: Optional limit on number of rows to process
    """
    print("\n" + "=" * 80)
    print("🧪 Running Experiment with CSV Dataset")
    print("=" * 80 + "\n")
    
    # Load dataset
    dataset = load_existing_dataset(csv_path)
    
    # Limit rows if specified
    if limit and limit < len(dataset):
        print(f"\n⚠️  Limiting to first {limit} rows for testing")
        dataset = dataset[:limit]
    
    print(f"\n📊 Processing {len(dataset)} rows through agent...\n")
    
    # Run experiment
    results = run_with_custom_dataset(
        experiment_name=experiment_name,
        data=dataset
    )
    
    print("\n" + "=" * 80)
    print("✅ Experiment Complete!")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run experiment with existing CSV dataset"
    )
    parser.add_argument(
        '--csv',
        default=DATASET_PATH,
        help=f'Path to CSV file (default: {DATASET_PATH})'
    )
    parser.add_argument(
        '--experiment',
        default='finance-csv-baseline',
        help='Experiment name (default: finance-csv-baseline)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of rows to process (for testing)'
    )
    
    args = parser.parse_args()
    
    # Check file exists
    if not os.path.exists(args.csv):
        print(f"❌ Error: File not found: {args.csv}")
        print(f"\nMake sure the dataset file exists at the specified path.")
        exit(1)
    
    # Run experiment
    results = run_experiment_with_csv(
        csv_path=args.csv,
        experiment_name=args.experiment,
        limit=args.limit
    )
    
    print(f"\n📊 Results Summary:")
    print(f"   Total rows: {len(results)}")
    print(f"\n🔗 View in Galileo Console: https://console.galileo.ai")
    print(f"   Look for experiment: {args.experiment}\n")


