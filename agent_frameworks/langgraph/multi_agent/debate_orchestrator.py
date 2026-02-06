"""
Debate Orchestrator - Manages multi-agent debate flow

Orchestrates the debate between Bull and Bear agents, with the Moderator
making the final recommendation. Uses LangGraph StateGraph for flow management.

Debate Flow:
1. User Query -> Bull Opening
2. Bull Opening -> Bear Rebuttal
3. Bear Rebuttal -> Bull Counter (if max_rounds > 1)
4. Bull Counter -> Bear Counter (if max_rounds > 1)
5. ... (repeat for max_rounds)
6. Final Round -> Moderator Evaluation
7. Moderator Evaluation -> Final Recommendation

Galileo Integration:
Each agent turn is logged with metadata including:
- Agent persona (bull/bear/moderator)
- Turn type (opening/rebuttal/counter/evaluation)
- Round number
- Debate topic
"""

import os
import sys
import json
import yaml
import time
from typing import List, Dict, Any, Optional, TypedDict, Annotated, Generator, Callable
from dataclasses import dataclass, field
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from domain_manager import DomainManager, DomainConfig
from .a2a_protocol import (
    Task, TaskStatus, Message, MessageRole, TextPart, Artifact,
    TaskManager, AgentRegistry, AgentCard
)
from .committee_agent import CommitteeAgent, load_committee_tools

# Galileo logging helper (optional - enhances observability)
try:
    from galileo import GalileoLogger
    GALILEO_AVAILABLE = True
except ImportError:
    GALILEO_AVAILABLE = False


def log_debate_turn_to_galileo(
    logger: Optional[Any],
    agent_name: str,
    agent_persona: str,
    turn_type: str,
    round_number: int,
    topic: str,
    input_text: str,
    output_text: str,
    duration_ns: int
) -> None:
    """
    Log a debate turn to Galileo as a custom span.
    
    This provides additional observability beyond what the LangChain callback captures,
    specifically adding debate-specific metadata.
    """
    if logger is None:
        return
    
    try:
        # Add a workflow span for the debate turn
        logger.add_workflow_span(
            input=input_text,
            output=output_text,
            name=f"Debate Turn: {agent_name} ({turn_type})",
            duration_ns=duration_ns,
            metadata={
                "agent_name": agent_name,
                "agent_persona": agent_persona,
                "turn_type": turn_type,
                "round_number": str(round_number),
                "debate_topic": topic,
                "multi_agent": "true",
                "framework": "investment_committee"
            },
            tags=["investment-committee", "multi-agent", "debate", agent_persona, turn_type]
        )
    except Exception as e:
        print(f"Warning: Could not log debate turn to Galileo: {e}")


# =============================================================================
# Debate State
# =============================================================================

class DebateState(TypedDict):
    """State for the debate orchestrator graph"""
    topic: str  # The investment topic/question
    current_round: int  # Current debate round
    max_rounds: int  # Maximum rounds
    debate_history: List[Dict[str, Any]]  # All debate turns
    bull_arguments: List[str]  # Bull's arguments
    bear_arguments: List[str]  # Bear's arguments
    moderator_decision: Optional[str]  # Final decision
    status: str  # Current status
    error: Optional[str]  # Error message if any


@dataclass
class DebateTurn:
    """Represents one turn in the debate"""
    agent_name: str
    agent_persona: str
    content: str
    round_number: int
    turn_type: str  # "opening", "rebuttal", "counter", "evaluation"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_persona": self.agent_persona,
            "content": self.content,
            "round_number": self.round_number,
            "turn_type": self.turn_type,
            "timestamp": self.timestamp,
            "tool_calls": self.tool_calls
        }


# =============================================================================
# Debate Orchestrator
# =============================================================================

class DebateOrchestrator:
    """
    Orchestrates the debate between Bull, Bear, and Moderator agents.
    
    Uses LangGraph to manage the debate flow and A2A protocol for
    inter-agent communication.
    """
    
    def __init__(
        self,
        domain_config: DomainConfig,
        committee_path: str,
        callbacks: List = None
    ):
        """
        Initialize the debate orchestrator.
        
        Args:
            domain_config: The finance domain configuration
            committee_path: Path to investment_committee directory
            callbacks: LangChain callbacks for observability
        """
        self.domain_config = domain_config
        self.committee_path = committee_path
        self.callbacks = callbacks or []
        
        # Load committee configuration
        config_path = os.path.join(committee_path, "config.yaml")
        with open(config_path, 'r') as f:
            self.committee_config = yaml.safe_load(f)
        
        # Initialize A2A components
        self.task_manager = TaskManager()
        self.agent_registry = AgentRegistry()
        
        # Load shared tools from parent domain
        self.tools = load_committee_tools(domain_config)
        
        # Create committee agents
        self.bull_agent = self._create_agent("bull")
        self.bear_agent = self._create_agent("bear")
        self.moderator_agent = self._create_agent("moderator")
        
        # Register agents
        self.agent_registry.register(self.bull_agent.agent_card)
        self.agent_registry.register(self.bear_agent.agent_card)
        self.agent_registry.register(self.moderator_agent.agent_card)
        
        # Build orchestrator graph
        self.graph = self._build_graph()
    
    def _create_agent(self, agent_name: str) -> CommitteeAgent:
        """Create a committee agent from config"""
        return CommitteeAgent.from_config(
            agent_name=agent_name,
            committee_config=self.committee_config,
            domain_config=self.domain_config,
            committee_path=self.committee_path,
            tools=self.tools
        )
    
    def _get_agent_prompt(self, agent_name: str, prompt_type: str) -> str:
        """Get a specific prompt for an agent"""
        agent_config = None
        for agent in self.committee_config.get("agents", []):
            if agent["name"] == agent_name:
                agent_config = agent
                break
        
        if not agent_config:
            return ""
        
        prompt_path = os.path.join(self.committee_path, agent_config["prompt_file"])
        with open(prompt_path, 'r') as f:
            prompt_data = json.load(f)
        
        return prompt_data.get(prompt_type, prompt_data.get("system_prompt", ""))
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph for debate orchestration"""
        
        def bull_opening(state: DebateState) -> Dict[str, Any]:
            """Bull presents opening argument"""
            topic = state["topic"]
            prompt = self._get_agent_prompt("bull", "opening_prompt")
            full_prompt = f"{prompt}\n\nInvestment Topic: {topic}"
            
            response = self.bull_agent.process_turn(
                user_message=full_prompt,
                debate_context="",
                callbacks=self.callbacks
            )
            
            turn = DebateTurn(
                agent_name="Bull",
                agent_persona="bull",
                content=response,
                round_number=1,
                turn_type="opening"
            )
            
            return {
                "debate_history": state["debate_history"] + [turn.to_dict()],
                "bull_arguments": state["bull_arguments"] + [response],
                "status": "bull_opening_complete"
            }
        
        def bear_rebuttal(state: DebateState) -> Dict[str, Any]:
            """Bear responds to Bull's argument"""
            topic = state["topic"]
            bull_args = state["bull_arguments"]
            prompt = self._get_agent_prompt("bear", "rebuttal_prompt")
            
            # Build context from Bull's arguments
            context = f"Topic: {topic}\n\nBull's Arguments:\n" + "\n---\n".join(bull_args)
            full_prompt = f"{prompt}\n\nRespond to Bull's analysis above."
            
            response = self.bear_agent.process_turn(
                user_message=full_prompt,
                debate_context=context,
                callbacks=self.callbacks
            )
            
            turn = DebateTurn(
                agent_name="Bear",
                agent_persona="bear",
                content=response,
                round_number=state["current_round"],
                turn_type="rebuttal"
            )
            
            return {
                "debate_history": state["debate_history"] + [turn.to_dict()],
                "bear_arguments": state["bear_arguments"] + [response],
                "status": "bear_rebuttal_complete"
            }
        
        def bull_counter(state: DebateState) -> Dict[str, Any]:
            """Bull counters Bear's arguments"""
            topic = state["topic"]
            bear_args = state["bear_arguments"]
            prompt = self._get_agent_prompt("bull", "rebuttal_prompt")
            
            # Build context from Bear's arguments
            context = self._build_debate_context(state)
            full_prompt = f"{prompt}\n\nCounter Bear's concerns and reinforce your bullish thesis."
            
            response = self.bull_agent.process_turn(
                user_message=full_prompt,
                debate_context=context,
                callbacks=self.callbacks
            )
            
            turn = DebateTurn(
                agent_name="Bull",
                agent_persona="bull",
                content=response,
                round_number=state["current_round"],
                turn_type="counter"
            )
            
            return {
                "debate_history": state["debate_history"] + [turn.to_dict()],
                "bull_arguments": state["bull_arguments"] + [response],
                "current_round": state["current_round"] + 1,
                "status": "bull_counter_complete"
            }
        
        def bear_counter(state: DebateState) -> Dict[str, Any]:
            """Bear counters Bull's arguments"""
            topic = state["topic"]
            prompt = self._get_agent_prompt("bear", "rebuttal_prompt")
            
            context = self._build_debate_context(state)
            full_prompt = f"{prompt}\n\nCounter Bull's optimism and reinforce your cautious stance."
            
            response = self.bear_agent.process_turn(
                user_message=full_prompt,
                debate_context=context,
                callbacks=self.callbacks
            )
            
            turn = DebateTurn(
                agent_name="Bear",
                agent_persona="bear",
                content=response,
                round_number=state["current_round"],
                turn_type="counter"
            )
            
            return {
                "debate_history": state["debate_history"] + [turn.to_dict()],
                "bear_arguments": state["bear_arguments"] + [response],
                "status": "bear_counter_complete"
            }
        
        def moderator_evaluation(state: DebateState) -> Dict[str, Any]:
            """Moderator evaluates and makes final recommendation"""
            topic = state["topic"]
            prompt = self._get_agent_prompt("moderator", "evaluation_prompt")
            
            context = self._build_debate_context(state)
            full_prompt = f"{prompt}\n\nTopic: {topic}"
            
            response = self.moderator_agent.process_turn(
                user_message=full_prompt,
                debate_context=context,
                callbacks=self.callbacks
            )
            
            turn = DebateTurn(
                agent_name="Moderator",
                agent_persona="moderator",
                content=response,
                round_number=state["current_round"],
                turn_type="evaluation"
            )
            
            return {
                "debate_history": state["debate_history"] + [turn.to_dict()],
                "moderator_decision": response,
                "status": "completed"
            }
        
        def should_continue_debate(state: DebateState) -> str:
            """Determine if debate should continue or go to moderator"""
            current_round = state["current_round"]
            max_rounds = state["max_rounds"]
            
            if current_round >= max_rounds:
                return "moderator"
            return "continue"
        
        # Build the graph
        graph_builder = StateGraph(DebateState)
        
        # Add nodes
        graph_builder.add_node("bull_opening", bull_opening)
        graph_builder.add_node("bear_rebuttal", bear_rebuttal)
        graph_builder.add_node("bull_counter", bull_counter)
        graph_builder.add_node("bear_counter", bear_counter)
        graph_builder.add_node("moderator_evaluation", moderator_evaluation)
        
        # Add edges
        graph_builder.add_edge(START, "bull_opening")
        graph_builder.add_edge("bull_opening", "bear_rebuttal")
        
        # Conditional edge after bear rebuttal
        graph_builder.add_conditional_edges(
            "bear_rebuttal",
            should_continue_debate,
            {
                "continue": "bull_counter",
                "moderator": "moderator_evaluation"
            }
        )
        
        # Continue debate loop
        graph_builder.add_edge("bull_counter", "bear_counter")
        graph_builder.add_conditional_edges(
            "bear_counter",
            should_continue_debate,
            {
                "continue": "bull_counter",
                "moderator": "moderator_evaluation"
            }
        )
        
        # End at moderator
        graph_builder.add_edge("moderator_evaluation", END)
        
        return graph_builder.compile()
    
    def _build_debate_context(self, state: DebateState) -> str:
        """Build debate context string from history"""
        context_parts = [f"Topic: {state['topic']}\n"]
        
        for turn in state["debate_history"]:
            agent = turn["agent_name"]
            content = turn["content"]
            turn_type = turn["turn_type"]
            context_parts.append(f"[{agent} - {turn_type}]:\n{content}\n")
        
        return "\n---\n".join(context_parts)
    
    def run_debate(
        self,
        topic: str,
        max_rounds: int = None
    ) -> Dict[str, Any]:
        """
        Run a complete debate on the given topic.
        
        Args:
            topic: The investment topic/question to debate
            max_rounds: Override max rounds from config
            
        Returns:
            Complete debate result with history and decision
        """
        if max_rounds is None:
            max_rounds = self.committee_config.get("debate", {}).get("max_rounds", 2)
        
        # Create A2A task
        task = self.task_manager.create_task(
            topic=topic,
            max_rounds=max_rounds,
            metadata={"domain": self.domain_config.name}
        )
        task.update_status(TaskStatus.WORKING)
        
        # Initial state
        initial_state: DebateState = {
            "topic": topic,
            "current_round": 1,
            "max_rounds": max_rounds,
            "debate_history": [],
            "bull_arguments": [],
            "bear_arguments": [],
            "moderator_decision": None,
            "status": "started",
            "error": None
        }
        
        try:
            # Run the debate graph
            config = {"configurable": {"thread_id": task.id}}
            if self.callbacks:
                config["callbacks"] = self.callbacks
            
            result = self.graph.invoke(initial_state, config)
            
            # Update task with results
            task.update_status(TaskStatus.COMPLETED)
            
            # Create final artifact
            final_artifact = Artifact(
                name="Investment Recommendation",
                description=f"Final recommendation for: {topic}",
                parts=[TextPart(content=result.get("moderator_decision", ""))]
            )
            task.add_artifact(final_artifact)
            
            return {
                "task_id": task.id,
                "topic": topic,
                "status": "completed",
                "debate_history": result.get("debate_history", []),
                "bull_arguments": result.get("bull_arguments", []),
                "bear_arguments": result.get("bear_arguments", []),
                "moderator_decision": result.get("moderator_decision"),
                "rounds_completed": result.get("current_round", 1)
            }
            
        except Exception as e:
            task.update_status(TaskStatus.FAILED)
            task.metadata["error"] = str(e)
            
            return {
                "task_id": task.id,
                "topic": topic,
                "status": "failed",
                "error": str(e),
                "debate_history": [],
                "moderator_decision": None
            }
    
    def run_debate_streaming(
        self,
        topic: str,
        max_rounds: int = None,
        galileo_logger: Optional[Any] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Run a debate with streaming updates for each turn.
        
        Yields debate turns as they complete, useful for UI updates.
        Each turn is also logged to Galileo for observability.
        
        Args:
            topic: The investment topic/question
            max_rounds: Override max rounds from config
            galileo_logger: Optional Galileo logger for enhanced observability
            
        Yields:
            Dict with turn information after each agent responds
        """
        if max_rounds is None:
            max_rounds = self.committee_config.get("debate", {}).get("max_rounds", 2)
        
        # Track state manually for streaming
        debate_history = []
        bull_arguments = []
        bear_arguments = []
        current_round = 1
        
        # Bull opening
        yield {"status": "bull_opening", "agent": "Bull", "round": 1}
        
        start_time = time.time()
        prompt = self._get_agent_prompt("bull", "opening_prompt")
        input_text = f"{prompt}\n\nInvestment Topic: {topic}"
        response = self.bull_agent.process_turn(
            user_message=input_text,
            callbacks=self.callbacks
        )
        duration_ns = int((time.time() - start_time) * 1_000_000_000)
        
        # Log to Galileo
        log_debate_turn_to_galileo(
            galileo_logger, "Bull", "bull", "opening", 1, topic,
            input_text, response, duration_ns
        )
        
        bull_arguments.append(response)
        turn = {
            "agent_name": "Bull",
            "agent_persona": "bull",
            "content": response,
            "round_number": 1,
            "turn_type": "opening"
        }
        debate_history.append(turn)
        yield {"status": "turn_complete", "turn": turn}
        
        # Bear rebuttal
        yield {"status": "bear_rebuttal", "agent": "Bear", "round": 1}
        
        start_time = time.time()
        context = f"Topic: {topic}\n\nBull's Arguments:\n{response}"
        prompt = self._get_agent_prompt("bear", "rebuttal_prompt")
        input_text = f"{prompt}\n\nRespond to Bull's analysis above."
        response = self.bear_agent.process_turn(
            user_message=input_text,
            debate_context=context,
            callbacks=self.callbacks
        )
        duration_ns = int((time.time() - start_time) * 1_000_000_000)
        
        # Log to Galileo
        log_debate_turn_to_galileo(
            galileo_logger, "Bear", "bear", "rebuttal", 1, topic,
            input_text, response, duration_ns
        )
        
        bear_arguments.append(response)
        turn = {
            "agent_name": "Bear",
            "agent_persona": "bear",
            "content": response,
            "round_number": 1,
            "turn_type": "rebuttal"
        }
        debate_history.append(turn)
        yield {"status": "turn_complete", "turn": turn}
        
        # Additional rounds
        while current_round < max_rounds:
            current_round += 1
            
            # Bull counter
            yield {"status": "bull_counter", "agent": "Bull", "round": current_round}
            
            start_time = time.time()
            context = self._build_streaming_context(topic, debate_history)
            prompt = self._get_agent_prompt("bull", "rebuttal_prompt")
            input_text = f"{prompt}\n\nCounter Bear's concerns."
            response = self.bull_agent.process_turn(
                user_message=input_text,
                debate_context=context,
                callbacks=self.callbacks
            )
            duration_ns = int((time.time() - start_time) * 1_000_000_000)
            
            # Log to Galileo
            log_debate_turn_to_galileo(
                galileo_logger, "Bull", "bull", "counter", current_round, topic,
                input_text, response, duration_ns
            )
            
            bull_arguments.append(response)
            turn = {
                "agent_name": "Bull",
                "agent_persona": "bull",
                "content": response,
                "round_number": current_round,
                "turn_type": "counter"
            }
            debate_history.append(turn)
            yield {"status": "turn_complete", "turn": turn}
            
            # Bear counter
            yield {"status": "bear_counter", "agent": "Bear", "round": current_round}
            
            start_time = time.time()
            context = self._build_streaming_context(topic, debate_history)
            prompt = self._get_agent_prompt("bear", "rebuttal_prompt")
            input_text = f"{prompt}\n\nCounter Bull's optimism."
            response = self.bear_agent.process_turn(
                user_message=input_text,
                debate_context=context,
                callbacks=self.callbacks
            )
            duration_ns = int((time.time() - start_time) * 1_000_000_000)
            
            # Log to Galileo
            log_debate_turn_to_galileo(
                galileo_logger, "Bear", "bear", "counter", current_round, topic,
                input_text, response, duration_ns
            )
            
            bear_arguments.append(response)
            turn = {
                "agent_name": "Bear",
                "agent_persona": "bear",
                "content": response,
                "round_number": current_round,
                "turn_type": "counter"
            }
            debate_history.append(turn)
            yield {"status": "turn_complete", "turn": turn}
        
        # Moderator evaluation
        yield {"status": "moderator_evaluation", "agent": "Moderator", "round": current_round}
        
        start_time = time.time()
        context = self._build_streaming_context(topic, debate_history)
        prompt = self._get_agent_prompt("moderator", "evaluation_prompt")
        input_text = f"{prompt}\n\nTopic: {topic}"
        response = self.moderator_agent.process_turn(
            user_message=input_text,
            debate_context=context,
            callbacks=self.callbacks
        )
        duration_ns = int((time.time() - start_time) * 1_000_000_000)
        
        # Log to Galileo
        log_debate_turn_to_galileo(
            galileo_logger, "Moderator", "moderator", "evaluation", current_round, topic,
            input_text, response, duration_ns
        )
        
        turn = {
            "agent_name": "Moderator",
            "agent_persona": "moderator",
            "content": response,
            "round_number": current_round,
            "turn_type": "evaluation"
        }
        debate_history.append(turn)
        yield {"status": "turn_complete", "turn": turn}
        
        # Final result
        yield {
            "status": "completed",
            "debate_history": debate_history,
            "bull_arguments": bull_arguments,
            "bear_arguments": bear_arguments,
            "moderator_decision": response
        }
    
    def _build_streaming_context(self, topic: str, history: List[Dict]) -> str:
        """Build context from streaming history"""
        parts = [f"Topic: {topic}\n"]
        for turn in history:
            parts.append(f"[{turn['agent_name']}]: {turn['content']}")
        return "\n---\n".join(parts)


def create_debate_orchestrator(
    domain_name: str = "finance",
    callbacks: List = None
) -> DebateOrchestrator:
    """
    Factory function to create a debate orchestrator.
    
    Args:
        domain_name: Name of the parent domain (default: finance)
        callbacks: LangChain callbacks for observability
        
    Returns:
        Configured DebateOrchestrator instance
    """
    dm = DomainManager()
    domain_config = dm.load_domain_config(domain_name)
    
    # Find investment_committee path
    committee_path = os.path.join(domain_config.docs_dir, "..", "investment_committee")
    committee_path = os.path.normpath(committee_path)
    
    if not os.path.exists(committee_path):
        raise ValueError(
            f"Investment committee not found at {committee_path}. "
            f"Please ensure the investment_committee folder exists in the {domain_name} domain."
        )
    
    return DebateOrchestrator(
        domain_config=domain_config,
        committee_path=committee_path,
        callbacks=callbacks
    )
