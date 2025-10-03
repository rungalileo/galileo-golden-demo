"""
Galileo Demo App
"""
import uuid
import streamlit as st
# import phoenix as px
from dotenv import load_dotenv
from galileo import galileo_context
from agent_factory import AgentFactory
from setup_env import setup_environment
from langchain_core.messages import AIMessage, HumanMessage
# from phoenix.otel import register
import os

# TODO: Add sidebar with link to traces

# Load environment variables
load_dotenv()

# tracer_provider = register(
#   project_name="galileo-demo",
#   endpoint="https://app.phoenix.arize.com/s/paul/v1/traces",
#   auto_instrument=True
# )

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


def multi_domain_agent_app():
    """Main agent app - configuration-driven using domain config"""
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
