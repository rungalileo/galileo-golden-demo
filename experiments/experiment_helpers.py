"""
Helper functions for running experiments from both CLI and UI.
"""
import os
import csv
import time
from typing import List, Dict, Any, Optional
from galileo import Experiment, GalileoMetrics
from galileo.experiments import run_experiment
from galileo.datasets import get_dataset, create_dataset, list_datasets
from galileo_core.schemas.shared.scorers.scorer_name import ScorerName as GalileoScorers
from galileo import galileo_context
from galileo.handlers.langchain import GalileoCallback


# Default metrics submitted to run_experiment() AND read back when polling.
DEFAULT_METRICS = [
    GalileoMetrics.context_adherence,
    GalileoMetrics.ground_truth_adherence,
]

# Full set of metrics offered in the Streamlit UI's metric selector.
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


def create_experiment_function(
    domain_name: str,
    agent_factory,
    model_name: Optional[str] = None,
    llm_provider: str = "local",
):
    """
    Create a function that can be used in experiments.
    This function will use the existing agent from AgentFactory.
    
    Args:
        domain_name: Name of the domain
        agent_factory: AgentFactory instance
        model_name: Optional model override (e.g. from UI selector); uses domain default if None
        
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
        
        # Create the agent using the existing factory (with optional model override)
        agent = agent_factory.create_agent(
            domain_name,
            "LangGraph",
            model_name=model_name,
            llm_provider=llm_provider,
        )
        
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
    project: Optional[str] = None,
    model_name: Optional[str] = None,
    llm_provider: str = "local",
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
        model_name: Optional model override (e.g. from UI); uses domain default if None
        
    Returns:
        Experiment results
    """
    if metrics is None:
        metrics = DEFAULT_METRICS
    
    if project is None:
        project = os.environ.get("GALILEO_PROJECT", "default")
    
    # Create the experiment function (with optional model override)
    experiment_function = create_experiment_function(
        domain_name,
        agent_factory,
        model_name=model_name,
        llm_provider=llm_provider,
    )
    
    # Run the experiment. The SDK returns immediately; metric scoring continues
    # server-side, so callers that want metric values should follow up with
    # wait_for_experiment_metrics() using the returned experiment name.
    results = run_experiment(
        experiment_name,
        dataset=dataset,
        function=experiment_function,
        metrics=metrics,
        project=project
    )
    
    return results


def _metric_name(metric: Any) -> str:
    """Coerce a scorer enum / string / object into its canonical name for logging."""
    return getattr(metric, "value", None) or getattr(metric, "name", None) or str(metric)


# How to read the average for each metric:
#   - "aggregate_key": pass to experiment.get_metric_aggregate() (one HTTP call,
#     works for metrics whose UUID is populated in the metric_aggregates dict).
#   - "trace_field": page through experiment.get_traces() and average the
#     per-trace field `metrics_<trace_field>_multijudge_average` (needed for
#     boolean-style scorers like ground_truth_adherence and prompt_injection,
#     whose UUIDs aren't populated in the aggregate response — same path the
#     Galileo console uses to render True/False counts).
_METRIC_LOOKUP: Dict[Any, Dict[str, Any]] = {
    GalileoMetrics.context_adherence:             {"aggregate_key": GalileoMetrics.context_adherence},
    GalileoMetrics.chunk_attribution_utilization: {"aggregate_key": "retriever_utilization"},
    GalileoMetrics.ground_truth_adherence:        {"trace_field":   "ground_truth_adherence"},
    GalileoMetrics.prompt_injection:              {"trace_field":   "prompt_injection_gpt"},
}

_TRACE_PAGE_SIZE = 100


def _average_metric_from_traces(
    experiment: "Experiment", trace_field: str
) -> Optional[float]:
    """Average ``metrics_<trace_field>_multijudge_average`` across all traces."""
    column = f"metrics_{trace_field}_multijudge_average"
    total, count, token = 0.0, 0, 0
    while True:
        page = experiment.get_traces(limit=_TRACE_PAGE_SIZE, starting_token=token)
        rows = page.to_list()
        for row in rows:
            value = row.get(column)
            if value is not None:
                total += float(value)
                count += 1
        if not page.has_next_page:
            break
        token = page.next_starting_token
    return (total / count) if count else None


def lookup_metric_average(experiment: "Experiment", metric: Any) -> Optional[float]:
    """Return the average score for ``metric``, or ``None`` if not yet computed."""
    lookup = _METRIC_LOOKUP.get(metric)
    if lookup is None:
        # Unknown metric — best-effort: try the aggregate API directly.
        agg = experiment.get_metric_aggregate(metric)
        return agg.avg if agg is not None else None

    if "aggregate_key" in lookup:
        agg = experiment.get_metric_aggregate(lookup["aggregate_key"])
        return agg.avg if agg is not None else None

    return _average_metric_from_traces(experiment, lookup["trace_field"])


def _experiment_name_from_response(experiment_response: Any) -> str:
    """
    Extract the actual experiment name from a run_experiment response.

    run_experiment may rewrite the name (appending a timestamp) when the
    requested name isn't unique, so the response is the source of truth.
    """
    try:
        return experiment_response["experiment"].name
    except (TypeError, KeyError, AttributeError):
        experiment = getattr(experiment_response, "experiment", None)
        if experiment is not None and hasattr(experiment, "name"):
            return experiment.name
        raise ValueError(
            "Could not determine experiment name from run_experiment response"
        )


def wait_for_experiment_metrics(
    experiment_name: str,
    metrics: List[Any],
    project: Optional[str] = None,
    timeout: float = 600.0,
    interval: float = 5.0,
) -> Any:
    """
    Poll Galileo until every metric in ``metrics`` has an aggregate value.

    Args:
        experiment_name: Exact experiment name returned by run_experiment.
        metrics: Metrics to wait on (same values passed to run_experiment).
        project: Project name; falls back to GALILEO_PROJECT.
        timeout: Max seconds to wait before raising TimeoutError.
        interval: Seconds between polls.

    Returns:
        The fully-scored ExperimentResponse.

    Raises:
        TimeoutError: If any metric is still uncomputed after ``timeout``.
    """
    if project is None:
        project = os.environ.get("GALILEO_PROJECT")

    start = time.time()
    deadline = start + timeout
    experiment = Experiment.get(name=experiment_name, project_name=project)
    iteration = 0

    while True:
        iteration += 1
        elapsed = int(time.time() - start)
        ready: Dict[str, float] = {}
        pending: List[str] = []
        for m in metrics:
            name = _metric_name(m)
            avg = lookup_metric_average(experiment, m)
            if avg is None:
                pending.append(name)
            else:
                ready[name] = avg

        ready_str = ", ".join(f"{k}={v:.3f}" for k, v in ready.items()) or "—"
        print(
            f"  [poll #{iteration} t={elapsed}s] ready: {ready_str} | pending: {pending or '—'}",
            flush=True,
        )

        if not pending:
            return experiment

        if time.time() >= deadline:
            available_columns = sorted(
                col.label for col in experiment.experiment_columns.values()
                if col.id.startswith("metrics/")
            )
            raise TimeoutError(
                f"Timed out after {timeout}s waiting for metrics: {pending}.\n"
                f"Ready metrics: {ready}\n"
                f"Metric columns registered for this experiment: {available_columns}\n"
                f"This usually means a boolean-style scorer (e.g. "
                f"ground_truth_adherence, prompt_injection) was requested — "
                f"those don't aggregate via the metrics API. Use ASSERTABLE_METRICS "
                f"for the wait list and check the console for boolean results."
            )

        time.sleep(interval)
        experiment.refresh()

