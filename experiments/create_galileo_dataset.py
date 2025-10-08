#!/usr/bin/env python3
"""
Script to create a Galileo dataset from a domain's dataset.csv file.

Usage:
    python create_galileo_dataset.py <domain_name>
    
Example:
    python create_galileo_dataset.py finance
"""

import sys
import os
import csv
import argparse

# Add parent directory to path to import domain_manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from galileo.datasets import create_dataset
from domain_manager import DomainManager
from setup_env import setup_environment


def read_dataset_csv(dataset_file: str):
    """Read the dataset.csv file and return list of input/output pairs."""
    dataset = []
    with open(dataset_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'input' in row and 'output' in row:
                dataset.append({
                    'input': row['input'].strip(),
                    'output': row['output'].strip()
                })
    return dataset


def main():
    # Setup environment (load API keys)
    setup_environment()
    
    parser = argparse.ArgumentParser(description="Create Galileo dataset from domain CSV")
    parser.add_argument("domain", help="Domain name (e.g., 'finance')")
    parser.add_argument("--preview", "-p", action="store_true", help="Preview the dataset without creating")
    
    args = parser.parse_args()
    
    # Use DomainManager to load domain config
    dm = DomainManager()
    
    try:
        domain_config = dm.load_domain_config(args.domain)
    except ValueError as e:
        print(f"Error: {e}")
        print("Available domains:", dm.list_domains())
        sys.exit(1)
    
    # Read dataset
    dataset = read_dataset_csv(domain_config.dataset_file)
    
    if not dataset:
        print("No data found in dataset.csv")
        sys.exit(1)
    
    if args.preview:
        print(f"Found {len(dataset)} samples")
        for i, sample in enumerate(dataset[:3]):
            print(f"\nSample {i+1}:")
            print(f"Input: {sample['input']}")
            print(f"Output: {sample['output'][:100]}...")
        return
    
    # Create Galileo dataset
    dataset_name = f"{args.domain.title()} Domain Dataset"
    dataset_obj = create_dataset(name=dataset_name, content=dataset)
    
    print(f"Dataset created: {dataset_name}")
    print(f"ID: {dataset_obj.id}")


if __name__ == "__main__":
    main()