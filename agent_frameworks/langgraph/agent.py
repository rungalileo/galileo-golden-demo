"""
LangGraph Agent - Domain-agnostic implementation with RAG support
"""
import sys
import os
import importlib.util
import json
from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from base_agent import BaseAgent
from domain_manager import DomainConfig
from galileo.handlers.langchain import GalileoCallback

# Import chaos engine
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from chaos_engine import get_chaos_engine
    CHAOS_AVAILABLE = True
except ImportError:
    CHAOS_AVAILABLE = False

# Import RAG retrieval function
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from tools.rag_retrieval import create_domain_retrieval_function
from .langgraph_rag import create_domain_rag_tool


# Define the state for our graph
class State(TypedDict):
    messages: Annotated[list, add_messages]


class LangGraphAgent(BaseAgent):
    """
    LangGraph implementation of BaseAgent
    """
    
    def __init__(self, domain_config: DomainConfig, session_id: str = None):
        super().__init__(domain_config, session_id)
        self.graph = None
        self.config = {"configurable": {"thread_id": self.session_id}, "callbacks": [GalileoCallback()]}
    
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
            # Chaos: Check if RAG should be disconnected
            if CHAOS_AVAILABLE:
                chaos = get_chaos_engine()
                should_fail, error_msg = chaos.should_disconnect_rag()
                if should_fail:
                    print(f"🔥 CHAOS: RAG disconnected - {error_msg}")
                    print(f"⚠️  Skipping RAG tool addition due to chaos injection")
                    # Don't add RAG tool - simulate disconnection
                    print(f"RAG disabled for domain '{self.domain_config.name}' (chaos mode)")
                    return  # Skip RAG initialization
            
            print(f"✓ RAG enabled for domain '{self.domain_config.name}' - adding LangChain retrieval chain")
            try:
                # Get top_k from domain config
                top_k = rag_config.get("top_k", 5)
                
                # Create LangChain retrieval chain tool (should work with GalileoCallback)
                rag_tool = create_domain_rag_tool(self.domain_config.name, top_k)
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

        def invoke_chatbot(state):
            # Add system message if we have one
            if self.system_prompt:
                system_message = SystemMessage(content=self.system_prompt)
                messages = [system_message] + state["messages"]
            else:
                messages = state["messages"]
            
            message = llm_with_tools.invoke(messages)
            return {"messages": [message]}

        # Build the graph
        graph_builder = StateGraph(State)
        graph_builder.add_node("chatbot", invoke_chatbot)

        tool_node = ToolNode(tools=self.tools)
        graph_builder.add_node("tools", tool_node)

        graph_builder.add_conditional_edges("chatbot", tools_condition)
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_edge(START, "chatbot")

        return graph_builder.compile()
    
    def process_query(self, messages: List[Dict[str, str]]) -> str:
        """Process a user query and return a response"""
        try:
            # Load tools if not already loaded
            if not self.tools:
                self.load_tools()
            
            # Build graph if not already built
            if not self.graph:
                self.graph = self._build_graph()
            
            # Convert messages to LangChain format
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    from langchain_core.messages import AIMessage
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            # Process the query
            initial_state = {"messages": langchain_messages}
            result = self.graph.invoke(initial_state, self.config)

            # Return the last message content
            if result["messages"]:
                response = result["messages"][-1].content
                
                # Chaos: Maybe transpose numbers in response (simulate hallucination)
                if CHAOS_AVAILABLE:
                    chaos = get_chaos_engine()
                    response = chaos.maybe_transpose_numbers(response)
                
                return response
            return "No response generated"
            
        except Exception as e:
            print(f"[ERROR] Error processing query: {e}")
            return f"Error processing your request: {str(e)}"
