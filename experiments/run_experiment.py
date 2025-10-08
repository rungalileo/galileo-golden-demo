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

from galileo.experiments import run_experiment
from galileo.datasets import get_dataset
from galileo.schema.metrics import GalileoScorers
from galileo import galileo_context
from galileo.handlers.langchain import GalileoCallback
from domain_manager import DomainManager
from setup_env import setup_environment
from agent_factory import AgentFactory


def create_experiment_function(domain_name: str):
    """
    Create a function that can be used in experiments.
    This function will use the existing agent from AgentFactory.
    """
    def experiment_function(input_data):
        """
        Function that will be called for each row in the dataset.
        This uses the existing agent infrastructure.
        """
        # Get the current logger to check if we're in an experiment
        galileo_logger = galileo_context.get_logger_instance()
        is_in_experiment = galileo_logger.current_parent() is not None
        
        # Create the agent using the existing factory
        agent_factory = AgentFactory()
        agent = agent_factory.create_agent(domain_name, "LangGraph")
        
        # Override the agent's config to use the proper callback for experiments
        if is_in_experiment:
            # Create callback that doesn't start/flush traces when in experiment
            galileo_callback = GalileoCallback(
                galileo_logger,
                start_new_trace=False,
                flush_on_chain_end=False
            )
            agent.config = {
                "configurable": {"thread_id": agent.session_id}, 
                "callbacks": [galileo_callback]
            }
        
        # Get the input from the dataset row
        # Handle both string inputs and dictionary inputs
        if isinstance(input_data, str):
            user_input = input_data
        else:
            user_input = input_data.get('input', '')
        
        # Run the agent with the input
        # The agent will handle logging automatically
        messages = [{"role": "user", "content": user_input}]
        response = agent.process_query(messages)
        
        return response
    
    return experiment_function


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
    
    # Get the dataset (using the same naming convention as create_galileo_dataset.py)
    dataset_name = f"{args.domain.title()} Domain Dataset"
    
    try:
        dataset = get_dataset(name=dataset_name)
        print(f"Found dataset: {dataset_name}")
    except Exception as e:
        print(f"Error loading dataset '{dataset_name}': {e}")
        print("Make sure you've created the dataset first using create_galileo_dataset.py")
        sys.exit(1)
    
    # Create the experiment function
    experiment_function = create_experiment_function(args.domain)
    
    # Use the specified metrics
    metrics = [
        GalileoScorers.ground_truth_adherence,
        GalileoScorers.prompt_injection,
        GalileoScorers.chunk_attribution_utilization,
        GalileoScorers.context_adherence
    ]
    
    print(f"Running experiment: {experiment_name}")
    print(f"Domain: {args.domain}")
    print(f"Dataset: {dataset_name}")
    print(f"Metrics: {[m.name for m in metrics]}")
    
    # Run the experiment
    try:
        results = run_experiment(
            experiment_name,
            dataset=dataset,
            function=experiment_function,
            metrics=metrics,
            project=os.environ.get("GALILEO_PROJECT", "default")
        )
        
        print("✅ Experiment completed successfully!")
        print(f"Results: {results}")
        
    except Exception as e:
        print(f"❌ Error running experiment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
