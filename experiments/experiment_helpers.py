"""
Helper functions for running experiments from both CLI and UI.
"""
import os
import csv
from typing import List, Dict, Any, Optional
from galileo.experiments import run_experiment
from galileo.datasets import get_dataset, create_dataset, list_datasets
from galileo.schema.metrics import GalileoScorers
from galileo import galileo_context
from galileo.handlers.langchain import GalileoCallback


# Default metrics for experiments
DEFAULT_METRICS = [
    GalileoScorers.ground_truth_adherence,
    GalileoScorers.prompt_injection,
    GalileoScorers.chunk_attribution_utilization,
    GalileoScorers.context_adherence
]

# Metric display names and their corresponding GalileoScorers
AVAILABLE_METRICS = {
    "Ground Truth Adherence": GalileoScorers.ground_truth_adherence,
    "Prompt Injection": GalileoScorers.prompt_injection,
    "Chunk Attribution Utilization": GalileoScorers.chunk_attribution_utilization,
    "Context Adherence": GalileoScorers.context_adherence,
}


def read_dataset_csv(dataset_file: str) -> List[Dict[str, str]]:
    """
    Read a CSV file and return list of input/output pairs.
    
    Args:
        dataset_file: Path to the CSV file
        
    Returns:
        List of dictionaries with 'input' and 'output' keys
    """
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


def create_domain_dataset(domain_name: str, dataset_file: str, custom_name: Optional[str] = None) -> Any:
    """
    Create a Galileo dataset from a domain's CSV file.
    
    Args:
        domain_name: Name of the domain
        dataset_file: Path to the dataset CSV file
        custom_name: Optional custom name for the dataset (defaults to domain dataset name)
        
    Returns:
        Created dataset object
    """
    dataset_content = read_dataset_csv(dataset_file)
    
    if not dataset_content:
        raise ValueError("No data found in dataset file")
    
    dataset_name = custom_name if custom_name else get_domain_dataset_name(domain_name)
    return create_dataset(name=dataset_name, content=dataset_content)


def get_domain_dataset_name(domain_name: str) -> str:
    """Get the standardized dataset name for a domain."""
    return f"{domain_name.title()} Domain Dataset"


def get_dataset_by_name(name: str) -> Any:
    """
    Get a dataset by name.
    
    Args:
        name: Dataset name
        
    Returns:
        Dataset object
    """
    return get_dataset(name=name)


def get_dataset_by_id(dataset_id: str) -> Any:
    """
    Get a dataset by ID.
    
    Args:
        dataset_id: Dataset ID
        
    Returns:
        Dataset object
    """
    return get_dataset(id=dataset_id)


def get_all_datasets() -> List[Any]:
    """
    Get all available datasets.
    
    Returns:
        List of dataset objects
    """
    return list_datasets()


def create_experiment_function(domain_name: str, agent_factory):
    """
    Create a function that can be used in experiments.
    This function will use the existing agent from AgentFactory.
    
    Args:
        domain_name: Name of the domain
        agent_factory: AgentFactory instance
        
    Returns:
        Function that can be called for each experiment row
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


def run_domain_experiment(
    domain_name: str,
    experiment_name: str,
    dataset: Any,
    agent_factory,
    metrics: Optional[List] = None,
    project: Optional[str] = None
) -> Any:
    """
    Run an experiment for a domain.
    
    Args:
        domain_name: Name of the domain
        experiment_name: Name for the experiment
        dataset: Dataset object to use
        agent_factory: AgentFactory instance
        metrics: List of metrics to evaluate (defaults to DEFAULT_METRICS)
        project: Galileo project name (defaults to GALILEO_PROJECT env var)
        
    Returns:
        Experiment results
    """
    if metrics is None:
        metrics = DEFAULT_METRICS
    
    if project is None:
        project = os.environ.get("GALILEO_PROJECT", "default")
    
    # Create the experiment function
    experiment_function = create_experiment_function(domain_name, agent_factory)
    
    # Run the experiment
    results = run_experiment(
        experiment_name,
        dataset=dataset,
        function=experiment_function,
        metrics=metrics,
        project=project
    )
    
    return results

