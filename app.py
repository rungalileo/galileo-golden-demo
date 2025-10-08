"""
Galileo Demo App with Experiments Support
"""
import uuid
import streamlit as st
import phoenix as px
from dotenv import load_dotenv, find_dotenv
from galileo import galileo_context
from agent_factory import AgentFactory
from setup_env import setup_environment
from langchain_core.messages import AIMessage, HumanMessage
from phoenix.otel import register
import os
import pandas as pd
import threading

# Load environment variables
# 1) load global/shared first
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
# 2) then load per-app .env (if present) to override selectively
load_dotenv(find_dotenv(usecwd=True), override=True)

# Initialize Phoenix tracing
tracer_provider = register(
  project_name="galileo-demo",
  endpoint="https://app.phoenix.arize.com/s/paul/v1/traces",
  auto_instrument=True
)

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


def multi_domain_agent_app():
    """Main agent app with tabs for chat and experiments"""
    # Setup environment and secrets (only once)
    if "environment_setup_done" not in st.session_state:
        setup_environment()
        st.session_state.environment_setup_done = True
    
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
    
    # Sidebar with navigation
    with st.sidebar:
        st.title("Navigation")
        st.markdown("---")
        
        # Session info
        st.markdown("### 📊 Session Info")
        st.caption(f"Session ID: `{st.session_state.session_id}`")
        st.caption(f"Domain: `{DOMAIN}`")
        st.caption(f"Framework: `{FRAMEWORK}`")
        
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
    
    # Main content with tabs
    tab1, tab2 = st.tabs(["💬 Chat", "🧪 Experiments"])
    
    with tab1:
        render_chat_tab(app_title, example_queries)
    
    with tab2:
        render_experiments_tab()


if __name__ == "__main__":
    multi_domain_agent_app()
