# Galileo Experiments - UI & CLI Integration

This directory contains the experiment functionality for running Galileo experiments against your domain agents. Experiments can now be run from both the **Command Line** and the **Streamlit UI**.

## Overview

The experiments system allows you to:
- Create datasets from domain sample data or CSV uploads
- Select existing datasets from Galileo
- Run experiments with customizable metrics
- View results in the Galileo Console

## File Structure

```
experiments/
├── experiment_helpers.py      # Shared functions for both CLI and UI
├── run_experiment.py          # CLI script to run experiments
├── create_galileo_dataset.py  # CLI script to create datasets
└── README.md                  # This file
```

## Using the CLI

The CLI provides two separate scripts: one for dataset creation and one for running experiments.

### Step 1: Create a Dataset (One-Time Setup)

**Script:** `create_galileo_dataset.py`

```bash
# Preview the dataset before creating (shows first 3 rows)
python experiments/create_galileo_dataset.py finance --preview

# Create the dataset in Galileo
python experiments/create_galileo_dataset.py finance
```

**What this does:**
1. Reads the CSV file at `domains/{domain}/dataset.csv`
2. Validates the file has required `input` and `output` columns
3. Creates a Galileo dataset with the name `"{Domain} Domain Dataset"`
4. Uploads all rows to Galileo
5. Returns the dataset ID

**Example output:**
```
Found 20 samples
Dataset created: Finance Domain Dataset
ID: abc123-def456-ghi789
```

**Note:** You only need to create the dataset once. After it's created, it persists in Galileo and can be reused for multiple experiments.

### Step 2: Run an Experiment

**Script:** `run_experiment.py`

```bash
# Run an experiment with default settings
python experiments/run_experiment.py finance

# Run with custom experiment name
python experiments/run_experiment.py finance --experiment-name "my-custom-experiment"
```

**What this does:**
1. Loads the dataset created in Step 1 (by name: "{Domain} Domain Dataset")
2. Creates a LangGraph agent for the specified domain (uses the domain's **default model** from `config.yaml`)
3. For each row in the dataset:
   - Sends the `input` to the agent
   - Collects the agent's response
   - Evaluates with default metrics (Ground Truth Adherence, Chunk Attribution, Context Adherence)
4. Logs all traces and metrics to Galileo
5. Provides a direct link to view results in Galileo Console

**Default metrics evaluated:**
- Ground Truth Adherence
- Prompt Injection
- Chunk Attribution Utilization
- Context Adherence

## Using the UI

### Accessing Experiments in the UI

1. Start the Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Click on the **🧪 Experiments** tab at the top of the page

### Workflow in the UI

#### Step 1: Dataset Setup

Choose one of four options:

1. **Select Existing Dataset by Name**
   - Browse all available Galileo datasets
   - Defaults to domain-specific dataset if available
   - View dataset link in Galileo Console after loading

2. **Select Existing Dataset by ID**
   - Enter a specific Galileo dataset ID
   - View dataset link in Galileo Console after loading

3. **Create from Sample Test Data**
   - Uses the domain's `dataset.csv` file
   - Previews data before creation
   - Customize dataset name (defaults to "{Domain} Domain Dataset")
   - View dataset link in Galileo Console after creation

4. **Upload CSV File**
   - Upload a custom CSV with `input` and `output` columns
   - Previews data before creation
   - Customize dataset name (defaults to uploaded filename)
   - View dataset link in Galileo Console after creation

#### Step 2: Experiment Configuration

Once a dataset is loaded:

1. **View Dataset Info**
   - See the selected dataset name
   - Access direct link to view dataset in Galileo Console
   - **Model**: The experiment uses the **same model as the sidebar** (Model → LLM). Change the model in the sidebar before running; the config shows which model will be used.

2. **Set Experiment Name**
   - Auto-generates a unique name with random suffix
   - Fully customizable

3. **Select Metrics**
   - Ground Truth Adherence
   - Prompt Injection
   - Chunk Attribution Utilization
   - Context Adherence
   
   All metrics are selected by default and can be toggled on/off

#### Step 3: Run Experiment

- Click "🚀 Run Experiment"
- Wait for completion (may take a few minutes)
- **View direct link to experiment results** in Galileo Console
- Access experiment details including:
  - Experiment name
  - Domain
  - Dataset used
  - Metrics evaluated
  - Project name
  - Experiment ID

## Architecture

### Shared Helpers (`experiment_helpers.py`)

The `experiment_helpers.py` module provides reusable functions for both CLI and UI:

- `read_dataset_csv()` - Read CSV files
- `create_domain_dataset()` - Create Galileo datasets
- `get_dataset_by_name()` / `get_dataset_by_id()` - Retrieve datasets
- `run_domain_experiment()` - Execute experiments
- `AVAILABLE_METRICS` - Predefined metric configurations

### Integration with Existing Code

The experiments system integrates with:
- **AgentFactory** - Uses the same agent creation logic
- **DomainManager** - Leverages domain configurations
- **Galileo SDK** - Direct integration with Galileo experiments API

## Default Metrics

The following metrics are used by default:

1. **Ground Truth Adherence** - Measures how well responses match expected outputs
2. **Prompt Injection** - Detects potential prompt injection attempts
3. **Chunk Attribution Utilization** - Evaluates RAG chunk usage
4. **Context Adherence** - Measures adherence to provided context

## Dataset Format

Datasets should be CSV files with the following columns:

| Column | Required | Description |
|--------|----------|-------------|
| `input` | Yes | User query or input |
| `output` | Yes | Expected or reference output |

Example:
```csv
input,output
"What is the stock price of AAPL?","The current stock price of AAPL is $150.25"
"Buy 10 shares of TSLA","Successfully purchased 10 shares of TSLA at $180.00 per share"
```

## Key Features

- **Tab Navigation**: Experiments accessible via top-level tabs alongside Chat
- **Model Selection (UI)**: Experiments run with the model selected in the sidebar (Model → LLM). Change it before clicking "Run Experiment". CLI runs use the domain's default model from `config.yaml`.
- **Dataset Management**: Create, select, and view datasets with direct links to Galileo Console
- **Custom Naming**: Name your datasets to avoid conflicts and organize better
- **Direct Links**: Click through to view datasets and experiment results in Galileo Console
- **Real-time Feedback**: Progress indicators and status updates during experiment execution
- **Domain-Specific**: Experiments automatically use domain-specific agents and configurations
- **Flexible Metrics**: Select which metrics to evaluate for each experiment run

## Dataset Naming

When creating datasets:
- **From Sample Data**: Defaults to `{Domain} Domain Dataset` (e.g., "Finance Domain Dataset")
- **From Upload**: Defaults to uploaded filename without extension
- **Both**: Fully customizable before creation

## Experiment Results

After running an experiment, you get:
- Direct link to the specific experiment results page (not just the experiments list)
- Experiment ID for reference
- Full details of configuration used
- Links persist in the UI for easy access

