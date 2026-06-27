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
<<<<<<< Updated upstream
=======
- PostgreSQL with pgvector (local Docker container or hosted instance)
>>>>>>> Stashed changes

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd golden-demo-hosted
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
<<<<<<< Updated upstream
=======
   # OpenAI (required)
>>>>>>> Stashed changes
   openai_api_key = "your_openai_api_key_here"
   openai_default_chat_model = "gpt-4o"
   openai_embedding_model = "text-embedding-3-large"

   galileo_api_key = "your_galileo_api_key_here"
<<<<<<< Updated upstream
   galileo_project = "your_project_name"
   galileo_log_stream = "your_log_stream_name"
=======
   
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
>>>>>>> Stashed changes
   ```

6. **Set up vector databases**
   RAG uses OpenAI embeddings stored in pgvector (`{domain}_local_index`). Load documents for each domain you plan to use:

   ```bash
   python helpers/setup_vectordb.py healthcare local
   python helpers/setup_vectordb.py bank local
   ```

7. **Run the Streamlit app**
   ```bash
   streamlit run app.py
   ```

The app will be available at `http://localhost:8501`

<<<<<<< Updated upstream
## How to Add a New Domain
This demo code is designed to easily be extended to different domains, that way, SE's can spend less time
writing code and more time focusing on how to display Galileo in the best light. 
=======
## Model Selection

Use the **sidebar → Model** section to choose an OpenAI model for chat and experiments. Available models are configured per domain in `config.yaml` (`default_model` and `additional_models`). You can change the selection mid-session without losing conversation history.

## Multi-Domain Support

This demo supports **multiple domains** with automatic routing and separate Galileo projects per domain. The app automatically discovers all domains in the `domains/` directory and creates navigation pages for each.

Each domain automatically gets its own Galileo project using the convention: `galileo-demo-{domain_name}` (e.g., `galileo-demo-finance`). You can optionally override this in the domain's `config.yaml`.

**📖 For detailed multi-domain setup instructions, see [documentation/MULTI_DOMAIN_SETUP.md](documentation/MULTI_DOMAIN_SETUP.md)**

## How to Add a New Domain

This demo is designed so you can add new use cases by creating files under `domains/` — no changes to `app.py` are required. The fastest path is to copy `domains/healthcare/` or `domains/bank/` and customize the content.
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
  app_title: "🤖 Your Domain Assistant"
=======
  app_title: "Your Domain Assistant"
  icon: "🤖"
>>>>>>> Stashed changes
  example_queries:
    - "Example query 1"
    - "Example query 2"

model:
<<<<<<< Updated upstream
  model_name: "gpt-4.1"
  temperature: 0.1
=======
  default_model: "gpt-4o"
  temperature: 0.1
  additional_models:
    - "gpt-4o-mini"
    - "gpt-4.1"
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
def your_tool_name(param1: str) -> str:
    """
    Tool implementation
    """
    # Your logic here
    return "Tool result"
```

### 3. Add Domain Documents
=======
TOOLS = [get_record_info, delete_record, search_qa]
```

#### Text-to-SQL + retrieval pattern (healthcare / bank)

The current domains use three tool types:
>>>>>>> Stashed changes

| Tool type | Pattern |
|-----------|---------|
| Lookup | `get_*_info(id)` → `generate_sql(..., operation="select")` → `_execute_*_sql(sql)` |
| Delete | `delete_*_record(id)` → `generate_sql(..., operation="delete")` → `_execute_*_delete_sql(sql)` |
| Search | `search_*_qa(query)` → pgvector retrieval |

Set these constants at the top of `logic.py`:

<<<<<<< Updated upstream
Run this command once when adding a new domain:
```bash
python helpers/setup_vectordb.py your_domain_name
```

This creates a persistent vector database at `domains/your_domain_name/chroma_db/` that only needs to be set up once per domain.

### 5. Update App Configuration (Temporary)

In `app.py`, change the domain configuration:
```python
DOMAIN = "your_domain_name"  # Change this line
```

*Note: This step is temporary while we finalize multi-domain support in the UI.*
=======
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
python helpers/setup_vectordb.py your_domain local
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
>>>>>>> Stashed changes

## Underlying Architecture

### Data Flow

1. **User Input** → Streamlit UI captures user message
2. **Agent Processing** → AgentFactory creates domain-specific agent
3. **Tool Execution** → Agent decides which tools to call based on user intent
<<<<<<< Updated upstream
4. **RAG Integration** → Vector database provides relevant context when needed
5. **Response Generation** → Agent synthesizes final response
6. **Observability** → All interactions logged to Galileo automatically

=======
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

>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
├── documentation/          # Setup guides and documentation
│   ├── MULTI_DOMAIN_SETUP.md  # Multi-domain configuration guide
│   └── POSTGRES_SETUP.md      # PostgreSQL/pgvector setup instructions
>>>>>>> Stashed changes
├── agent_frameworks/        # Agent framework implementations
│   └── langgraph/
│       ├── agent.py         # LangGraph agent implementation
│       └── langgraph_rag.py # RAG integration for LangGraph
├── domains/                 # Domain-specific configurations
│   ├── healthcare/         # Example healthcare domain
│   └── bank/               # Example bank domain
│       ├── config.yaml     # Domain configuration
│       ├── system_prompt.json
<<<<<<< Updated upstream
│       ├── dataset.csv     # Evaluation data
│       ├── docs/          # RAG documents
│       └── tools/         # Domain tools
├── helpers/                # Utility scripts
│   ├── setup_vectordb.py  # Vector database setup
│   └── test_vectordb.py   # Vector database testing
=======
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
>>>>>>> Stashed changes
└── tools/                 # Shared tools
    └── rag_retrieval.py   # General RAG functionality (Currently Unused)
```

### For Sales Engineers

As an SE, you primarily need to focus on the `domains/` directory:

- **To customize for a demo**: Update the domain configuration files
- **To add new use cases**: Create a new domain following the structure above
- **For troubleshooting**: If you encounter issues with other files, reach out to the FDE team immediately

The system is designed so that domain customization requires just configuration updates and document additions.

## Running Experiments

This repo now supports running Galileo experiments programmatically! You can:
- 📊 Create synthetic datasets via Galileo API
- 🧪 Run experiments with your agent
- 📈 Evaluate with built-in metrics
- 🔍 Track everything in Galileo Console

### Quick Start

```bash
# Run experiment with inline test data
python experiment_cli.py --inline --experiment quick-test

# Or with a Galileo dataset
python experiment_cli.py --dataset-name my-dataset --experiment baseline-v1
```

See **[EXPERIMENTS_README.md](EXPERIMENTS_README.md)** for detailed instructions.

## Live Stock Data & News (Optional)

The finance agent can use **real-time stock prices** instead of mock data!

### 🎛️ Easiest: Use UI Controls

**No configuration files needed!**

1. Run: `streamlit run app.py`
2. **Sidebar** → "⚙️ Live Data Settings"
3. **Toggle ON** "Use Live Stock Data"
4. Ask: "What's the price of AAPL?" → Real-time data!

See **[UI_CONTROLS_GUIDE.md](UI_CONTROLS_GUIDE.md)** for details.

### Alternative: Command Line Setup

```bash
# 1. Install yfinance
pip install yfinance

# 2. Enable live data
echo 'USE_LIVE_DATA = "true"' >> .streamlit/secrets.toml

# 3. Run app
streamlit run app.py
```

### Or Use Setup Script

<<<<<<< Updated upstream
```bash
./setup_live_data.sh
```

**Supports:**
- ✅ Yahoo Finance (yfinance) - Free, no API key needed
- ✅ Alpha Vantage - Free tier with API key, includes news
- ✅ Automatic fallback to mock data if APIs fail

See **[LIVE_DATA_SETUP.md](LIVE_DATA_SETUP.md)** for full documentation.
=======
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
>>>>>>> Stashed changes

## Chaos Engineering (Testing Galileo Insights)

<<<<<<< Updated upstream
Simulate real-world failures to test Galileo's observability and guardrails!
=======
- **[Agent Control](https://agentcontrol.dev/)** — open-source control plane for AI agents
- Reference implementation: `training/getting_started/09_guardrails/09_sample_app_postgres_steer.py`
>>>>>>> Stashed changes

### Quick Chaos Test

```bash
streamlit run app.py
```

**Sidebar → 🔥 Chaos Engineering → Enable:**
- 🔢 **Sloppiness** - Transposes numbers (simulates hallucinations)
- 🔌 **Tool Instability** - Random API failures
- 📚 **RAG Disconnects** - Vector DB failures
- ⏱️ **Rate Limits** - API quota errors
- 💥 **Data Corruption** - Wrong/invalid data

**Then ask**: "What's the price of AAPL?" (repeat 5-10 times)

**Result**: Chaos creates varied failures that Galileo Insights will detect and recommend fixes for!

See **[CHAOS_ENGINEERING.md](CHAOS_ENGINEERING.md)** and **[CHAOS_QUICK_START.md](CHAOS_QUICK_START.md)** for details.

## Galileo Guardrails (Production Safety)

Real-time content filtering and safety for production deployments!

### Quick Start

```bash
pip install galileo-protect
streamlit run app.py
```

**Sidebar → 🛡️ Galileo Guardrails → Enable**

### Protections

**Input Filtering:**
- 🔒 **PII Detection** - Blocks SSN, account numbers, credit cards
- 🚫 **Sexism Detection** - Filters discriminatory content
- ⚠️ **Toxicity Detection** - Blocks harmful language

**Output Filtering:**
- 🔒 **PII Leakage Prevention** - Stops sensitive data exposure
- 🚫 **Inappropriate Content** - Blocks sexist/toxic responses
- ⚠️ **Safety Layer** - Comprehensive content filtering

**Trade Protection:**
- 📊 **Context Adherence** - Blocks trades < 70% confidence
- 🎯 **Hallucination Detection** - Catches wrong amounts/prices
- ⛔ **Auto-Block** - Prevents suspicious trades

### Test It

1. **Enable guardrails** (sidebar toggle)
2. **Try**: "Show me my account information"
3. **See**: 🛡️ **Guardrail Active** - PII blocked!

**Other tests:**
- "My SSN is 123-45-6789" → Input PII blocked
- Enable chaos + "Buy 10 shares" → Trade blocked if hallucinated

**Result:** Production-ready safety with real-time monitoring!

See **[GUARDRAILS_GUIDE.md](GUARDRAILS_GUIDE.md)** for full documentation.

## What's Coming Next

- **Live deployment URL** for easy demo access without local setup
- **Direct links to Galileo sessions/spans** from the UI
- **Hallucination logging buttons** for interactive evaluation
- ✅ **Experiment integration** for A/B testing different prompts/models *(now available!)*
- **Galileo Protect integration** for safety and compliance monitoring

## Updates and Issues

If you encounter any issues or have feedback please contact the FDE team via slack
