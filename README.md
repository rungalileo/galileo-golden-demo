# Galileo Golden Demo

A multi-turn agentic system that showcases Galileo across multiple domains and agent frameworks, designed to be used for product demos. The code itself is reusable and configurable for a variety of use cases.

## What This Repo Is

A multi-turn agentic system showcasing Galileo's observability capabilities with configurable domains and RAG integration. Built to be reusable for product demos with minimal setup time.

## What This Repo Isn't

Not a production reference architecture or replacement for customer-specific POCs requiring heavy customization.

## Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key
- Galileo API key
- PostgreSQL with pgvector (local Docker container or hosted instance)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd new-golden-demo
   ```

2. **Start PostgreSQL with pgvector (Docker)**
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

   See [documentation/POSTGRES_SETUP.md](documentation/POSTGRES_SETUP.md) for detailed configuration and troubleshooting.

3. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install requirements**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure secrets**
   Create `.streamlit/secrets.toml` with your API keys:
   
   Edit `.streamlit/secrets.toml` with your actual API keys:
   ```toml
   # API Keys
   openai_api_key = "your_openai_api_key_here"
   galileo_api_key = "your_galileo_api_key_here"
   
   # Galileo Configuration
   galileo_console_url = "https://console.galileo.ai"  # or your custom URL
   
   # PostgreSQL Configuration (pgvector)
   postgres_host = "localhost"
   postgres_port = "5432"
   postgres_user = "postgres"
   postgres_password = "mypassword"
   postgres_db = "vectordb"
   
   # Environment: "local" for development, "hosted" for production
   environment = "local"
   ```
   
   **Note:** Galileo project names are configured per-domain in `domains/{domain}/config.yaml`

6. **Set up vector databases**
   Load documents into PostgreSQL for each domain you plan to use:
   ```bash
   python helpers/setup_vectordb.py healthcare local
   python helpers/setup_vectordb.py bank local
   ```

7. **Run the Streamlit app**
   ```bash
   streamlit run app.py
   ```

The app will be available at `http://localhost:8501`

## Model Selection

You can change the LLM used for chat and experiments from the **sidebar** (Model → LLM dropdown). Each domain's `config.yaml` defines a **default model** and **additional models** (OpenAI family). The selected model applies to both the Chat tab and the Experiments tab, and you can change it mid-session without losing conversation history.

## Multi-Domain Support

This demo supports **multiple domains** with automatic routing and separate Galileo projects per domain. The app automatically discovers all domains in the `domains/` directory and creates navigation pages for each.

Each domain automatically gets its own Galileo project using the convention: `galileo-demo-{domain_name}` (e.g., `galileo-demo-finance`). You can optionally override this in the domain's `config.yaml`.

**📖 For detailed multi-domain setup instructions, see [documentation/MULTI_DOMAIN_SETUP.md](documentation/MULTI_DOMAIN_SETUP.md)**

## How to Add a New Domain

This demo is designed so you can add new use cases by creating files under `domains/` — no changes to `app.py` are required. The fastest path is to copy `domains/healthcare/` or `domains/bank/` and customize the content.

### Quick overview

| You write | The app handles automatically |
|-----------|-------------------------------|
| `config.yaml`, `system_prompt.json` | Domain discovery and navigation |
| `tools/schema.json`, `tools/logic.py` | Tool loading, chaos wrapping, LangGraph agent |
| `docs/` data | Vector DB setup (via script) |
| Agent Control policies in Galileo UI | Step registration from `schema.json` |

### 1. Create the domain folder

Copy an existing domain as a template:

```bash
cp -r domains/healthcare domains/your_domain
```

Required structure (the app will not discover the domain without all of these):

```
domains/your_domain/
├── config.yaml              # required
├── system_prompt.json       # required
├── dataset.csv              # optional (experiments)
├── docs/
│   ├── qa.csv               # optional — FAQ / retrieval knowledge
│   └── relational_*.csv     # optional — SQL tables (e.g. relational_patient.csv)
└── tools/
    ├── schema.json          # required
    └── logic.py             # required
```

### 2. Configure `config.yaml`

Set domain metadata, UI, model, RAG, tools list, and optionally Galileo:

- `domain.name` / `domain.description`
- `ui.app_title`, `icon`, `example_queries`
- `model.default_model`, `temperature`, `additional_models`
- `rag.enabled`, `chunk_size`, `chunk_overlap`, `top_k`
- `tools` — list of tool names (must match `schema.json`)
- `vectorstore.embedding_model`
- `galileo.project` / `galileo.log_stream` (optional; defaults to `galileo-demo-{domain}`)
- `demo_hallucinations` (optional; see Hallucination Demo section below)

Example:

```yaml
domain:
  name: "your_domain"
  description: "Your domain description"

ui:
  app_title: "Your Domain Assistant"
  icon: "🤖"
  example_queries:
    - "Example query 1"
    - "Example query 2"

model:
  default_model: "gpt-4o"
  temperature: 0.1
  additional_models:
    - "gpt-4o-mini"
    - "gpt-4.1"

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
  embedding_model: "text-embedding-3-large"
```

### 3. Write `system_prompt.json`

Describe the agent's role and when to use each tool. Tool names in the prompt must match `schema.json` exactly.

```json
{
  "system_prompt": "You are a helpful assistant for [your domain]. Use search_qa for knowledge questions, get_record_info for lookups, and delete_record only when the user explicitly asks to delete a record."
}
```

### 4. Define tools

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

### 5. Add data under `docs/`

**Relational SQL data** — name files `relational_<table>.csv` (e.g. `relational_patient.csv`). They are loaded into PostgreSQL as `{domain}_{suffix}` tables (e.g. `healthcare_patient`).

**RAG / FAQ data** — either:

- `qa.csv` with `question` and `answer` columns (healthcare/bank pattern), or
- Generic PDFs, text files, and CSVs in `docs/` (chunked automatically)

**Note:** `helpers/setup_vectordb.py` has custom ingestion for `healthcare` and `bank` (structured `qa.csv` embedding plus relational table load). If your new domain uses the same `qa.csv` + relational CSV pattern, add a similar branch in `setup_vectordb.py`, or call `load_domain_relational_csvs()` after generic doc embedding.

### 6. Load data into PostgreSQL

```bash
# For local demos
python helpers/setup_vectordb.py your_domain local

# For hosted demos
python helpers/setup_vectordb.py your_domain hosted
```

This script:

- Embeds RAG documents into pgvector (`{domain}_{environment}_index`)
- Loads `relational_*.csv` files into SQL tables (for healthcare/bank; extend for new domains as noted above)

PostgreSQL with pgvector must be running before you run this. Re-running the script drops and recreates the vector collection for a clean state.

See [documentation/POSTGRES_SETUP.md](documentation/POSTGRES_SETUP.md) for detailed configuration.

### 7. Configure Agent Control (optional)

If you want runtime guardrails:

1. Set env vars in `.streamlit/secrets.toml` (see Agent Control section below)
2. In the Galileo UI, create controls scoped to the step names your domain registers:
   - **LLM:** `{Domain Title} Assistant` (e.g. `Healthcare Assistant`)
   - **Tools:** tool names from `schema.json` (e.g. `delete_patient_record`)
   - **Retrieval:** `retrieval_step`
3. For SQL blocking, scope controls to **tool** steps with path `input.sql`

Step names are registered automatically from `tools/schema.json` when the agent loads — you do not need to edit `agent.py`.

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

### How to add a domain with Cursor

Watch this video tutorial: https://drive.google.com/file/d/1yM0dMa9uNNJay1q9gfPZJ3eTJ4lPB129/view?usp=drive_link

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

See [documentation/POSTGRES_SETUP.md](documentation/POSTGRES_SETUP.md) for detailed configuration instructions.

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
├── documentation/          # Setup guides and documentation
│   ├── MULTI_DOMAIN_SETUP.md  # Multi-domain configuration guide
│   └── POSTGRES_SETUP.md      # PostgreSQL/pgvector setup instructions
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
- Reference implementation: `training/getting_started/09_guardrails/09_sample_app_postgres_steer.py`

## Hallucination Demo

The demo includes a **Hallucination Demo** feature to showcase Galileo's hallucination detection capabilities. This allows you to log intentional hallucinations that contradict retrieved context.

### How It Works

1. Click "Log Hallucination" in the sidebar
2. A pre-configured hallucination is logged to Galileo with:
   - Real context documents (that say one thing)
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
