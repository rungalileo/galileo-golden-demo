# Galileo Golden Demo

> **New Mac / executive installation:** use the automated full-stack installer
> and handoff guides in
> [`documentation/MACOS_EXECUTIVE_INSTALL.md`](documentation/MACOS_EXECUTIVE_INSTALL.md)
> and
> [`documentation/CODEX_AGENT_MACOS_RUNBOOK.md`](documentation/CODEX_AGENT_MACOS_RUNBOOK.md).
> Team-managed secrets use the single-item contract in
> [`documentation/ONEPASSWORD_TEAM_CONFIG.md`](documentation/ONEPASSWORD_TEAM_CONFIG.md).
> The installer uses MLX-LM (not Ollama), Open WebUI, PostgreSQL/pgvector,
> OpenAI, and Galileo Cloud, with optional GitHub and 1Password login.

***2026-07-13 Release: Now with support for AWS Bedrock models***

A multi-turn agentic system that showcases Galileo across multiple domains and agent frameworks, designed to be used for product demos. The code itself is reusable and configurable for a variety of use cases.

## What This Repo Is

A multi-turn agentic system showcasing Galileo's observability capabilities with configurable domains and RAG integration. Built to be reusable for product demos with minimal setup time.

## What This Repo Isn't

Not a production reference architecture or replacement for customer-specific POCs requiring heavy customization.

## Getting Started

### Prerequisites

- Python 3.8+
- Access to a Large Language Model
   - [Ollama](https://ollama.com/) running locally (default: `http://localhost:11434`); or
   - [MLX-LM](https://github.com/ml-explore/mlx-lm) on Apple Silicon (OpenAI-compatible API); or
   - AWS Bedrock LLM (via `AWS_BEARER_TOKEN_BEDROCK` token)
   - OpenAI API Key
- Galileo API key
- PostgreSQL with pgvector (local Docker container or hosted instance)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd new-golden-demo
   ```

2. **[Optional] Install Ollama on Mac and pull models**

   This demo can use **Ollama** for local inference when the sidebar **Model provider** is set to **Local (Ollama)**. The default chat model is **`gemma4`**.

   This is the best option, though it requires more hardware to ensure performance.

   #### Install Ollama (macOS)

   **Option A — Download the app (recommended)**

   1. Go to [https://ollama.com/download](https://ollama.com/download)
   2. Download **Ollama for macOS** and drag it into **Applications**
   3. Open **Ollama** from Applications — it runs in the menu bar and starts the server automatically

   **Option B — Homebrew**

   ```bash
   brew install ollama
   ollama serve
   ```

   Keep `ollama serve` running in a terminal, or use the menu-bar app from Option A instead.

   #### Verify Ollama is running

   ```bash
   curl http://localhost:11434/api/tags
   ```

   You should get a JSON response (possibly with an empty `models` list before pulling anything).

   #### Pull the models used by this demo

   ```bash
   # Default chat model (agent + tool calling)
   ollama pull gemma4

   # Embedding model for RAG (required for retrieval)
   ollama pull nomic-embed-text
   ```

   Confirm both models are installed:

   ```bash
   ollama list
   ```

   You should see `gemma4` and `nomic-embed-text` in the output.

   #### Optional additional chat models

   These appear in the sidebar **Select Model** dropdown under **Local (Ollama)**:

   ```bash
   ollama pull mistral
   ...
   ```

   Do keep in mind that you will need to download any other models you want to test with; also, the model needs to have tool and reasoning capabilities. Gemma4 was the only model to work consistently during testing, so make sure to test any other models thoroughly.

   Ollama serves models at `http://localhost:11434` by default. Override the URL in `.streamlit/secrets.toml` if needed:

   ```toml
   ollama_base_url = "http://localhost:11434"
   ollama_default_chat_model = "gemma4"
   ```

   #### Alternative: use MLX-LM for local chat

   Existing Ollama configuration remains the default. To use an MLX-LM server
   instead, opt in through `.streamlit/secrets.toml`:

   ```toml
   local_llm_backend = "mlx"
   mlx_base_url = "http://127.0.0.1:8080/v1"
   mlx_api_key = "local"
   mlx_default_chat_model = "mlx-community/gemma-4-26b-a4b-it-4bit"
   mlx_embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
   ```

   Start the server with the same model:

   ```bash
   mlx_lm.server \
     --model mlx-community/gemma-4-26b-a4b-it-4bit \
     --host 127.0.0.1 \
     --port 8080
   ```

   MLX-LM provides chat completions but not embeddings. When MLX is selected,
   the app uses the in-process `sentence-transformers/all-MiniLM-L6-v2` model
   for local RAG. Existing Ollama, OpenAI, and Bedrock embedding paths remain
   available and unchanged.

3. **Start PostgreSQL with pgvector (Docker)**
   ```bash
   docker pull pgvector/pgvector:pg16

   docker run -e POSTGRES_USER=postgres \
              -e POSTGRES_PASSWORD=mypassword \
              -e POSTGRES_DB=vectordb \
              --name golden-demo-postgres \
              -p 5432:5432 \
              -d pgvector/pgvector:pg16

   # Enable the pgvector extension
   docker exec -it golden-demo-postgres psql -U postgres -d vectordb -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

   
4. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

5. **Install requirements**
   ```bash
   pip install -r requirements.txt
   ```

6. **Configure secrets**
   Create `.streamlit/secrets.toml` with your API keys:
   
   Edit `.streamlit/secrets.toml` with your actual API keys:
   ```toml
   # MLX-LM (local chat on Apple Silicon)
   local_llm_backend = "mlx"
   mlx_base_url = "http://127.0.0.1:8080/v1"
   mlx_api_key = "local"
   mlx_default_chat_model = "mlx-community/gemma-4-26b-a4b-it-4bit"
   mlx_embedding_model = "sentence-transformers/all-MiniLM-L6-v2"

   # Ollama (local LLM — no API key required)
   # Set local_llm_backend = "ollama" to use this path instead.
   ollama_base_url = "http://localhost:11434"
   ollama_default_chat_model = "gemma4"
   ollama_embedding_model = "nomic-embed-text"

   # OpenAI (optional — for sidebar "Hosted (OpenAI)" provider)
   openai_api_key = "your_openai_api_key_here"

   # AWS Bedrock Configuration
   bedrock_api_key = "..." # Amazon Bedrock API key
   aws_region = "us-east-1" # AWS region for Bedrock inference
   bedrock_default_chat_model = "mistral.ministral-3-14b-instruct"
   bedrock_embedding_model = "amazon.titan-embed-text-v2:0"
 
   # PostgreSQL Configuration (pgvector)
   postgres_host = "localhost"
   postgres_port = "5432"
   postgres_user = "postgres"
   postgres_password = "mypassword"
   postgres_db = "vectordb"

   # Galileo Configuration
   galileo_api_key = "your_galileo_api_key_here"
   galileo_console_url = "https://console.galileo.ai"  # or your custom URL
    
   # Agent Control configuration
   galileo_api_url = "https://api.galileo.ai" 
   agent_control_url = "https://console.galileo.ai/api/agent-control"
   ```
   
   **Note:** Galileo project names are configured per-domain in `domains/{domain}/config.yaml`

7. **Set up vector databases**
   Local, OpenAI, and Bedrock embeddings can't share one index — different embedding models produce different vector spaces even at the same dimension count, so searching across them silently returns wrong results. Because of that, the script creates one index per configured provider for each domain, automatically. The index is chosen at runtime based on what LLM service is being used.

   ```bash
   python helpers/setup_vectordb.py bank
   python helpers/setup_vectordb.py healthcare
   python helpers/setup_vectordb.py insurance
   python helpers/setup_vectordb.py restaurant
   ```

   The script takes **no provider arguments** — it reads `.streamlit/secrets.toml` and builds an index for each provider whose credential is set:

   - if MLX is selected and `sentence-transformers` is installed → `{domain}_local_index` (local sentence-transformers)
   - if Ollama is selected and reachable → `{domain}_local_index` (Ollama)
   - if `openai_api_key` is set → `{domain}_hosted_index` (OpenAI)
   - if `bedrock_api_key` is set → `{domain}_bedrock_index` (Bedrock)

   Providers whose credential isn't set are skipped with a note. Each configured provider is built independently, so a failure in one is reported but doesn't abort the others.

   Switching the **Model provider** toggle in the UI then automatically uses the matching index (Local → MLX sentence-transformers or Ollama, Hosted → OpenAI, Bedrock → Bedrock). If the matching index wasn't built, RAG falls back to another prebuilt index so search always works. (Advanced: set `embedding_provider` in `secrets.toml` to `local`, `hosted`, or `bedrock` to pin RAG to one backend regardless of the chat toggle.)

PS: Make sure to run the setup script even if you are upgrading from a previous version of the demo, as the index layout changed (one index per provider).

&nbsp;


8. **Run the Streamlit app**
   ```bash
   streamlit run app.py
   ```

The app will be available at `http://localhost:8501`

## Model Selection

The behavior of the application has changed in this version. The Model Provider list will be defined dynamically; only the providers enabled and configured in the `secrets.toml` file will be shown in the UI: Local (Ollama), Hosted (OpenAI) and Bedrock (AWS). If you don't see one of these options in the running app, check the `secrets.toml` configuration.

Also, the priority of the default provider will be:
- Ollama
- Bedrock
- OpenAI

Use the **sidebar → Model** section to choose how the app runs:

- **Local (Ollama)** — uses models pulled locally (default: `gemma4`). See step 2 above for Mac install and `ollama pull gemma4`.
- **Hosted (OpenAI)** — uses OpenAI models via `openai_api_key` in `.streamlit/secrets.toml`.
- **Bedrock (AWS)** — uses AWS Bedrock models via `bedrock_api_key` (and `aws_region`, default `us-east-1`) in `.streamlit/secrets.toml`. Auth uses a Bedrock API key (bearer token) — no SigV4 access keys needed.

PS: to hide the provider options from the UI:
- Ollama: comment the `ollama_base_url` parameter in `secrets.toml`
- Bedrock: comment the `bedrock_api_key` parameter in `secrets.toml`
- OpenAI: comment the `openai_api_key` parameter in `secrets.toml`

&nbsp;

The **Select Model** dropdown lists provider-specific models from each domain's `config.yaml`. The selection applies to both **Chat** and **Experiments**, and you can change it mid-session without losing conversation history.

Switching this toggle also switches which prebuilt RAG index is queried (Local → the Ollama index, Hosted → the OpenAI index, Bedrock → the Bedrock index), so make sure you've built the ones you'll use — see Setup step 7. Each index is queried only with the embedding model that built it, so search is always internally consistent within a provider.

Keep in mind that reloading the page creates a new session and resets all controls to default value, including the model selection. If you're demoing with OpenAI, you will want to change the default value to prevent issues during the demo.

&nbsp;

## Multi-Domain Support

This demo supports **multiple domains** with automatic routing and separate Galileo projects per domain. The app automatically discovers all domains in the `domains/` directory and creates navigation pages for each.

Each domain automatically gets its own Galileo log stream, which is configured in the domain's `config.yaml`.

## How to Add a New Domain

This demo is designed so you can add new use cases by creating files under `domains/` — no changes to `app.py` are required. The fastest path is to copy one of the existing domains, like `domains/healthcare/` or `domains/bank/` and customize the content.

### Quick overview

| You edit  | The app handles automatically |
|-----------|-------------------------------|
| `config.yaml`, `system_prompt.json` | Domain discovery and navigation |
| `tools/schema.json`, `tools/logic.py` | Tool loading, chaos wrapping, LangGraph agent |
| `docs/` data | Vector DB & transactional table data (populated via script) |


### 1. Create the domain folder

Copy an existing domain as a template. For example, to create a new `telco` domain:

```bash
cp -r domains/healthcare domains/telco
```

The new folder's name must match the new domain name. Many things in this app are driven by domain name, so make sure the domain name is consistent everywhere within the domain files. 

Keep the domain name single word, lower case and with no special characters.

Keep in mind that using prospect names for domain names means you won't be able to reuse this demo with other prospects.


Required structure (the app will not discover the domain without all of these):

```
domains/your_domain/
├── config.yaml              # required
├── system_prompt.json       # required
├── docs/
│   ├── qa.csv               # required — FAQ / retrieval knowledge
│   └── relational_*.csv     # required — SQL table (e.g. relational_patient.csv)
└── tools/
    ├── schema.json          # required
    └── logic.py             # required
```

### 2. Create the datasets under `docs/`

Start here, because the inputs you define here will be reused in the config.yaml file. And it will help you think what kind of demo you want to run.

In the standard demo, there are 2 types of documents: Q&A, which will be transformed into vectors for semantic search, and tabular data, which will be used to create a relational table in Postgres.

Do keep in mind that this is a simple model out-of-the-box: one table. If you want more complex text-to-sql with joins, etc, you'll need to make more code changes. Should be possible, of course, but not out-of-the-box.

One tip is to find some kind of Q&A in your prospect's web site and prepare a list of 10 or so questions and answers. Choose one of them to be the example question in the main web UI.

**RAG / FAQ data**:
- `qa.csv` with `question` and `answer` columns.

Try to keep the number of questions low, around 10 or so.

Next, you can use a database table for text-to-sql operations. Usually, a list of customers, or patients, etc, or anything related to your prospect's business. The columns in the CSV will become columns in the postgres table. You can have as many columns as needed, with any names. However, do try to keep it simple.

**Relational SQL data** — name files `relational_<table>.csv` (e.g. `relational_patient.csv`). They are loaded into PostgreSQL as `{domain}_{suffix}` tables (e.g. `healthcare_patient`).

Do keep in mind that only very basic text-to-sql was used for the demo ("show me data for customer 1", etc). If you're looking to do more complex queries, make sure to test the prompts, because you may need to add more logic to the tools.

&nbsp;

**IMPORTANT**

**Note:** `helpers/setup_vectordb.py` has custom ingestion for each domain (structured `qa.csv` embedding plus relational table load). If your new domain uses the same `qa.csv` + relational CSV pattern, add a similar branch in `setup_vectordb.py`, or call `load_domain_relational_csvs()` after generic doc embedding.

&nbsp;

PS: This is implemented like this in case you decide to create a new domain with completely different tools. In this case, you can add custom logic to the `setup_vectordb.py` so the Database structure can be created in the exact format that you need. Otherwise, you can copy the same `if` block used by one of the existing domains (or just change to something like `if domain in [list]`).

&nbsp;

Finally, as noted above, `helpers/setup_vectordb.py` will create the index for the providers that are configured in the `secrets.toml` file. Make sure that configuration is correct before running this script.

### 3. Define tools

There are 2 tools that will work out-of-the-box: 
- Vector search for Q&A data (called `search_[domain]_qa`)
- Text-to-sql for each table. One will be for SELECT operations, like `get_customer_info`, and the other for the DELETE operation (`delete_customer_info`). If that's all you need, then you should simply rename the tools so they make sense with the context of the new domain.

In case you need to add new logic (insert records, execute joins, etc), this would be the place to add that code.

**`tools/schema.json`** — OpenAI function-calling format for each tool (name, description, parameters).

**`tools/logic.py`** — implement tools and export them in a `TOOLS` array at the end of the file:

```python
TOOLS = [get_record_info, delete_record, search_qa]
```


#### Text-to-SQL + retrieval pattern (healthcare / bank)

The current domains use three tool types:

| Tool type | Pattern |
|-----------|---------|
| Lookup | `get_*_info(id)` → `generate_sql(..., operation="select")` → `_execute_*_sql(sql)` |
| Delete | `delete_*_record(id)` → `generate_sql(..., operation="delete")` → `_execute_*_delete_sql(sql)` |
| Search | `search_*_qa(query)` → pgvector retrieval |

Set these constants at the top of `logic.py`:

- `_DOMAIN_NAME` — must match the folder name (e.g. `"healthcare"`)
- `_TABLE_SUFFIX` — matches the relational CSV name (e.g. `"patient"` for `relational_patient.csv`)
- `_ID_COLUMN` — primary key column in the CSV (e.g. `"patient_id"`)


For Agent Control guardrails, decorate internal SQL handlers and search tools:

```python
from helpers.agent_control_helpers import domain_controlled_tool

@domain_controlled_tool(step_name="get_record_info")
async def _execute_record_sql(sql: str) -> str:
    ...

@domain_controlled_tool(step_name="delete_record")
async def _execute_record_delete_sql(sql: str) -> str:
    ...

@domain_controlled_tool(step_name="retrieval_step")
async def search_qa(query: str) -> str:
    ...
```

Public tools (`get_record_info`, `delete_record`) take a record ID, generate SQL, then call the internal `_execute_*` handlers. Guardrails on `input.sql` run on those internal handlers, not on the public tool boundary.

See `domains/healthcare/tools/logic.py` for a complete reference implementation.



&nbsp;

### 4. Write `system_prompt.json`

Describe the agent's role and when to use each tool. Tool names in the prompt must match `schema.json` exactly.

```json
{
  "system_prompt": "You are a helpful assistant for [your domain]. Use search_qa for knowledge questions, get_record_info for lookups, and delete_record only when the user explicitly asks to delete a record."
}
```

You may need to tweak your prompt to adapt it to guardrail behaviors.


&nbsp;


### 5. Configure `config.yaml`

This is the most critical file, as it has all the basic configuration.

Easiest way to start is to find and replace all mentions of the original domain (like `bank`) with the new domain name (like `telco`).

Set domain metadata, UI, model, RAG, tools list, etc:

- `domain.name` / `domain.description`
- `ui.app_title`, `icon`, `example_queries`
- `model.default_model`, `temperature`, `additional_models`
- `rag.enabled`, `chunk_size`, `chunk_overlap`, `top_k`
- `tools` — list of tool names (must match `schema.json`)
- `vectorstore.embedding_model`
- `galileo.project` / `galileo.log_stream`
- `demo_hallucinations` (optional; see Hallucination Demo section below)

PS: Copy the suggested inputs from your .CSV files; you can also create a hallucinated version of the same Q&A prompt to show how Galileo detects hallucinations.

Example:

```yaml
domain:
  name: "telco"
  description: "Demo use case for Telco customer"

ui:
  app_title: "Telco Online Assistant"
  icon: "🤖"
  example_queries:
    - "Example question from Q&A document"
    - "Example question about relational table -- 'Lookup account info for customer C001'"

model:
  default_model: "gemma4"
  temperature: 0.1
  additional_models:
    - "mistral"

rag:
  enabled: true
  chunk_size: 1000
  chunk_overlap: 200
  top_k: 5

tools:
  - "get_record_info"
  - "delete_record"
  - "search_qa"

vectorstore:
  embedding_model: "nomic-embed-text"
```



&nbsp;

### 6. Load data into PostgreSQL

```bash
python helpers/setup_vectordb.py your_domain
```

This script:

- Embeds `qa.csv` RAG documents into pgvector, building one index per configured provider (`{domain}_local_index` / `{domain}_hosted_index` / `{domain}_bedrock_index`)
- Loads `relational_*.csv` files into SQL tables (for healthcare/bank; extend for new domains as noted above)

PostgreSQL with pgvector must be running before you run this. Re-running the script drops and recreates the vector collection for a clean state.



&nbsp;

### 7. Configure Agent Control (optional)

There are 3 runtime guardrails that must be created (or enabled, if they are already created)

1. `block-harmful-sql`
   - This guardrail will prevent the DELETE operation from being executed
   - It should be kept enabled at all times (since it won't impact other parts of the demo)
   - Configuration:
      - Stage: PRE
      - Action: Deny
      - Execution Environment: Server
      - Step Types: tool
      - Evaluator Configuration
         - Path: input.sql
         - Blocked Operations: DELETE
         - Blocked DDL: Checked

&nbsp;

2. `block-output-pii`
   - This guardrail will prevent PII from being added to the LLM output
   - It should be kept disabled at the beginning of your demo
   - Configuration:
      - Stage: POST
      - Action: Steer
      - Steering Context: Remove phone number and address from output
      - Execution Environment: Server
      - Step Types: llm
      - Evaluator Configuration
         - Path: *
         - Scorer Label: Output PII (SML)
         - Threshold: phone_number, address
         - Operator: any
         - Payload Field: input

&nbsp;

2. `block-prompt-injection`
   - This guardrail will prevent prompt injection inputs from being processed.
   - It should be kept disabled at the beginning of your demo
   - Configuration:
      - Stage: PRE
      - Action: Deny
      - Execution Environment: Server
      - Step Types: llm
      - Evaluator Configuration
         - Path: input
         - Scorer Label: Prompt Injection (SML)
         - Threshold: 0.80
         - Operator: gte
         - Payload Field: input


These controls can be created in the UI, through the Controls page; then added to each Log Stream, through the Control tab in the log stream page.

Controls can be further configured to apply to specific steps. Step names are registered automatically from `tools/schema.json` when the agent loads — you do not need to edit `agent.py`.


&nbsp;

### 8. Run and verify

```bash
streamlit run app.py
```

Your domain is available at `http://localhost:8501/your_domain`.

Smoke-test:

- Example queries from `config.yaml`
- Tool calls appear in Galileo traces
- RAG search returns results
- SQL lookup/delete works against relational tables
- Guardrails fire on the expected step types (if configured)

### 9. Optional polish

- `dataset.csv` — for the Experiments tab (`input` and `output` columns)
- `domains/your_domain/README.md` — demo questions and context for SEs
- Custom Galileo project/log stream in `config.yaml`


&nbsp;

## Underlying Architecture

### Data Flow

1. **User Input** → Streamlit UI captures user message
2. **Agent Processing** → AgentFactory creates domain-specific agent
3. **Tool Execution** → Agent decides which tools to call based on user intent
4. **RAG Integration** → PostgreSQL/pgvector database provides relevant context when needed
5. **Response Generation** → Agent synthesizes final response
6. **Observability** → All interactions logged to Galileo automatically

### Vector Database Architecture

The app uses **PostgreSQL with pgvector** for vector storage with environment-based configuration:

- **Local Demos**: PostgreSQL running in Docker on `localhost:5432`
- **Hosted Demos**: PostgreSQL instance accessible from the deployed environment
- **Collection Naming**: `{domain}_{environment}_index` (e.g., `finance_local_index`)
- **Automatic Selection**: The app uses the correct collection based on the `environment` setting in secrets


## Code Structure

```
new-golden-demo/
├── app.py                    # Streamlit application entry point
├── agent_factory.py          # Agent creation and management
├── base_agent.py            # Abstract base agent class
├── domain_manager.py        # Domain configuration management
├── setup_env.py            # Environment setup utilities
├── run_streamlit.py        # Alternative app runner
├── requirements.txt         # Python dependencies
├── agent_frameworks/        # Agent framework implementations
│   └── langgraph/
│       ├── agent.py         # LangGraph agent implementation
│       └── langgraph_rag.py # RAG integration for LangGraph
├── domains/                 # Domain-specific configurations
│   ├── healthcare/         # Example healthcare domain
│   └── bank/               # Example bank domain
│       ├── config.yaml     # Domain configuration
│       ├── system_prompt.json
│       ├── dataset.csv     # Evaluation data (optional)
│       ├── docs/           # RAG + relational CSV data
│       └── tools/          # Domain tools (schema.json + logic.py)
├── experiments/            # Experiment system (UI + CLI)
│   ├── experiment_helpers.py  # Shared experiment functions
│   ├── run_experiment.py      # CLI script to run experiments
│   ├── create_galileo_dataset.py  # CLI script to create datasets
│   └── README.md              # Detailed experiments documentation
├── helpers/                # Utility scripts
│   ├── setup_vectordb.py  # PostgreSQL/pgvector database setup
│   ├── pgvector_utils.py  # Shared pgvector connection helpers
│   ├── test_vectordb.py   # Vector database testing
│   ├── agent_control_helpers.py # Agent Control initialization
│   ├── hallucination_helpers.py  # Hallucination demo logging
│   └── galileo_api_helpers.py  # Galileo API utilities
└── tools/                 # Shared tools
    └── rag_retrieval.py   # General RAG functionality (not implemented)
```

### For Sales Engineers

As an SE, you primarily need to focus on the `domains/` directory:

- **To customize for a demo**: Update the domain configuration files
- **To add new use cases**: Create a new domain following the structure above
- **For troubleshooting**: If you encounter issues with other files, reach out to the FDE team immediately

The system is designed so that domain customization requires just configuration updates and document additions.

## Running Experiments

The demo includes a full experiments system to evaluate your agents using Galileo. Experiments can be run from both the **Streamlit UI** and the **command line**.

### Quick Start

#### Via UI
1. Start the Streamlit app: `streamlit run app.py`
2. Click on the **🧪 Experiments** tab
3. Follow the 3-step workflow:
   - Select or create a dataset
   - Configure experiment settings and metrics
   - Run the experiment and view results

#### Via CLI

**Step 1: Create a Dataset (one-time setup)**
```bash
# Preview the dataset before creating
python experiments/create_galileo_dataset.py finance --preview

# Create the dataset in Galileo
python experiments/create_galileo_dataset.py finance
```

This script:
- Reads the `domains/{domain}/dataset.csv` file
- Validates it has `input` and `output` columns
- Creates a Galileo dataset with name: `"{Domain} Domain Dataset"`
- Returns the dataset ID for reference

**Step 2: Run an Experiment**
```bash
# Run experiment with default settings
python experiments/run_experiment.py finance

# Run with custom experiment name
python experiments/run_experiment.py finance --experiment-name "my-experiment-v1"
```

This script:
- Loads the dataset created in Step 1
- Runs each input through the domain's agent
- Evaluates responses with selected metrics
- Logs all traces to Galileo as an experiment
- Provides link to view results in Galileo Console

### Key Features

- **Multiple Dataset Options**: Select existing datasets, create from sample data, or upload CSV files
- **Model Selection**: Experiments use the same model as the sidebar (Model → LLM). Change it in the sidebar before running; the experiment config shows which model will be used.
- **Custom Naming**: Avoid conflicts with customizable dataset and experiment names
- **Direct Links**: Click through to view datasets and results in Galileo Console
- **Flexible Metrics**: Choose which metrics to evaluate for each run
- **Tab Navigation**: Easy access alongside the Chat interface

### 📖 Full Documentation

For detailed information including:
- Complete UI workflow guide
- CLI usage examples
- Dataset format requirements
- Architecture and integration details
- Available metrics

See **[experiments/README.md](experiments/README.md)** for the full documentation.

## Agent Control Integration

The demo uses **Agent Control** for runtime guardrails. Policies are configured on the Agent Control server (Galileo UI) — not in domain YAML files.

### Prerequisites

1. Add Agent Control settings to `.streamlit/secrets.toml`:

```toml
agent_control_url = "https://agent-control.demo-v2.galileocloud.io"
agent_control_agent_name = "your-agent-name"
agent_control_api_key_header = "Galileo-API-Key"
```

2. Install dependencies: `pip install -r requirements.txt` (includes `agent-control-sdk[galileo]`)

3. Create controls in the Galileo UI scoped to the step names your domain uses. Steps are registered automatically from `tools/schema.json` when the agent loads.

### Step names

| Step type | Step name | Where it applies |
|-----------|-----------|------------------|
| LLM | `{Domain} Assistant` (e.g. `Healthcare Assistant`) | LLM call in `agent_frameworks/langgraph/agent.py` |
| Tool | Tool name from `schema.json` (e.g. `delete_patient_record`) | Internal `_execute_*_sql` handlers in `logic.py` |
| Tool | `retrieval_step` | Search/RAG tools in `logic.py` and `langgraph_rag.py` |

For SQL guardrails (e.g. blocking `DELETE`), scope controls to **tool** steps with path `input.sql`. The internal SQL handlers must use `@domain_controlled_tool(step_name="<tool_name>")` so Agent Control emits `span_type=tool` with the generated SQL in the input.

When adding a new domain, decorate tools in `logic.py` as **async** functions (required when running inside LangGraph's event loop):

```python
from helpers.agent_control_helpers import domain_controlled_tool

@domain_controlled_tool(step_name="my_tool_name")
async def _execute_my_sql(sql: str) -> str:
    ...

@domain_controlled_tool(step_name="retrieval_step")
async def search_qa(query: str) -> str:
    ...
```

### Learn More

- **[Agent Control](https://agentcontrol.dev/)** — open-source control plane for AI agents


## Hallucination Demo

The demo includes a **Hallucination Demo** feature to showcase Galileo's hallucination detection capabilities. This allows you to log intentional hallucinations that contradict retrieved context.

### How It Works

1. Click "Log Hallucination" in the sidebar
2. The question configured in the `config.yaml` file for the domain is printed as a new user prompt
   - The hallucinated response from the `config.yaml` file is printed as the output
2. This also generates a trace in Galileo with:
   - Real context documents (containing the correct response)
   - A hallucinated answer (that contradicts the context)
3. Galileo's hallucination detection flags the contradiction

### Configuring Hallucinations for Your Domain

Add a `demo_hallucinations` section to your domain's `config.yaml`:

```yaml
demo_hallucinations:
  - question: "What was the Q4 revenue?"
    hallucinated_answer: "Revenue was $9.3B, up 4% from the previous quarter."
    # NOTE: The real answer in context says "up 4% from a year ago"
    context:
      - "Q4 revenue was $9.3 billion, up 4% from a year ago."
      - "Additional context documents..."
```

## Chaos Engineering

The demo includes a **Chaos Engineering** system to showcase Galileo's observability and detection capabilities by intentionally injecting failures. Chaos modes can be toggled from the sidebar during demos.

### Available Chaos Modes

The system includes 5 chaos modes that work automatically across all domains:

1. **🔧 Tool Instability** - Simulate API failures with realistic HTTP errors
2. **🔢 Sloppiness** - Corrupt numbers in tool outputs before LLM sees them
3. **💥 Data Corruption** - Force LLM to corrupt data it receives correctly
4. **📚 RAG Disconnects** - Simulate vector database failures
5. **⏱️ Rate Limits** - Inject rate limit errors (429 responses)

All modes operate at **100%** when enabled for predictable, demo-ready behavior.

Each mode tests different observability capabilities and helps demonstrate how Galileo detects issues at different levels (span, trace, session).

### How to Use

1. **Enable in UI**: Toggle chaos modes in the sidebar under "Chaos Engineering"
2. **Run Queries**: Ask normal questions - chaos is injected automatically based on configured rates
3. **Check Galileo**: View traces in Galileo Console to see detected issues
4. **View Stats**: Real-time counters show how many chaos events occurred
5. **Reset Stats**: Click "Reset Stats" to clear counters between demos

### What Makes This Special

- 🌍 **Domain-Agnostic**: Works automatically across all domains without custom code
- 🎯 **Targeted Testing**: Each mode tests specific observability capabilities
- 📊 **Real-time Stats**: See chaos injection rates and counts in the UI
- 🔧 **Demo-Ready**: Perfect for showing Galileo's detection capabilities in action

### Learn More

**[📖 Full Chaos Engineering Documentation](documentation/CHAOS_ENGINEERING.md)** - Complete guide including:
- Detailed explanation of each chaos mode
- What Galileo detects for each type of failure
- Technical architecture and how chaos is applied
- Demo tips and best practices
- Common questions and troubleshooting

## What's Coming Next

- **Live deployment URL** for easy demo access without local setup

## Updates and Issues

If you encounter any issues or have feedback please contact the FDE team via slack
