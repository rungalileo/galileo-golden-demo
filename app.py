"""
Galileo Demo App
"""
import uuid
import streamlit as st
from dotenv import load_dotenv
from galileo import galileo_context
from agent_factory import AgentFactory
from setup_env import setup_environment
from domain_manager import DomainManager
from langchain_core.messages import AIMessage, HumanMessage
from agent_frameworks.langgraph.langgraph_rag import get_domain_rag_system
from helpers.galileo_api_helpers import get_galileo_app_url, get_galileo_project_id, get_galileo_log_stream_id
from helpers.protect_helpers import get_or_create_protect_stage
from helpers.hallucination_helpers import log_hallucination_for_domain
from experiments.experiment_helpers import (
    get_all_datasets,
    get_dataset_by_name,
    get_dataset_by_id,
    create_domain_dataset,
    read_dataset_csv,
    run_domain_experiment,
    get_domain_dataset_name,
    AVAILABLE_METRICS
)
import os
import io

# Load environment variables
load_dotenv()

# LangSmith imports
try:
    from langchain_classic.callbacks.tracers import LangChainTracer
    from langsmith import Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    print("⚠️ LangSmith not available - install with: pip install langsmith langchain")

# Braintrust imports
try:
    from braintrust import init_logger as braintrust_init_logger
    from braintrust_langchain import BraintrustCallbackHandler, set_global_handler as braintrust_set_global_handler
    BRAINTRUST_AVAILABLE = True
except ImportError:
    BRAINTRUST_AVAILABLE = False
    print("⚠️ Braintrust not available - install with: pip install braintrust braintrust-langchain")


# Configuration
FRAMEWORK = "LangGraph"


def initialize_rag_systems(domain_name: str):
    """Initialize RAG systems at app startup for better performance"""
    try:
        # Initialize RAG system for the specified domain
        print(f"🔧 Initializing RAG system for domain: {domain_name}")
        rag_system = get_domain_rag_system(domain_name)
        print(f"✅ RAG system initialized successfully")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize RAG system: {e}")
        return False


def initialize_langsmith_tracing(domain_name: str = None):
    """Initialize LangSmith tracing if enabled and configured
    
    Uses the same project naming as Galileo:
    - First checks galileo.project in domain config
    - Falls back to galileo-demo-{domain_name}
    
    Args:
        domain_name: Name of the domain to get project configuration from
    """
    if not LANGSMITH_AVAILABLE:
        return False
    
    if not hasattr(st.session_state, 'logger_langsmith') or not st.session_state.logger_langsmith:
        return False
    
    langsmith_api_key = os.getenv("LANGCHAIN_API_KEY")
    
    if not langsmith_api_key:
        print("⚠️ LangSmith enabled but LANGCHAIN_API_KEY not found")
        return False
    
    # Use the same project name as Galileo
    langsmith_project = None
    if domain_name:
        full_config_key = f"full_domain_config_{domain_name}"
        if full_config_key in st.session_state:
            domain_config = st.session_state[full_config_key]
            galileo_config = domain_config.get("galileo", {})
            langsmith_project = galileo_config.get("project")
    
    # Fall back to default: galileo-demo-{domain_name}
    if not langsmith_project and domain_name:
        langsmith_project = f"galileo-demo-{domain_name}"
    elif not langsmith_project:
        langsmith_project = "galileo-demo"
    
    try:
        # Create LangSmith client and tracer
        langsmith_client = Client(api_key=langsmith_api_key)
        langsmith_tracer = LangChainTracer(
            project_name=langsmith_project,
            client=langsmith_client
        )
        
        st.session_state.langsmith_tracer = langsmith_tracer
        st.session_state.langsmith_project = langsmith_project
        print(f"✅ LangSmith tracing initialized")
        print(f"   Project: {langsmith_project}")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize LangSmith: {e}")
        return False


def initialize_braintrust_tracing(domain_name: str = None):
    """Initialize Braintrust tracing if enabled and configured
    
    Uses the same project naming as Galileo:
    - First checks galileo.project in domain config
    - Falls back to galileo-demo-{domain_name}
    
    Args:
        domain_name: Name of the domain to get project configuration from
    """
    if not BRAINTRUST_AVAILABLE:
        return False
    
    if not hasattr(st.session_state, 'logger_braintrust') or not st.session_state.logger_braintrust:
        return False
    
    braintrust_api_key = os.getenv("BRAINTRUST_API_KEY")
    
    if not braintrust_api_key:
        print("⚠️ Braintrust enabled but BRAINTRUST_API_KEY not found")
        return False
    
    # Use the same project name as Galileo
    braintrust_project = None
    if domain_name:
        full_config_key = f"full_domain_config_{domain_name}"
        if full_config_key in st.session_state:
            domain_config = st.session_state[full_config_key]
            galileo_config = domain_config.get("galileo", {})
            braintrust_project = galileo_config.get("project")
        else:
            print(f"⚠️ Braintrust: domain config not found in session state for {domain_name}")
    else:
        print(f"⚠️ Braintrust: domain_name not provided")
    
    # Fall back to default: galileo-demo-{domain_name}
    if not braintrust_project and domain_name:
        braintrust_project = f"galileo-demo-{domain_name}"
    elif not braintrust_project:
        braintrust_project = "galileo-demo"
    
    try:
        # Initialize Braintrust logger first
        print(f"🔧 Initializing Braintrust logger with project: {braintrust_project}")
        braintrust_init_logger(project=braintrust_project, api_key=braintrust_api_key)
        
        # Create Braintrust callback handler
        braintrust_handler = BraintrustCallbackHandler()
        
        # Set as global handler (recommended by Braintrust)
        braintrust_set_global_handler(braintrust_handler)
        
        st.session_state.braintrust_handler = braintrust_handler
        st.session_state.braintrust_project = braintrust_project
        print(f"✅ Braintrust tracing initialized")
        print(f"   Project: {braintrust_project}")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize Braintrust: {e}")
        import traceback
        traceback.print_exc()
        return False


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
    
    # Show loading indicator if currently processing
    if st.session_state.get("processing", False):
        with st.chat_message("assistant"):
            st.write("Thinking...")


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
    agent_title: str, example_query_1: str, example_query_2: str, domain_name: str
):
    """Set up the Streamlit interface and get user input"""
    # App title and description
    st.title(agent_title)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # Create state variable but don't start Galileo session until we have user input
    if "galileo_session_started" not in st.session_state:
        st.session_state.galileo_session_started = False
    # Store domain name in session state
    if "domain_name" not in st.session_state:
        st.session_state.domain_name = domain_name

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
        # Start Galileo session on first user input
        if not st.session_state.galileo_session_started:
            try:
                domain_name = st.session_state.get("domain_name", "default")
                session_name = f"{domain_name.title()} Agent Demo"
                galileo_context.start_session(name=session_name, external_id=st.session_state.session_id)
                st.session_state.galileo_logger = galileo_context
                st.session_state.galileo_session_started = True
            except Exception as e:
                st.error(f"Failed to start Galileo session: {str(e)}")
                st.stop()
        
        # Add user message to chat history
        user_message = HumanMessage(content=user_input)
        st.session_state.messages.append({"message": user_message, "agent": "user"})

        # Set processing flag and rerun to show the loading state
        st.session_state.processing = True
        st.rerun()
    
    # Check if we need to process a message
    if st.session_state.get("processing", False):
        # Set Protect on the agent if enabled
        if st.session_state.get("protect_enabled", False):
            stage_id = st.session_state.get("protect_stage_id")
            if stage_id:
                st.session_state.agent.set_protect(True, stage_id)
            else:
                st.session_state.agent.set_protect(False)
        else:
            st.session_state.agent.set_protect(False)
        
        # Convert session state messages to the format expected by the agent
        conversation_messages = []
        for msg_data in st.session_state.messages:
            if isinstance(msg_data, dict) and "message" in msg_data:
                message = msg_data["message"]
                if isinstance(message, HumanMessage):
                    conversation_messages.append({"role": "user", "content": message.content})
                elif isinstance(message, AIMessage):
                    conversation_messages.append({"role": "assistant", "content": message.content})
        
        # Get the actual response from the agent (Protect is handled inside)
        response = st.session_state.agent.process_query(conversation_messages)

        # Create AI message and add to history
        ai_message = AIMessage(content=response)
        st.session_state.messages.append(
            {"message": ai_message, "agent": "assistant"}
        )
        
        # Clear processing flag and rerun to show the response
        st.session_state.processing = False
        st.rerun()


def render_experiments_page(domain_name: str, domain_config, agent_factory):
    """Render the experiments page UI.
    
    Args:
        domain_name: Name of the domain
        domain_config: DomainConfig object from DomainManager
        agent_factory: AgentFactory instance
    """
    st.title("🧪 Experiments")
    st.markdown("Create and run experiments to evaluate your agent's performance.")
    
    # Initialize session state for experiments
    if "selected_dataset" not in st.session_state:
        st.session_state.selected_dataset = None
    if "dataset_loaded" not in st.session_state:
        st.session_state.dataset_loaded = False
    if "experiment_running" not in st.session_state:
        st.session_state.experiment_running = False
    
    # Section 1: Dataset Selection/Creation
    st.header("1️⃣ Dataset Setup")
    
    dataset_option = st.radio(
        "Choose how to setup your dataset:",
        ["Select Existing Dataset by Name", "Select Existing Dataset by ID", 
         "Create from Sample Test Data", "Upload CSV File"],
        key="dataset_option"
    )
    
    # Handle different dataset options
    if dataset_option == "Select Existing Dataset by Name":
        render_select_dataset_by_name(domain_name)
    
    elif dataset_option == "Select Existing Dataset by ID":
        render_select_dataset_by_id()
    
    elif dataset_option == "Create from Sample Test Data":
        render_create_from_sample_data(domain_name, domain_config)
    
    elif dataset_option == "Upload CSV File":
        render_upload_csv(domain_name)
    
    st.divider()
    
    # Section 2: Experiment Configuration (only show if dataset is loaded)
    if st.session_state.dataset_loaded and st.session_state.selected_dataset:
        st.header("2️⃣ Experiment Configuration")
        
        # Show dataset info with link
        dataset = st.session_state.selected_dataset
        dataset_name_display = dataset.name if hasattr(dataset, 'name') else "Selected Dataset"
        st.info(f"📊 Using Dataset: **{dataset_name_display}**")
        
        # Show link to view in Galileo
        try:
            console_url = get_galileo_app_url()
            dataset_url = f"{console_url}/datasets/{dataset.id}"
            st.markdown(f"[🔗 View Dataset in Galileo Console]({dataset_url})")
        except Exception:
            pass  # Silently fail if we can't get the URL
        
        st.markdown("---")
        
        # Experiment name
        default_exp_name = f"{domain_name}-experiment-{uuid.uuid4().hex[:6]}"
        experiment_name = st.text_input(
            "Experiment Name",
            value=default_exp_name,
            help="A unique name for this experiment run"
        )
        
        # Metrics selection
        st.subheader("Select Metrics")
        st.markdown("Choose which metrics to evaluate:")
        
        selected_metrics = {}
        cols = st.columns(2)
        for idx, (metric_name, metric_obj) in enumerate(AVAILABLE_METRICS.items()):
            with cols[idx % 2]:
                selected_metrics[metric_name] = st.checkbox(
                    metric_name,
                    value=True,
                    key=f"metric_{metric_name}"
                )
        
        # Get selected metrics as list
        metrics_to_run = [
            metric_obj for metric_name, metric_obj in AVAILABLE_METRICS.items()
            if selected_metrics[metric_name]
        ]
        
        st.divider()
        
        # Section 3: Run Experiment
        st.header("3️⃣ Run Experiment")
        
        if not metrics_to_run:
            st.warning("⚠️ Please select at least one metric to run the experiment.")
        else:
            st.info(f"📊 Ready to run experiment with {len(metrics_to_run)} metric(s)")
            
            if st.button("🚀 Run Experiment", type="primary", disabled=st.session_state.experiment_running):
                run_experiment_ui(
                    domain_name=domain_name,
                    experiment_name=experiment_name,
                    metrics=metrics_to_run,
                    agent_factory=agent_factory
                )
    else:
        st.info("👆 Please select or create a dataset to continue.")


def render_select_dataset_by_name(domain_name: str):
    """Render UI for selecting dataset by name."""
    try:
        # Get all datasets
        all_datasets = get_all_datasets()
        
        if not all_datasets:
            st.warning("No datasets found. Please create a dataset first.")
            return
        
        # Create list of dataset names
        dataset_names = [ds.name for ds in all_datasets]
        
        # Default to domain dataset if it exists
        domain_dataset_name = get_domain_dataset_name(domain_name)
        default_index = 0
        if domain_dataset_name in dataset_names:
            default_index = dataset_names.index(domain_dataset_name)
        
        selected_name = st.selectbox(
            "Select Dataset",
            dataset_names,
            index=default_index,
            help="Choose a dataset to use for the experiment"
        )
        
        if st.button("Load Dataset", key="load_by_name"):
            with st.spinner("Loading dataset..."):
                try:
                    dataset = get_dataset_by_name(selected_name)
                    st.session_state.selected_dataset = dataset
                    st.session_state.dataset_loaded = True
                    st.success(f"✅ Dataset '{selected_name}' loaded successfully!")
                    
                    # Show link to view in Galileo
                    try:
                        console_url = get_galileo_app_url()
                        dataset_url = f"{console_url}/datasets/{dataset.id}"
                        st.markdown(f"[📊 View Dataset in Galileo]({dataset_url})")
                    except Exception:
                        pass  # Silently fail if we can't get the URL
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error loading dataset: {str(e)}")
    
    except Exception as e:
        st.error(f"❌ Error fetching datasets: {str(e)}")


def render_select_dataset_by_id():
    """Render UI for selecting dataset by ID."""
    dataset_id = st.text_input(
        "Dataset ID",
        help="Enter the Galileo dataset ID"
    )
    
    if st.button("Load Dataset", key="load_by_id"):
        if not dataset_id:
            st.error("Please enter a dataset ID")
            return
        
        with st.spinner("Loading dataset..."):
            try:
                dataset = get_dataset_by_id(dataset_id)
                st.session_state.selected_dataset = dataset
                st.session_state.dataset_loaded = True
                st.success(f"✅ Dataset loaded successfully!")
                
                # Show link to view in Galileo
                try:
                    console_url = get_galileo_app_url()
                    dataset_url = f"{console_url}/datasets/{dataset.id}"
                    st.markdown(f"[📊 View Dataset in Galileo]({dataset_url})")
                except Exception:
                    pass  # Silently fail if we can't get the URL
                
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error loading dataset: {str(e)}")


def render_create_from_sample_data(domain_name: str, domain_config):
    """Render UI for creating dataset from domain's sample data."""
    st.markdown(f"Create a dataset from the **{domain_name}** domain's `dataset.csv` file.")
    
    # Get the dataset file path (domain_config is a DomainConfig object)
    dataset_file = domain_config.dataset_file if hasattr(domain_config, 'dataset_file') else ""
    
    if not dataset_file or not os.path.exists(dataset_file):
        st.error(f"❌ Dataset file not found at: {dataset_file}")
        return
    
    # Preview the data
    try:
        preview_data = read_dataset_csv(dataset_file)
        st.info(f"📄 Found {len(preview_data)} rows in dataset file")
        
        # Show preview of first few rows
        if preview_data:
            with st.expander("Preview Data"):
                for i, row in enumerate(preview_data[:3]):
                    st.markdown(f"**Sample {i+1}:**")
                    st.markdown(f"- **Input:** {row['input'][:100]}...")
                    st.markdown(f"- **Output:** {row['output'][:100]}...")
    except Exception as e:
        st.error(f"❌ Error reading dataset file: {str(e)}")
        return
    
    # Dataset name input
    default_name = get_domain_dataset_name(domain_name)
    dataset_name = st.text_input(
        "Dataset Name",
        value=default_name,
        key="sample_dataset_name",
        help="Enter a unique name for this dataset"
    )
    
    if st.button("Create Dataset", key="create_from_sample"):
        if not dataset_name or not dataset_name.strip():
            st.error("❌ Please enter a dataset name")
            return
            
        with st.spinner("Creating dataset..."):
            try:
                dataset = create_domain_dataset(domain_name, dataset_file, custom_name=dataset_name.strip())
                st.session_state.selected_dataset = dataset
                st.session_state.dataset_loaded = True
                st.success(f"✅ Dataset created successfully!")
                st.success(f"Dataset ID: {dataset.id}")
                
                # Show link to view in Galileo
                try:
                    console_url = get_galileo_app_url()
                    dataset_url = f"{console_url}/datasets/{dataset.id}"
                    st.markdown(f"[📊 View Dataset in Galileo]({dataset_url})")
                except Exception:
                    pass  # Silently fail if we can't get the URL
                
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error creating dataset: {str(e)}")


def render_upload_csv(domain_name: str):
    """Render UI for uploading CSV file to create dataset."""
    st.markdown("Upload a CSV file with `input` and `output` columns.")
    
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=['csv'],
        help="CSV file should have 'input' and 'output' columns"
    )
    
    if uploaded_file is not None:
        try:
            # Read the uploaded CSV
            content = uploaded_file.getvalue().decode("utf-8")
            
            # Save to temporary file and read
            import tempfile
            import csv
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            try:
                # Read and preview
                preview_data = read_dataset_csv(tmp_path)
                st.info(f"📄 Found {len(preview_data)} rows in uploaded file")
                
                # Show preview
                if preview_data:
                    with st.expander("Preview Data"):
                        for i, row in enumerate(preview_data[:3]):
                            st.markdown(f"**Sample {i+1}:**")
                            st.markdown(f"- **Input:** {row['input'][:100]}...")
                            st.markdown(f"- **Output:** {row['output'][:100]}...")
                
                # Dataset name input
                # Use uploaded filename (without extension) as default
                default_name = os.path.splitext(uploaded_file.name)[0]
                dataset_name = st.text_input(
                    "Dataset Name",
                    value=default_name,
                    key="upload_dataset_name",
                    help="Enter a unique name for this dataset"
                )
                
                if st.button("Create Dataset from Upload", key="create_from_upload"):
                    if not dataset_name or not dataset_name.strip():
                        st.error("❌ Please enter a dataset name")
                        return
                        
                    with st.spinner("Creating dataset..."):
                        try:
                            dataset = create_domain_dataset(domain_name, tmp_path, custom_name=dataset_name.strip())
                            st.session_state.selected_dataset = dataset
                            st.session_state.dataset_loaded = True
                            st.success(f"✅ Dataset created successfully!")
                            st.success(f"Dataset ID: {dataset.id}")
                            
                            # Show link to view in Galileo
                            try:
                                console_url = get_galileo_app_url()
                                dataset_url = f"{console_url}/datasets/{dataset.id}"
                                st.markdown(f"[📊 View Dataset in Galileo]({dataset_url})")
                            except Exception:
                                pass  # Silently fail if we can't get the URL
                            
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error creating dataset: {str(e)}")
            finally:
                # Clean up temp file
                os.unlink(tmp_path)
                
        except Exception as e:
            st.error(f"❌ Error processing uploaded file: {str(e)}")


def run_experiment_ui(domain_name: str, experiment_name: str, metrics: list, agent_factory):
    """Run the experiment and display results."""
    st.session_state.experiment_running = True
    
    with st.spinner("🔄 Running experiment... This may take a few minutes."):
        try:
            results = run_domain_experiment(
                domain_name=domain_name,
                experiment_name=experiment_name,
                dataset=st.session_state.selected_dataset,
                agent_factory=agent_factory,
                metrics=metrics
            )
            
            st.session_state.experiment_running = False
            
            # Show success message
            st.success("✅ Experiment completed successfully!")
            
            # Get experiment link from results
            # results contains: {"experiment": experiment_obj, "link": link, "message": message}
            if isinstance(results, dict):
                # Try to use the direct link from results
                experiment_link = results.get("link")
                experiment_obj = results.get("experiment")
                
                if experiment_link:
                    st.markdown(f"### [📊 View Experiment Results in Galileo]({experiment_link})")
                elif experiment_obj and hasattr(experiment_obj, 'id'):
                    # Fallback: construct the link manually
                    try:
                        console_url = get_galileo_app_url()
                        project_name = os.environ.get("GALILEO_PROJECT", "")
                        
                        if project_name:
                            project_id = get_galileo_project_id(project_name)
                            if project_id:
                                experiment_url = f"{console_url}/project/{project_id}/experiments/{experiment_obj.id}"
                                st.markdown(f"### [📊 View Experiment Results in Galileo]({experiment_url})")
                            else:
                                st.info("View the experiment results in the Galileo Console")
                        else:
                            st.info("View the experiment results in the Galileo Console")
                    except Exception:
                        st.info("View the experiment results in the Galileo Console")
                else:
                    st.info("View the experiment results in the Galileo Console")
            else:
                st.info("View the experiment results in the Galileo Console")
            
            # Show experiment details
            with st.expander("Experiment Details"):
                experiment_details = {
                    "experiment_name": experiment_name,
                    "domain": domain_name,
                    "dataset": st.session_state.selected_dataset.name if hasattr(st.session_state.selected_dataset, 'name') else "Unknown",
                    "metrics": [m.name for m in metrics],
                    "project": os.environ.get("GALILEO_PROJECT", "default")
                }
                
                # Add experiment ID if available
                if isinstance(results, dict):
                    experiment_obj = results.get("experiment")
                    if experiment_obj and hasattr(experiment_obj, 'id'):
                        experiment_details["experiment_id"] = experiment_obj.id
                
                st.json(experiment_details)
            
        except Exception as e:
            st.session_state.experiment_running = False
            st.error(f"❌ Error running experiment: {str(e)}")
            import traceback
            with st.expander("Error Details"):
                st.code(traceback.format_exc())


def multi_domain_agent_app(domain_name: str):
    """Main agent app - configuration-driven using domain config"""
    # Load domain configuration first (needed for environment setup)
    dm = DomainManager()
    full_config_key = f"full_domain_config_{domain_name}"
    if full_config_key not in st.session_state:
        full_config = dm.load_domain_config(domain_name)
        st.session_state[full_config_key] = full_config.config
    
    # Setup environment with domain-specific project (per domain)
    env_setup_key = f"environment_setup_{domain_name}"
    if env_setup_key not in st.session_state:
        setup_environment(
            domain_name=domain_name,
            domain_config=st.session_state[full_config_key]
        )
        st.session_state[env_setup_key] = True
    
    # Initialize RAG systems for this domain (per domain)
    rag_key = f"rag_initialized_{domain_name}"
    if rag_key not in st.session_state:
        initialize_rag_systems(domain_name)
        st.session_state[rag_key] = True
    
    # Initialize AgentFactory once
    if "factory" not in st.session_state:
        st.session_state.factory = AgentFactory()
    
    factory = st.session_state.factory
    
    # Load domain configuration for UI settings (per domain)
    domain_config_key = f"domain_config_{domain_name}"
    if domain_config_key not in st.session_state:
        domain_info = factory.get_domain_info(domain_name)
        st.session_state[domain_config_key] = domain_info
    
    # Create tabs at the top of the main page
    tab1, tab2 = st.tabs(["💬 Chat", "🧪 Experiments"])
    
    # Chat Tab
    with tab1:
        render_chat_page(factory, domain_name)
        
        # Add Galileo Tracing link in sidebar when on Chat tab
        with st.sidebar:
            st.subheader("Galileo Tracing")
            
            # Get project and log stream names from environment variables (set by setup_environment)
            project_name = os.environ.get("GALILEO_PROJECT", "")
            log_stream_name = os.environ.get("GALILEO_LOG_STREAM", "")
            
            if project_name and log_stream_name:
                try:
                    # Get the console URL and project/log stream info
                    console_url = get_galileo_app_url()
                    project_id = get_galileo_project_id(project_name)
                    
                    if project_id:
                        log_stream_id = get_galileo_log_stream_id(project_id, log_stream_name)
                        
                        if log_stream_id:
                            project_url = f"{console_url}/project/{project_id}/log-streams/{log_stream_id}"
                            st.markdown(f"[📊 View traces in Galileo]({project_url})")
                        else:
                            st.write("Log stream not found")
                    else:
                        st.write("Project not found")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.write("Galileo project/log stream not configured")
            
            # Add Galileo Protect toggle
            st.divider()
            st.subheader("🛡️ Galileo Protect")
            
            # Initialize protect_enabled in session state (default to False, per domain)
            protect_key = f"protect_enabled_{domain_name}"
            if protect_key not in st.session_state:
                st.session_state[protect_key] = False
            
            # Toggle for Protect
            protect_enabled = st.checkbox(
                "Enable Prompt Injection Protection",
                value=st.session_state[protect_key],
                help="Enable Galileo Protect to detect and block prompt injection attempts"
            )
            st.session_state[protect_key] = protect_enabled
            
            # Show current Protect configuration from domain config
            if protect_enabled:
                protect_config = st.session_state.get(full_config_key, {}).get("protect", {})
                if protect_config:
                    metrics = protect_config.get("metrics", [])
                    if metrics:
                        with st.expander("Protect Configuration"):
                            st.write("**Active Metrics:**")
                            for metric in metrics:
                                metric_name = metric.get("name", "Unknown")
                                operator = metric.get("operator", "")
                                
                                # Display based on metric type
                                if "target_values" in metric:
                                    target_values = metric["target_values"]
                                    st.write(f"- **{metric_name}** ({operator}): {', '.join(target_values)}")
                                elif "threshold" in metric:
                                    threshold = metric["threshold"]
                                    st.write(f"- **{metric_name}** ({operator}): {threshold}")
                                else:
                                    st.write(f"- **{metric_name}** ({operator})")
                            
                            messages = protect_config.get("messages", [])
                            if messages:
                                st.write("")
                                st.write("**Custom Messages:**")
                                for i, msg in enumerate(messages, 1):
                                    st.write(f"{i}. {msg}")
            
            if protect_enabled:
                st.info("🛡️ Protect is active. Prompt injection attempts will be blocked.")
                
                # Initialize stage if needed (per domain)
                stage_key = f"protect_stage_id_{domain_name}"
                if stage_key not in st.session_state and project_name:
                    try:
                        with st.spinner("Setting up Protect stage..."):
                            stage_id = get_or_create_protect_stage(project_name)
                            st.session_state[stage_key] = stage_id
                    except Exception as e:
                        st.error(f"Failed to setup Protect stage: {str(e)}")
                        st.session_state[protect_key] = False
            else:
                st.info("Protect is disabled. All queries will be processed normally.")
            
            # Add Chaos Engineering section
            st.divider()
            st.subheader("🔥 Chaos Engineering")
            st.markdown("Simulate real-world failures to test Galileo's observability.")
            
            # Import chaos engine
            try:
                from chaos_engine import get_chaos_engine
                chaos = get_chaos_engine()
                
                with st.expander("⚙️ Chaos Controls"):
                    st.markdown("Enable chaos modes to inject failures:")
                    
                    # Tool Instability
                    tool_instability = st.checkbox(
                        "🔌 Tool Instability",
                        value=chaos.tool_instability_enabled,
                        key=f"chaos_tool_instability_{domain_name}",
                        help="Fail API calls with 503, timeout, etc."
                    )
                    chaos.enable_tool_instability(tool_instability)
                    
                    # Sloppiness
                    sloppiness = st.checkbox(
                        "🔢 Sloppiness",
                        value=chaos.sloppiness_enabled,
                        key=f"chaos_sloppiness_{domain_name}",
                        help="Corrupt numbers in tool outputs before LLM sees them"
                    )
                    chaos.enable_sloppiness(sloppiness)
                    
                    # Data Corruption (Random LLM Errors)
                    data_corruption = st.checkbox(
                        "💥 Data Corruption",
                        value=chaos.data_corruption_enabled,
                        key=f"chaos_data_corruption_{domain_name}",
                        help="LLM corrupts correct tool data (simulates LLM hallucinations)"
                    )
                    chaos.enable_data_corruption(data_corruption)
                    
                    # RAG Chaos
                    rag_chaos = st.checkbox(
                        "📚 RAG Disconnects",
                        value=chaos.rag_chaos_enabled,
                        key=f"chaos_rag_{domain_name}",
                        help="Simulate vector database connection failures"
                    )
                    chaos.enable_rag_chaos(rag_chaos)
                    
                    # Rate Limits
                    rate_limits = st.checkbox(
                        "⏱️ Rate Limits",
                        value=chaos.rate_limit_chaos_enabled,
                        key=f"chaos_rate_limits_{domain_name}",
                        help="Simulate API rate limit exceeded (429 errors)"
                    )
                    chaos.enable_rate_limit_chaos(rate_limits)
                    
                    # Show active chaos count
                    active_count = sum([
                        chaos.tool_instability_enabled,
                        chaos.sloppiness_enabled,
                        chaos.data_corruption_enabled,
                        chaos.rag_chaos_enabled,
                        chaos.rate_limit_chaos_enabled
                    ])
                    
                    if active_count > 0:
                        st.warning(f"🔥 {active_count} chaos mode(s) active")
                        
                        # Show statistics
                        stats = chaos.get_stats()
                        with st.expander("📊 Chaos Statistics"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Tool Instability", stats['tool_instability_count'])
                                st.metric("Sloppiness", stats['sloppiness_count'])
                                st.metric("RAG Chaos", stats['rag_chaos_count'])
                            with col2:
                                st.metric("Rate Limits", stats['rate_limit_chaos_count'])
                                st.metric("Data Corruption", stats['data_corruption_count'])
                            
                            if st.button("Reset Stats", key=f"reset_chaos_stats_{domain_name}"):
                                chaos.reset_stats()
                                st.rerun()
                    else:
                        st.info("✅ No chaos active - all systems normal")
            
            except ImportError:
                st.info("Chaos engineering not available (chaos_engine.py not found)")
            
            # Add Hallucination Demo section (only if configured)
            domain_full_config = st.session_state.get(full_config_key, {})
            has_hallucinations = bool(domain_full_config.get("demo_hallucinations", []))
            
            if has_hallucinations:
                st.divider()
                st.subheader("Hallucination Demo")
                st.markdown("Log an intentional hallucination to Galileo.")
                if st.button("Log Hallucination", key=f"log_hallucination_{domain_name}"):
                    with st.spinner("Logging hallucination to Galileo..."):
                        # Use existing logger if a session has been started, otherwise create new
                        existing_logger = st.session_state.get("galileo_logger") if st.session_state.get("galileo_session_started", False) else None
                        
                        success = log_hallucination_for_domain(
                            domain_name=domain_name,
                            domain_config=domain_full_config,
                            existing_logger=existing_logger,
                        )
                        if success:
                            session_context = " in current session" if existing_logger else " in new session"
                            st.success(f"Hallucination logged{session_context}! Check Galileo console.")
                        else:
                            st.error("Failed to log hallucination. Check logs for details.")
            
            # Add Observability Platforms section
            st.divider()
            st.subheader("Observability Platforms")
            st.caption("Galileo is always enabled")
            
            with st.expander("Settings: Configure Loggers"):
                # Initialize LangSmith toggle (per domain)
                langsmith_key = f"logger_langsmith_{domain_name}"
                if langsmith_key not in st.session_state:
                    # Default to disabled
                    st.session_state[langsmith_key] = False
                
                if LANGSMITH_AVAILABLE:
                    langsmith_enabled = st.checkbox(
                        "LangSmith",
                        value=st.session_state.get(langsmith_key, False),
                        help="LangChain LangSmith tracing",
                        disabled=not bool(os.getenv("LANGCHAIN_API_KEY")),
                        key=f"langsmith_toggle_{domain_name}"
                    )
                    
                    # Update session state and reinitialize if changed
                    if langsmith_enabled != st.session_state.get(langsmith_key, False):
                        st.session_state[langsmith_key] = langsmith_enabled
                        st.session_state.logger_langsmith = langsmith_enabled
                        
                        # Reinitialize LangSmith tracing
                        if langsmith_enabled:
                            if initialize_langsmith_tracing(domain_name):
                                st.success("✅ LangSmith tracing enabled!")
                            else:
                                st.error("❌ Failed to enable LangSmith")
                        else:
                            # Remove tracer from session state
                            if 'langsmith_tracer' in st.session_state:
                                del st.session_state.langsmith_tracer
                            if 'langsmith_project' in st.session_state:
                                del st.session_state.langsmith_project
                            st.info("LangSmith tracing disabled")
                        
                        # Force agent to reinitialize with new callbacks
                        agent_key = f"agent_{domain_name}"
                        if agent_key in st.session_state:
                            del st.session_state[agent_key]
                        st.rerun()
                    
                    # Initialize on first load if enabled
                    if langsmith_enabled and 'langsmith_tracer' not in st.session_state:
                        st.session_state.logger_langsmith = True
                        initialize_langsmith_tracing(domain_name)
                    
                    if langsmith_enabled:
                        langsmith_project = st.session_state.get('langsmith_project', 'galileo-demo')
                        st.caption(f"📊 Project: {langsmith_project}")
                else:
                    st.warning("⚠️ LangSmith not installed")
                    st.caption("Install with: `pip install langsmith`")
                
                # Initialize Braintrust toggle (per domain)
                braintrust_key = f"logger_braintrust_{domain_name}"
                if braintrust_key not in st.session_state:
                    # Default to disabled
                    st.session_state[braintrust_key] = False
                
                if BRAINTRUST_AVAILABLE:
                    braintrust_enabled = st.checkbox(
                        "Braintrust",
                        value=st.session_state.get(braintrust_key, False),
                        help="Braintrust AI evaluation and observability",
                        disabled=not bool(os.getenv("BRAINTRUST_API_KEY")),
                        key=f"braintrust_toggle_{domain_name}"
                    )
                    
                    # Update session state and reinitialize if changed
                    if braintrust_enabled != st.session_state.get(braintrust_key, False):
                        st.session_state[braintrust_key] = braintrust_enabled
                        st.session_state.logger_braintrust = braintrust_enabled
                        
                        # Reinitialize Braintrust tracing
                        if braintrust_enabled:
                            if initialize_braintrust_tracing(domain_name):
                                st.success("✅ Braintrust tracing enabled!")
                            else:
                                st.error("❌ Failed to enable Braintrust")
                        else:
                            # Remove handler from session state
                            if 'braintrust_handler' in st.session_state:
                                del st.session_state.braintrust_handler
                            if 'braintrust_project' in st.session_state:
                                del st.session_state.braintrust_project
                            st.info("Braintrust tracing disabled")
                        
                        # Force agent to reinitialize with new callbacks
                        agent_key = f"agent_{domain_name}"
                        if agent_key in st.session_state:
                            del st.session_state[agent_key]
                        st.rerun()
                    
                    # Initialize on first load if enabled
                    if braintrust_enabled and 'braintrust_handler' not in st.session_state:
                        st.session_state.logger_braintrust = True
                        initialize_braintrust_tracing(domain_name)
                    
                    if braintrust_enabled:
                        braintrust_project = st.session_state.get('braintrust_project', 'galileo-demo')
                        st.caption(f"📊 Project: {braintrust_project}")
                else:
                    st.warning("⚠️ Braintrust not installed")
                    st.caption("Install with: `pip install braintrust braintrust-langchain`")
    
    # Experiments Tab
    with tab2:
        # Load the full domain config for experiments
        dm = DomainManager()
        full_domain_config = dm.load_domain_config(domain_name)
        render_experiments_page(domain_name, full_domain_config, factory)


def render_chat_page(factory, domain_name: str):
    """Render the chat page."""
    # Extract UI configuration from domain config (per domain)
    domain_config_key = f"domain_config_{domain_name}"
    ui_config = st.session_state[domain_config_key].get("ui", {})
    app_title = ui_config.get("app_title", f"{domain_name.title()} Assistant")
    example_queries = ui_config.get("example_queries", [
        "Hello, how can you help me?",
        "What can you do?"
    ])
    
    # Initialize session ID (per domain)
    session_id_key = f"session_id_{domain_name}"
    if session_id_key not in st.session_state:
        session_id = str(uuid.uuid4())[:10]
        st.session_state[session_id_key] = session_id
        st.session_state.session_id = session_id  # Also set the global session_id
    else:
        st.session_state.session_id = st.session_state[session_id_key]
    
    user_input = orchestrate_streamlit_and_get_user_input(
        app_title,
        example_queries[0] if len(example_queries) > 0 else "Hello, how can you help me?",
        example_queries[1] if len(example_queries) > 1 else "What can you do?",
        domain_name
    )
    
    # Create agent dynamically using AgentFactory - works for any domain!
    agent_key = f"agent_{domain_name}"
    if agent_key not in st.session_state:
        st.session_state[agent_key] = factory.create_agent(
            domain=domain_name, 
            framework=FRAMEWORK,
            session_id=st.session_state.session_id
        )
    
    # Set current agent for processing
    st.session_state.agent = st.session_state[agent_key]
    
    # Update protect_enabled for the current domain
    protect_key = f"protect_enabled_{domain_name}"
    st.session_state.protect_enabled = st.session_state.get(protect_key, False)
    
    # Update protect_stage_id for the current domain
    stage_key = f"protect_stage_id_{domain_name}"
    if stage_key in st.session_state:
        st.session_state.protect_stage_id = st.session_state[stage_key]
    
    process_input_for_simple_app(user_input)


def create_domain_page(domain_name: str):
    """Create a page function for a specific domain"""
    def page_func():
        multi_domain_agent_app(domain_name)
    return page_func


def main():
    """Main app with dynamic routing based on discovered domains"""
    # Initialize domain manager
    dm = DomainManager()
    
    try:
        # Auto-discover available domains
        available_domains = dm.list_domains()
        
        if not available_domains:
            st.error("No domains found! Please create a domain in the 'domains/' directory.")
            st.info("Example: Create 'domains/finance/config.yaml' with your domain configuration.")
            st.stop()
        
        # Create pages dictionary for st.navigation
        pages = []
        
        # Determine default domain (prefer "finance" if it exists, otherwise first domain)
        default_domain = "finance" if "finance" in available_domains else available_domains[0]
        
        for domain in available_domains:
            try:
                domain_info = dm.get_domain_info(domain)
                ui_config = domain_info.get("ui", {})
                app_title = ui_config.get("app_title", f"{domain.title()} Assistant")
                app_icon = ui_config.get("icon", "🤖")  # Default to robot emoji
                
                # Create page using st.Page
                is_default = (domain == default_domain)
                
                if is_default:
                    # Default domain gets both root and named path
                    # Default page (root URL)
                    default_page = st.Page(
                        create_domain_page(domain),
                        title=app_title,
                        icon=app_icon,
                        default=True
                    )
                    pages.append(default_page)
                
                # Named path for all domains
                page = st.Page(
                    create_domain_page(domain),
                    title=app_title,
                    url_path=f"/{domain}",
                    icon=app_icon
                )
                pages.append(page)
                
            except Exception as e:
                st.error(f"Error loading domain '{domain}': {str(e)}")
                continue
        
        if not pages:
            st.error("No valid domains found! Please check your domain configurations.")
            st.stop()
        
        # Create navigation with list of pages - hide navigation for clean demo
        try:
            # uncomment this to show the navigation with different pages per domain
            nav = st.navigation(pages, position="hidden")
            nav.run()
        except Exception as nav_error:
            st.error(f"Navigation error: {str(nav_error)}")
            st.info(f"Available domains: {available_domains}")
            st.info(f"Number of pages created: {len(pages)}")
            # Fallback to default domain
            if available_domains:
                st.warning("Falling back to direct domain execution...")
                multi_domain_agent_app(default_domain)
        
    except Exception as e:
        st.error(f"Error initializing app: {str(e)}")
        st.info("Please check your domain configurations and try again.")


if __name__ == "__main__":
    main()
