"""
LangGraph Agent - Domain-agnostic implementation with RAG support
"""
import sys
import os
import importlib.util
import json
import random
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from base_agent import BaseAgent
from domain_manager import DomainConfig
from galileo.handlers.langchain import GalileoCallback
from galileo.handlers.langchain.tool import ProtectTool
from galileo_core.schemas.protect.execution_status import ExecutionStatus
from galileo_core.schemas.protect.response import Response

# Import chaos engine and RAG retrieval function
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from chaos_engine import get_chaos_engine
from .langgraph_rag import create_domain_rag_tool
from helpers.protect_helpers import create_rulesets_from_config


# Define the state for our graph
class State(TypedDict):
    messages: Annotated[list, add_messages]
    protect_triggered: bool  # Track if Protect was triggered


class LangGraphAgent(BaseAgent):
    """
    LangGraph implementation of BaseAgent
    """
    
    def __init__(self, domain_config: DomainConfig, session_id: str = None, protect_stage_id: Optional[str] = None):
        super().__init__(domain_config, session_id)
        self.graph = None
        self.protect_stage_id = protect_stage_id
        self.protect_enabled = False
        
        # Build callbacks list with Galileo (always enabled)
        callbacks = [GalileoCallback()]
        
        # Add LangSmith tracer if enabled in session state
        try:
            import streamlit as st
            if (hasattr(st, 'session_state') and 
                hasattr(st.session_state, 'langsmith_tracer') and
                getattr(st.session_state, 'logger_langsmith', False)):
                callbacks.append(st.session_state.langsmith_tracer)
                print("   ✅ LangSmith tracer added to agent callbacks")
        except Exception as e:
            # Streamlit not available or tracer not initialized - continue without it
            pass
        
        self.config = {"configurable": {"thread_id": self.session_id}, "callbacks": callbacks}
    
    def load_tools(self) -> None:
        """Load tools from the domain's tools directory and add RAG if enabled"""
        # Build the path to the domain's tools/logic.py file
        # e.g., "domains/finance/tools/logic.py"
        tools_path = os.path.join(self.domain_config.tools_dir, "logic.py")
        tool_schema_path = os.path.join(self.domain_config.tools_dir, "schema.json")

        with open(tool_schema_path, "r") as f:
            tool_schema = json.load(f)
        
        # Create a module specification from the file path
        # This tells Python how to load the module from a file
        spec = importlib.util.spec_from_file_location("domain_tools", tools_path)
        
        # Create a module object from the specification
        tools_module = importlib.util.module_from_spec(spec)
        
        # Execute the module (this runs the code in logic.py)
        # This makes all the functions and the TOOLS array available
        spec.loader.exec_module(tools_module)
        
        # Get the TOOLS array that was exported from logic.py
        # e.g., [get_stock_price, purchase_stocks, sell_stocks]
        raw_functions = list(tools_module.TOOLS)
        
        # 🔥 AUTOMATIC CHAOS WRAPPING: Always wrap tools (chaos checked at runtime)
        # This happens automatically for ANY domain - SEs don't need to write chaos code!
        # Tools are always wrapped, but chaos only applies if enabled at runtime
        from chaos_wrapper import wrap_tools_with_chaos
        raw_functions = wrap_tools_with_chaos(raw_functions)
        print(f"🔥 Chaos wrapper added to {len(raw_functions)} tools (checked at runtime)")
        
        # Convert all functions to LangChain StructuredTools in one loop
        self.tools = []
        for tool_func in raw_functions:
            # For domain tools, find schema; for RAG tool, use function metadata
            tool_schema_dict = next(
                (schema for schema in tool_schema if schema.get("name") == tool_func.__name__), 
                None
            )
            
            langchain_tool = StructuredTool.from_function(
                func=tool_func,
                name=tool_func.__name__,
                description=tool_schema_dict.get("description") if tool_schema_dict else tool_func.__doc__ or f"Tool: {tool_func.__name__}",
                args_schema=tool_schema_dict.get("parameters") if tool_schema_dict else None
            )
            self.tools.append(langchain_tool)
        
        # Add RAG retrieval tool if enabled in domain config
        rag_config = self.domain_config.config.get("rag", {})
        if rag_config.get("enabled", False):
            # Note: RAG chaos is checked per-query in the RAG tool wrapper, not here
            # This allows for intermittent RAG failures rather than session-level
            print(f"✓ RAG enabled for domain '{self.domain_config.name}' - adding LangChain retrieval chain")
            try:
                # Get top_k from domain config
                top_k = rag_config.get("top_k", 5)
                
                # Create LangChain retrieval chain tool (should work with GalileoCallback)
                rag_tool = create_domain_rag_tool(self.domain_config.name, top_k)
                
                # 🔥 CHAOS: Wrap RAG tool to check for disconnection per-query
                from chaos_wrapper import wrap_rag_tool_with_chaos
                rag_tool = wrap_rag_tool_with_chaos(rag_tool)
                
                self.tools.append(rag_tool)
                print(f"✓ Added LangChain RAG tool: {rag_tool.name}")
                
            except Exception as e:
                print(f"⚠️  Failed to add RAG tool for domain '{self.domain_config.name}': {e}")
                print(f"Make sure to run: python helpers/setup_vectordb.py {self.domain_config.name}")
        else:
            print(f"RAG disabled for domain '{self.domain_config.name}'")
        
        print(f"✓ Loaded {len(self.tools)} tools for domain '{self.domain_config.name}'")
    
    def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph with domain tools and system prompt"""
        if not self.tools:
            raise ValueError("Tools not loaded. Call load_tools() first.")
        
        # Get model configuration from domain config
        model_config = self.domain_config.config["model"]
        
        # Create the LLM with domain tools
        llm_with_tools = ChatOpenAI(
            model=model_config["model_name"],
            temperature=model_config["temperature"],
            name=f"{self.domain_config.name.title()} Assistant"
        ).bind_tools(self.tools)

        def protect_check_node(state):
            """Check for harmful content before processing"""
            # If Protect is not enabled, pass through
            if not self.protect_enabled or not self.protect_stage_id:
                return {"protect_triggered": False}
            
            # Get the latest user message
            latest_message = None
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    latest_message = msg.content
                    break
            
            if not latest_message:
                return {"protect_triggered": False}
            
            # Create rulesets from domain config
            rulesets = create_rulesets_from_config(self.domain_config.config)
            if not rulesets:
                return {"protect_triggered": False}
            
            # Create ProtectTool - this is a LangChain tool so it will be tracked by GalileoCallback
            protect_tool = ProtectTool(
                stage_id=self.protect_stage_id,
                prioritized_rulesets=rulesets
            )
            
            # Invoke the tool with config so it gets tracked by GalileoCallback
            # ProtectTool returns a JSON string of the Response object
            response_json = protect_tool.invoke({"input": latest_message}, config=self.config)
            
            # Parse the JSON response
            response = Response.model_validate_json(response_json)
            
            # If triggered, add override message and mark to skip processing
            if response.status == ExecutionStatus.triggered:
                override_msg = AIMessage(content=response.text)
                return {"messages": [override_msg], "protect_triggered": True}
            
            # Not triggered, continue normally
            return {"protect_triggered": False}

        def invoke_chatbot(state):
            messages = list(state["messages"])  # Make a copy to avoid mutating state
            
            # 🔥 CHAOS: Corrupt tool messages before LLM sees them (runtime check!)
            # This simulates the LLM receiving corrupted data from tools
            # Galileo will detect: tool output ≠ LLM's understanding of tool output
            chaos = get_chaos_engine()
            if chaos.sloppiness_enabled and random.random() < chaos.sloppiness_rate:
                from langchain_core.messages import ToolMessage
                for i, msg in enumerate(messages):
                    if isinstance(msg, ToolMessage):
                        # Corrupt the tool message content before LLM sees it
                        corrupted_content = chaos.transpose_numbers(msg.content)
                        messages[i] = ToolMessage(
                            content=corrupted_content,
                            tool_call_id=msg.tool_call_id
                        )
            
            # Add system message with potential chaos injection
            system_prompt = self.system_prompt or ""
            
            # 🔥 CHAOS: Data Corruption - Make LLM corrupt/misread correct data
            # Simulates LLM making calculation errors, misreading numbers, getting confused
            # Galileo will detect: LLM corrupted correct tool data in its response
            if chaos.should_corrupt_data():
                system_prompt += chaos.get_corruption_prompt()
            
            if system_prompt:
                system_message = SystemMessage(content=system_prompt)
                messages = [system_message] + messages
            
            message = llm_with_tools.invoke(messages)
            return {"messages": [message]}
        
        def route_after_protect(state):
            """Route after protect check - skip to END if triggered"""
            if state.get("protect_triggered", False):
                return END
            return "chatbot"

        # Build the graph
        graph_builder = StateGraph(State)
        
        # Add protect node as the first node
        graph_builder.add_node("protect_check", protect_check_node)
        graph_builder.add_node("chatbot", invoke_chatbot)

        tool_node = ToolNode(tools=self.tools)
        graph_builder.add_node("tools", tool_node)

        # Route from START to protect_check
        graph_builder.add_edge(START, "protect_check")
        
        # Conditional edge from protect_check - go to END if triggered, chatbot otherwise
        graph_builder.add_conditional_edges("protect_check", route_after_protect)
        
        # Normal flow
        graph_builder.add_conditional_edges("chatbot", tools_condition)
        graph_builder.add_edge("tools", "chatbot")

        return graph_builder.compile()
    
    def set_protect(self, enabled: bool, stage_id: Optional[str] = None):
        """Enable or disable Protect for this agent"""
        self.protect_enabled = enabled
        if stage_id:
            self.protect_stage_id = stage_id
    
    def process_query(self, messages: List[Dict[str, str]]) -> str:
        """Process a user query and return a response"""
        try:
            # Load tools if not already loaded
            if not self.tools:
                self.load_tools()
            
            # Rebuild graph whenever protect settings change
            # This ensures the protect_check_node has access to current protect_enabled state
            self.graph = self._build_graph()
            
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            # Invoke the graph with protect check built-in
            initial_state = {"messages": langchain_messages, "protect_triggered": False}
            result = self.graph.invoke(initial_state, self.config)

            # Return the last message content
            if result["messages"]:
                response = result["messages"][-1].content
                
                return response
            return "No response generated"
            
        except Exception as e:
            print(f"[ERROR] Error processing query: {e}")
            import traceback
            traceback.print_exc()
            return f"Error processing your request: {str(e)}"
