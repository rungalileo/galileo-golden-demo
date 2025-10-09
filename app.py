"""
Galileo Demo App - Multi-Domain with Dynamic Routing
"""
import uuid
import streamlit as st
from dotenv import load_dotenv
from galileo import galileo_context
from agent_factory import AgentFactory
from setup_env import setup_environment
from domain_manager import DomainManager
from langchain_core.messages import AIMessage, HumanMessage
import os

# TODO: Add sidebar with link to traces

# Load environment variables
load_dotenv()


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
    agent_title: str, example_query_1: str, example_query_2: str, domain_name: str
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
            galileo_context.start_session(name=f"{domain_name.title()} Agent Demo", external_id=session_id)
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


def multi_domain_agent_app(domain_name: str):
    """Main agent app - configuration-driven using domain config"""
    # Setup environment and secrets (only once)
    if "environment_setup_done" not in st.session_state:
        setup_environment()
        st.session_state.environment_setup_done = True
    
    # Initialize AgentFactory once
    if "factory" not in st.session_state:
        st.session_state.factory = AgentFactory()
    
    factory = st.session_state.factory
    
    # Load domain configuration for UI settings (per domain)
    domain_key = f"domain_config_{domain_name}"
    if domain_key not in st.session_state:
        domain_info = factory.get_domain_info(domain_name)
        st.session_state[domain_key] = domain_info
    
    # Extract UI configuration from domain config
    ui_config = st.session_state[domain_key].get("ui", {})
    app_title = ui_config.get("app_title", f"🤖 {domain_name.title()} Assistant")
    example_queries = ui_config.get("example_queries", [
        "Hello, how can you help me?",
        "What can you do?"
    ])
    
    user_input = orchestrate_streamlit_and_get_user_input(
        app_title,
        example_queries[0] if len(example_queries) > 0 else "Hello, how can you help me?",
        example_queries[1] if len(example_queries) > 1 else "What can you do?",
        domain_name  # Pass domain for session naming
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
        
        for i, domain in enumerate(available_domains):
            try:
                domain_info = dm.get_domain_info(domain)
                ui_config = domain_info.get("ui", {})
                app_title = ui_config.get("app_title", f"🤖 {domain.title()} Assistant")
                
                # Create page using st.Page
                if i == 0:
                    # First domain gets both root and named path
                    # Default page (root URL)
                    default_page = st.Page(
                        create_domain_page(domain),
                        title=app_title,
                        icon="🤖",
                        default=True
                    )
                    pages.append(default_page)
                
                # Named path for all domains
                page = st.Page(
                    create_domain_page(domain),
                    title=app_title,
                    url_path=f"/{domain}",
                    icon="🤖"
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
            # Fallback to first domain
            if available_domains:
                st.warning("Falling back to direct domain execution...")
                multi_domain_agent_app(available_domains[0])
        
    except Exception as e:
        st.error(f"Error initializing app: {str(e)}")
        st.info("Please check your domain configurations and try again.")


if __name__ == "__main__":
    main()
