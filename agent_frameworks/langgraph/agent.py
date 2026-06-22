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
<<<<<<< Updated upstream
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, END, StateGraph
=======
from langchain_core.messages import AIMessage, ToolMessage
from helpers.llm_utils import get_chat_model, reset_llm_provider, set_llm_provider
from langgraph.graph import START, StateGraph
>>>>>>> Stashed changes
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from base_agent import BaseAgent
from domain_manager import DomainConfig
from galileo.handlers.langchain import GalileoCallback
<<<<<<< Updated upstream
from galileo.handlers.langchain.tool import ProtectTool
from galileo_core.schemas.protect.execution_status import ExecutionStatus
from galileo_core.schemas.protect.response import Response
=======
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
>>>>>>> Stashed changes

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
from helpers.protect_helpers import create_rulesets_from_config


# Define the state for our graph
class State(TypedDict):
    messages: Annotated[list, add_messages]
<<<<<<< Updated upstream
    protect_triggered: bool  # Track if Protect was triggered
=======
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
>>>>>>> Stashed changes


class LangGraphAgent(BaseAgent):
    """
    LangGraph implementation of BaseAgent
    """
    
    def __init__(
        self,
        domain_config: DomainConfig,
        session_id: str = None,
        protect_stage_id: Optional[str] = None,
        protect_output_stage_id: Optional[str] = None,
        model_override: Optional[str] = None,
        galileo_logger=None,
        llm_provider: str = "local",
    ):
        super().__init__(domain_config, session_id)
        self.graph = None
        self.protect_stage_id = protect_stage_id
        self.protect_output_stage_id = protect_output_stage_id
        self.protect_enabled = False
        self.model_override = model_override
<<<<<<< Updated upstream
=======
        self.galileo_logger = galileo_logger
        self.llm_provider = llm_provider if llm_provider in ("local", "hosted") else "local"
>>>>>>> Stashed changes
        
        # Build callbacks list with Galileo (always enabled).
        # Pass the per-session logger so each browser tab writes to its own Galileo session.
        callbacks = [GalileoCallback(galileo_logger=galileo_logger)]
        
        # Add LangSmith tracer if enabled in session state
        if STREAMLIT_AVAILABLE:
            if (hasattr(st, 'session_state') and 
                hasattr(st.session_state, 'langsmith_tracer') and
                getattr(st.session_state, 'logger_langsmith', False)):
                callbacks.append(st.session_state.langsmith_tracer)
                print("   ✅ LangSmith tracer added to agent callbacks")
        
        # Add Braintrust handler if enabled in session state
        if STREAMLIT_AVAILABLE:
            if (hasattr(st, 'session_state') and 
                hasattr(st.session_state, 'braintrust_handler') and
                getattr(st.session_state, 'logger_braintrust', False)):
                callbacks.append(st.session_state.braintrust_handler)
                print("   ✅ Braintrust handler added to agent callbacks")
        
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

        def _get_latest_human_message(state) -> Optional[str]:
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    return msg.content
            return None

<<<<<<< Updated upstream
        def _get_latest_ai_message(state) -> Optional[str]:
            for msg in reversed(state["messages"]):
                if isinstance(msg, AIMessage):
                    return msg.content
            return None

        def _run_protect(payload_kwargs: dict, section: str = "protect") -> Optional[AIMessage]:
            """Invoke ProtectTool and return an AIMessage override if triggered, else None."""
            rulesets = create_rulesets_from_config(self.domain_config.config, section=section)
            if not rulesets:
                return None
            stage_id = (
                self.protect_output_stage_id if section == "protect_output"
                else self.protect_stage_id
            )
            if not stage_id:
                return None
            protect_tool = ProtectTool(
                stage_id=stage_id,
                prioritized_rulesets=rulesets,
            )
            response_json = protect_tool.invoke(payload_kwargs, config=self.config)
            response = Response.model_validate_json(response_json)
            if response.status == ExecutionStatus.triggered:
                return AIMessage(content=response.text)
            return None

        def protect_input_node(state):
            """Scan the user's message before it reaches the LLM.

            Sends payload(input=<user message>) only. Configure metrics under
            `protect_input` in the domain config — input-side metrics only
            (input_toxicity, prompt_injection, input_pii, …). Sending output-side
            metrics here causes API errors because the output field is absent.
            """
            if not self.protect_enabled or not self.protect_stage_id:
                return {"protect_triggered": False}

            user_input = _get_latest_human_message(state)
            if not user_input:
                return {"protect_triggered": False}

            override = _run_protect({"input": user_input}, section="protect_input")
            if override:
                return {"messages": [override], "protect_triggered": True}
            return {"protect_triggered": False}

        def protect_output_node(state):
            """Scan the LLM's response after the chatbot runs.

            Sends payload(input=<user message>, output=<AI reply>). Configure metrics
            under `protect_output` in the domain config — output-side metrics
            (output_toxicity, output_pii, …) and metrics that need both sides
            (completeness, …). Sending input-only metrics here is harmless but
            redundant since protect_input already caught them.
            """
            if not self.protect_enabled or not self.protect_stage_id:
                return {"protect_triggered": False}

            user_input = _get_latest_human_message(state)
            ai_output = _get_latest_ai_message(state)
            if not user_input or not ai_output:
                return {"protect_triggered": False}

            override = _run_protect({"input": user_input, "output": ai_output}, section="protect_output")
            if override:
                return {"messages": [override], "protect_triggered": True}
            return {"protect_triggered": False}

        def invoke_chatbot(state):
            messages = list(state["messages"])  # Make a copy to avoid mutating state
            
=======
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

>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
            message = llm_with_tools.invoke(messages)
            return {"messages": [message]}
        
        def route_after_protect_input(state):
            """Short-circuit to END if the input check triggered, otherwise run the chatbot."""
            if state.get("protect_triggered", False):
                return END
            return "chatbot"
=======
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
>>>>>>> Stashed changes

        def route_after_chatbot(state):
            """Go to tools if the LLM made tool calls, otherwise run the output protect check."""
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools"
            return "protect_output"

        def route_after_protect_output(state):
            """End the turn whether or not the output check triggered."""
            return END

        # Build the graph
        #
        # Flow:
        #   START
        #     → protect_input  (input-only check: prompt injection, input toxicity, input PII, …)
        #         → END          if triggered
        #         → chatbot      if clean
        #             → tools        if LLM made tool calls  →  back to chatbot
        #             → protect_output  (input + output check: output toxicity, output PII,
        #                                context_adherence, completeness, …)
        #                 → END
        graph_builder = StateGraph(State)

        graph_builder.add_node("protect_input", protect_input_node)
        graph_builder.add_node("chatbot", invoke_chatbot)
        graph_builder.add_node("tools", ToolNode(tools=self.tools))
        graph_builder.add_node("protect_output", protect_output_node)

        graph_builder.add_edge(START, "protect_input")
        graph_builder.add_conditional_edges("protect_input", route_after_protect_input)
        graph_builder.add_conditional_edges("chatbot", route_after_chatbot)
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_conditional_edges("protect_output", route_after_protect_output)

        return graph_builder.compile()
    
<<<<<<< Updated upstream
    def set_protect(
        self,
        enabled: bool,
        stage_id: Optional[str] = None,
        output_stage_id: Optional[str] = None,
    ):
        """Enable or disable Protect for this agent"""
        self.protect_enabled = enabled
        if stage_id:
            self.protect_stage_id = stage_id
        if output_stage_id:
            self.protect_output_stage_id = output_stage_id
    
=======
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

>>>>>>> Stashed changes
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
