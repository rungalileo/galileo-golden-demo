#!/usr/bin/env python3
"""
Script to run a Galileo experiment using a domain's dataset.

Usage:
    python run_experiment.py <domain_name>
    
Example:
    python run_experiment.py finance
"""

import sys
import os
import argparse

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from domain_manager import DomainManager
from setup_env import setup_environment
from agent_factory import AgentFactory
from experiments.experiment_helpers import (
    get_domain_dataset_name,
    get_dataset_by_name,
    run_domain_experiment,
    DEFAULT_METRICS
)


def main():
    # Setup environment (load API keys)
    setup_environment()
    
    parser = argparse.ArgumentParser(description="Run Galileo experiment for a domain")
    parser.add_argument("domain", help="Domain name (e.g., 'finance')")
    parser.add_argument("--experiment-name", help="Custom experiment name", default=None)
    
    args = parser.parse_args()
    
    # Use DomainManager to load domain config
    dm = DomainManager()
    
    try:
        domain_config = dm.load_domain_config(args.domain)
    except ValueError as e:
        print(f"Error: {e}")
        print("Available domains:", dm.list_domains())
        sys.exit(1)
    
    # Create experiment name
    experiment_name = args.experiment_name or f"{args.domain}-experiment"
    
    # Get the dataset
    dataset_name = get_domain_dataset_name(args.domain)
    
    try:
        dataset = get_dataset_by_name(dataset_name)
        print(f"Found dataset: {dataset_name}")
    except Exception as e:
        print(f"Error loading dataset '{dataset_name}': {e}")
        print("Make sure you've created the dataset first using create_galileo_dataset.py")
        sys.exit(1)
    
    # Create agent factory
    agent_factory = AgentFactory()
    
    print(f"Running experiment: {experiment_name}")
    print(f"Domain: {args.domain}")
    print(f"Dataset: {dataset_name}")
    print(f"Metrics: {[m.name for m in DEFAULT_METRICS]}")
    
    # Run the experiment
    try:
        results = run_domain_experiment(
            domain_name=args.domain,
            experiment_name=experiment_name,
            dataset=dataset,
            agent_factory=agent_factory,
            metrics=DEFAULT_METRICS
        )
        
        print("✅ Experiment completed successfully!")
        print(f"Results: {results}")
        
    except Exception as e:
        print(f"❌ Error running experiment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
