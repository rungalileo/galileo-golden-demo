# Galileo Golden Demo

A multi-turn agentic system that showcases Galileo across multiple domains and agent frameworks, designed to be used for product demos. The code itself is reusable and configurable for a variety of use cases.

## What This Repo Is

A multi-turn agentic system showcasing Galileo's observability capabilities with configurable domains and RAG integration. Built to be reusable for product demos with minimal setup time.

## What This Repo Isn't

Not a production reference architecture or replacement for customer-specific POCs requiring heavy customization.

## Getting Started

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.com/) running locally (default: `http://localhost:11434`)
- Galileo API key
- Pinecone API keys (for both local and hosted environments)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd galileo-golden-demo
   ```

<<<<<<< Updated upstream
2. **Set up virtual environment**
=======
2. **Install Ollama on Mac and pull models**

   This demo uses **Ollama** for local inference when the sidebar **Model provider** is set to **Local (Ollama)**. The default chat model is **`gemma4`**.

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
   ollama pull llama3.1
   ollama pull llama3.2
   ollama pull deepseek-r1
   ollama pull mistral
   ollama pull qwen2.5
   ```

   Ollama serves models at `http://localhost:11434` by default. Override the URL in `.streamlit/secrets.toml` if needed:

   ```toml
   ollama_base_url = "http://localhost:11434"
   ollama_default_chat_model = "gemma4"
   ```

3. **Start PostgreSQL with pgvector (Docker)**

   Install Docker Desktop (macOS) and make sure it’s running:

   - Install: https://docs.docker.com/desktop/setup/install/mac-install/
   - Start Docker Desktop: open **Docker** from Applications and wait until it shows “Docker Desktop is running”.
   - Verify in a terminal:
     ```bash
     docker --version
     docker ps
     ```

   Then start Postgres with pgvector:

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
>>>>>>> Stashed changes
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

<<<<<<< Updated upstream
3. **Install requirements**
=======
5. **Install requirements**
>>>>>>> Stashed changes
   ```bash
   pip install -r requirements.txt
   ```

<<<<<<< Updated upstream
4. **Configure secrets**
   Copy the secrets template and add your API keys:
   ```bash
   cp .streamlit/secrets.toml.template .streamlit/secrets.toml
   ```
=======
6. **Configure secrets**
   Create `.streamlit/secrets.toml` with your API keys:
>>>>>>> Stashed changes
   
   Edit `.streamlit/secrets.toml` with your actual API keys:
   ```toml
   # Ollama (local LLM — no API key required)
   ollama_base_url = "http://localhost:11434"
   ollama_default_chat_model = "gemma4"
   ollama_embedding_model = "nomic-embed-text"

   # OpenAI (optional — for sidebar "Hosted (OpenAI)" provider)
   openai_api_key = "your_openai_api_key_here"

   galileo_api_key = "your_galileo_api_key_here"
   
   # Galileo Configuration
   galileo_console_url = "https://console.galileo.ai"  # or your custom URL
   
   # Pinecone Configuration
   pinecone_api_key_local = "your_local_project_api_key"
   pinecone_api_key_hosted = "your_hosted_project_api_key"
   
   # Environment: "local" for development, "hosted" for production
   environment = "local"
   ```
   
   **Note:** Galileo project names are configured per-domain in `domains/{domain}/config.yaml`

<<<<<<< Updated upstream
5. **Run the Streamlit app**
=======
7. **Set up vector databases**
   RAG always uses the local Ollama embedding index (`{domain}_local_index`), even when chat runs on Hosted (OpenAI). Load documents for each domain you plan to use:

   ```bash
   python helpers/setup_vectordb.py healthcare local
   python helpers/setup_vectordb.py bank local
   ```

8. **Run the Streamlit app**
>>>>>>> Stashed changes
   ```bash
   streamlit run app.py
   ```

The app will be available at `http://localhost:8501`

## Model Selection

Use the **sidebar → Model** section to choose how the app runs:

- **Local (Ollama)** — uses models pulled locally (default: `gemma4`). See step 2 above for Mac install and `ollama pull gemma4`.
- **Hosted (OpenAI)** — uses OpenAI models via `openai_api_key` in `.streamlit/secrets.toml`.

The **Select Model** dropdown lists provider-specific models from each domain's `config.yaml`. The selection applies to both **Chat** and **Experiments**, and you can change it mid-session without losing conversation history.

## Multi-Domain Support

This demo supports **multiple domains** with automatic routing and separate Galileo projects per domain. The app automatically discovers all domains in the `domains/` directory and creates navigation pages for each.

Each domain automatically gets its own Galileo project using the convention: `galileo-demo-{domain_name}` (e.g., `galileo-demo-finance`). You can optionally override this in the domain's `config.yaml`.

**📖 For detailed multi-domain setup instructions, see [documentation/MULTI_DOMAIN_SETUP.md](documentation/MULTI_DOMAIN_SETUP.md)**

## How to Add a New Domain

This demo code is designed to easily be extended to different domains, that way, SE's can spend less time writing code and more time focusing on how to display Galileo in the best light. 

Adding a new domain is straightforward - simply copy the existing finance domain structure and customize the components:

### 1. Create Domain Directory Structure

```bash
mkdir domains/your_domain_name
cd domains/your_domain_name
```

Create the following structure:
```
your_domain_name/
├── config.yaml          # Domain configuration
├── system_prompt.json   # System prompt for the agent
├── dataset.csv          # Evaluation dataset (optional)
├── docs/               # RAG documents
│   ├── document1.pdf
│   └── document2.csv
└── tools/              # Domain-specific tools
    ├── schema.json     # Tool definitions (OpenAI format)
    └── logic.py        # Tool implementation
```

### 2. Configure Domain Settings

**config.yaml** - Main configuration file:
```yaml
domain:
  name: "your_domain"
  description: "Your domain description"

# Galileo Configuration (OPTIONAL)
# If not specified, defaults to: "galileo-demo-{domain_name}"
# galileo:
#   project: "custom-project-name"      # Override default project name
#   log_stream: "custom-stream"         # Override default log stream

ui:
  app_title: "Your Domain Assistant"
  icon: "🤖"  # Icon for navigation (optional, defaults to 🤖)
  example_queries:
    - "Example query 1"
    - "Example query 2"

# Model configuration (OpenAI family)
# default_model: used by default; additional_models: list shown in the sidebar selector
model:
<<<<<<< Updated upstream
  default_model: "gpt-4.1"
  temperature: 0.1
  additional_models:
    - "gpt-4o"
    - "gpt-4o-mini"
    - "gpt-4.1"
=======
  default_model: "gemma4"
  temperature: 0.1
  additional_models:
    - "llama3.1"
    - "deepseek-r1"
    - "llama3.2"
    - "mistral"
>>>>>>> Stashed changes

rag:
  enabled: true
  chunk_size: 1000
  chunk_overlap: 200
  top_k: 5

tools:
  - "your_tool_name"

vectorstore:
<<<<<<< Updated upstream
  embedding_model: "text-embedding-3-large"

# Optional: Add Galileo Protect (see Protect section below)
# protect:
#   metrics:
#     - name: "prompt_injection"
#       operator: "any"
#       target_values: ["impersonation", "obfuscation"]
#   messages:
#     - "I cannot process that request."

# Optional: Hallucination demo examples (see Hallucination Demo section below)
# demo_hallucinations:
#   - question: "Sample question"
#     hallucinated_answer: "Wrong answer"
#     context:
#       - "Real context"
=======
  embedding_model: "nomic-embed-text"
>>>>>>> Stashed changes
```

**system_prompt.json** - Define the agent's behavior:
```json
{
  "system_prompt": "You are a helpful assistant for [your domain]. Your role is to..."
}
```

**tools/schema.json** - Define available tools in OpenAI function format:
```json
[
  {
    "name": "your_tool_name",
    "description": "What your tool does",
    "parameters": {
      "type": "object",
      "properties": {
        "param1": {
          "type": "string",
          "description": "Parameter description"
        }
      },
      "required": ["param1"]
    }
  }
]
```

**tools/logic.py** - Implement tool functionality:
```python
def your_tool_name(param1: str) -> str:
    """
    Tool implementation
    """
    # Your logic here
    return "Tool result"

 TOOLS = [your_tool_name]
```

Make sure you export your tools in this file by creating a `TOOLS` array at the end of your file

### 3. Add Domain Documents

Place your RAG documents in the `docs/` directory:
- PDFs, text files, CSVs are all supported
- Documents will be automatically chunked and embedded

### 4. Set Up Vector Database

The app uses Pinecone for vector storage. This is a **one-time setup** per domain and environment:

```bash
<<<<<<< Updated upstream
# For local demos
python helpers/setup_vectordb.py your_domain_name local

# For hosted demos  
python helpers/setup_vectordb.py your_domain_name hosted
=======
python helpers/setup_vectordb.py your_domain local
>>>>>>> Stashed changes
```

**Important Notes:**
- You need both project API keys to create indexes using the setup scripts
- Once indexes are created, you only need the environment and matching API key in your secrets file
- This processes documents from `domains/your_domain_name/docs/` directory
- Creates Pinecone indexes that persist in the cloud and don't need to be rebuilt

See [documentation/PINECONE_SETUP.md](documentation/PINECONE_SETUP.md) for detailed configuration instructions.

### 5. Test Your Domain

That's it! The app will automatically discover your new domain:

```bash
streamlit run app.py
```

Your domain will be available at:
- Root URL: `http://localhost:8501` (defaults to "finance" domain, or first available domain)
- Direct URL: `http://localhost:8501/your_domain_name`

### 6. Create a Domain README (Optional but Recommended)

Create a `README.md` in your domain directory to help users understand what questions they can ask. This is especially helpful for demos and testing.

See `domains/finance/README.md` and `domains/healthcare/README.md` for complete examples.

### How To Add a Domain with Cursor
Watch the following video tutorial to see how you can add a new domain using cursor: https://drive.google.com/file/d/1yM0dMa9uNNJay1q9gfPZJ3eTJ4lPB129/view?usp=drive_link

## Underlying Architecture

### Data Flow

1. **User Input** → Streamlit UI captures user message
2. **Agent Processing** → AgentFactory creates domain-specific agent
3. **Tool Execution** → Agent decides which tools to call based on user intent
4. **RAG Integration** → Pinecone vector database provides relevant context when needed
5. **Response Generation** → Agent synthesizes final response
6. **Observability** → All interactions logged to Galileo automatically

### Vector Database Architecture

The app uses **Pinecone** for vector storage with environment-based configuration:

- **Local Demos**: Uses `galileo-demo-local` Pinecone project
- **Hosted Demos (i.e. streamlit)**: Uses `galileo-demo-hosted` Pinecone project
- **Index Naming**: `{domain}-{environment}-index` (e.g., `finance-local-index`)
- **Automatic Selection**: When the app executes vectorDB searches, the app automatically uses the correct project based on environment setting

See [documentation/PINECONE_SETUP.md](documentation/PINECONE_SETUP.md) for detailed configuration instructions.

## Code Structure

```
galileo-golden-demo/
├── app.py                    # Streamlit application entry point
├── agent_factory.py          # Agent creation and management
├── base_agent.py            # Abstract base agent class
├── domain_manager.py        # Domain configuration management
├── setup_env.py            # Environment setup utilities
├── run_streamlit.py        # Alternative app runner
├── requirements.txt         # Python dependencies
├── documentation/          # Setup guides and documentation
│   ├── MULTI_DOMAIN_SETUP.md  # Multi-domain configuration guide
│   └── PINECONE_SETUP.md      # Pinecone setup instructions
├── agent_frameworks/        # Agent framework implementations
│   └── langgraph/
│       ├── agent.py         # LangGraph agent implementation
│       └── langgraph_rag.py # RAG integration for LangGraph
├── domains/                 # Domain-specific configurations
│   └── finance/            # Example finance domain
│       ├── config.yaml     # Domain configuration
│       ├── system_prompt.json
│       ├── dataset.csv     # Evaluation data
│       ├── docs/          # RAG documents (for vectorDB)
│       └── tools/         # Domain tools
├── experiments/            # Experiment system (UI + CLI)
│   ├── experiment_helpers.py  # Shared experiment functions
│   ├── run_experiment.py      # CLI script to run experiments
│   ├── create_galileo_dataset.py  # CLI script to create datasets
│   └── README.md              # Detailed experiments documentation
├── helpers/                # Utility scripts
│   ├── setup_vectordb.py  # Pinecone vector database setup
│   ├── test_vectordb.py   # Vector database testing
│   ├── protect_helpers.py # Galileo Protect stage setup and rulesets
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

## Galileo Protect Integration

The demo includes **Galileo Protect** for runtime protection against harmful content. Protect can be enabled from the sidebar and is fully configurable per domain.

### How to Enable

1. **Enable in UI**: Toggle "Enable Prompt Injection Protection" in the sidebar
2. **Automatic Setup**: The app automatically creates and configures a Protect stage
3. **Runtime Protection**: Each query is checked against configured rules before processing
4. **Observability**: All Protect checks are logged to Galileo along with agent traces

### Configuring Protect for Your Domain

Add a `protect` section to your domain's `config.yaml`:

```yaml
# Protect configuration
protect:
  metrics:
    - name: "prompt_injection"
      operator: "any"
      target_values:
        - "impersonation"
        - "obfuscation"
        - "simple_instruction"
        - "few_shot"
        - "new_context"
    - name: "input_toxicity"
      operator: "gt"
      threshold: 0.95
  messages:
    - "I'm sorry, but I cannot process that request."
    - "I've detected harmful content. Please rephrase your query."
```

### What You Get

- **Domain-Specific Rules**: Configure different protection rules for each domain
- **Multiple Metrics**: Combine prompt injection, toxicity, PII detection, and more
- **Custom Messages**: Define what users see when Protect triggers
- **Full Observability**: All checks logged to Galileo with complete trace visibility
- **Automatic Routing**: Harmful queries are blocked before reaching your agent

### Learn More

- **[Protect Overview](https://v2docs.galileo.ai/concepts/protect/overview)** - Complete guide to runtime protection concepts and metrics
- **[LangChain Integration](https://v2docs.galileo.ai/sdk-api/third-party-integrations/langchain/protect)** - Using Protect with LangChain and LangGraph

## Hallucination Demo

The demo includes a **Hallucination Demo** feature to showcase Galileo's hallucination detection. It can be fired two ways: from the sidebar button, **or directly from the chat** when the user's message contains configured trigger keywords. Both paths produce the same Galileo trace shape.

> ⚠️ **Heads up for presenters**: when a chat message matches a configured trigger, the agent will respond with the **intentionally wrong** canned answer (the LLM is bypassed for that turn). This is by design — the wrong answer + correct retrieved context is what gives Galileo's hallucination / context-adherence metrics something to score against. If you don't want hallucinations firing in chat, remove or comment out the `trigger_keywords` from the domain's `demo_hallucinations` entries.

### How It Works

**Path 1 — Sidebar button**
1. Click "Log Hallucination" in the sidebar.
2. A trace is logged to Galileo with the configured `question`, `context`, and `hallucinated_answer`.

**Path 2 — Chat trigger** *(new)*
1. User types something matching a hallucination's `trigger_keywords` (case-insensitive substring AND — every keyword must appear in the message).
2. The agent short-circuits and responds with the configured `hallucinated_answer`.
3. The same trace as Path 1 is logged to Galileo, but the trace input is the user's actual wording (not the canned `question`).
4. Each domain's second **example query button** is intentionally crafted to contain the trigger keywords, so demos can fire the hallucination with a single click as well.

In Galileo, the trace looks like a normal RAG query:
- Trace name: `"Agent"`
- Spans: `RAG Retrieval` (with the **correct** context) and `LLM Response` (with the **wrong** answer)
- Session name: `"{Domain} Agent Demo"`

No `"Hallucination Demo"` branding in the trace, so it blends in with real production traces.

### Configuring Hallucinations for Your Domain

Add a `demo_hallucinations` section to your domain's `config.yaml`:

```yaml
demo_hallucinations:
  - question: "What was the Q4 revenue?"
    # Optional. If present, the chat will trigger the canned answer when
    # ALL keywords appear (case-insensitive) in the user's message. Omit
    # to disable chat-triggering for this hallucination (sidebar button
    # still works).
    trigger_keywords: ["broadcom", "q4", "revenue"]
    hallucinated_answer: "Revenue was $9.3B, up 4% from the previous quarter."
    # NOTE: The real answer in context says "up 4% from a year ago"
    context:
      - "Q4 revenue was $9.3 billion, up 4% from a year ago."
      - "Additional context documents..."
```

**Tips for picking `trigger_keywords`:**
- Keep them short (1–3 words each), specific to the question, and unlikely to appear in unrelated queries.
- Use **2–3 keywords combined** rather than one — `["broadcom", "revenue"]` is safer than `["revenue"]` (which would fire on any revenue question).
- Multi-word phrases work: `["free shipping", "return"]` requires both phrases.

**Tip for `example_queries`**: write the second entry so it naturally contains the trigger keywords. That way the button click and the typed phrase both produce the demo. See `domains/healthcare/config.yaml` for an example.

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
