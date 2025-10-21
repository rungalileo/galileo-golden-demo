# Running Galileo Experiments

This guide explains how to run Galileo experiments programmatically with your agent application.

## Overview

The experiment setup allows you to:
- 📊 Create synthetic datasets via Galileo API
- 🧪 Run experiments programmatically through your agent
- 📈 Evaluate performance with Galileo's built-in metrics
- 🔍 Track all traces and spans in Galileo Console

## Prerequisites

1. **Galileo API Key**: Set in `.streamlit/secrets.toml` or environment variables
2. **OpenAI API Key**: Required for agent and synthetic data generation
3. **Agent Setup**: Domain configured and vector database initialized

## Quick Start

### Option 1: Use Existing Synthetic Dataset from Galileo

```python
from run_experiment import run_with_synthetic_dataset

# Run experiment with a dataset you've already created in Galileo
results = run_with_synthetic_dataset(
    experiment_name="finance-agent-eval-v1",
    dataset_name="finance-queries-synthetic"  # Your dataset name from Galileo
)
```

### Option 2: Use Inline Dataset for Quick Testing

```python
from run_experiment import run_with_custom_dataset

# Define your test data
test_data = [
    {
        "input": "What was Costco's revenue for Q3 2024?",
        "output": "Expected answer here...",  # Optional: for correctness metrics
        "context": "Financial context..."      # Optional: for context adherence
    },
    # ... more test cases
]

results = run_with_custom_dataset(
    experiment_name="finance-agent-quick-test",
    data=test_data
)
```

## Creating Synthetic Datasets

### Method 1: Using Galileo MCP Tool (Recommended in IDE)

The easiest way is to ask your AI assistant to create a dataset:

```
"Create a Galileo synthetic dataset with 30 finance-related queries"
```

The MCP tool will guide you through:
- Dataset name and description
- Number of samples (1-100)
- Model selection (e.g., gpt-4o-mini)
- Data types (General Query, Off-Topic, Toxic, etc.)
- Sample data for guidance

### Method 2: Using Galileo Console

1. Go to https://console.galileo.ai/datasets
2. Click "Create Dataset"
3. Choose "Synthetic Data Generation"
4. Configure:
   - Name: `finance-agent-eval-dataset`
   - Description: What your dataset tests
   - Model: `gpt-4o-mini` or `gpt-4`
   - Count: 20-50 samples
   - Data Types: Select relevant types
   - Sample Data: Provide example queries
5. Wait for generation to complete
6. Note the dataset name for use in experiments

### Method 3: Using Python SDK

```python
from galileo.datasets import create_dataset

# Create from CSV
dataset = create_dataset(
    name="finance-queries",
    file_path="domains/finance/dataset.csv"
)

# Or create synthetic
# (See Galileo SDK docs for synthetic generation)
```

## Dataset Format

Your dataset should include these fields:

### Required Fields
- `input`: The user query/prompt to process

### Optional Fields (enhance metrics)
- `output`: Expected/ground truth answer (enables correctness metrics)
- `context`: Relevant context (enables context adherence metrics)
- `expected_output`: Alternative name for expected answer
- `metadata`: Additional information

### Example CSV Format

```csv
input,output,context
"What was Costco's Q3 2024 revenue?","$62.15 billion","From 10-Q filing"
"How is S&P 500 performing?","Strong performance in 2024","Market data"
```

## Running Experiments

### Basic Experiment Run

```bash
# Edit run_experiment.py to configure your dataset
python run_experiment.py
```

### Advanced Configuration

```python
from run_experiment import run_galileo_experiment
from galileo.schema.metrics import GalileoScorers, LocalMetricConfig

# Custom metrics
def custom_metric(step):
    # Your custom evaluation logic
    return score

custom_scorer = LocalMetricConfig(
    name="CustomMetric",
    scorer_fn=custom_metric,
    aggregator_fn=lambda scores: sum(scores) / len(scores)
)

# Run with custom metrics
results = run_galileo_experiment(
    experiment_name="finance-eval-with-custom-metrics",
    dataset_name="my-dataset",
    metrics=[
        GalileoScorers.context_adherence_plus,
        GalileoScorers.completeness,
        GalileoScorers.correctness,
        custom_scorer
    ]
)
```

## Available Metrics

Galileo provides built-in scorers:

- `context_adherence_plus`: How well response adheres to provided context
- `completeness`: Coverage of the query requirements
- `correctness`: Accuracy compared to expected output
- `toxicity`: Detection of harmful content
- `chunk_attribution_utilization_precision`: RAG retrieval quality
- `faithfulness`: Factual consistency with context
- `prompt_injection`: Security risk detection

## Experiment Workflow

```mermaid
graph LR
    A[Create/Fetch Dataset] --> B[Initialize Agent]
    B --> C[Run Experiment]
    C --> D[Process Each Row]
    D --> E[Evaluate Metrics]
    E --> F[View in Console]
```

### Step-by-Step

1. **Create Dataset**
   ```bash
   python create_synthetic_dataset.py
   # Then create via MCP tool or Console
   ```

2. **Configure Experiment**
   ```python
   # Edit run_experiment.py
   DOMAIN = "finance"  # Your domain
   FRAMEWORK = "LangGraph"  # Your framework
   ```

3. **Run Experiment**
   ```bash
   python run_experiment.py
   ```

4. **View Results**
   - Galileo Console: https://console.galileo.ai
   - Navigate to your project
   - Find your experiment by name
   - Analyze metrics and traces

## Integration with Existing App

The experiment runner uses your existing agent infrastructure:

```python
# Your agent is automatically initialized from AgentFactory
agent = factory.create_agent(
    domain=DOMAIN,
    framework=FRAMEWORK,
    session_id="experiment-session"
)

# Each dataset row is processed through your agent
@log(span_type="workflow", name="Agent Query Processing")
def run_agent_query(input: str, agent) -> str:
    messages = [{"role": "user", "content": input}]
    response = agent.process_query(messages)
    return response
```

## Troubleshooting

### Dataset Not Found
- Verify dataset name matches exactly (case-sensitive)
- Check it's in the correct Galileo project
- Try using dataset ID instead: `get_dataset(id="dataset-id")`

### Agent Initialization Errors
- Ensure domain configuration is correct
- Check vector database is set up: `python helpers/setup_vectordb.py finance`
- Verify API keys are configured

### Missing Metrics
- Some metrics require specific fields:
  - `correctness` needs `output` or `expected_output`
  - `context_adherence_plus` needs `context`
- Check your dataset includes necessary fields

### Experiment Not Appearing in Console
- Verify `GALILEO_PROJECT` matches your Console project
- Check API key has write permissions
- Look for error messages in console output

## Best Practices

1. **Start Small**: Test with 5-10 samples before scaling
2. **Use Descriptive Names**: Include version/date in experiment names
3. **Include Context**: Add `context` field for better metric evaluation
4. **Iterate**: Run multiple experiments to track improvements
5. **Document**: Note what each experiment tests in the name/description

## Examples

### Example 1: Baseline Evaluation
```python
results = run_with_synthetic_dataset(
    experiment_name="finance-agent-baseline-2024-10-08",
    dataset_name="finance-queries-general"
)
```

### Example 2: Prompt Variation Testing
```python
# Modify system prompt in domains/finance/system_prompt.json
# Then run experiment
results = run_with_synthetic_dataset(
    experiment_name="finance-agent-prompt-v2-test",
    dataset_name="finance-queries-general"
)
```

### Example 3: RAG Evaluation
```python
# Dataset with context field for RAG testing
results = run_with_synthetic_dataset(
    experiment_name="finance-agent-rag-eval",
    dataset_name="finance-queries-with-context"
)
```

## Next Steps

1. Create your first synthetic dataset (use MCP tool or Console)
2. Run a baseline experiment with `run_experiment.py`
3. Analyze results in Galileo Console
4. Iterate on prompts/agent configuration
5. Run comparative experiments

## Resources

- [Galileo Experiments Docs](https://v2docs.galileo.ai/sdk-api/experiments)
- [Galileo Datasets Docs](https://v2docs.galileo.ai/sdk-api/experiments/datasets)
- [Galileo Console](https://console.galileo.ai)

