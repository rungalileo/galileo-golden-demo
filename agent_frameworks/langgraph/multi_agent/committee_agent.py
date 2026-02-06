"""
Committee Agent - Individual agent for multi-agent debates

Extends the LangGraph agent pattern to support debate-specific functionality,
including persona-based prompting and A2A protocol integration.
"""

import os
import sys
import json
import importlib.util
from typing import List, Dict, Any, Optional, Annotated
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from domain_manager import DomainConfig
from .a2a_protocol import AgentCard, Task, Message, MessageRole, TextPart


class CommitteeAgentState(TypedDict):
    """State for committee agent graph"""
    messages: Annotated[list, add_messages]
    debate_context: str  # Previous debate history for context


class CommitteeAgent:
    """
    Individual agent for participation in multi-agent debates.
    
    Each CommitteeAgent represents one participant (Bull, Bear, or Moderator)
    with its own persona, prompt, and capabilities.
    """
    
    def __init__(
        self,
        agent_card: AgentCard,
        system_prompt: str,
        domain_config: DomainConfig,
        tools: List[StructuredTool] = None,
        model_name: str = "gpt-4.1",
        temperature: float = 0.3,
        session_id: str = None
    ):
        """
        Initialize a committee agent.
        
        Args:
            agent_card: A2A agent card with identity and capabilities
            system_prompt: The system prompt defining the agent's persona
            domain_config: Domain configuration for tool loading
            tools: Pre-loaded tools (if None, will load from domain)
            model_name: LLM model to use
            temperature: LLM temperature setting
            session_id: Session ID for tracking
        """
        self.agent_card = agent_card
        self.system_prompt = system_prompt
        self.domain_config = domain_config
        self.model_name = model_name
        self.temperature = temperature
        self.session_id = session_id or f"committee-{agent_card.persona}"
        
        # Tools can be provided or loaded from domain
        self.tools = tools if tools is not None else []
        
        # Build the agent graph
        self.graph = None
        self._llm = None
    
    @property
    def name(self) -> str:
        return self.agent_card.name
    
    @property
    def persona(self) -> str:
        return self.agent_card.persona
    
    def _get_llm(self) -> ChatOpenAI:
        """Get or create the LLM instance"""
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                name=f"{self.agent_card.name} Agent"
            )
        return self._llm
    
    def _build_graph(self):
        """Build the LangGraph for this agent"""
        llm = self._get_llm()
        
        # Bind tools if available
        if self.tools:
            llm_with_tools = llm.bind_tools(self.tools)
        else:
            llm_with_tools = llm
        
        def invoke_agent(state: CommitteeAgentState) -> Dict[str, Any]:
            """Process a turn in the debate"""
            messages = list(state["messages"])
            debate_context = state.get("debate_context", "")
            
            # Build full system prompt with debate context
            full_system_prompt = self.system_prompt
            if debate_context:
                full_system_prompt += f"\n\n## Previous Debate Context:\n{debate_context}"
            
            # Add system message
            all_messages = [SystemMessage(content=full_system_prompt)] + messages
            
            # Invoke LLM
            response = llm_with_tools.invoke(all_messages)
            
            return {"messages": [response]}
        
        # Build graph
        graph_builder = StateGraph(CommitteeAgentState)
        graph_builder.add_node("agent", invoke_agent)
        
        if self.tools:
            tool_node = ToolNode(tools=self.tools)
            graph_builder.add_node("tools", tool_node)
            graph_builder.add_edge(START, "agent")
            graph_builder.add_conditional_edges("agent", tools_condition)
            graph_builder.add_edge("tools", "agent")
        else:
            graph_builder.add_edge(START, "agent")
            graph_builder.add_edge("agent", END)
        
        self.graph = graph_builder.compile()
    
    def process_turn(
        self,
        user_message: str,
        debate_context: str = "",
        callbacks: List = None
    ) -> str:
        """
        Process one turn of the debate.
        
        Args:
            user_message: The prompt for this turn (could be the topic or rebuttal instruction)
            debate_context: Previous debate history for context
            callbacks: LangChain callbacks for observability
            
        Returns:
            The agent's response as a string
        """
        # Build graph if not already built
        if self.graph is None:
            self._build_graph()
        
        # Prepare initial state
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "debate_context": debate_context
        }
        
        # Configure callbacks
        config = {"configurable": {"thread_id": self.session_id}}
        if callbacks:
            config["callbacks"] = callbacks
        
        # Invoke the graph
        result = self.graph.invoke(initial_state, config)
        
        # Extract the final response
        if result["messages"]:
            final_message = result["messages"][-1]
            if hasattr(final_message, 'content'):
                return final_message.content
        
        return "No response generated"
    
    def create_a2a_message(self, content: str) -> Message:
        """Create an A2A protocol message from this agent"""
        return Message(
            role=MessageRole.AGENT,
            parts=[TextPart(content=content)],
            sender_id=self.agent_card.name,
            metadata={
                "persona": self.agent_card.persona,
                "agent_name": self.agent_card.name
            }
        )
    
    @classmethod
    def from_config(
        cls,
        agent_name: str,
        committee_config: Dict[str, Any],
        domain_config: DomainConfig,
        committee_path: str,
        tools: List[StructuredTool] = None
    ) -> "CommitteeAgent":
        """
        Create a CommitteeAgent from configuration.
        
        Args:
            agent_name: Name of the agent (bull, bear, moderator)
            committee_config: The committee's config.yaml contents
            domain_config: Parent domain configuration
            committee_path: Path to the investment_committee directory
            tools: Pre-loaded tools to share
            
        Returns:
            Configured CommitteeAgent instance
        """
        # Find agent config
        agent_config = None
        for agent in committee_config.get("agents", []):
            if agent["name"] == agent_name:
                agent_config = agent
                break
        
        if not agent_config:
            raise ValueError(f"Agent '{agent_name}' not found in committee config")
        
        # Load agent card
        card_path = os.path.join(committee_path, agent_config["card_file"])
        agent_card = AgentCard.from_file(card_path)
        
        # Load system prompt
        prompt_path = os.path.join(committee_path, agent_config["prompt_file"])
        with open(prompt_path, 'r') as f:
            prompt_data = json.load(f)
        system_prompt = prompt_data.get("system_prompt", "")
        
        # Get model config
        model_config = committee_config.get("model", {})
        model_name = model_config.get("model_name", "gpt-4.1")
        temperature = model_config.get("temperature", 0.3)
        
        return cls(
            agent_card=agent_card,
            system_prompt=system_prompt,
            domain_config=domain_config,
            tools=tools,
            model_name=model_name,
            temperature=temperature
        )


def load_committee_tools(domain_config: DomainConfig) -> List[StructuredTool]:
    """
    Load tools from the parent finance domain for use by committee agents.
    
    Args:
        domain_config: The finance domain configuration
        
    Returns:
        List of LangChain StructuredTool instances
    """
    tools_path = os.path.join(domain_config.tools_dir, "logic.py")
    tool_schema_path = os.path.join(domain_config.tools_dir, "schema.json")
    
    # Load tool schemas
    with open(tool_schema_path, "r") as f:
        tool_schemas = json.load(f)
    
    # Load tool module
    spec = importlib.util.spec_from_file_location("domain_tools", tools_path)
    tools_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tools_module)
    
    # Get raw functions
    raw_functions = list(tools_module.TOOLS)
    
    # Convert to StructuredTools
    tools = []
    for tool_func in raw_functions:
        tool_schema_dict = next(
            (schema for schema in tool_schemas if schema.get("name") == tool_func.__name__),
            None
        )
        
        langchain_tool = StructuredTool.from_function(
            func=tool_func,
            name=tool_func.__name__,
            description=tool_schema_dict.get("description") if tool_schema_dict else tool_func.__doc__,
            args_schema=tool_schema_dict.get("parameters") if tool_schema_dict else None
        )
        tools.append(langchain_tool)
    
    # Add RAG tool if enabled
    rag_config = domain_config.config.get("rag", {})
    if rag_config.get("enabled", False):
        try:
            from agent_frameworks.langgraph.langgraph_rag import create_domain_rag_tool
            top_k = rag_config.get("top_k", 5)
            rag_tool = create_domain_rag_tool(domain_config.name, top_k)
            tools.append(rag_tool)
        except Exception as e:
            print(f"Warning: Could not load RAG tool: {e}")
    
    return tools
