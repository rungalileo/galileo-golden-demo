"""
Multi-Agent Framework for LangGraph

Implements A2A (Agent2Agent) protocol for multi-agent communication and debate.
"""

from .a2a_protocol import (
    AgentCard,
    Task,
    TaskStatus,
    Message,
    MessageRole,
    TextPart,
    DataPart,
    Artifact,
    TaskManager,
    AgentRegistry,
    MessageBus,
)

from .committee_agent import (
    CommitteeAgent,
    CommitteeAgentState,
    load_committee_tools,
)

from .debate_orchestrator import (
    DebateOrchestrator,
    DebateState,
    DebateTurn,
    create_debate_orchestrator,
)

__all__ = [
    # A2A Protocol
    "AgentCard",
    "Task",
    "TaskStatus",
    "Message",
    "MessageRole",
    "TextPart",
    "DataPart",
    "Artifact",
    "TaskManager",
    "AgentRegistry",
    "MessageBus",
    # Committee Agent
    "CommitteeAgent",
    "CommitteeAgentState",
    "load_committee_tools",
    # Debate Orchestrator
    "DebateOrchestrator",
    "DebateState",
    "DebateTurn",
    "create_debate_orchestrator",
]
