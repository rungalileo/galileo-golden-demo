"""
Integration tests that run Galileo experiments end-to-end against the
domain agents and assert on aggregate metric scores.

These tests are intentionally marked as ``integration`` because they:
  * Hit real LLM, RAG, and Galileo APIs.
  * Take minutes (LLM calls + server-side metric scoring + polling).
  * Cost real money per run.

Run locally with:
    pytest experiments/test_experiments.py -m integration -s

Run a single domain:
    pytest experiments/test_experiments.py -m integration -k finance -s

Skipped by default unless ``-m integration`` is passed (see pytest.ini).
"""
import os
import sys
import uuid

import pytest

# Allow ``pytest experiments/`` to resolve top-level demo modules.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_factory import AgentFactory
from domain_manager import DomainManager
from setup_env import setup_environment
from galileo import GalileoMetrics

from experiments.experiment_helpers import (
    DEFAULT_METRICS,
    _experiment_name_from_response,
    create_domain_dataset,
    get_dataset_by_name,
    get_domain_dataset_name,
    lookup_metric_average,
    run_domain_experiment,
    wait_for_experiment_metrics,
)


# Per-metric pass thresholds (avg over all dataset rows). Must be a subset of
# DEFAULT_METRICS. Start conservative; tighten as agents stabilize.
DEFAULT_THRESHOLDS = {
    GalileoMetrics.context_adherence: 0.6,
    GalileoMetrics.ground_truth_adherence: 0.5,
}

DOMAINS_UNDER_TEST = ["finance", "healthcare", "ecommerce"]


def _ensure_dataset(domain_name: str, domain_config: dict):
    """Fetch the domain's Galileo dataset, creating it from the CSV if missing."""
    dataset_name = get_domain_dataset_name(domain_name)
    try:
        dataset = get_dataset_by_name(dataset_name)
        if dataset is not None:
            return dataset
    except Exception:
        pass

    # Fall back to creating from the domain's bundled dataset.csv
    dataset_file = os.path.join("domains", domain_name, "dataset.csv")
    if not os.path.exists(dataset_file):
        pytest.skip(f"No dataset in Galileo and no local CSV at {dataset_file}")
    return create_domain_dataset(domain_name, dataset_file)


@pytest.mark.integration
@pytest.mark.parametrize("domain", DOMAINS_UNDER_TEST)
def test_domain_experiment_meets_thresholds(domain):
    dm = DomainManager()
    domain_config = dm.load_domain_config(domain)

    setup_environment(domain, domain_config.config)

    dataset = _ensure_dataset(domain, domain_config.config)

    # Unique-ish name so re-runs don't collide; the SDK will still rewrite if needed.
    experiment_name = f"ci-{domain}-{uuid.uuid4().hex[:8]}"

    response = run_domain_experiment(
        domain_name=domain,
        experiment_name=experiment_name,
        dataset=dataset,
        agent_factory=AgentFactory(),
        metrics=DEFAULT_METRICS,
    )

    actual_name = _experiment_name_from_response(response)
    print(f"[{domain}] experiment running as: {actual_name}")

    experiment = wait_for_experiment_metrics(
        experiment_name=actual_name,
        metrics=DEFAULT_METRICS,
        timeout=480,
        interval=10,
    )

    failures = []
    for metric, threshold in DEFAULT_THRESHOLDS.items():
        avg = lookup_metric_average(experiment, metric)
        name = getattr(metric, "value", str(metric))
        if avg is None:
            failures.append(f"{name}: no aggregate returned")
            continue
        print(f"[{domain}] {name} avg={avg:.3f} (threshold>={threshold})")
        if avg < threshold:
            failures.append(f"{name}: avg={avg:.3f} < threshold={threshold}")

    assert not failures, f"[{domain}] metric threshold failures:\n  " + "\n  ".join(failures)
