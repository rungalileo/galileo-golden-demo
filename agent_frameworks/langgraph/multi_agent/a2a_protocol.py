"""
A2A (Agent2Agent) Protocol Implementation

Following Google's A2A specification for multi-agent communication.
https://google.github.io/A2A/specification/

Core Components:
- AgentCard: JSON metadata describing agent identity, capabilities, endpoint
- Task: Stateful work unit with lifecycle management
- Message: Communication turn with role and parts
- Part: Content units (TextPart, DataPart)
- Artifact: Tangible outputs generated during task processing
"""

import uuid
import json
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Union
from datetime import datetime


# =============================================================================
# Enums
# =============================================================================

class TaskStatus(Enum):
    """Task lifecycle states as per A2A specification"""
    SUBMITTED = "submitted"      # Task received, not yet started
    WORKING = "working"          # Task is being processed
    INPUT_REQUIRED = "input_required"  # Waiting for additional input
    COMPLETED = "completed"      # Task finished successfully
    FAILED = "failed"            # Task failed
    CANCELLED = "cancelled"      # Task was cancelled


class MessageRole(Enum):
    """Message roles in A2A communication"""
    USER = "user"        # From user or orchestrator
    AGENT = "agent"      # From an AI agent
    SYSTEM = "system"    # System-level messages


class PartType(Enum):
    """Types of content parts in messages"""
    TEXT = "text"
    DATA = "data"
    FILE = "file"


# =============================================================================
# Data Classes - Parts
# =============================================================================

@dataclass
class TextPart:
    """Text content in a message"""
    type: str = "text"
    content: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "content": self.content}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextPart":
        return cls(content=data.get("content", ""))


@dataclass
class DataPart:
    """Structured data content (e.g., tool results, JSON data)"""
    type: str = "data"
    data: Dict[str, Any] = field(default_factory=dict)
    mime_type: str = "application/json"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "mime_type": self.mime_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataPart":
        return cls(
            data=data.get("data", {}),
            mime_type=data.get("mime_type", "application/json")
        )


Part = Union[TextPart, DataPart]


# =============================================================================
# Data Classes - Core A2A Types
# =============================================================================

@dataclass
class Message:
    """
    Communication turn in A2A protocol.
    
    A message represents one turn of communication, containing
    the role (who sent it) and parts (the content).
    """
    role: MessageRole
    parts: List[Part] = field(default_factory=list)
    sender_id: Optional[str] = None  # Agent ID that sent the message
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "parts": [p.to_dict() for p in self.parts],
            "sender_id": self.sender_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        parts = []
        for part_data in data.get("parts", []):
            if part_data.get("type") == "text":
                parts.append(TextPart.from_dict(part_data))
            elif part_data.get("type") == "data":
                parts.append(DataPart.from_dict(part_data))
        
        return cls(
            role=MessageRole(data.get("role", "user")),
            parts=parts,
            sender_id=data.get("sender_id"),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
            metadata=data.get("metadata", {})
        )
    
    def get_text_content(self) -> str:
        """Extract all text content from message parts"""
        texts = []
        for part in self.parts:
            if isinstance(part, TextPart):
                texts.append(part.content)
        return "\n".join(texts)
    
    @classmethod
    def create_text_message(cls, role: MessageRole, content: str, sender_id: str = None) -> "Message":
        """Convenience method to create a simple text message"""
        return cls(
            role=role,
            parts=[TextPart(content=content)],
            sender_id=sender_id
        )


@dataclass
class Artifact:
    """
    Tangible output generated during task processing.
    
    Examples: final recommendations, reports, decisions
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    parts: List[Part] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parts": [p.to_dict() for p in self.parts],
            "created_at": self.created_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        parts = []
        for part_data in data.get("parts", []):
            if part_data.get("type") == "text":
                parts.append(TextPart.from_dict(part_data))
            elif part_data.get("type") == "data":
                parts.append(DataPart.from_dict(part_data))
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            parts=parts,
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            metadata=data.get("metadata", {})
        )


@dataclass
class AgentCard:
    """
    A2A Agent Card - JSON metadata describing an agent.
    
    The Agent Card is a fundamental concept in A2A that describes
    an agent's identity, capabilities, and how to communicate with it.
    """
    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    persona: str = ""  # e.g., "bull", "bear", "moderator"
    endpoint: str = ""  # e.g., "internal://bull-agent"
    version: str = "1.0.0"
    authentication: Dict[str, Any] = field(default_factory=lambda: {"type": "none"})
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "persona": self.persona,
            "endpoint": self.endpoint,
            "version": self.version,
            "authentication": self.authentication,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCard":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            capabilities=data.get("capabilities", []),
            persona=data.get("persona", ""),
            endpoint=data.get("endpoint", ""),
            version=data.get("version", "1.0.0"),
            authentication=data.get("authentication", {"type": "none"}),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "AgentCard":
        return cls.from_dict(json.loads(json_str))
    
    @classmethod
    def from_file(cls, file_path: str) -> "AgentCard":
        with open(file_path, 'r') as f:
            return cls.from_dict(json.load(f))


@dataclass
class Task:
    """
    A2A Task - Stateful unit of work with lifecycle management.
    
    Tasks progress through states: submitted -> working -> completed/failed
    They contain the conversation history (messages) and outputs (artifacts).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.SUBMITTED
    messages: List[Message] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Debate-specific fields
    current_round: int = 0
    max_rounds: int = 3
    topic: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.value,
            "messages": [m.to_dict() for m in self.messages],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "topic": self.topic
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            status=TaskStatus(data.get("status", "submitted")),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            artifacts=[Artifact.from_dict(a) for a in data.get("artifacts", [])],
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            metadata=data.get("metadata", {}),
            current_round=data.get("current_round", 0),
            max_rounds=data.get("max_rounds", 3),
            topic=data.get("topic", "")
        )
    
    def add_message(self, message: Message) -> None:
        """Add a message to the task"""
        self.messages.append(message)
        self.updated_at = datetime.utcnow().isoformat()
    
    def add_artifact(self, artifact: Artifact) -> None:
        """Add an artifact to the task"""
        self.artifacts.append(artifact)
        self.updated_at = datetime.utcnow().isoformat()
    
    def update_status(self, status: TaskStatus) -> None:
        """Update task status"""
        self.status = status
        self.updated_at = datetime.utcnow().isoformat()
    
    def get_messages_by_sender(self, sender_id: str) -> List[Message]:
        """Get all messages from a specific sender"""
        return [m for m in self.messages if m.sender_id == sender_id]
    
    def get_debate_history(self) -> str:
        """Get formatted debate history for context"""
        history = []
        for msg in self.messages:
            if msg.sender_id:
                history.append(f"[{msg.sender_id}]: {msg.get_text_content()}")
            else:
                history.append(f"[{msg.role.value}]: {msg.get_text_content()}")
        return "\n\n".join(history)


# =============================================================================
# Agent Registry
# =============================================================================

class AgentRegistry:
    """
    Registry for managing agent cards.
    
    Allows agents to be registered, discovered, and retrieved by name or persona.
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentCard] = {}
    
    def register(self, agent_card: AgentCard) -> None:
        """Register an agent card"""
        self._agents[agent_card.name] = agent_card
    
    def unregister(self, name: str) -> None:
        """Unregister an agent by name"""
        if name in self._agents:
            del self._agents[name]
    
    def get(self, name: str) -> Optional[AgentCard]:
        """Get an agent card by name"""
        return self._agents.get(name)
    
    def get_by_persona(self, persona: str) -> Optional[AgentCard]:
        """Get an agent card by persona"""
        for agent in self._agents.values():
            if agent.persona == persona:
                return agent
        return None
    
    def list_agents(self) -> List[AgentCard]:
        """List all registered agents"""
        return list(self._agents.values())
    
    def list_names(self) -> List[str]:
        """List all registered agent names"""
        return list(self._agents.keys())


# =============================================================================
# Task Manager
# =============================================================================

class TaskManager:
    """
    Manages task lifecycle and state.
    
    Responsible for creating, updating, and tracking tasks through their lifecycle.
    """
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
    
    def create_task(self, topic: str, max_rounds: int = 3, metadata: Dict[str, Any] = None) -> Task:
        """Create a new task"""
        task = Task(
            topic=topic,
            max_rounds=max_rounds,
            metadata=metadata or {}
        )
        self._tasks[task.id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self._tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> Optional[Task]:
        """Update a task's status"""
        task = self._tasks.get(task_id)
        if task:
            task.update_status(status)
        return task
    
    def add_message_to_task(self, task_id: str, message: Message) -> Optional[Task]:
        """Add a message to a task"""
        task = self._tasks.get(task_id)
        if task:
            task.add_message(message)
        return task
    
    def add_artifact_to_task(self, task_id: str, artifact: Artifact) -> Optional[Task]:
        """Add an artifact to a task"""
        task = self._tasks.get(task_id)
        if task:
            task.add_artifact(artifact)
        return task
    
    def complete_task(self, task_id: str, final_artifact: Artifact = None) -> Optional[Task]:
        """Mark a task as completed"""
        task = self._tasks.get(task_id)
        if task:
            if final_artifact:
                task.add_artifact(final_artifact)
            task.update_status(TaskStatus.COMPLETED)
        return task
    
    def fail_task(self, task_id: str, error_message: str) -> Optional[Task]:
        """Mark a task as failed"""
        task = self._tasks.get(task_id)
        if task:
            task.metadata["error"] = error_message
            task.update_status(TaskStatus.FAILED)
        return task
    
    def list_tasks(self, status: TaskStatus = None) -> List[Task]:
        """List all tasks, optionally filtered by status"""
        if status:
            return [t for t in self._tasks.values() if t.status == status]
        return list(self._tasks.values())
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False


# =============================================================================
# Message Bus (for inter-agent communication)
# =============================================================================

class MessageBus:
    """
    Simple message bus for inter-agent communication within a debate.
    
    Allows agents to publish messages and subscribe to receive them.
    """
    
    def __init__(self):
        self._messages: List[Message] = []
        self._subscribers: Dict[str, List[callable]] = {}
    
    def publish(self, message: Message) -> None:
        """Publish a message to the bus"""
        self._messages.append(message)
        
        # Notify subscribers
        for subscriber_id, callbacks in self._subscribers.items():
            if subscriber_id != message.sender_id:  # Don't notify sender
                for callback in callbacks:
                    callback(message)
    
    def subscribe(self, agent_id: str, callback: callable) -> None:
        """Subscribe to receive messages"""
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = []
        self._subscribers[agent_id].append(callback)
    
    def unsubscribe(self, agent_id: str) -> None:
        """Unsubscribe from messages"""
        if agent_id in self._subscribers:
            del self._subscribers[agent_id]
    
    def get_history(self) -> List[Message]:
        """Get all messages in order"""
        return self._messages.copy()
    
    def clear(self) -> None:
        """Clear all messages"""
        self._messages.clear()
