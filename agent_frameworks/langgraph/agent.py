"""
LangGraph Agent - Domain-agnostic implementation with RAG support
"""
import sys
import os
import importlib.util
import inspect
import json
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langchain_core.messages import AIMessage, ToolMessage
from helpers.llm_utils import get_chat_model, reset_llm_provider, set_llm_provider
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from agent_control import ControlSteerError, ControlViolationError, control
from base_agent import BaseAgent
from domain_manager import DomainConfig
from galileo.handlers.langchain import GalileoCallback
from helpers.agent_control_helpers import (
    ensure_trace_started,
    finalize_trace,
    format_blocked_message,
    init_agent_control,
    notify_control_block,
    build_agent_control_steps,
    make_controlled_tool,
    uses_internal_sql_control,
    infer_control_step_name,
    MAX_STEER_RETRIES,
    STEER_EXHAUSTED_MESSAGE,
    extract_steering_instructions,
    build_steer_correction_prompt,
)

# Streamlit import (optional - for UI integration)
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# Import chaos engine and RAG retrieval function
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from chaos_engine import get_chaos_engine
from .langgraph_rag import create_domain_rag_tool


# Define the state for our graph
class State(TypedDict):
    messages: Annotated[list, add_messages]
    steer_attempts: int


def _run_async(coro):
    """Run an async coroutine from sync code (e.g. Streamlit), even if a loop is active."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()




def _message_content_text(message: BaseMessage) -> str:
    """Return plain text from an LLM message for steering retries."""
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        return "\n".join(part for part in text_parts if part)
    return str(content)


def _tool_content_text(content: Any) -> str:
    """Return plain text from ToolMessage content (str or multimodal blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif isinstance(block, str):
                text_parts.append(block)
        return "\n".join(part for part in text_parts if part)
    return str(content) if content is not None else ""


def _parse_tool_message_payload(content: Any) -> Optional[dict]:
    """Parse ToolMessage content into a dict when it represents a steer/block payload."""
    if isinstance(content, dict):
        return content

    text = _tool_content_text(content)
    if not text:
        return None

    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        if "steered_by_agent_control" in text or "Agent Control instructions" in text:
            return {
                "steered_by_agent_control": True,
                "steering_instructions": text,
            }
        return None

    if isinstance(payload, dict):
        return payload
    return None


def _count_tool_steer_events(messages: List[BaseMessage]) -> int:
    """Count tool results flagged by Agent Control steering in this turn."""
    count = 0
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        payload = _parse_tool_message_payload(msg.content)
        if payload and payload.get("steered_by_agent_control"):
            count += 1
    return count


def _extract_tool_steer_instructions(messages: List[BaseMessage]) -> Optional[str]:
    """Return steering instructions from the most recent steered tool results."""
    instructions: List[str] = []
    idx = len(messages) - 1
    while idx >= 0 and isinstance(messages[idx], ToolMessage):
        payload = _parse_tool_message_payload(messages[idx].content)
        if payload and payload.get("steered_by_agent_control"):
            instruction = payload.get("steering_instructions") or payload.get("error", "")
            if instruction:
                instructions.insert(0, str(instruction))
        idx -= 1
    if not instructions:
        return None
    return "\n".join(instructions)


def _append_tool_steer_correction_if_needed(messages: List[BaseMessage]) -> List[BaseMessage]:
    """Add explicit LLM correction instructions after a steered tool call."""
    steering_instructions = _extract_tool_steer_instructions(messages)
    if not steering_instructions:
        return messages

    correction_prompt = build_steer_correction_prompt(
        steering_instructions=steering_instructions
    )
    if messages and isinstance(messages[-1], HumanMessage):
        last_content = _message_content_text(messages[-1])
        if correction_prompt == last_content or steering_instructions in last_content:
            return messages

    return messages + [HumanMessage(content=correction_prompt)]


def _build_steering_retry_messages(
    messages: List[BaseMessage],
    original_output: AIMessage,
    steer_error: ControlSteerError,
) -> List[BaseMessage]:
    """Build a follow-up prompt with the original input, output, and steering guidance."""
    steering_instructions = extract_steering_instructions(steer_error)
    original_text = _message_content_text(original_output)

    retry_messages = list(messages)
    retry_messages.append(
        AIMessage(
            content=original_text,
            tool_calls=getattr(original_output, "tool_calls", None) or [],
        )
    )
    retry_messages.append(
        HumanMessage(
            content=build_steer_correction_prompt(
                steering_instructions=steering_instructions,
                previous_output=original_text,
            )
        )
    )
    return retry_messages


class LangGraphAgent(BaseAgent):
    """
    LangGraph implementation of BaseAgent
    """
    
    def __init__(
        self,
        domain_config: DomainConfig,
        session_id: str = None,
        model_override: Optional[str] = None,
        galileo_logger=None,
        llm_provider: str = "local",
    ):
        super().__init__(domain_config, session_id)
        self.graph = None
        self.model_override = model_override
        self.galileo_logger = galileo_logger
        self.llm_provider = llm_provider if llm_provider in ("local", "hosted") else "local"
        
        # Build callbacks list with Galileo (always enabled).
        # Pass the per-session logger so each browser tab writes to its own Galileo session.
        # Attach LangGraph spans to a manually started trace (see _process_query_async).
        callbacks = [
            GalileoCallback(
                galileo_logger=galileo_logger,
                start_new_trace=False,
                flush_on_chain_end=False,
            )
        ]
        
        self.config = {"configurable": {"thread_id": self.session_id}, "callbacks": callbacks}
    
    def load_tools(self) -> None:
        """Load tools from the domain's tools directory and add RAG if enabled"""
        # Build the path to the domain's tools/logic.py file
        # e.g., "domains/finance/tools/logic.py"
        tools_path = os.path.join(self.domain_config.tools_dir, "logic.py")
        tool_schema_path = os.path.join(self.domain_config.tools_dir, "schema.json")

        with open(tool_schema_path, "r") as f:
            tool_schema = json.load(f)

        llm_step_name = f"{self.domain_config.name.title()} Assistant"
        tool_names = [schema.get("name") for schema in tool_schema if schema.get("name")]
        control_steps = build_agent_control_steps(llm_step_name, tool_names)
        
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
            func_name = tool_func.__name__
            if not uses_internal_sql_control(func_name) and not getattr(
                tool_func, "_agent_control_step", None
            ):
                step_name = infer_control_step_name(func_name)
                tool_func = make_controlled_tool(tool_func, step_name)
                print(f"   🛡️ Agent Control step '{step_name}' → {func_name}")

            # For domain tools, find schema; for RAG tool, use function metadata
            tool_schema_dict = next(
                (schema for schema in tool_schema if schema.get("name") == tool_func.__name__), 
                None
            )
            
            tool_kwargs = {
                "name": tool_func.__name__,
                "description": tool_schema_dict.get("description") if tool_schema_dict else tool_func.__doc__ or f"Tool: {tool_func.__name__}",
                "args_schema": tool_schema_dict.get("parameters") if tool_schema_dict else None,
            }
            if inspect.iscoroutinefunction(tool_func):
                langchain_tool = StructuredTool.from_function(coroutine=tool_func, **tool_kwargs)
            else:
                langchain_tool = StructuredTool.from_function(func=tool_func, **tool_kwargs)
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
                # Use same model as main agent so RAG assistant appears with selected model in traces
                model_config = self.domain_config.config.get("model", {})
                if self.model_override:
                    effective_model = self.model_override
                elif self.llm_provider == "hosted":
                    effective_model = (
                        model_config.get("hosted_default_model")
                        or model_config.get("default_model")
                        or model_config.get("model_name")
                    )
                else:
                    effective_model = (
                        model_config.get("default_model")
                        or model_config.get("model_name")
                    )
                # Create LangChain retrieval chain tool (should work with GalileoCallback)
                rag_tool = create_domain_rag_tool(
                    self.domain_config.name, top_k, model_name=effective_model
                )
                
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

        if self.galileo_logger:
            galileo_cfg = self.domain_config.config.get("galileo", {})
            project_name = galileo_cfg.get("project") or f"galileo-demo-{self.domain_config.name}"
            log_stream = galileo_cfg.get("log_stream", "default")
            init_agent_control(
                self.galileo_logger,
                project_name=project_name,
                log_stream=log_stream,
                agent_description=f"{self.domain_config.name.title()} demo agent",
                steps=control_steps,
                force=True,
            )
    
    def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph with domain tools and system prompt"""
        if not self.tools:
            raise ValueError("Tools not loaded. Call load_tools() first.")
        
        # Get model configuration from domain config
        model_config = self.domain_config.config["model"]
        if self.model_override:
            effective_model = self.model_override
        elif self.llm_provider == "hosted":
            effective_model = (
                model_config.get("hosted_default_model")
                or model_config.get("default_model")
                or model_config.get("model_name")
            )
        else:
            effective_model = (
                model_config.get("default_model")
                or model_config.get("model_name")
            )
        temperature = model_config.get("temperature", 0.1)
        
        # Create the LLM with domain tools
        llm_with_tools = get_chat_model(
            effective_model,
            temperature=temperature,
            name=f"{self.domain_config.name.title()} Assistant",
            provider=self.llm_provider,
        ).bind_tools(self.tools)

        llm_step_name = f"{self.domain_config.name.title()} Assistant"
        last_llm_output: Dict[str, Any] = {"message": None}

        @control(step_name=llm_step_name)
        async def _invoke_llm(msgs):
            result = await llm_with_tools.ainvoke(msgs)
            last_llm_output["message"] = result
            # print(f"--> LLM output: {result}", flush=True)
            return result

        async def invoke_chatbot(state):
            messages = list(state["messages"])
            message = None
            tool_steer_events = _count_tool_steer_events(messages)
            llm_steer_attempts = 0

            if tool_steer_events >= MAX_STEER_RETRIES:
                return {
                    "messages": [AIMessage(content=STEER_EXHAUSTED_MESSAGE)],
                    "steer_attempts": tool_steer_events,
                }

            # 🔥 CHAOS: Corrupt tool messages before LLM sees them (runtime check!)
            chaos = get_chaos_engine()
            if chaos.sloppiness_enabled and random.random() < chaos.sloppiness_rate:
                for i, msg in enumerate(messages):
                    if isinstance(msg, ToolMessage):
                        corrupted_content = chaos.transpose_numbers(msg.content)
                        messages[i] = ToolMessage(
                            content=corrupted_content,
                            tool_call_id=msg.tool_call_id,
                        )

            messages = _append_tool_steer_correction_if_needed(messages)

            system_prompt = self.system_prompt or ""
            if chaos.should_corrupt_data():
                system_prompt += chaos.get_corruption_prompt()

            if system_prompt:
                messages = [SystemMessage(content=system_prompt)] + messages

            llm_messages = messages
            last_llm_output["message"] = None
            remaining_attempts = max(MAX_STEER_RETRIES - tool_steer_events, 0)

            for _attempt in range(remaining_attempts):
                try:
                    message = await _invoke_llm(llm_messages)
                    break
                except ControlViolationError as e:
                    notify_control_block(e, step_name=llm_step_name)
                    message = AIMessage(
                        content=format_blocked_message(e, step_name=llm_step_name)
                    )
                    break
                except ControlSteerError as e:
                    notify_control_block(
                        e, step_name=llm_step_name, guardrail_result="steered"
                    )
                    llm_steer_attempts += 1
                    total_steer_events = tool_steer_events + llm_steer_attempts
                    if (
                        total_steer_events >= MAX_STEER_RETRIES
                        or last_llm_output["message"] is None
                    ):
                        message = AIMessage(content=STEER_EXHAUSTED_MESSAGE)
                        break
                    llm_messages = _build_steering_retry_messages(
                        llm_messages, last_llm_output["message"], e
                    )
                    last_llm_output["message"] = None

            if message is None:
                message = AIMessage(content="No response generated")

            return {
                "messages": [message],
                "steer_attempts": tool_steer_events + llm_steer_attempts,
            }

        graph_builder = StateGraph(State)
        graph_builder.add_node("chatbot", invoke_chatbot)
        graph_builder.add_node("tools", ToolNode(tools=self.tools))
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_conditional_edges("chatbot", tools_condition)
        graph_builder.add_edge("tools", "chatbot")

        return graph_builder.compile()
    
    async def _process_query_async(self, messages: List[Dict[str, str]]) -> str:
        """Process a user query asynchronously (required for @control async nodes)."""
        provider_token = set_llm_provider(self.llm_provider)
        response = "No response generated"
        try:
            # Load tools if not already loaded (must run under active provider context)
            if not self.tools:
                self.load_tools()

            self.graph = self._build_graph()

            langchain_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))

            initial_state = {"messages": langchain_messages, "steer_attempts": 0}
            ensure_trace_started(
                self.galileo_logger,
                langchain_messages,
                trace_name="Run Agent",
            )

            result = await self.graph.ainvoke(initial_state, self.config)
            if result["messages"]:
                response = result["messages"][-1].content
            return response
        finally:
            reset_llm_provider(provider_token)
            if self.galileo_logger:
                finalize_trace(self.galileo_logger, response)

    def process_query(self, messages: List[Dict[str, str]]) -> str:
        """Process a user query and return a response"""
        try:
            return _run_async(self._process_query_async(messages))
        except ControlViolationError as e:
            return format_blocked_message(e, step_name="Bank Assistant")
        except ControlSteerError as e:
            return format_blocked_message(e, step_name="Bank Assistant", steered=True)
        except Exception as e:
            print(f"[ERROR] Error processing query: {e}")
            import traceback
            traceback.print_exc()
            return f"Error processing your request: {str(e)}"
