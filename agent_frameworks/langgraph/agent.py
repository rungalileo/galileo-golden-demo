"""LangGraph Agent - Domain-agnostic implementation with optional RAG support."""

from __future__ import annotations

import importlib.util
import json
import os
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from base_agent import BaseAgent
from domain_manager import DomainConfig
from galileo.handlers.langchain import GalileoCallback

# Optional Streamlit integration
try:
    import streamlit as st

    STREAMLIT_AVAILABLE = True
except Exception:
    STREAMLIT_AVAILABLE = False

from helpers.llm_utils import get_chat_model, reset_llm_provider, set_llm_provider
from .langgraph_rag import create_domain_rag_tool


class State(TypedDict):
    messages: Annotated[list, add_messages]


class LangGraphAgent(BaseAgent):
    """LangGraph implementation of BaseAgent."""

    def __init__(
        self,
        domain_config: DomainConfig,
        session_id: Optional[str] = None,
        protect_stage_id: Optional[str] = None,
        protect_output_stage_id: Optional[str] = None,
        model_override: Optional[str] = None,
        galileo_logger=None,
        llm_provider: str = "local",
    ):
        super().__init__(domain_config, session_id)
        self.graph: Optional[CompiledStateGraph] = None
        self.model_override = model_override
        self.galileo_logger = galileo_logger
        self.llm_provider = llm_provider if llm_provider in ("local", "hosted") else "local"

        # Galileo Protect toggle/state (controlled by Streamlit sidebar)
        self.protect_enabled: bool = False
        self.protect_stage_id: Optional[str] = protect_stage_id
        self.protect_output_stage_id: Optional[str] = protect_output_stage_id

        callbacks = [GalileoCallback(galileo_logger=galileo_logger)]
        self.config = {"configurable": {"thread_id": self.session_id}, "callbacks": callbacks}

        self.load_tools()
        self._build_graph()

    def load_tools(self) -> None:
        """Load tools from the domain's tools directory and add RAG if enabled."""
        tools_path = os.path.join(self.domain_config.tools_dir, "logic.py")
        tool_schema_path = os.path.join(self.domain_config.tools_dir, "schema.json")

        # Load schema for descriptions
        tool_schema = {}
        if os.path.exists(tool_schema_path):
            with open(tool_schema_path, "r") as f:
                tool_schema = json.load(f)

        spec = importlib.util.spec_from_file_location("domain_tools", tools_path)
        if not spec or not spec.loader:
            raise ValueError(f"Could not load tools module from {tools_path}")
        tools_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tools_module)

        raw_functions = list(getattr(tools_module, "TOOLS", []))

        structured_tools: List[StructuredTool] = []
        for fn in raw_functions:
            name = getattr(fn, "__name__", "tool")
            description = ""
            try:
                for entry in (tool_schema.get("tools") or tool_schema.get("functions") or []):
                    if entry.get("name") == name:
                        description = entry.get("description", "")
                        break
            except Exception:
                pass

            structured_tools.append(
                StructuredTool.from_function(
                    fn,
                    name=name,
                    description=description or (fn.__doc__ or ""),
                )
            )

        # Optional RAG tool
        rag_cfg = (self.domain_config.config or {}).get("rag", {})
        if rag_cfg.get("enabled", True):
            rag_tool = create_domain_rag_tool(
                self.domain_config.name,
                top_k=rag_cfg.get("top_k", 5),
                model_name=self.model_override,
            )
            structured_tools.append(rag_tool)

        self.tools = structured_tools

    def _build_graph(self) -> None:
        llm_provider_token = None

        def _agent_node(state: State) -> Dict[str, Any]:
            nonlocal llm_provider_token

            if llm_provider_token is None:
                llm_provider_token = set_llm_provider(self.llm_provider)

            model_cfg = (self.domain_config.config or {}).get("model", {})
            temperature = float(model_cfg.get("temperature", 0.1))
            model_name = self.model_override or model_cfg.get("default_model") or "gemma4"
            if self.llm_provider == "hosted":
                model_name = self.model_override or model_cfg.get("hosted_default_model") or "gpt-4o"

            llm = get_chat_model(
                model_name,
                temperature=temperature,
                name=f"{self.domain_config.name.title()} Assistant",
                provider=self.llm_provider,
            )

            msgs: List[BaseMessage] = list(state.get("messages") or [])
            if not msgs or not isinstance(msgs[0], SystemMessage):
                msgs = [SystemMessage(content=self.system_prompt)] + msgs

            resp = llm.bind_tools(self.tools).invoke(msgs, config=self.config)
            return {"messages": [resp]}

        def _should_continue(state: State) -> str:
            msgs = state.get("messages") or []
            if not msgs:
                return END
            last = msgs[-1]
            tool_calls = getattr(last, "tool_calls", None) or []
            return "tools" if tool_calls else END

        builder = StateGraph(State)
        builder.add_node("agent", _agent_node)
        builder.add_node("tools", ToolNode(self.tools))
        builder.add_edge(START, "agent")
        builder.add_conditional_edges("agent", _should_continue)
        builder.add_edge("tools", "agent")

        self.graph = builder.compile()

    def set_protect(
        self,
        enabled: bool,
        stage_id: Optional[str] = None,
        output_stage_id: Optional[str] = None,
    ) -> None:
        """Enable/disable Galileo Protect for this agent.

        The Streamlit UI calls this before each turn. This minimal agent
        implementation stores the flag + stage IDs so other components can
        inspect them, even if the current agent runtime doesn't actively enforce
        Protect inside the graph.
        """

        self.protect_enabled = bool(enabled)
        if stage_id is not None:
            self.protect_stage_id = stage_id
        if output_stage_id is not None:
            self.protect_output_stage_id = output_stage_id

    def process_query(self, messages: List[Dict[str, str]]) -> str:
        """Run the graph with the provided chat history and return assistant text."""
        if not self.graph:
            raise RuntimeError("LangGraph graph not initialized")

        lc_messages: List[BaseMessage] = []
        for m in messages:
            role = (m.get("role") or "").lower()
            content = m.get("content", "")
            if role in ("system",):
                lc_messages.append(SystemMessage(content=content))
            elif role in ("assistant", "ai"):
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))

        out = self.graph.invoke({"messages": lc_messages}, config=self.config)
        out_messages: List[BaseMessage] = out.get("messages", [])
        if not out_messages:
            return ""

        last = out_messages[-1]
        if isinstance(last, AIMessage):
            return str(last.content or "")
        return str(getattr(last, "content", "") or "")

    def __del__(self):
        # Best-effort restore contextvar if set.
        try:
            # reset_llm_provider requires the token used in set_llm_provider;
            # we don't keep it reliably across GC, so skip.
            pass
        except Exception:
            pass
