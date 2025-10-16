"""
Galileo Demo App with Experiments Support
"""
import uuid
import streamlit as st
import os
import pandas as pd
import threading

# ============================================================================
# CRITICAL: Load environment variables BEFORE any LangChain imports!
# LangSmith checks LANGCHAIN_TRACING_V2 when langchain modules are imported
# ============================================================================
from dotenv import load_dotenv, find_dotenv
from setup_env import setup_environment

# 1) load global/shared first
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
# 2) then load per-app .env (if present) to override selectively
load_dotenv(find_dotenv(usecwd=True), override=True)

# 3) Load from secrets.toml
# This runs once when the module is first imported
# Environment variables persist for the entire Python process
# Check if already loaded to avoid printing the message multiple times
if not os.getenv('_GALILEO_ENV_LOADED'):
    setup_environment()
    os.environ['_GALILEO_ENV_LOADED'] = 'true'

# ============================================================================
# CRITICAL: Initialize Phoenix BEFORE importing LangChain!
# Phoenix instrumentation must be set up before LangChain modules are loaded
# ============================================================================
phoenix_endpoint = os.getenv("PHOENIX_ENDPOINT")
phoenix_api_key = os.getenv("PHOENIX_API_KEY")
phoenix_project = os.getenv("PHOENIX_PROJECT", "galileo-demo")

# Store Phoenix/Arize credentials for later initialization
# Actual initialization happens after session state is available
_phoenix_credentials_available = bool(phoenix_endpoint and phoenix_api_key)
_arize_credentials_available = bool(os.getenv("ARIZE_API_KEY") and os.getenv("ARIZE_SPACE_ID"))

# Read OTLP platform preference from file
def _get_otlp_preference():
    """Read the OTLP platform preference from file"""
    pref_file = os.path.join(os.path.dirname(__file__), ".otlp_preference")
    try:
        if os.path.exists(pref_file):
            with open(pref_file, "r") as f:
                return f.read().strip().lower()
    except:
        pass
    return "phoenix"  # Default to Phoenix

def _save_otlp_preference(platform):
    """Save the OTLP platform preference to file"""
    pref_file = os.path.join(os.path.dirname(__file__), ".otlp_preference")
    try:
        with open(pref_file, "w") as f:
            f.write(platform.lower())
    except Exception as e:
        print(f"Failed to save OTLP preference: {e}")

_otlp_preference = _get_otlp_preference()

def _initialize_phoenix_otlp():
    """Initialize Phoenix OTLP tracing (must be called before LangChain imports)"""
    if os.getenv('_PHOENIX_INITIALIZED'):
        return True
    
    print(f"\n🔭 Initializing Phoenix (before LangChain import)...")
    
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk import trace as trace_sdk
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        
        # Create OTLP exporter with Bearer token auth and project headers
        exporter = OTLPSpanExporter(
            endpoint=phoenix_endpoint,
            headers={
                "authorization": f"Bearer {phoenix_api_key}",
                "project": phoenix_project,
                "x-project": phoenix_project,
                "x-project-name": phoenix_project,
            }
        )
        
        # Create resource with project attributes
        resource = Resource.create({
            "service.name": phoenix_project,
            "project.name": phoenix_project,
            "openinference.project.name": phoenix_project,
        })
        
        # Create tracer provider with resource and BatchSpanProcessor
        tracer_provider = trace_sdk.TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(tracer_provider)
        
        # Instrument LangChain with OpenInference semantic conventions
        LangChainInstrumentor().instrument(
            tracer_provider=tracer_provider,
            skip_dep_check=True
        )
        
        os.environ['_PHOENIX_INITIALIZED'] = 'true'
        print(f"   ✅ Phoenix initialized with BatchSpanProcessor")
        print(f"   Project: {phoenix_project}")
        print(f"   Endpoint: {phoenix_endpoint}")
        return True
    except Exception as e:
        print(f"   ⚠️  Phoenix pre-init failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Global flag to prevent re-initialization (more reliable than env var in Streamlit)
_arize_ax_initialized = False

def _initialize_arize_ax_otlp():
    """Initialize Arize AX OTLP tracing (must be called before LangChain imports)"""
    global _arize_ax_initialized
    
    if _arize_ax_initialized:
        return True  # Silent return if already initialized
    
    print(f"\n🔭 Initializing Arize AX (before LangChain import)...")
    
    space_id = os.getenv("ARIZE_SPACE_ID")
    api_key = os.getenv("ARIZE_API_KEY")
    project = os.getenv("ARIZE_PROJECT", "galileo-demo")
    
    if not space_id or not api_key:
        print(f"   ❌ Arize AX credentials not set!")
        return False
    
    try:
        # Use manual OTLP setup (same as Phoenix) which we know sends traces successfully
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk import trace as trace_sdk
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        
        # Arize OTLP endpoint (HTTP)
        arize_endpoint = "https://otlp.arize.com/v1/traces"
        
        # Create OTLP exporter with Arize-specific headers
        # Based on Arize documentation for HTTP OTLP
        exporter = OTLPSpanExporter(
            endpoint=arize_endpoint,
            headers={
                "authorization": api_key,
                "space_id": space_id,
                "model_id": project,
                "model_version": "production",
            }
        )
        
        # Create resource with OpenInference-specific attributes
        # These are critical for Arize to classify span types
        resource = Resource.create({
            "service.name": project,
            "model_id": project,
            "model_version": "production",
            # OpenInference attributes for proper span classification
            "openinference.project.name": project,
        })
        
        # Create tracer provider with resource and BatchSpanProcessor
        tracer_provider = trace_sdk.TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(tracer_provider)
        
        # Instrument LangChain with OpenInference semantic conventions
        # This adds the span.kind and other attributes needed for type classification
        LangChainInstrumentor().instrument(
            tracer_provider=tracer_provider,
            skip_dep_check=True
        )
        
        # Mark as initialized
        _arize_ax_initialized = True
        os.environ['_ARIZE_AX_INITIALIZED'] = 'true'
        
        print(f"   ✅ Arize AX initialized with BatchSpanProcessor + OpenInference")
        print(f"   Model ID: {project}")
        print(f"   Endpoint: {arize_endpoint}")
        return True
    except Exception as e:
        print(f"   ❌ Arize AX pre-init failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Initialize OTLP platform at module load based on saved preference (ONCE ONLY)
# This code runs ONCE when the module is first imported
if not os.getenv('_OTLP_INITIALIZED'):
    if _otlp_preference == "phoenix" and _phoenix_credentials_available:
        _initialize_phoenix_otlp()
    elif _otlp_preference == "arize ax" and _arize_credentials_available:
        _initialize_arize_ax_otlp()
    os.environ['_OTLP_INITIALIZED'] = 'true'

# NOW we can import LangChain - Phoenix instrumentation is ready!
import phoenix as px
from galileo import galileo_context
from agent_factory import AgentFactory
from langchain_core.messages import AIMessage, HumanMessage
from arize.otel import register as arize_register
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from braintrust import init_logger as braintrust_init_logger
from braintrust_langchain import BraintrustCallbackHandler, set_global_handler as braintrust_set_global_handler

# Tracing initialization will happen inside multi_domain_agent_app() where st.session_state is available
def _initialize_callback_platforms():
    st.session_state.tracing_initialized = True
    
    print("\n🔧 Initializing callback-based observability platforms...")
    platforms_enabled = []
    
    # ============================================================================
    # OTLP Platforms (Phoenix/Arize AX) - Already initialized at module load
    # ============================================================================
    if os.getenv('_PHOENIX_INITIALIZED'):
        platforms_enabled.append("Phoenix")
        print(f"✅ Phoenix - initialized at module load")
    elif os.getenv('_ARIZE_AX_INITIALIZED'):
        platforms_enabled.append("Arize AX")
        print(f"✅ Arize AX - initialized at module load")
    else:
        print(f"⏭️  No OTLP platform enabled")
    
    # ============================================================================
    # LANGSMITH - Uses callbacks (only if enabled in UI)
    # ============================================================================
    if hasattr(st.session_state, 'logger_langsmith') and st.session_state.logger_langsmith:
        langsmith_api_key = os.getenv("LANGCHAIN_API_KEY")
        langsmith_project = os.getenv("LANGCHAIN_PROJECT")
        
        if langsmith_api_key:
            try:
                # Create explicit LangSmith tracer callback
                from langchain.callbacks.tracers import LangChainTracer
                from langsmith import Client
                
                langsmith_client = Client(api_key=langsmith_api_key)
                langsmith_tracer = LangChainTracer(
                    project_name=langsmith_project,
                    client=langsmith_client
                )
                
                st.session_state.langsmith_tracer = langsmith_tracer
                platforms_enabled.append("LangSmith")
                print(f"✅ LangSmith tracing initialized")
                print(f"   🎯 Traces will go to project: {langsmith_project}")
            except Exception as e:
                print(f"   ⚠️ Failed to create LangSmith tracer: {e}")
        else:
            print(f"   ⚠️ LangSmith enabled but missing LANGCHAIN_API_KEY")
    else:
        print(f"   ⏭️  LangSmith disabled (UI toggle off)")
    
    # ============================================================================
    # LANGFUSE - Callback handler (only if enabled in UI)
    # ============================================================================
    if hasattr(st.session_state, 'logger_langfuse') and st.session_state.logger_langfuse:
        try:
            langfuse_pk = os.getenv("LANGFUSE_API_PK")
            langfuse_sk = os.getenv("LANGFUSE_API_SK")
            langfuse_host = os.getenv("LANGFUSE_HOST_URL") or os.getenv("LANGFUSE_HOST")
            
            if langfuse_pk and langfuse_sk and langfuse_host:
                langfuse = Langfuse(public_key=langfuse_pk, secret_key=langfuse_sk, host=langfuse_host)
                st.session_state.langfuse_handler = LangfuseCallbackHandler()
                platforms_enabled.append("Langfuse")
                print(f"✅ Langfuse callback initialized")
            else:
                print(f"   ⚠️ Langfuse enabled but missing credentials")
        except Exception as e:
            print(f"   ⚠️ Failed to initialize Langfuse: {e}")
    else:
        print(f"   ⏭️  Langfuse disabled (UI toggle off)")
    
    # ============================================================================
    # BRAINTRUST - Callback handler (only if enabled in UI)
    # ============================================================================
    if hasattr(st.session_state, 'logger_braintrust') and st.session_state.logger_braintrust:
        try:
            braintrust_api_key = os.getenv("BRAINTRUST_API_KEY")
            braintrust_project = os.getenv("BRAINTRUST_PROJECT")
            
            if braintrust_api_key and braintrust_project:
                braintrust_init_logger(api_key=braintrust_api_key, project=braintrust_project)
                st.session_state.braintrust_handler = BraintrustCallbackHandler()
                braintrust_set_global_handler(st.session_state.braintrust_handler)
                platforms_enabled.append("Braintrust")
                print(f"✅ Braintrust callback initialized")
            else:
                print(f"   ⚠️ Braintrust enabled but missing credentials")
        except Exception as e:
            print(f"   ⚠️ Failed to initialize Braintrust: {e}")
    else:
        print(f"   ⏭️  Braintrust disabled (UI toggle off)")
    
    # ============================================================================
    # SUMMARY
    # ============================================================================
    print(f"\n🎉 Tracing initialized for {len(platforms_enabled)} platform(s): {', '.join(platforms_enabled)}")
    print(f"   Note: Galileo tracing via GalileoCallback (initialized per-agent)\n")


# Configuration - easily changeable for different domains
DOMAIN = "finance"  # Could be "healthcare", "legal", etc.
FRAMEWORK = "LangGraph"


def escape_dollar_signs(text: str) -> str:
    """Escape dollar signs in text to prevent LaTeX interpretation."""
    return text.replace('$', '\\$')


def display_chat_history():
    """Display all messages in the chat history with agent attribution."""
    if not st.session_state.messages:
        return

    for message_data in st.session_state.messages:
        if isinstance(message_data, dict):
            message = message_data.get("message")

            if isinstance(message, HumanMessage):
                with st.chat_message("user"):
                    st.write(escape_dollar_signs(message.content))
            elif isinstance(message, AIMessage):
                with st.chat_message("assistant"):
                    st.write(escape_dollar_signs(message.content))
        else:
            # Fallback for old message format
            if isinstance(message_data, HumanMessage):
                with st.chat_message("user"):
                    st.write(escape_dollar_signs(message_data.content))
            elif isinstance(message_data, AIMessage):
                with st.chat_message("assistant"):
                    st.write(escape_dollar_signs(message_data.content))


def show_example_queries(query_1: str, query_2: str):
    """Show example queries demonstrating the finance system"""
    st.subheader("💡 Try these examples")

    # Use a container with custom CSS to reduce spacing
    with st.container():
        col1, col2 = st.columns([0.48, 0.48])

        with col1:
            if st.button(query_1, key="query_1", use_container_width=True):
                return query_1

        with col2:
            if st.button(query_2, key="query_2", use_container_width=True):
                return query_2
    return None


def orchestrate_streamlit_and_get_user_input(
    agent_title: str, example_query_1: str, example_query_2: str
):
    """Set up the Streamlit interface and get user input - simplified like John Deere example"""
    # App title and description
    st.title(agent_title)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        session_id = str(uuid.uuid4())[:10]
        st.session_state.session_id = session_id
        try:
            galileo_context.start_session(name="Finance Agent Demo", external_id=session_id)
        except Exception as e:
            st.error(f"Failed to start Galileo session: {str(e)}")
            st.stop()

    # Show example queries
    example_query = show_example_queries(example_query_1, example_query_2)

    # Display chat history
    display_chat_history()

    # Get user input
    user_input = st.chat_input("How can I help you?...")
    # Use example query if button was clicked
    if example_query:
        user_input = example_query
    return user_input


def process_input_for_simple_app(user_input: str | None):
    """Process user input and generate response - using AgentFactory directly"""
    if user_input:
        # Add user message to chat history
        user_message = HumanMessage(content=user_input)
        st.session_state.messages.append({"message": user_message, "agent": "user"})

        # Display the user message immediately
        with st.chat_message("user"):
            st.write(escape_dollar_signs(user_input))

        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                # Convert session state messages to the format expected by the agent
                conversation_messages = []
                for msg_data in st.session_state.messages:
                    if isinstance(msg_data, dict) and "message" in msg_data:
                        message = msg_data["message"]
                        if isinstance(message, HumanMessage):
                            conversation_messages.append({"role": "user", "content": message.content})
                        elif isinstance(message, AIMessage):
                            conversation_messages.append({"role": "assistant", "content": message.content})
                

                # Get the actual response from the agent
                response = st.session_state.agent.process_query(conversation_messages)

                # Create and display AI message
                ai_message = AIMessage(content=response)
                st.session_state.messages.append(
                    {"message": ai_message, "agent": "assistant"}
                )

                # Display response
                st.write(escape_dollar_signs(response))

        # Rerun to update chat history
        st.rerun()


def render_chat_tab(app_title: str, example_queries: list):
    """Render the chat interface tab"""
    user_input = orchestrate_streamlit_and_get_user_input(
        app_title,
        example_queries[0] if len(example_queries) > 0 else "Hello, how can you help me?",
        example_queries[1] if len(example_queries) > 1 else "What can you do?",
    )
    
    # Create agent dynamically using AgentFactory - works for any domain!
    if "agent" not in st.session_state:
        st.session_state.agent = st.session_state.factory.create_agent(
            domain=DOMAIN, 
            framework=FRAMEWORK,
            session_id=st.session_state.session_id
        )
    
    process_input_for_simple_app(user_input)


def run_experiment_background(experiment_config):
    """Run experiment in background (called from UI)"""
    import run_experiment as exp_module
    from galileo.schema.metrics import GalileoScorers
    
    try:
        # Update status
        st.session_state.experiment_status = "running"
        st.session_state.experiment_progress = "Initializing experiment..."
        
        # Prepare metrics
        metrics = []
        if experiment_config.get("metric_context_adherence"):
            metrics.append(GalileoScorers.context_adherence)
        if experiment_config.get("metric_completeness"):
            metrics.append(GalileoScorers.completeness)
        if experiment_config.get("metric_correctness"):
            metrics.append(GalileoScorers.correctness)
        if experiment_config.get("metric_toxicity"):
            metrics.append(GalileoScorers.output_toxicity)
        if experiment_config.get("metric_chunk_attribution"):
            metrics.append(GalileoScorers.chunk_attribution_utilization)
        
        if not metrics:
            metrics = None  # Use defaults
        
        # Prepare dataset
        dataset = None
        dataset_name = None
        dataset_id = None
        
        if experiment_config["dataset_source"] == "galileo_name":
            dataset_name = experiment_config["dataset_name"]
        elif experiment_config["dataset_source"] == "galileo_id":
            dataset_id = experiment_config["dataset_id"]
        elif experiment_config["dataset_source"] in ["inline", "csv_file"]:
            dataset = experiment_config["inline_data"]
        
        # Temporarily set project name from config
        original_project = exp_module.PROJECT_NAME
        exp_module.PROJECT_NAME = experiment_config["project_name"]
        
        # Run experiment
        results = exp_module.run_galileo_experiment(
            experiment_name=experiment_config["experiment_name"],
            dataset_name=dataset_name,
            dataset_id=dataset_id,
            inline_dataset=dataset,
            metrics=metrics
        )
        
        # Restore original project name
        exp_module.PROJECT_NAME = original_project
        
        # Store results
        st.session_state.experiment_results = results
        st.session_state.experiment_status = "completed"
        
        # Format progress message based on results type
        if isinstance(results, list):
            st.session_state.experiment_progress = f"Completed! Processed {len(results)} rows."
        else:
            st.session_state.experiment_progress = f"Completed! Check Galileo Console for results."
        
    except Exception as e:
        st.session_state.experiment_status = "failed"
        st.session_state.experiment_progress = f"Error: {str(e)}"
        st.session_state.experiment_error = str(e)
        import traceback
        st.session_state.experiment_traceback = traceback.format_exc()


def render_experiments_tab():
    """Render the experiments configuration and execution tab"""
    st.header("🧪 Run Experiments")
    
    st.markdown("""
    Configure and run Galileo experiments to evaluate your agent's performance.
    Experiments will process your dataset through the agent and evaluate with Galileo metrics.
    """)
    
    # Initialize experiment state
    if "experiment_status" not in st.session_state:
        st.session_state.experiment_status = "idle"
    if "experiment_results" not in st.session_state:
        st.session_state.experiment_results = None
    
    # Dataset Source Selection (OUTSIDE form so it updates immediately)
    st.subheader("📊 Dataset Source")
    dataset_source = st.radio(
        "Choose dataset source:",
        ["galileo_name", "galileo_id", "inline", "csv_file"],
        format_func=lambda x: {
            "galileo_name": "Galileo Dataset (by name)",
            "galileo_id": "Galileo Dataset (by ID)",
            "inline": "Sample Test Data",
            "csv_file": "Upload CSV File"
        }[x],
        help="Where to get the evaluation dataset",
        key="dataset_source_radio"
    )
    
    # Initialize dataset variables
    dataset_name = None
    dataset_id = None
    inline_data = None
    
    # Handle dataset input based on source (OUTSIDE form for immediate updates)
    if dataset_source == "galileo_name":
        st.markdown("**Enter the name of your dataset in Galileo:**")
        dataset_name = st.text_input(
            "Dataset Name",
            placeholder="e.g., finance-queries-synthetic",
            help="Name of the dataset in Galileo",
            key="dataset_name_input"
        )
    
    elif dataset_source == "galileo_id":
        st.markdown("**Enter the ID of your dataset in Galileo:**")
        dataset_id = st.text_input(
            "Dataset ID",
            placeholder="e.g., abc-123-def",
            help="ID of the dataset in Galileo",
            key="dataset_id_input"
        )
    
    elif dataset_source == "inline":
        st.info("✓ Using built-in sample dataset (5 finance queries)")
        inline_data = [
            {
                "input": "What was Costco's revenue for Q3 2024?",
                "output": "Costco reported net sales of $62.15 billion for Q3 2024.",
            },
            {
                "input": "How is the S&P 500 performing this year?",
                "output": "The S&P 500 has shown strong performance in 2024.",
            },
            {
                "input": "Should I invest in technology stocks?",
                "output": "I can provide information but cannot give personalized investment advice.",
            },
            {
                "input": "What are the current market trends?",
                "output": "Current market trends show continued growth in tech and AI sectors.",
            },
            {
                "input": "Can you explain what a 10-Q filing is?",
                "output": "A 10-Q is a quarterly report filed by public companies with the SEC.",
            }
        ]
        
    elif dataset_source == "csv_file":
        uploaded_file = st.file_uploader(
            "Upload CSV file",
            type=["csv"],
            help="CSV with columns: input, output (optional), context (optional)",
            key="csv_uploader"
        )
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.success(f"✓ Loaded {len(df)} rows")
                st.dataframe(df.head(), use_container_width=True)
                inline_data = df.to_dict('records')
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
    
    st.divider()
    
    # Experiment Configuration Form
    with st.form("experiment_config"):
        st.subheader("📋 Experiment Configuration")
        
        # Experiment name
        experiment_name = st.text_input(
            "Experiment Name",
            value=f"finance-agent-eval-{pd.Timestamp.now().strftime('%Y%m%d-%H%M')}",
            help="Unique name for this experiment run"
        )
        
        # Project name
        project_name = st.text_input(
            "Galileo Project",
            value=os.getenv("GALILEO_PROJECT", "finance-agent-experiments"),
            help="Galileo project where results will be stored"
        )
        
        st.divider()
        
        # Metrics Selection
        st.subheader("📏 Evaluation Metrics")
        st.markdown("Select which metrics to evaluate:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            metric_context_adherence = st.checkbox(
                "Context Adherence",
                value=True,
                help="How well the response adheres to provided context"
            )
            metric_completeness = st.checkbox(
                "Completeness",
                value=True,
                help="Coverage of query requirements"
            )
            metric_correctness = st.checkbox(
                "Correctness",
                value=True,
                help="Accuracy compared to expected output"
            )
        
        with col2:
            metric_toxicity = st.checkbox(
                "Toxicity",
                value=True,
                help="Detection of harmful content"
            )
            metric_chunk_attribution = st.checkbox(
                "Chunk Attribution & Utilization",
                value=True,
                help="RAG retrieval quality - whether chunks were used in the response"
            )
        
        st.divider()
        
        # Submit button
        submitted = st.form_submit_button(
            "🚀 Run Experiment",
            type="primary",
            use_container_width=True
        )
        
        if submitted:
            # Validate inputs
            validation_error = None
            
            if not experiment_name or not experiment_name.strip():
                validation_error = "Please provide an experiment name"
            elif dataset_source == "galileo_name" and (not dataset_name or not dataset_name.strip()):
                validation_error = "Please provide a dataset name (cannot be empty)"
            elif dataset_source == "galileo_id" and (not dataset_id or not dataset_id.strip()):
                validation_error = "Please provide a dataset ID (cannot be empty)"
            elif dataset_source == "csv_file" and not inline_data:
                validation_error = "Please upload a CSV file"
            
            if validation_error:
                st.error(validation_error)
            else:
                # Store config and trigger experiment
                experiment_config = {
                    "experiment_name": experiment_name,
                    "project_name": project_name,
                    "dataset_source": dataset_source,
                    "dataset_name": dataset_name,
                    "dataset_id": dataset_id,
                    "inline_data": inline_data,
                    "metric_context_adherence": metric_context_adherence,
                    "metric_completeness": metric_completeness,
                    "metric_correctness": metric_correctness,
                    "metric_toxicity": metric_toxicity,
                    "metric_chunk_attribution": metric_chunk_attribution,
                }
                
                st.session_state.current_experiment = experiment_config
                st.session_state.experiment_status = "queued"
                st.rerun()
    
    # Display experiment status
    if st.session_state.experiment_status != "idle":
        st.divider()
        st.subheader("📊 Experiment Status")
        
        if st.session_state.experiment_status == "queued":
            with st.spinner("Starting experiment..."):
                # Run experiment
                run_experiment_background(st.session_state.current_experiment)
                st.rerun()
        
        elif st.session_state.experiment_status == "running":
            st.info("⏳ Experiment is running...")
            if "experiment_progress" in st.session_state:
                st.write(st.session_state.experiment_progress)
            
            # Show progress bar
            progress_bar = st.progress(0)
            st.caption("Processing queries through agent...")
        
        elif st.session_state.experiment_status == "completed":
            st.success("✅ Experiment completed successfully!")
            
            if st.session_state.experiment_results is not None:
                results = st.session_state.experiment_results
                
                # Check if results is a list/dict and has content
                if isinstance(results, list) and len(results) > 0:
                    st.write(f"📊 Processed {len(results)} rows")
                    
                    # Show sample results
                    st.subheader("Sample Results")
                    try:
                        st.json(results[0] if isinstance(results[0], dict) else str(results[0]))
                    except Exception as e:
                        st.warning(f"Could not display sample result: {e}")
                        st.code(str(results[0]))
                elif isinstance(results, dict):
                    st.write(f"📊 Experiment completed")
                    st.subheader("Results")
                    st.json(results)
                else:
                    st.write(f"📊 Experiment completed")
                    st.info("Results returned successfully (check Galileo Console for details)")
            else:
                st.info("📊 Experiment completed - check Galileo Console for results")
            
            # Link to Galileo Console
            st.markdown("---")
            st.markdown("### 🔗 View Full Results")
            st.markdown(f"""
            View detailed results in [Galileo Console](https://console.galileo.ai):
            - Project: `{st.session_state.current_experiment['project_name']}`
            - Experiment: `{st.session_state.current_experiment['experiment_name']}`
            """)
            
            # Reset button
            if st.button("Run Another Experiment", type="secondary"):
                st.session_state.experiment_status = "idle"
                st.session_state.experiment_results = None
                st.rerun()
        
        elif st.session_state.experiment_status == "failed":
            st.error(f"❌ Experiment failed")
            if "experiment_error" in st.session_state:
                st.error(st.session_state.experiment_error)
                with st.expander("View error details"):
                    if "experiment_traceback" in st.session_state:
                        st.code(st.session_state.experiment_traceback)
                    else:
                        st.code(st.session_state.experiment_error)
            
            # Reset button
            if st.button("Try Again", type="secondary"):
                st.session_state.experiment_status = "idle"
                st.rerun()
    
    # Help section
    with st.expander("ℹ️ Help & Documentation"):
        st.markdown("""
        ### How to Run Experiments
        
        1. **Choose a dataset source:**
           - Galileo Dataset: Use a dataset you've created in Galileo Console
           - Sample Data: Quick test with 5 built-in queries
           - CSV Upload: Use your own CSV file (needs `input` column)
        
        2. **Select metrics:**
           - Context Adherence: Requires `context` field in dataset
           - Correctness: Requires `output` or `expected_output` field
           - Other metrics work with just `input` field
        
        3. **Run the experiment:**
           - Click "Run Experiment" to start
           - Results will appear in Galileo Console
        
        ### Creating Datasets
        
        - **Synthetic Data:** Ask AI to create via MCP tool
        - **Manual:** Use Galileo Console to create/upload datasets
        - **CSV Format:** Columns: `input` (required), `output` (optional), `context` (optional)
        
        ### Resources
        
        - [Experiments Guide](EXPERIMENTS_README.md)
        - [Quick Start](QUICKSTART_EXPERIMENTS.md)
        - [Galileo Console](https://console.galileo.ai)
        """)


def run_dataset_background(run_config):
    """Run dataset through agent in background (called from Runs UI)"""
    from galileo.datasets import get_dataset
    from galileo import galileo_context
    import uuid
    import os
    
    try:
        # Update status
        st.session_state.run_status = "running"
        st.session_state.run_progress = "Initializing run..."
        
        # Get Galileo project from environment
        project_name = os.getenv("GALILEO_PROJECT", "finance-agent-demo")
        
        # Get session mode (multi-turn vs single-turn)
        session_mode = run_config.get('session_mode', 'multi_turn')
        run_name = run_config.get('run_name', 'Dataset Run')
        
        # For multi-turn: start one session for all queries
        # For single-turn: we'll create a new session for each query
        run_session_id = f"run-{uuid.uuid4().hex[:8]}"
        
        if session_mode == 'multi_turn':
            print(f"\n🚀 Starting Multi-turn Galileo session: {run_name}")
            print(f"   Project: {project_name} (set via GALILEO_PROJECT env)")
            print(f"   Session ID: {run_session_id}")
            print(f"   Mode: All queries in one session")
            
            try:
                # Start session (project determined by GALILEO_PROJECT environment variable)
                galileo_context.start_session(
                    name=run_name,
                    external_id=run_session_id
                )
                print(f"   ✓ Session started successfully")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not start Galileo session: {e}")
                print("   Logs may not be captured properly")
        else:
            print(f"\n🚀 Starting Single-turn run: {run_name}")
            print(f"   Project: {project_name}")
            print(f"   Mode: Each query gets its own session")
            # Sessions will be created per-query in the loop
        
        # Get dataset
        dataset = None
        if run_config["dataset_source"] == "galileo_name":
            st.session_state.run_progress = f"Fetching dataset: {run_config['dataset_name']}..."
            dataset = get_dataset(name=run_config["dataset_name"])
        elif run_config["dataset_source"] == "galileo_id":
            st.session_state.run_progress = f"Fetching dataset ID: {run_config['dataset_id']}..."
            dataset = get_dataset(id=run_config["dataset_id"])
        elif run_config["dataset_source"] in ["inline", "csv_file"]:
            dataset = run_config["inline_data"]
        
        if not dataset:
            raise ValueError("Failed to load dataset")
        
        # Convert to list if needed
        if not isinstance(dataset, list):
            try:
                # Galileo Dataset - use get_content() to get the actual data
                if hasattr(dataset, 'get_content'):
                    dataset_content = dataset.get_content()
                    print(f"  Got dataset content: {type(dataset_content)}")
                    # Convert content to list of dicts
                    if hasattr(dataset_content, 'rows'):
                        # Convert DatasetRow objects to dictionaries
                        # IMPORTANT: Extract just the values_dict, not the full row structure
                        converted_rows = []
                        for row in dataset_content.rows:
                            row_dict = None
                            
                            # Method 1: Access values_dict.additional_properties directly (the actual data)
                            if hasattr(row, 'values_dict') and hasattr(row.values_dict, 'additional_properties'):
                                row_dict = row.values_dict.additional_properties
                            
                            # Method 2: Try to access values_dict as dict
                            elif hasattr(row, 'values_dict'):
                                try:
                                    if hasattr(row.values_dict, 'items'):
                                        row_dict = {k: v for k, v in row.values_dict.items()}
                                    else:
                                        row_dict = row.values_dict
                                except:
                                    # Fallback to the full row.to_dict() which includes metadata
                                    if hasattr(row, 'to_dict') and callable(row.to_dict):
                                        full_row = row.to_dict()
                                        # Extract just the values_dict part
                                        if isinstance(full_row, dict) and 'values_dict' in full_row:
                                            row_dict = full_row['values_dict']
                                        else:
                                            row_dict = full_row
                            
                            # Method 3: Already a dict
                            elif isinstance(row, dict):
                                row_dict = row
                            
                            if row_dict is not None:
                                converted_rows.append(row_dict)
                            else:
                                print(f"  Warning: Could not convert row of type {type(row)}")
                        
                        dataset = converted_rows
                    elif isinstance(dataset_content, list):
                        dataset = dataset_content
                    else:
                        # Try to convert to list
                        dataset = list(dataset_content)
                elif hasattr(dataset, 'content'):
                    # Try content property
                    dataset_content = dataset.content
                    print(f"  Got dataset content via property: {type(dataset_content)}")
                    if hasattr(dataset_content, 'rows'):
                        # Convert DatasetRow objects to dictionaries (same logic as above)
                        # Extract just the values_dict, not the full row structure
                        converted_rows = []
                        for row in dataset_content.rows:
                            row_dict = None
                            
                            # Method 1: Access values_dict.additional_properties directly
                            if hasattr(row, 'values_dict') and hasattr(row.values_dict, 'additional_properties'):
                                row_dict = row.values_dict.additional_properties
                            
                            # Method 2: Try to access values_dict as dict
                            elif hasattr(row, 'values_dict'):
                                try:
                                    if hasattr(row.values_dict, 'items'):
                                        row_dict = {k: v for k, v in row.values_dict.items()}
                                    else:
                                        row_dict = row.values_dict
                                except:
                                    if hasattr(row, 'to_dict') and callable(row.to_dict):
                                        full_row = row.to_dict()
                                        if isinstance(full_row, dict) and 'values_dict' in full_row:
                                            row_dict = full_row['values_dict']
                                        else:
                                            row_dict = full_row
                            
                            # Method 3: Already a dict
                            elif isinstance(row, dict):
                                row_dict = row
                            
                            if row_dict is not None:
                                converted_rows.append(row_dict)
                        
                        dataset = converted_rows
                    elif isinstance(dataset_content, list):
                        dataset = dataset_content
                    else:
                        dataset = list(dataset_content)
                else:
                    raise ValueError(f"Dataset type {type(dataset)} has no get_content() or content")
                print(f"  Converted dataset to list: {len(dataset)} rows")
                
                # Debug: Show first row structure
                if dataset:
                    print(f"  First row type: {type(dataset[0])}")
                    print(f"  First row keys: {list(dataset[0].keys()) if isinstance(dataset[0], dict) else 'Not a dict'}")
                    if isinstance(dataset[0], dict):
                        print(f"  First row sample: {dict(list(dataset[0].items())[:3])}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise ValueError(f"Failed to convert dataset to list (type: {type(dataset)}): {e}")
        
        st.session_state.run_progress = f"Loaded {len(dataset)} rows from dataset"
        
        # Get number of cycles
        num_cycles = run_config.get("num_cycles", 1)
        
        # Initialize agent factory
        st.session_state.run_progress = "Initializing agent..."
        
        # Ensure factory exists
        if "factory" not in st.session_state:
            from agent_factory import AgentFactory
            st.session_state.factory = AgentFactory()
        
        # For multi-turn: create one agent with the session_id
        # For single-turn: we'll create a new agent for each query
        agent = None
        if session_mode == 'multi_turn':
            # Create agent with the run's session ID so logs are properly associated
            print(f"   Creating agent with session_id: {run_session_id}")
            agent = st.session_state.factory.create_agent(
                domain=DOMAIN,
                framework=FRAMEWORK,
                session_id=run_session_id  # Use same session_id as Galileo session
            )
            
            if agent is None:
                raise ValueError("Failed to create agent - agent is None")
            if not hasattr(agent, 'process_query'):
                raise ValueError(f"Agent missing process_query method. Agent type: {type(agent)}")
            
            print(f"   ✓ Agent created successfully")
        else:
            print(f"   Agent will be created for each query")
        
        # Track results
        total_processed = 0
        total_rows = len(dataset) * num_cycles
        
        # Cycle through dataset
        print(f"\n📋 Starting processing:")
        print(f"   Dataset size: {len(dataset)} rows")
        print(f"   Cycles: {num_cycles}")
        print(f"   Total queries: {total_rows}")
        
        for cycle in range(num_cycles):
            st.session_state.run_progress = f"Cycle {cycle + 1}/{num_cycles} - Processing rows..."
            print(f"\n🔁 Cycle {cycle + 1}/{num_cycles}")
            
            for idx, row in enumerate(dataset):
                # Get input - rows should now be flat dicts with actual data
                if isinstance(row, dict):
                    user_input = row.get('input', '') or row.get('query', '') or row.get('text', '')
                else:
                    user_input = ""
                
                if not user_input:
                    if idx == 0:
                        # Debug first row to understand structure
                        print(f"   Debug: First row keys - {list(row.keys()) if isinstance(row, dict) else 'not a dict'}")
                        if isinstance(row, dict) and len(row) > 0:
                            print(f"   Debug: First few items - {dict(list(row.items())[:3])}")
                    print(f"   ⚠️  Skipping row {idx + 1} - no input found")
                    continue
                
                # Update progress
                total_processed += 1
                st.session_state.run_progress = (
                    f"Cycle {cycle + 1}/{num_cycles} - "
                    f"Row {idx + 1}/{len(dataset)} - "
                    f"Total: {total_processed}/{total_rows}"
                )
                
                # Process through agent
                # Single-turn mode: create session and agent for each query
                # Multi-turn mode: use existing session and agent
                messages = [{"role": "user", "content": user_input}]
                
                if session_mode == 'single_turn':
                    # Create a unique session for this query
                    query_session_id = f"run-{uuid.uuid4().hex[:8]}"
                    query_name = f"{run_name} - Query {total_processed}"
                    
                    try:
                        # Start session for this query (project set via environment)
                        galileo_context.start_session(
                            name=query_name,
                            external_id=query_session_id
                        )
                        
                        # Create agent for this query
                        query_agent = st.session_state.factory.create_agent(
                            domain=DOMAIN,
                            framework=FRAMEWORK,
                            session_id=query_session_id
                        )
                        
                        # Process the query
                        print(f"  🔄 Processing row {idx + 1}/{len(dataset)}: {user_input[:60]}...")
                        response = query_agent.process_query(messages)
                        print(f"  ✓ Completed (response length: {len(response)} chars)")
                        
                        # Session will auto-close when agent goes out of scope
                        
                    except Exception as e:
                        # Log error but continue
                        print(f"  ✗ Error processing row {idx + 1}: {e}")
                        import traceback
                        traceback.print_exc()
                        response = f"Error: {str(e)}"
                
                else:  # multi_turn mode
                    try:
                        if agent.process_query is None:
                            raise ValueError("agent.process_query is None")
                        
                        # Process the query - GalileoCallback will log everything
                        print(f"  🔄 Processing row {idx + 1}/{len(dataset)}: {user_input[:60]}...")
                        response = agent.process_query(messages)
                        print(f"  ✓ Completed (response length: {len(response)} chars)")
                        
                    except Exception as e:
                        # Log error but continue
                        print(f"  ✗ Error processing row {idx + 1}: {e}")
                        import traceback
                        traceback.print_exc()
                        response = f"Error: {str(e)}"
        
        # Store results
        st.session_state.run_results = {
            "total_rows": len(dataset),
            "num_cycles": num_cycles,
            "total_processed": total_processed
        }
        st.session_state.run_status = "completed"
        st.session_state.run_progress = f"Completed! Processed {total_processed} total queries ({len(dataset)} rows × {num_cycles} cycles)"
        
        # Sessions auto-close when agents go out of scope
        print(f"\n✅ Processing complete:")
        print(f"   Total processed: {total_processed} queries")
        
        if session_mode == 'multi_turn':
            print(f"   Session: {run_name} (will auto-close)")
            print(f"\n💡 View logs in Galileo Console:")
            print(f"   Project: {project_name}")
            print(f"   Session: {run_name}")
        else:
            print(f"   All sessions will auto-close (single-turn mode)")
            print(f"\n💡 View logs in Galileo Console:")
            print(f"   Project: {project_name}")
            print(f"   Sessions: {run_name} - Query 1 through {total_processed}")
        
    except Exception as e:
        # Sessions will auto-close on error
        st.session_state.run_status = "failed"
        st.session_state.run_progress = f"Error: {str(e)}"
        st.session_state.run_error = str(e)
        import traceback
        st.session_state.run_traceback = traceback.format_exc()


def render_runs_tab():
    """Render the dataset runs tab for creating real logs"""
    st.header("🔄 Dataset Runs")
    
    st.markdown("""
    Pull a dataset from Galileo and run it through your agent to create **real production logs**.
    
    This is different from experiments:
    - **Experiments**: Evaluation mode with metrics and scorers
    - **Runs**: Production mode creating real session logs in Galileo
    
    Use this to:
    - Generate logs for chaos testing
    - Populate your Galileo project with realistic data
    - Test guardrails with multiple scenarios
    - Create baseline logs for monitoring
    """)
    
    # Initialize run state
    if "run_status" not in st.session_state:
        st.session_state.run_status = "idle"
    if "run_results" not in st.session_state:
        st.session_state.run_results = None
    
    # Dataset Source Selection (OUTSIDE form so it updates immediately)
    st.subheader("📊 Dataset Source")
    dataset_source = st.radio(
        "Choose dataset source:",
        ["galileo_name", "galileo_id", "inline", "csv_file"],
        format_func=lambda x: {
            "galileo_name": "Galileo Dataset (by name)",
            "galileo_id": "Galileo Dataset (by ID)",
            "inline": "Sample Test Data",
            "csv_file": "Upload CSV File"
        }[x],
        help="Where to get the dataset for the run",
        key="run_dataset_source_radio"
    )
    
    # Initialize dataset variables
    dataset_name = None
    dataset_id = None
    inline_data = None
    
    # Handle dataset input based on source (OUTSIDE form for immediate updates)
    if dataset_source == "galileo_name":
        st.markdown("**Enter the name of your dataset in Galileo:**")
        dataset_name = st.text_input(
            "Dataset Name",
            placeholder="e.g., finance-queries-synthetic",
            help="Name of the dataset in Galileo",
            key="run_dataset_name_input"
        )
    
    elif dataset_source == "galileo_id":
        st.markdown("**Enter the ID of your dataset in Galileo:**")
        dataset_id = st.text_input(
            "Dataset ID",
            placeholder="e.g., abc-123-def",
            help="ID of the dataset in Galileo",
            key="run_dataset_id_input"
        )
    
    elif dataset_source == "inline":
        st.info("✓ Using built-in sample dataset (5 finance queries)")
        inline_data = [
            {"input": "What was Costco's revenue for Q3 2024?"},
            {"input": "How is the S&P 500 performing this year?"},
            {"input": "Should I invest in technology stocks?"},
            {"input": "What are the current market trends?"},
            {"input": "Can you explain what a 10-Q filing is?"}
        ]
        
    elif dataset_source == "csv_file":
        uploaded_file = st.file_uploader(
            "Upload CSV file",
            type=["csv"],
            help="CSV with 'input' column",
            key="run_csv_uploader"
        )
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.success(f"✓ Loaded {len(df)} rows")
                st.dataframe(df.head(), use_container_width=True)
                inline_data = df.to_dict('records')
            except Exception as e:
                st.error(f"Error reading CSV: {e}")
    
    st.divider()
    
    # Run Configuration Form
    with st.form("run_config"):
        st.subheader("⚙️ Run Configuration")
        
        # Run name
        run_name = st.text_input(
            "Run Name",
            value=f"dataset-run-{pd.Timestamp.now().strftime('%Y%m%d-%H%M')}",
            help="Descriptive name for this run"
        )
        
        # Number of cycles
        num_cycles = st.number_input(
            "Number of Cycles",
            min_value=1,
            max_value=100,
            value=1,
            help="How many times to cycle through the entire dataset (e.g., 3 means each row will be processed 3 times)"
        )
        
        # Session grouping option
        session_mode = st.radio(
            "Session Grouping",
            options=["multi_turn", "single_turn"],
            format_func=lambda x: {
                "multi_turn": "Multi-turn (All queries in one session)",
                "single_turn": "Single-turn (Each query as separate session)"
            }[x],
            help="Multi-turn groups all queries under one session. Single-turn creates a separate session for each query.",
            horizontal=True
        )
        
        if session_mode == "multi_turn":
            st.info(f"💡 This will process the dataset **{num_cycles}** time(s). All queries will be grouped in **one session**.")
        else:
            total_sessions = len(st.session_state.get('inline_data', [])) * num_cycles if dataset_source in ["inline", "csv_file"] else "N"
            st.info(f"💡 This will process the dataset **{num_cycles}** time(s). Each query will create a **separate session** (total: {total_sessions} sessions).")
        
        st.divider()
        
        # Show current settings that will be honored
        st.subheader("🎛️ Active Settings")
        st.markdown("This run will honor your current chaos and guardrails settings:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Guardrails:**")
            if "guardrails_enabled" in st.session_state and st.session_state.guardrails_enabled:
                st.success("✅ Enabled")
            else:
                st.warning("🔓 Disabled")
        
        with col2:
            st.markdown("**Chaos Engineering:**")
            chaos_count = sum([
                st.session_state.get("chaos_tool_instability", False),
                st.session_state.get("chaos_sloppiness", False),
                st.session_state.get("chaos_rag", False),
                st.session_state.get("chaos_rate_limit", False),
                st.session_state.get("chaos_data_corruption", False)
            ])
            if chaos_count > 0:
                st.warning(f"🔥 {chaos_count} mode(s) active")
            else:
                st.success("😌 All systems normal")
        
        st.caption("💡 You can change these settings in the sidebar before running")
        
        st.divider()
        
        # Submit button
        submitted = st.form_submit_button(
            "🚀 Start Run",
            type="primary",
            use_container_width=True
        )
        
        if submitted:
            # Validate inputs
            validation_error = None
            
            if not run_name or not run_name.strip():
                validation_error = "Please provide a run name"
            elif dataset_source == "galileo_name" and (not dataset_name or not dataset_name.strip()):
                validation_error = "Please provide a dataset name"
            elif dataset_source == "galileo_id" and (not dataset_id or not dataset_id.strip()):
                validation_error = "Please provide a dataset ID"
            elif dataset_source == "csv_file" and not inline_data:
                validation_error = "Please upload a CSV file"
            
            if validation_error:
                st.error(validation_error)
            else:
                # Store config and trigger run
                run_config = {
                    "run_name": run_name,
                    "dataset_source": dataset_source,
                    "dataset_name": dataset_name,
                    "dataset_id": dataset_id,
                    "inline_data": inline_data,
                    "num_cycles": num_cycles,
                    "session_mode": session_mode,
                }
                
                st.session_state.current_run = run_config
                st.session_state.run_status = "queued"
                st.rerun()
    
    # Display run status
    if st.session_state.run_status != "idle":
        st.divider()
        st.subheader("📊 Run Status")
        
        if st.session_state.run_status == "queued":
            with st.spinner("Starting run..."):
                # Run dataset
                run_dataset_background(st.session_state.current_run)
                st.rerun()
        
        elif st.session_state.run_status == "running":
            st.info("⏳ Run in progress...")
            if "run_progress" in st.session_state:
                st.write(st.session_state.run_progress)
            
            # Show progress bar
            progress_bar = st.progress(0)
            st.caption("Processing dataset through agent...")
        
        elif st.session_state.run_status == "completed":
            st.success("✅ Run completed successfully!")
            
            if st.session_state.run_results is not None:
                results = st.session_state.run_results
                
                st.write(f"📊 Run Summary:")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Dataset Rows", results.get("total_rows", 0))
                with col2:
                    st.metric("Cycles", results.get("num_cycles", 0))
                with col3:
                    st.metric("Total Processed", results.get("total_processed", 0))
            
            # Link to Galileo Console
            st.markdown("---")
            st.markdown("### 🔗 View Logs in Galileo")
            st.markdown(f"""
            Your run created real logs in Galileo. View them in [Galileo Console](https://console.galileo.ai):
            - Run name: `{st.session_state.current_run.get('run_name', 'Unknown')}`
            - Each query was processed through the agent with full logging
            - Full traces with tool calls, RAG retrievals, and agent reasoning
            - Look in your Galileo project for the logs
            """)
            
            # Reset button
            if st.button("Run Another Dataset", type="secondary"):
                st.session_state.run_status = "idle"
                st.session_state.run_results = None
                st.rerun()
        
        elif st.session_state.run_status == "failed":
            st.error(f"❌ Run failed")
            if "run_error" in st.session_state:
                st.error(f"**Error**: {st.session_state.run_error}")
                with st.expander("View full error details", expanded=True):
                    if "run_traceback" in st.session_state:
                        st.code(st.session_state.run_traceback, language="python")
                    else:
                        st.code(st.session_state.run_error, language="python")
                    
                    # Add debugging info
                    st.markdown("### Debugging Information")
                    st.write("Check the terminal/console for additional error messages.")
            
            # Reset button
            if st.button("Try Again", type="secondary"):
                st.session_state.run_status = "idle"
                st.rerun()
    
    # Help section
    with st.expander("ℹ️ Help & Documentation"):
        st.markdown("""
        ### How Dataset Runs Work
        
        **What is a Dataset Run?**
        - Pulls a dataset from Galileo (or uses inline/CSV data)
        - Processes each row through the agent as a real query
        - Creates production-style session logs in Galileo
        - Can cycle through the dataset multiple times
        
        **Difference from Experiments:**
        - **Experiments**: For evaluation with metrics and scorers
        - **Runs**: For creating real logs (testing, demos, baselines)
        
        **Use Cases:**
        - **Chaos Testing**: Enable chaos modes and run dataset to generate problematic logs
        - **Guardrails Testing**: Test how guardrails handle various inputs
        - **Demo Data**: Generate realistic logs for demos or testing
        - **Baseline Logs**: Create a baseline set of logs for monitoring
        
        ### Cycling Through Dataset
        
        If you set **Number of Cycles = 3**:
        - Each row in your dataset will be processed 3 times
        - Total queries = Dataset size × Number of cycles
        
        ### Session Grouping
        
        **Multi-turn (All queries in one session)**:
        - All queries grouped under a single Galileo session
        - Good for: Analyzing overall patterns, conversation flow simulation
        - View: One session with multiple turns
        
        **Single-turn (Each query as separate session)**:
        - Each query gets its own Galileo session
        - Good for: Independent query evaluation, easier filtering/analysis
        - View: Multiple sessions, one query each
        
        ### Settings Honored
        
        The run will use your current sidebar settings:
        - **Chaos Engineering**: All active chaos modes will apply
        - **Guardrails**: If enabled, will filter inputs/outputs
        - **Live Data**: Will use live or mock data based on your setting
        
        ### Creating Datasets
        
        - **Galileo Console**: Create datasets in your Galileo project
        - **MCP Tool**: Use AI to generate synthetic datasets
        - **CSV Upload**: Upload your own CSV with an `input` column
        
        ### Resources
        
        - [Galileo Console](https://console.galileo.ai)
        - [Chaos Engineering Guide](CHAOS_ENGINEERING.md)
        - [Guardrails Guide](GUARDRAILS_GUIDE.md)
        """)


def multi_domain_agent_app():
    """Main agent app with tabs for chat, experiments, and runs"""
    # Environment setup already done at module import time (top of file)
    # No need to call setup_environment() again
    
    # Initialize AgentFactory once
    if "factory" not in st.session_state:
        st.session_state.factory = AgentFactory()
    
    factory = st.session_state.factory
    
    # Load domain configuration for UI settings
    if "domain_config" not in st.session_state:
        domain_info = factory.get_domain_info(DOMAIN)
        st.session_state.domain_config = domain_info
    
    # Extract UI configuration from domain config
    ui_config = st.session_state.domain_config.get("ui", {})
    app_title = ui_config.get("app_title", f"🤖 {DOMAIN.title()} Assistant")
    example_queries = ui_config.get("example_queries", [
        "Hello, how can you help me?",
        "What can you do?"
    ])
    
    # Initialize session if not exists
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        session_id = str(uuid.uuid4())[:10]
        st.session_state.session_id = session_id
        try:
            galileo_context.start_session(name="Finance Agent Demo", external_id=session_id)
        except Exception as e:
            st.error(f"Failed to start Galileo session: {str(e)}")
    
    # Initialize logger toggle defaults (must be in app context, not module level)
    if "logger_phoenix" not in st.session_state:
        st.session_state.logger_phoenix = (_otlp_preference == "phoenix")
    if "logger_arize_ax" not in st.session_state:
        st.session_state.logger_arize_ax = (_otlp_preference == "arize ax")
    if "logger_langsmith" not in st.session_state:
        langsmith_available = os.getenv("LANGCHAIN_API_KEY")
        st.session_state.logger_langsmith = bool(langsmith_available)
    if "logger_langfuse" not in st.session_state:
        langfuse_available = os.getenv("LANGFUSE_API_PK") and os.getenv("LANGFUSE_API_SK")
        st.session_state.logger_langfuse = bool(langfuse_available)
    if "logger_braintrust" not in st.session_state:
        braintrust_available = os.getenv("BRAINTRUST_API_KEY") and os.getenv("BRAINTRUST_PROJECT")
        st.session_state.logger_braintrust = bool(braintrust_available)
    
    # Initialize callback-based tracing platforms (only once)
    if "tracing_initialized" not in st.session_state:
        _initialize_callback_platforms()
    
    # Sidebar with navigation and settings
    with st.sidebar:
        st.title("Navigation")
        st.markdown("---")
        
        # Session info
        st.markdown("### 📊 Session Info")
        st.caption(f"Session ID: `{st.session_state.session_id}`")
        st.caption(f"Domain: `{DOMAIN}`")
        st.caption(f"Framework: `{FRAMEWORK}`")
        
        st.markdown("---")
        
        # Live Data Settings
        st.markdown("### ⚙️ Live Data Settings")
        
        # Initialize settings if not exists
        if "use_live_data" not in st.session_state:
            # Check st.secrets first (Streamlit config), then environment variables
            use_live = False
            config_source = "default"
            
            # Try Streamlit secrets first
            try:
                if hasattr(st, 'secrets') and "USE_LIVE_DATA" in st.secrets:
                    use_live = str(st.secrets["USE_LIVE_DATA"]).lower() == "true"
                    config_source = "secrets.toml"
                else:
                    # Fall back to environment variable
                    env_value = os.getenv("USE_LIVE_DATA", "false")
                    use_live = env_value.lower() == "true"
                    if env_value != "false":
                        config_source = ".env"
            except Exception as e:
                # If secrets fails, try environment
                env_value = os.getenv("USE_LIVE_DATA", "false")
                use_live = env_value.lower() == "true"
                if env_value != "false":
                    config_source = ".env"
            
            st.session_state.use_live_data = use_live
            st.session_state.config_source = config_source
            # Sync to environment
            os.environ["USE_LIVE_DATA"] = "true" if use_live else "false"
            
        if "data_source" not in st.session_state:
            # Check st.secrets first, then environment
            try:
                if hasattr(st, 'secrets') and "STOCK_DATA_SOURCE" in st.secrets:
                    source = str(st.secrets["STOCK_DATA_SOURCE"])
                else:
                    source = os.getenv("STOCK_DATA_SOURCE", "auto")
            except:
                source = os.getenv("STOCK_DATA_SOURCE", "auto")
            st.session_state.data_source = source
            # Sync to environment
            os.environ["STOCK_DATA_SOURCE"] = source
        
        # Show where config came from and reload button
        col1, col2 = st.columns([3, 1])
        with col1:
            if hasattr(st.session_state, 'config_source'):
                st.caption(f"💡 From: {st.session_state.config_source}")
        with col2:
            if st.button("🔄", help="Reload from config", key="reload_settings", use_container_width=True):
                # Clear session state to force reload
                for key in ["use_live_data", "data_source", "config_source"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        # Toggle for live data
        use_live_data = st.toggle(
            "Use Live Stock Data",
            value=st.session_state.use_live_data,
            help="Enable real-time stock prices from APIs. Disable to use mock data.",
            key="live_data_toggle"
        )
        
        # Update session state
        if use_live_data != st.session_state.use_live_data:
            st.session_state.use_live_data = use_live_data
            # Update environment variable so tools see it
            os.environ["USE_LIVE_DATA"] = "true" if use_live_data else "false"
            # Clear agent to force reload with new settings
            if "agent" in st.session_state:
                del st.session_state.agent
            st.info("Settings updated! Agent will reinitialize with new configuration on next query.")
        
        # Source selection (only show if live data is enabled)
        if use_live_data:
            data_source = st.selectbox(
                "Data Source",
                options=["auto", "yfinance", "alpha_vantage", "finnhub"],
                format_func=lambda x: {
                    "auto": "Auto (Try All)",
                    "yfinance": "Yahoo Finance",
                    "alpha_vantage": "Alpha Vantage",
                    "finnhub": "Finnhub"
                }[x],
                index=["auto", "yfinance", "alpha_vantage", "finnhub"].index(st.session_state.data_source),
                help="Choose which API to use for stock data",
                key="data_source_select"
            )
            
            # Update session state and environment
            if data_source != st.session_state.data_source:
                st.session_state.data_source = data_source
                os.environ["STOCK_DATA_SOURCE"] = data_source
                # Clear agent to force reload with new settings
                if "agent" in st.session_state:
                    del st.session_state.agent
                st.info(f"Data source changed to {data_source}. Agent will reinitialize.")
            
            # Show status indicator
            if data_source == "auto":
                st.caption("🔄 Will try: Yahoo → Alpha Vantage → Mock")
            elif data_source == "yfinance":
                st.caption("✓ Using Yahoo Finance (no API key needed)")
            elif data_source == "alpha_vantage":
                api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
                if api_key:
                    st.caption("✓ Alpha Vantage key configured")
                else:
                    st.caption("⚠️ Alpha Vantage key not set")
            elif data_source == "finnhub":
                api_key = os.getenv("FINNHUB_API_KEY")
                if api_key:
                    st.caption("✓ Finnhub key configured")
                else:
                    st.caption("⚠️ Finnhub key not set")
        else:
            st.caption("📊 Using mock data")
        
        # Quick test button
        with st.expander("🧪 Test Live Data"):
            st.markdown("""
            **Quick Test:**
            1. Toggle live data ON above
            2. Go to Chat tab
            3. Ask: "What's the current price of AAPL?"
            4. Agent should call get_stock_price tool
            5. Check response for real-time data
            
            **Note:** Agent prefers RAG for historical data.
            Use phrases like "current price" or "price right now" 
            to trigger the live API tool.
            """)
            
            if st.button("Run Quick Test", key="test_live_data_btn"):
                # Run test
                st.code("python test_live_data_quick.py")
                st.info("Run this command in terminal to test APIs directly")
        
        st.markdown("---")
        
        # Galileo Guardrails Settings
        st.markdown("### 🛡️ Galileo Guardrails")
        st.caption("Real-time content filtering and safety")
        
        # Import guardrails
        try:
            from guardrails_config import get_guardrails_manager
            guardrails = get_guardrails_manager()
            GUARDRAILS_AVAILABLE = True
        except ImportError:
            GUARDRAILS_AVAILABLE = False
            st.warning("Guardrails not available - install galileo-protect")
        
        if GUARDRAILS_AVAILABLE:
            # Initialize guardrails settings
            if "guardrails_enabled" not in st.session_state:
                st.session_state.guardrails_enabled = guardrails.is_enabled()
            
            # Main toggle
            guardrails_enabled = st.toggle(
                "Enable Guardrails",
                value=st.session_state.guardrails_enabled,
                help="Enable Galileo Guardrails for input/output filtering and trade validation",
                key="guardrails_main_toggle"
            )
            
            if guardrails_enabled != st.session_state.guardrails_enabled:
                st.session_state.guardrails_enabled = guardrails_enabled
                if guardrails_enabled:
                    guardrails.enable()
                    os.environ["GUARDRAILS_ENABLED"] = "true"
                else:
                    guardrails.disable()
                    os.environ["GUARDRAILS_ENABLED"] = "false"
                # Force agent reinitialize
                if "agent" in st.session_state:
                    del st.session_state.agent
                st.rerun()
            
            if guardrails_enabled:
                with st.expander("⚙️ Guardrails Details", expanded=False):
                    st.markdown("""
                    **Active Protections:**
                    
                    **Input Filtering:**
                    - 🔒 PII Detection (account numbers, SSN, credit cards)
                    - 🚫 Sexism Detection
                    - ⚠️ Toxicity Detection
                    
                    **Output Filtering:**
                    - 🔒 PII Leakage Prevention
                    - 🚫 Inappropriate Content Blocking
                    - ⚠️ Harmful Content Prevention
                    
                    **Trade Protection:**
                    - 📊 Context Adherence Check (70% threshold)
                    - 🎯 Hallucination Detection
                    - ⛔ Auto-block suspicious trades
                    """)
                    
                    st.divider()
                    
                    # Show stats
                    stats = guardrails.get_stats()
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Input Checks", stats["input_checks"])
                        st.metric("Input Blocks", stats["input_blocks"])
                    
                    with col2:
                        st.metric("Output Checks", stats["output_checks"])
                        st.metric("Output Blocks", stats["output_blocks"])
                    
                    st.metric("Trade Checks", stats["trade_checks"])
                    st.metric("Trade Blocks", stats["trade_blocks"])
                    
                    if stats["input_checks"] + stats["output_checks"] + stats["trade_checks"] > 0:
                        block_rate = stats["block_rate"]
                        st.progress(block_rate / 100, text=f"Block Rate: {block_rate:.1f}%")
                    
                    if st.button("Reset Stats", key="guardrails_reset"):
                        guardrails.reset_stats()
                        st.rerun()
                
                # Test examples
                with st.expander("🧪 Test Guardrails", expanded=False):
                    st.markdown("**Try these to trigger guardrails:**")
                    
                    test_queries = [
                        ("PII Output", "Show me my account information"),
                        ("PII Input", "My SSN is 123-45-6789, can you help?"),
                        ("Hallucinated Trade", "Buy 1000 shares of XYZ"),
                    ]
                    
                    for label, query in test_queries:
                        if st.button(f"Test: {label}", key=f"test_gr_{label.replace(' ', '_')}"):
                            st.session_state.example_query_pending = query
                            st.rerun()
            
            else:
                st.info("🔓 Guardrails disabled - all content will pass through unchecked")
        
        st.markdown("---")
        
        # Chaos Engineering Settings
        st.markdown("### 🔥 Chaos Engineering")
        st.caption("Simulate real-world failures and anomalies")
        
        # Import chaos engine
        try:
            from chaos_engine import get_chaos_engine
            chaos = get_chaos_engine()
            CHAOS_ENABLED = True
        except ImportError:
            CHAOS_ENABLED = False
            st.warning("Chaos engine not available")
        
        if CHAOS_ENABLED:
            # Initialize chaos settings
            if "chaos_tool_instability" not in st.session_state:
                st.session_state.chaos_tool_instability = False
            if "chaos_sloppiness" not in st.session_state:
                st.session_state.chaos_sloppiness = False
            if "chaos_rag" not in st.session_state:
                st.session_state.chaos_rag = False
            if "chaos_rate_limit" not in st.session_state:
                st.session_state.chaos_rate_limit = False
            if "chaos_data_corruption" not in st.session_state:
                st.session_state.chaos_data_corruption = False
            
            with st.expander("⚙️ Chaos Controls", expanded=False):
                # Tool Instability
                tool_instability = st.checkbox(
                    "🔌 Tool Instability",
                    value=st.session_state.chaos_tool_instability,
                    help="Randomly fail API calls (25% chance) - simulates network issues, timeouts, service outages",
                    key="chaos_tool_instability_checkbox"
                )
                if tool_instability != st.session_state.chaos_tool_instability:
                    st.session_state.chaos_tool_instability = tool_instability
                    chaos.enable_tool_instability(tool_instability)
                    if "agent" in st.session_state:
                        del st.session_state.agent
                
                # Sloppiness (Number Transpositions)
                sloppiness = st.checkbox(
                    "🔢 Sloppiness",
                    value=st.session_state.chaos_sloppiness,
                    help="Randomly transpose numbers in responses (30% chance) - simulates hallucinations and data errors",
                    key="chaos_sloppiness_checkbox"
                )
                if sloppiness != st.session_state.chaos_sloppiness:
                    st.session_state.chaos_sloppiness = sloppiness
                    chaos.enable_sloppiness(sloppiness)
                    if "agent" in st.session_state:
                        del st.session_state.agent
                
                # RAG Chaos
                rag_chaos = st.checkbox(
                    "📚 RAG Disconnects",
                    value=st.session_state.chaos_rag,
                    help="Randomly disconnect RAG database (20% chance) - simulates vector DB failures",
                    key="chaos_rag_checkbox"
                )
                if rag_chaos != st.session_state.chaos_rag:
                    st.session_state.chaos_rag = rag_chaos
                    chaos.enable_rag_chaos(rag_chaos)
                    if "agent" in st.session_state:
                        del st.session_state.agent
                
                # Rate Limit Chaos
                rate_limit = st.checkbox(
                    "⏱️ Rate Limits",
                    value=st.session_state.chaos_rate_limit,
                    help="Randomly trigger rate limit errors (15% chance) - simulates API quota exhaustion",
                    key="chaos_rate_limit_checkbox"
                )
                if rate_limit != st.session_state.chaos_rate_limit:
                    st.session_state.chaos_rate_limit = rate_limit
                    chaos.enable_rate_limit_chaos(rate_limit)
                
                # Data Corruption
                data_corruption = st.checkbox(
                    "💥 Data Corruption",
                    value=st.session_state.chaos_data_corruption,
                    help="Randomly corrupt API responses (20% chance) - wrong prices, missing fields, invalid data",
                    key="chaos_data_corruption_checkbox"
                )
                if data_corruption != st.session_state.chaos_data_corruption:
                    st.session_state.chaos_data_corruption = data_corruption
                    chaos.enable_data_corruption(data_corruption)
                
                st.divider()
                
                # Show chaos stats
                stats = chaos.get_stats()
                if any([stats['tool_instability'], stats['sloppiness'], stats['rag_chaos'], 
                       stats['rate_limit_chaos'], stats['data_corruption']]):
                    st.markdown("**Active Chaos:**")
                    active_chaos = []
                    if stats['tool_instability']:
                        active_chaos.append("🔌 Tool Instability")
                    if stats['sloppiness']:
                        active_chaos.append(f"🔢 Sloppiness ({stats['sloppy_outputs']} so far)")
                    if stats['rag_chaos']:
                        active_chaos.append(f"📚 RAG Chaos ({stats['rag_failures']} so far)")
                    if stats['rate_limit_chaos']:
                        active_chaos.append("⏱️ Rate Limits")
                    if stats['data_corruption']:
                        active_chaos.append("💥 Data Corruption")
                    
                    for item in active_chaos:
                        st.caption(item)
                    
                    if st.button("Reset Stats", key="reset_chaos_stats"):
                        chaos.reset_stats()
                        st.rerun()
                else:
                    st.caption("No chaos active")
            
            # Quick chaos info
            active_count = sum([
                st.session_state.chaos_tool_instability,
                st.session_state.chaos_sloppiness,
                st.session_state.chaos_rag,
                st.session_state.chaos_rate_limit,
                st.session_state.chaos_data_corruption
            ])
            if active_count > 0:
                st.caption(f"🔥 {active_count} chaos mode(s) active")
            else:
                st.caption("😌 All systems normal")
        
        st.markdown("---")
        
        # Links
        st.markdown("### 🔗 Links")
        st.markdown("[Galileo Console](https://console.galileo.ai)")
        st.markdown("[Phoenix Traces](https://app.phoenix.arize.com)")
        
        st.markdown("---")
        
        # Documentation
        st.markdown("### 📚 Documentation")
        st.markdown("[Experiments Guide](https://github.com)")
        st.markdown("[Quick Start](https://github.com)")
        
        st.markdown("---")
        
        # Logger Controls (at bottom of sidebar)
        st.markdown("### 📊 Observability Platforms")
        st.caption("Galileo is always enabled")
        
        # Session state is already initialized at module level (before tracing init)
        with st.expander("⚙️ Configure Loggers", expanded=False):
            st.markdown("**OpenTelemetry Platform** (select one)")
            
            # Check if running on localhost - simpler approach
            # Check for common development environment indicators
            is_localhost = True  # Default to localhost/development mode
            
            # Check if deployed (common production environment variables)
            if os.getenv("STREAMLIT_SERVER_PORT") or os.getenv("STREAMLIT_DEPLOYMENT"):
                is_localhost = False
            
            # Override: always allow switching if explicitly set
            if os.getenv("ALLOW_OTLP_SWITCHING") == "true":
                is_localhost = True
            
            if not is_localhost:
                st.warning("⚠️ OTLP platform switching disabled in production. Change requires app restart with new environment variables.")
            else:
                st.caption("💡 **Important:** Changing OTLP platform requires a **hard reset** of the app")
                st.caption("Use Ctrl+C to stop the server, then restart with `streamlit run app.py`")
                st.caption("Callback platforms (below) work instantly without restart")
            
            # Determine current selection
            if st.session_state.logger_phoenix:
                current_otlp = "Phoenix"
            elif st.session_state.logger_arize_ax:
                current_otlp = "Arize AX"
            else:
                current_otlp = "None"
            
            # Build options based on available credentials
            otlp_options = ["None"]
            if phoenix_endpoint and phoenix_api_key:
                otlp_options.append("Phoenix")
            if os.getenv("ARIZE_API_KEY"):
                otlp_options.append("Arize AX")
            
            # Radio button for OTLP platform selection (disabled in production)
            otlp_selection = st.radio(
                "Select OTLP Platform:",
                options=otlp_options,
                index=otlp_options.index(current_otlp) if current_otlp in otlp_options else 0,
                help="Choose Phoenix or Arize AX for OpenTelemetry tracing (mutually exclusive). Requires hard reset to take effect.",
                key="otlp_radio",
                horizontal=True,
                disabled=not is_localhost
            )
            
            # Update session state based on selection
            if otlp_selection != current_otlp:
                # Save preference to file for next restart
                _save_otlp_preference(otlp_selection)
                
                # Update session state
                st.session_state.logger_phoenix = (otlp_selection == "Phoenix")
                st.session_state.logger_arize_ax = (otlp_selection == "Arize AX")
                
                # Show hard reset instructions
                st.info(f"✅ OTLP platform changed to: **{otlp_selection}**")
                st.warning("⚠️ **Hard reset required:** Press Ctrl+C to stop the server, then run `streamlit run app.py` again")
                st.caption("OpenTelemetry tracer providers cannot be changed at runtime")
            
            st.divider()
            st.markdown("**Callback-based Platforms**")
            
            # LangSmith
            langsmith_enabled = st.checkbox(
                "LangSmith",
                value=st.session_state.logger_langsmith,
                help="LangChain LangSmith tracing",
                key="langsmith_checkbox",
                disabled=not (os.getenv("LANGCHAIN_API_KEY"))
            )
            if langsmith_enabled != st.session_state.logger_langsmith:
                st.session_state.logger_langsmith = langsmith_enabled
                if "tracing_initialized" in st.session_state:
                    del st.session_state.tracing_initialized
                if "agent" in st.session_state:
                    del st.session_state.agent
                st.rerun()
            
            # Langfuse
            langfuse_enabled = st.checkbox(
                "Langfuse",
                value=st.session_state.logger_langfuse,
                help="Langfuse observability",
                key="langfuse_checkbox",
                disabled=not (os.getenv("LANGFUSE_API_PK") and os.getenv("LANGFUSE_API_SK"))
            )
            if langfuse_enabled != st.session_state.logger_langfuse:
                st.session_state.logger_langfuse = langfuse_enabled
                if "tracing_initialized" in st.session_state:
                    del st.session_state.tracing_initialized
                if "agent" in st.session_state:
                    del st.session_state.agent
                st.rerun()
            
            # Braintrust
            braintrust_enabled = st.checkbox(
                "Braintrust",
                value=st.session_state.logger_braintrust,
                help="Braintrust AI evaluation",
                key="braintrust_checkbox",
                disabled=not (os.getenv("BRAINTRUST_API_KEY") and os.getenv("BRAINTRUST_PROJECT"))
            )
            if braintrust_enabled != st.session_state.logger_braintrust:
                st.session_state.logger_braintrust = braintrust_enabled
                if "tracing_initialized" in st.session_state:
                    del st.session_state.tracing_initialized
                if "agent" in st.session_state:
                    del st.session_state.agent
                st.rerun()
            
            # Show status
            st.divider()
            enabled_platforms = ["Galileo (always on)"]
            if st.session_state.logger_phoenix:
                enabled_platforms.append("Phoenix")
            if st.session_state.logger_arize_ax:
                enabled_platforms.append("Arize AX")
            if st.session_state.logger_langsmith:
                enabled_platforms.append("LangSmith")
            if st.session_state.logger_langfuse:
                enabled_platforms.append("Langfuse")
            if st.session_state.logger_braintrust:
                enabled_platforms.append("Braintrust")
            
            st.success(f"✅ Active: {', '.join(enabled_platforms)}")
    
    # Main content with tabs
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "🧪 Experiments", "🔄 Runs"])
    
    with tab1:
        render_chat_tab(app_title, example_queries)
    
    with tab2:
        render_experiments_tab()
    
    with tab3:
        render_runs_tab()


if __name__ == "__main__":
    multi_domain_agent_app()
