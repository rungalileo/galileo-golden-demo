"""
Galileo Demo App
"""
import uuid
from typing import Optional
import streamlit as st
from dotenv import load_dotenv
from galileo import galileo_context
from agent_factory import AgentFactory
from setup_env import setup_environment
from setup_otel import setup_opentelemetry_from_env
from langchain_core.messages import AIMessage, HumanMessage
from opentelemetry import trace
from agent_frameworks.langgraph.langgraph_rag import get_domain_rag_system
from helpers.galileo_api_helpers import get_galileo_app_url, get_galileo_project_id, get_galileo_log_stream_id
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
from create_custom_metric import get_bedrock_judge_model_id
from galileo.metrics import create_custom_llm_metric, OutputTypeEnum, StepType
import os
import io

# Load environment variables
load_dotenv()


# Configuration - easily changeable for different domains
DOMAIN = "finance"  # Could be "healthcare", "legal", etc.
FRAMEWORK = "LangGraph"


def initialize_rag_systems():
    """Initialize RAG systems at app startup for better performance"""
    try:
        
        # Initialize RAG system for the current domain
        print(f"🔧 Initializing RAG system for domain: {DOMAIN}")
        rag_system = get_domain_rag_system(DOMAIN)
        print(f"✅ RAG system initialized successfully")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize RAG system: {e}")
        return False


def initialize_custom_metric():
    """Create custom metric using AWS Bedrock at app startup"""
    try:
        metric_name = "Custom Metric - Response Quality"
        
        # Use the Bedrock model ID directly (not an alias)
        # This ensures Galileo can properly call Bedrock for metric evaluation
        judge_model = get_bedrock_judge_model_id()
        
        print(f"Using Bedrock model: {judge_model}")
        print("Note: If the model doesn't appear in the UI, register it as a model alias in Galileo first\n")
        
        custom_metric = create_custom_llm_metric(
            name=metric_name,
            user_prompt="""
You are an impartial evaluator, ensuring that LLM responses follow the given instructions.

For this evaluation, check if the LLM response:

1. Addresses the user's request appropriately

2. Follows the instructions provided in the prompt

3. Provides a relevant and helpful response

Task: Determine if the provided LLM output follows the instructions and is helpful.

Return true if the response follows instructions and is helpful

Return false if the response does not follow instructions or is not helpful
""",
            node_level=StepType.llm,
            cot_enabled=True,
            model_name=judge_model,
            num_judges=1,
            description="""
This metric determines if the LLM response follows the given instructions 
and provides a helpful, relevant answer to the user's request.
""",
            tags=["quality", "instructions", "demo"],
            output_type=OutputTypeEnum.BOOLEAN,
        )
        print(f"✓ Custom metric '{metric_name}' created successfully")
        return custom_metric
        
    except Exception as e:
        print(f"⚠️  Custom metric creation failed: {e}")
        return None


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
    """Set up the Streamlit interface and get user input"""
    # App title and description
    st.title(agent_title)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # Create state variable but don't start Galileo session until we have user input
    if "galileo_session_started" not in st.session_state:
        st.session_state.galileo_session_started = False

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


def process_input_for_simple_app(user_input: Optional[str]):
    """Process user input and generate response - using AgentFactory directly"""
    tracer = trace.get_tracer(__name__)
    
    if user_input:
        with tracer.start_as_current_span("process_user_query") as span:
            span.set_attribute("user_input.length", len(user_input))
            span.set_attribute("user_input.preview", user_input[:100])
            
            # Start Galileo session on first user input
            if not st.session_state.galileo_session_started:
                try:
                    galileo_context.start_session(name="Finance Agent Demo", external_id=st.session_state.session_id)
                    st.session_state.galileo_logger = galileo_context
                    st.session_state.galileo_session_started = True
                except Exception as e:
                    st.error(f"Failed to start Galileo session: {str(e)}")
                    st.stop()
            
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
                    with tracer.start_as_current_span("agent.process_query") as span:
                        span.set_attribute("conversation.messages_count", len(conversation_messages))
                        response = st.session_state.agent.process_query(conversation_messages)
                        span.set_attribute("response.length", len(response) if response else 0)

                    # Create and display AI message
                    ai_message = AIMessage(content=response)
                    st.session_state.messages.append(
                        {"message": ai_message, "agent": "assistant"}
                    )

                    # Display response
                    st.write(escape_dollar_signs(response))
            
            # Rerun to update chat history
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


def multi_domain_agent_app():
    """Main agent app - configuration-driven using domain config"""
    # Setup environment and secrets (only once)
    if "environment_setup_done" not in st.session_state:
        setup_environment()
        st.session_state.environment_setup_done = True
    
    # Setup OpenTelemetry (only once)
    if "otel_setup_done" not in st.session_state:
        try:
            setup_opentelemetry_from_env()
            st.session_state.otel_setup_done = True
        except Exception as e:
            print(f"⚠️  OpenTelemetry setup failed: {e}")
            st.session_state.otel_setup_done = True  # Mark as done to avoid retrying
    
    # Create custom metric (only once)
    if "custom_metric_created" not in st.session_state:
        try:
            custom_metric = initialize_custom_metric()
            st.session_state.custom_metric = custom_metric
            st.session_state.custom_metric_created = True
        except Exception as e:
            print(f"⚠️  Custom metric creation failed: {e}")
            st.session_state.custom_metric_created = True  # Mark as done to avoid retrying
    
    # Initialize RAG systems (only once)
    if "rag_systems_initialized" not in st.session_state:
        initialize_rag_systems()
        st.session_state.rag_systems_initialized = True
    
    # Initialize AgentFactory once
    if "factory" not in st.session_state:
        st.session_state.factory = AgentFactory()
    
    factory = st.session_state.factory
    
    # Load domain configuration for UI settings
    if "domain_config" not in st.session_state:
        domain_info = factory.get_domain_info(DOMAIN)
        st.session_state.domain_config = domain_info
    
    # Create tabs at the top of the main page
    tab1, tab2 = st.tabs(["💬 Chat", "🧪 Experiments"])
    
    # Chat Tab
    with tab1:
        render_chat_page(factory)
        
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
    
    # Experiments Tab
    with tab2:
        # Load the full domain config for experiments
        from domain_manager import DomainManager
        dm = DomainManager()
        full_domain_config = dm.load_domain_config(DOMAIN)
        render_experiments_page(DOMAIN, full_domain_config, factory)


def render_chat_page(factory):
    """Render the chat page."""
    # Extract UI configuration from domain config
    ui_config = st.session_state.domain_config.get("ui", {})
    app_title = ui_config.get("app_title", f"🤖 {DOMAIN.title()} Assistant")
    example_queries = ui_config.get("example_queries", [
        "Hello, how can you help me?",
        "What can you do?"
    ])
    
    # Initialize session ID
    if "session_id" not in st.session_state:
        session_id = str(uuid.uuid4())[:10]
        st.session_state.session_id = session_id
    
    user_input = orchestrate_streamlit_and_get_user_input(
        app_title,
        example_queries[0] if len(example_queries) > 0 else "Hello, how can you help me?",
        example_queries[1] if len(example_queries) > 1 else "What can you do?",
    )
    
    # Create agent dynamically using AgentFactory - works for any domain!
    if "agent" not in st.session_state:
        st.session_state.agent = factory.create_agent(
            domain=DOMAIN, 
            framework=FRAMEWORK,
            session_id=st.session_state.session_id
        )
    
    process_input_for_simple_app(user_input)


if __name__ == "__main__":
    multi_domain_agent_app()
