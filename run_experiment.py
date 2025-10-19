"""
Galileo Experiment Runner - Run experiments with synthetic datasets
"""
import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables FIRST (before any other imports)
# 1) load global/shared first
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
# 2) then load per-app .env (if present) to override selectively
load_dotenv(find_dotenv(usecwd=True), override=True)

# 3) Load from Streamlit secrets if available (for Streamlit integration)
try:
    from setup_env import setup_environment
    setup_environment()
    print("✅ Loaded environment from .streamlit/secrets.toml")
except Exception as e:
    print(f"⚠️  Could not load Streamlit secrets: {e}")
    print("   Falling back to .env variables")

# ============================================================================
# CRITICAL: Initialize OTLP tracing BEFORE importing LangChain or agent code
# This ensures Phoenix/Arize AX traces are captured during experiment runs
# ============================================================================
from tracing_setup import initialize_otlp_tracing
otlp_platform = initialize_otlp_tracing()
if otlp_platform != "none":
    print(f"✅ OTLP tracing enabled for experiments: {otlp_platform}")
else:
    print("⚠️  OTLP tracing not configured (traces will not go to Phoenix/Arize AX)")

# NOW import LangChain-dependent modules
from galileo.datasets import get_dataset
from galileo.experiments import run_experiment
from galileo.schema.metrics import GalileoScorers

# To see all available scorers, run: print(dir(GalileoScorers))
from galileo import galileo_context, log
from agent_factory import AgentFactory
from typing import Dict, Any, List

# Verify Galileo configuration
galileo_console_url = os.getenv("GALILEO_CONSOLE_URL")
galileo_api_key = os.getenv("GALILEO_API_KEY")

if not galileo_console_url:
    raise EnvironmentError(
        "GALILEO_CONSOLE_URL is not set! Please set it in one of:\n"
        "  1. .streamlit/secrets.toml (galileo_console_url = \"https://your-instance.galileo.ai\")\n"
        "  2. .env file (GALILEO_CONSOLE_URL=https://your-instance.galileo.ai)\n"
        "  3. Environment variable: export GALILEO_CONSOLE_URL=https://your-instance.galileo.ai"
    )

if not galileo_api_key:
    raise EnvironmentError(
        "GALILEO_API_KEY is not set! Please set it in one of:\n"
        "  1. .streamlit/secrets.toml (galileo_api_key = \"your-key\")\n"
        "  2. .env file (GALILEO_API_KEY=your-key)\n"
        "  3. Environment variable: export GALILEO_API_KEY=your-key"
    )

print(f"🔗 Galileo Console URL: {galileo_console_url}")
print(f"🔑 Galileo API Key: {'*' * 20}{galileo_api_key[-8:]}")

# Configuration
DOMAIN = "finance"
FRAMEWORK = "LangGraph"
PROJECT_NAME = os.getenv("GALILEO_PROJECT", "finance-agent-experiments")


def setup_agent():
    """Initialize the agent factory and create an agent instance"""
    factory = AgentFactory()
    agent = factory.create_agent(
        domain=DOMAIN,
        framework=FRAMEWORK,
        session_id="experiment-session"
    )
    return agent


@log(span_type="workflow", name="Agent Query Processing")
def run_agent_query(input: str, agent) -> str:
    """
    Run a single query through the agent with Galileo logging
    
    Args:
        input: The user query to process
        agent: The initialized agent instance
        
    Returns:
        The agent's response
    """
    # Convert input to message format expected by agent
    messages = [{"role": "user", "content": input}]
    
    # Process query through agent (this captures full LangGraph trace)
    response = agent.process_query(messages)
    
    print(f"  ✓ Query processed, output length: {len(response)} chars")
    print(f"  ✓ Output preview: {response[:100]}...")
    
    # Return the response - this will be used as the 'output' field for metrics
    return response


def run_galileo_experiment(
    experiment_name: str,
    dataset_name: str = None,
    dataset_id: str = None,
    inline_dataset: List[Dict] = None,
    metrics: List = None
):
    """
    Run a Galileo experiment with a dataset through the agent
    
    Args:
        experiment_name: Name for the experiment
        dataset_name: Name of dataset to fetch from Galileo (optional)
        dataset_id: ID of dataset to fetch from Galileo (optional)
        inline_dataset: Inline dataset as list of dicts (optional)
        metrics: List of metrics to evaluate (defaults to Galileo built-in scorers)
    """
    print(f"\n🧪 Starting experiment: {experiment_name}")
    print(f"📊 Domain: {DOMAIN}")
    print(f"🤖 Framework: {FRAMEWORK}")
    print(f"📁 Project: {PROJECT_NAME}\n")
    
    # Get dataset
    if dataset_name or dataset_id:
        print(f"📥 Fetching dataset from Galileo...")
        if dataset_name:
            dataset = get_dataset(name=dataset_name)
            print(f"✓ Loaded dataset: {dataset_name}")
        else:
            dataset = get_dataset(id=dataset_id)
            print(f"✓ Loaded dataset ID: {dataset_id}")
    elif inline_dataset:
        dataset = inline_dataset
        print(f"✓ Using inline dataset with {len(dataset)} rows")
    else:
        raise ValueError("Must provide either dataset_name, dataset_id, or inline_dataset")
    
    # Initialize agent
    print(f"\n🔧 Initializing {FRAMEWORK} agent for domain: {DOMAIN}")
    agent = setup_agent()
    print("✓ Agent initialized successfully")
    
    # Define metrics
    if metrics is None:
        metrics = [
            GalileoScorers.context_adherence,
            GalileoScorers.completeness,
            GalileoScorers.correctness,
            GalileoScorers.output_toxicity,
            GalileoScorers.chunk_attribution_utilization,
        ]
    
    print(f"\n📏 Using {len(metrics)} evaluation metrics")
    
    # Define the runner function - this is called once per dataset row
    def experiment_runner(input: str) -> str:
        """
        Function that processes each row in the dataset
        
        This function is called once per row in the dataset.
        Each call triggers a complete agent run with full tracing.
        The returned response is evaluated by Galileo metrics.
        
        Args:
            input: The input field from the dataset row
            
        Returns:
            Agent's response (will be used as 'output' for evaluation)
        """
        print(f"\n  Processing row: {input[:80]}...")
        
        # Run through agent - this creates a complete agent execution trace
        # The agent will use tools, RAG, etc. as needed
        agent_output = run_agent_query(input, agent)
        
        # IMPORTANT: This return value becomes the 'output' field for Galileo metrics
        # It will be compared against the 'output' field in the dataset row (if present)
        print(f"  ✓ Returning output for evaluation (length: {len(agent_output)})")
        
        return agent_output
    
    # Run the experiment
    print(f"\n🚀 Running experiment...")
    print("-" * 80)
    
    results = run_experiment(
        experiment_name=experiment_name,
        dataset=dataset,
        function=experiment_runner,
        metrics=metrics,
        project=PROJECT_NAME,
    )
    
    print("-" * 80)
    print(f"\n✅ Experiment completed successfully!")
    print(f"\n📊 Results summary:")
    print(f"   - Total rows processed: {len(results)}")
    print(f"   - Each row triggered a complete agent run")
    print(f"   - Agent outputs were captured for metric evaluation")
    print(f"\n💡 What happened:")
    print(f"   1. Loaded dataset with {len(results)} rows")
    print(f"   2. For each row:")
    print(f"      - Extracted 'input' field")
    print(f"      - Ran complete agent workflow (LangGraph + tools + RAG)")
    print(f"      - Captured agent output")
    print(f"      - Evaluated with {len(metrics) if metrics else 'default'} Galileo metrics")
    print(f"\n🔗 View detailed results in Galileo Console:")
    print(f"   Project: {PROJECT_NAME}")
    print(f"   Experiment: {experiment_name}")
    print(f"   URL: https://console.galileo.ai\n")
    
    return results


def run_with_synthetic_dataset(experiment_name: str, dataset_name: str):
    """
    Convenience function to run experiment with a synthetic dataset from Galileo
    
    Args:
        experiment_name: Name for the experiment
        dataset_name: Name of the synthetic dataset in Galileo
    """
    return run_galileo_experiment(
        experiment_name=experiment_name,
        dataset_name=dataset_name
    )


def run_with_custom_dataset(experiment_name: str, data: List[Dict]):
    """
    Convenience function to run experiment with an inline dataset
    
    Args:
        experiment_name: Name for the experiment
        data: List of dicts with 'input' field (and optionally 'output', 'context')
    """
    return run_galileo_experiment(
        experiment_name=experiment_name,
        inline_dataset=data
    )


if __name__ == "__main__":
    # Example 1: Run with a synthetic dataset from Galileo
    # First create a dataset in Galileo, then use its name here
    # run_with_synthetic_dataset(
    #     experiment_name="finance-agent-synthetic-eval-v1",
    #     dataset_name="finance-queries-synthetic"
    # )
    
    # Example 2: Run with an inline dataset for quick testing
    sample_data = [
        {
            "input": "What was Costco's revenue for Q3 2024?",
            "output": "Costco reported net sales of $62.15 billion for the third quarter of fiscal 2024.",
            "context": "Financial data from Costco's 10-Q filing"
        },
        {
            "input": "How is the S&P 500 performing this year?",
            "output": "Based on the latest data, the S&P 500 has shown strong performance in 2024.",
            "context": "S&P 500 market analysis"
        },
        {
            "input": "Should I invest in technology stocks right now?",
            "output": "I can provide information about technology sector trends, but I cannot give personalized investment advice.",
            "context": "General market information"
        }
    ]
    
    results = run_with_custom_dataset(
        experiment_name="finance-agent-baseline-test",
        data=sample_data
    )
    
    print("\n📝 Sample results:")
    for i, result in enumerate(results[:3], 1):
        print(f"\nRow {i}:")
        print(f"  Input: {sample_data[i-1]['input'][:60]}...")
        print(f"  Metrics: {list(result.keys())}")

