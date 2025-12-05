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
- Pinecone API keys (for both local and hosted environments)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd galileo-golden-demo
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install requirements**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure secrets**
   Copy the secrets template and add your API keys:
   ```bash
   cp .streamlit/secrets.toml.template .streamlit/secrets.toml
   ```
   
   Edit `.streamlit/secrets.toml` with your actual API keys:
   ```toml
   # API Keys
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

5. **Run the Streamlit app**
   ```bash
   streamlit run app.py
   ```

The app will be available at `http://localhost:8501`

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

model:
  model_name: "gpt-4.1"
  temperature: 0.1

rag:
  enabled: true
  chunk_size: 1000
  chunk_overlap: 200
  top_k: 5

tools:
  - "your_tool_name"

vectorstore:
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
# For local demos
python helpers/setup_vectordb.py your_domain_name local

# For hosted demos  
python helpers/setup_vectordb.py your_domain_name hosted
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

### Understanding Chaos Modes

Each chaos mode tests different aspects of your AI system and demonstrates what Galileo can detect:

#### 1. **Sloppiness** (Data Corruption in Transit)

**What it simulates**: Tool outputs getting corrupted during transmission to the LLM (e.g., numbers changing between tool execution and LLM processing)

**Example**: Tool returns `$178.45` → LLM receives `$423.89`

**What Galileo detects**:
- ✅ **Span-level metrics**: PASS (tool executed correctly)
- ❌ **Trace-level metrics**: FAIL (LLM response contains wrong data)
- ❌ **Session-level metrics**: FAIL (overall conversation quality degraded)

**Observability story**: "The tool worked fine, but something went wrong between the tool and the LLM. Galileo can detect when the LLM is working with corrupted data."

#### 2. **Tool Instability** (API Failures)

**What it simulates**: External API calls failing (network errors, timeouts, 500 errors)

**Example**: `get_stock_price()` returns `{"error": "Service temporarily unavailable", "status_code": 503}`

**What Galileo detects**:
- ❌ **Span-level metrics**: FAIL (tool execution failed)
- ❌ **Trace-level metrics**: FAIL (query couldn't be answered)
- ❌ **Session-level metrics**: FAIL (user experience degraded)

**Observability story**: "External dependencies are unreliable. Galileo tracks when and how often your tools fail."

#### 3. **RAG Disconnects**

**What it simulates**: Vector database or retrieval system becoming unavailable

**Example**: RAG tool returns `{"error": "Vector database connection failed", "status_code": 503}`

**What Galileo detects**:
- ❌ **Context quality metrics**: FAIL (no context retrieved)
- ❌ **Trace-level metrics**: FAIL (response lacks grounding)
- Enables testing how your agent handles knowledge base outages

**Observability story**: "Your RAG system went down. Galileo shows when agents are operating without proper context."

#### 4. **Rate Limiting**

**What it simulates**: Hitting API rate limits on external services

**Example**: Tool calls get delayed or rejected with `429 Too Many Requests`

**What Galileo detects**:
- ⚠️ **Latency metrics**: Degraded (increased response times)
- ❌ **Reliability metrics**: FAIL (some requests blocked)

**Observability story**: "You're hitting rate limits. Galileo tracks latency and helps you identify bottlenecks."

#### 5. **Data Corruption** (Future: LLM Hallucination)

**What it simulates**: Currently corrupts tool data. Future: LLM making up information despite correct tool outputs.

**Future observability story**: "The LLM hallucinated despite having correct data. Galileo's hallucination detection catches this."

### How to Use Chaos Modes

1. **Enable in UI**: Toggle chaos modes in the sidebar under "Chaos Engineering"
2. **Run Queries**: Ask normal questions - chaos is injected automatically based on configured rates
3. **Check Galileo**: View traces in Galileo Console to see detected issues
4. **Reset Stats**: Click "Reset Stats" to clear chaos counters between demos

### What Makes This Special

- 🌍 **Domain-Agnostic**: Works automatically across all domains without custom code
- 🎯 **Targeted Testing**: Each mode tests specific observability capabilities
- 📊 **Real-time Stats**: See chaos injection rates and counts in the UI
- 🔧 **Demo-Ready**: Perfect for showing Galileo's detection capabilities in action

### Learn More

- **[Full Chaos Documentation](documentation/CHAOS_ENGINEERING.md)** - Complete technical guide
- **[Quick Start Guide](documentation/CHAOS_QUICK_START.md)** - Get started in 2 minutes

## What's Coming Next

- **Live deployment URL** for easy demo access without local setup

## Updates and Issues

If you encounter any issues or have feedback please contact the FDE team via slack
