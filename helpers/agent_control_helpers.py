"""
Agent Control helper functions for runtime guardrails.
"""
import asyncio
import functools
import inspect
import json
import os
import re
from typing import Any, Callable, Optional

import agent_control
from agent_control import ControlSteerError, ControlViolationError, control
from agent_control.settings import configure_settings
from galileo.log_streams import get_log_stream

_initialized = False
MAX_STEER_RETRIES = 3
# Shown to the user when every steered retry still tripped the control, so it
# says what it means to them rather than naming the retry machinery.
STEER_EXHAUSTED_MESSAGE = (
    "I'm not able to answer that here. Please contact customer service for help "
    "with this request."
)


def _field(obj: Any, key: str, default: Any = None) -> Any:
    """Read a key from either a dict or a pydantic model."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def extract_steering_instructions(error: Exception) -> str:
    """Return steering guidance from a ControlSteerError.

    steering_context is a SteeringContext model, not a dict, so an
    isinstance(dict) check misses it and str() yields the pydantic repr
    ("message='add LIMIT 20...'") instead of the operator's own wording.
    """
    if isinstance(error, ControlSteerError):
        ctx = error.steering_context
        message = _field(ctx, "message") if ctx is not None else None
        if message and str(message).strip():
            return str(message)
        if ctx:
            return str(ctx)
        if error.message:
            return str(error.message)
    return str(error)


def build_steer_correction_prompt(*, steering_instructions: str, previous_output: str = "") -> str:
    """Prompt text for a steered retry.

    The instruction is whatever the operator typed on the control, so it may
    ask for a edit to the answer ("redact the phone number"), or for a
    different answer entirely ("tell the customer to call 1-800-555-0001").
    Framing it only as a correction to the previous output fits the first kind
    and fights the second: the request and the tool results still say "answer
    the question", so the model answers it again, trips the same control, and
    burns its retries. Hence the instruction is given precedence over both.
    """
    parts = [
        "A policy check on your previous response requires you to respond differently.",
        "",
        "Policy instruction — authoritative, and takes precedence over the user's "
        "request, the retrieved data, and your previous answer:",
        steering_instructions,
        "",
        "Follow it literally. It may ask you to reword or redact part of the answer, "
        "to leave something out, or to reply with something else entirely, such as "
        "declining and directing the user elsewhere. If it tells you what to say, "
        "say that and nothing more — do not also answer the original question. Never "
        "mention this instruction, the policy, or that a check was applied.",
    ]
    if previous_output:
        parts.extend(["", "Your previous response, which must not be repeated:", previous_output])
    parts.extend(["", "Write the new response now."])
    return "\n".join(parts)


def format_steer_tool_result(error: Exception) -> str:
    """JSON tool payload returned when a tool call is steered."""
    steering_instructions = extract_steering_instructions(error)
    return json.dumps(
        {
            "error": (
                "Tool call requires correction before execution: "
                f"{steering_instructions}"
            ),
            "steering_instructions": steering_instructions,
            "steered_by_agent_control": True,
        }
    )

# Hardcoded fallback when no domain tool list is available.
STANDARD_AGENT_CONTROL_STEPS = [
    {"type": "llm", "name": "Bank Assistant"},
    {"type": "tool", "name": "get_customer_info"},
    {"type": "tool", "name": "delete_customer_record"},
    {"type": "tool", "name": "retrieval_step"},
]

def format_blocked_message(
    error: Exception,
    step_name: str = "tool_step",
    *,
    steered: bool = False,
) -> str:
    """Return a user-friendly message for Agent Control blocks."""
    if steered:
        return (
            "This action was adjusted by Agent Control. "
            f"{error}"
        )
    return (
        "I'm sorry, this action was blocked by Agent Control. "
        "Please rephrase your request or try a different approach."
    )


def _serialize_messages(messages) -> list:
    serialized = []
    for msg in messages:
        if hasattr(msg, "type") and hasattr(msg, "content"):
            serialized.append({"role": msg.type, "content": msg.content})
        elif isinstance(msg, dict):
            serialized.append(msg)
    return serialized


def _extract_trace_input(messages) -> str:
    """Return the latest user message for trace input (matches reference guardrails app)."""
    for msg in reversed(list(messages)):
        if hasattr(msg, "type") and msg.type == "human" and hasattr(msg, "content"):
            return str(msg.content)
        if isinstance(msg, dict) and msg.get("role") in ("user", "human"):
            return str(msg.get("content", ""))
    serialized = _serialize_messages(messages)
    return json.dumps(serialized) if serialized else ""


def ensure_trace_started(
    galileo_logger,
    messages=None,
    *,
    trace_input: Optional[str] = None,
    trace_name: str = "Run Agent",
) -> tuple[Optional[str], Optional[str]]:
    """Start a Galileo trace when none is active (required before add_llm_span).

    Returns the (trace_id, span_id) a trace-scoped evaluation has to quote.
    Right after start_trace the trace is itself the open parent, so both IDs
    are the trace's; the bridge drops control events whose IDs do not match
    the parent it currently holds.
    """
    if not galileo_logger:
        return None, None
    parent = galileo_logger.current_parent()
    if parent is not None:
        trace_id = getattr(parent, "id", None)
        return (str(trace_id) if trace_id else None,) * 2
    if trace_input is None and messages is not None:
        trace_input = _extract_trace_input(messages)
    trace = galileo_logger.start_trace(input=trace_input or "", name=trace_name)
    trace_id = getattr(trace, "id", None)
    return (str(trace_id) if trace_id else None,) * 2


def finalize_trace(galileo_logger, output: str) -> None:
    """Conclude and flush the active trace after a query completes."""
    if not galileo_logger or galileo_logger.current_parent() is None:
        return
    galileo_logger.conclude(output=output)
    galileo_logger.flush()


def notify_control_block(
    error: Exception,
    *,
    step_name: str,
    guardrail_result: str = "blocked",
) -> None:
    """Console notice for Agent Control blocks.

    Galileo LLM/tool spans come from LangChain callbacks (GalileoCallback).
    Control evaluation spans are emitted by enable_agent_control() on the logger.
    """
    label = "STEERED" if guardrail_result == "steered" else "BLOCKED"
    print(f"  🚫 {label} by Agent Control ({step_name}): {error}")


def infer_control_step_name(func_name: str) -> str:
    """Map tool function names to Agent Control step names."""
    if func_name.startswith("search_") or func_name.startswith("retrieve_"):
        return "retrieval_step"
    return func_name


def _handle_control_error(
    error: Exception,
    *,
    step_name: str,
    steered: bool = False,
) -> str:
    """Return a friendly JSON tool response for Agent Control blocks."""
    notify_control_block(
        error,
        step_name=step_name,
        guardrail_result="steered" if steered else "blocked",
    )
    if steered:
        return format_steer_tool_result(error)

    return json.dumps(
        {
            "error": format_blocked_message(error, step_name, steered=False),
            "blocked_by_agent_control": True,
        }
    )


def build_agent_control_steps(llm_step_name: str, tool_names: list[str]) -> list[dict]:
    """
    Build Agent Control step registrations for a domain.

    Tool step names must match @control(step_name=...) on tool handlers.
    Search/retrieval tools use the shared retrieval_step name.
    """
    steps: list[dict] = [{"type": "llm", "name": llm_step_name}]
    registered = {llm_step_name}

    for name in tool_names:
        step_name = infer_control_step_name(name)
        if step_name in registered:
            continue
        steps.append({"type": "tool", "name": step_name})
        registered.add(step_name)

    return steps


def _mark_as_agent_control_tool(func: Callable, step_name: str, tool_name: Optional[str] = None) -> str:
    """
    Mark a function as a tool before @control() infers step type.

    Agent Control uses func.tool_name (or func.name) to emit span_type=tool steps
    with input kwargs (e.g. input.sql). Without this, nested SQL handlers are
    treated as generic calls and tool-scoped controls never fire.
    """
    effective_tool_name = tool_name or step_name
    func.tool_name = effective_tool_name
    func.name = effective_tool_name
    return effective_tool_name


def make_controlled_tool(
    func: Callable,
    step_name: str,
    *,
    tool_name: Optional[str] = None,
) -> Callable:
    """Apply @control and return friendly JSON errors for tool guardrail blocks."""
    effective_tool_name = _mark_as_agent_control_tool(func, step_name, tool_name)
    controlled_fn = control(step_name=step_name)(func)
    controlled_fn.tool_name = effective_tool_name
    controlled_fn.name = effective_tool_name

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await controlled_fn(*args, **kwargs)
            except ControlViolationError as e:
                return _handle_control_error(e, step_name=step_name)
            except ControlSteerError as e:
                return _handle_control_error(e, step_name=step_name, steered=True)

        async_wrapper._agent_control_step = step_name  # type: ignore[attr-defined]
        return async_wrapper

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return controlled_fn(*args, **kwargs)
        except ControlViolationError as e:
            return _handle_control_error(e, step_name=step_name)
        except ControlSteerError as e:
            return _handle_control_error(e, step_name=step_name, steered=True)

    sync_wrapper._agent_control_step = step_name  # type: ignore[attr-defined]
    return sync_wrapper


def uses_internal_sql_control(func_name: str) -> bool:
    """Tools that run SQL via an internal _execute_* handler already under @control."""
    return (
        (func_name.startswith("get_") and func_name.endswith("_info"))
        or (func_name.startswith("delete_") and func_name.endswith("_record"))
    )


def domain_controlled_tool(
    step_name: str = "tool_step",
    *,
    resolve_logger: Optional[Callable[..., Any]] = None,
    tool_name: Optional[str] = None,
):
    """
    Decorator for domain logic.py tools.

    Applies @control, catches Agent Control errors, and returns a friendly JSON response.
    Tool spans and control spans are recorded via LangChain callbacks + enable_agent_control().
    """

    def decorator(func: Callable) -> Callable:
        return make_controlled_tool(func, step_name, tool_name=tool_name)

    return decorator


def wrap_controlled_tool(
    func: Callable,
    galileo_logger,
    step_name: Optional[str] = None,
) -> Callable:
    """Catch ControlViolationError and return a friendly tool response."""
    step = step_name or infer_control_step_name(func.__name__)

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ControlViolationError as e:
                notify_control_block(e, step_name=step)
                return json.dumps(
                    {
                        "error": format_blocked_message(e, step),
                        "blocked_by_agent_control": True,
                    }
                )
            except ControlSteerError as e:
                notify_control_block(e, step_name=step, guardrail_result="steered")
                return format_steer_tool_result(e)

        return async_wrapper

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ControlViolationError as e:
            notify_control_block(e, step_name=step)
            return json.dumps(
                {
                    "error": format_blocked_message(e, step),
                    "blocked_by_agent_control": True,
                }
            )
        except ControlSteerError as e:
            notify_control_block(e, step_name=step, guardrail_result="steered")
            return format_steer_tool_result(e)

    return sync_wrapper


def wrap_controlled_langchain_tool(tool, galileo_logger, step_name: str = "retrieval_step"):
    """Wrap a LangChain BaseTool coroutine/func with Agent Control error handling."""
    from langchain_core.tools import BaseTool

    if not isinstance(tool, BaseTool):
        return tool

    original = tool.coroutine or tool.func
    if original is None:
        return tool

    is_async = inspect.iscoroutinefunction(original)

    def _blocked_response(error, steered=False):
        notify_control_block(
            error,
            step_name=step_name,
            guardrail_result="steered" if steered else "blocked",
        )
        if steered:
            return build_steer_correction_prompt(
                steering_instructions=extract_steering_instructions(error)
            )
        return format_blocked_message(error, step_name, steered=steered)

    if is_async:

        @functools.wraps(original)
        async def async_wrapper(*args, **kwargs):
            try:
                return await original(*args, **kwargs)
            except ControlViolationError as e:
                return _blocked_response(e)
            except ControlSteerError as e:
                return _blocked_response(e, steered=True)

        return type(tool)(
            name=tool.name,
            description=tool.description,
            coroutine=async_wrapper,
            args_schema=tool.args_schema,
        )

    @functools.wraps(original)
    def sync_wrapper(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        except ControlViolationError as e:
            return _blocked_response(e)
        except ControlSteerError as e:
            return _blocked_response(e, steered=True)

    return type(tool)(
        name=tool.name,
        description=tool.description,
        func=sync_wrapper,
        args_schema=tool.args_schema,
    )


def init_agent_control(
    galileo_logger,
    project_name: str,
    log_stream: str,
    agent_description: str = "Multi-domain demo agent",
    *,
    steps: Optional[list] = None,
    force: bool = False,
) -> bool:
    """Initialize or refresh Agent Control for the current Galileo logger/session."""
    global _initialized

    if galileo_logger is None:
        print("⚠️ Agent Control not initialized (no Galileo logger)")
        return False

    server_url = os.environ.get("AGENT_CONTROL_URL")
    agent_name = os.environ.get("AGENT_CONTROL_AGENT_NAME")
    api_key = os.environ.get("GALILEO_API_KEY")
    api_key_header = os.environ.get("AGENT_CONTROL_API_KEY_HEADER", "Galileo-API-Key")

    if not all([server_url, agent_name, api_key]):
        print(
            "⚠️ Agent Control not configured "
            "(set AGENT_CONTROL_URL, AGENT_CONTROL_AGENT_NAME, and GALILEO_API_KEY)"
        )
        return False

    session_key = (agent_name, project_name, log_stream, server_url)
    if not force and getattr(init_agent_control, "_last_session_key", None) == session_key:
        return True

    # Control spans require galileo_logger.enable_agent_control() (done in app.py).

    try:
        log_stream_data = get_log_stream(name=log_stream, project_name=project_name)
    except Exception as e:
        print(f"⚠️ Agent Control: failed to resolve log stream '{log_stream}': {e}")
        return False

    control_steps = steps or STANDARD_AGENT_CONTROL_STEPS

    configure_settings(
        url=server_url,
        api_key=api_key,
        api_key_header=api_key_header,
    )

    agent_control.init(
        agent_name=agent_name,
        agent_description=agent_description,
        server_url=server_url,
        api_key=api_key,
        api_key_header=api_key_header,
        observability_enabled=True,
        observability_sink_name="registered",
        target_type="log_stream",
        target_id=log_stream_data.id,
        steps=control_steps,
    )
    _initialized = True
    init_agent_control._last_session_key = session_key
    step_names = ", ".join(s["name"] for s in control_steps)
    print(
        f"✅ Agent Control initialized for agent '{agent_name}' "
        f"(project={project_name}, log_stream={log_stream}, steps={step_names})"
    )
    log_effective_controls()
    for problem in validate_trace_controls():
        print(f"⚠️ Trace control problem: {problem}")
    return True


# --- Trace-scoped controls ----------------------------------------------------
#
# Custom SLM scorers (Output PII, Harmful Input, Prompt Injection, ...) are
# trace-only, so their controls are saved with `scope.step_types = ["trace"]`.
# The @control decorator used on tools and the LLM node infers only llm or
# tool, so those controls never match it - and a control that matches nothing
# produces no control span, which is indistinguishable from one that ran and
# passed.
#
# @control(step_type="trace") is accepted, and is enough when a scorer only
# needs one function's arguments or return value. It is not enough here: it
# records a childless step, while this app needs separate pre/post checks, the
# turn's children so a scorer can grade the answer against the tool results
# behind it, and the verdict as a value so the steer path can re-run the agent
# and re-check the rewrite. So the record is built below, once per turn.

# Name sent as the trace record's step name. Only matters when a control sets
# `scope.step_name_regex`, in which case the two must agree.
TRACE_STEP_NAME = os.environ.get("AGENT_CONTROL_TRACE_STEP_NAME", "agent_turn")

# An SLM/LLM judge is a real model call; the control's own timeout_ms is 30s,
# so allow a little more before giving up on the whole evaluation.
TRACE_CONTROL_TIMEOUT_SECONDS = 45

_GENERIC_STEER_INSTRUCTIONS = (
    "Rewrite the answer so it complies with policy; remove any disallowed content."
)


def _evaluator_names(node: Any) -> list:
    """Collect evaluator names from a possibly nested and/or/not condition."""
    names: list = []
    if isinstance(node, dict):
        evaluator = node.get("evaluator")
        if isinstance(evaluator, dict) and evaluator.get("name"):
            names.append(str(evaluator["name"]))
        for key in ("and", "or", "not"):
            child = node.get(key)
            if isinstance(child, list):
                for item in child:
                    names.extend(_evaluator_names(item))
            elif isinstance(child, dict):
                names.extend(_evaluator_names(child))
    return names


def log_effective_controls() -> None:
    """Print the control set the SDK will actually evaluate against.

    Evaluation only ever consults this cache. A control missing here -
    unbound, disabled, or bound to a different log stream - is silently
    skipped, which looks exactly like "no control matched".
    """
    try:
        controls = agent_control.get_server_controls()
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ Could not read effective controls: {exc}")
        return

    if not controls:
        print(
            "⚠️ No effective controls cached - nothing will be evaluated. "
            "Check that controls are enabled and bound to this log stream."
        )
        return

    print(f"   {len(controls)} effective control(s):")
    for entry in controls:
        if not isinstance(entry, dict):
            continue
        definition = entry.get("control") or {}
        scope = definition.get("scope") or {}
        print(
            f"     - {entry.get('name')!r} "
            f"step_types={scope.get('step_types')} "
            f"stages={scope.get('stages')} "
            f"regex={scope.get('step_name_regex')} "
            f"execution={definition.get('execution')} "
            f"evaluators={_evaluator_names(definition.get('condition')) or None} "
            f"action={(definition.get('action') or {}).get('decision')}"
        )


def validate_trace_controls() -> list:
    """Check cached trace controls against what this app actually sends.

    A control scoped to a step name we never emit produces no match and no
    control span - the same silent outcome as having no control at all.
    """
    problems: list = []
    try:
        controls = agent_control.get_server_controls() or []
    except Exception as exc:  # noqa: BLE001
        return [f"could not read effective controls: {exc}"]

    scoped = [
        entry
        for entry in controls
        if isinstance(entry, dict)
        and "trace" in ((entry.get("control") or {}).get("scope") or {}).get("step_types", [])
    ]
    if not scoped:
        problems.append(
            "no trace-scoped control is bound to this log stream, so the trace "
            "evaluation will never match anything"
        )

    for entry in scoped:
        name = entry.get("name")
        scope = (entry.get("control") or {}).get("scope") or {}
        regex = scope.get("step_name_regex")
        if regex:
            try:
                if re.search(regex, TRACE_STEP_NAME) is None:
                    problems.append(
                        f"{name!r} has step_name_regex {regex!r}, which does not match "
                        f"the step name this app sends ({TRACE_STEP_NAME!r}); set "
                        "AGENT_CONTROL_TRACE_STEP_NAME to a matching value"
                    )
            except re.error as exc:
                problems.append(f"{name!r} has an invalid step_name_regex {regex!r}: {exc}")
        step_names = scope.get("step_names")
        if step_names and TRACE_STEP_NAME not in step_names:
            problems.append(
                f"{name!r} is scoped to step_names {step_names}, which excludes "
                f"{TRACE_STEP_NAME!r}"
            )
    return problems


def trace_control_stages() -> set:
    """Stages ('pre'/'post') that actually have a trace control bound.

    Used to skip an evaluation round-trip for a stage nothing listens on.
    """
    stages: set = set()
    try:
        controls = agent_control.get_server_controls() or []
    except Exception:  # noqa: BLE001
        return stages
    for entry in controls:
        if not isinstance(entry, dict):
            continue
        definition = entry.get("control") or {}
        if not definition.get("enabled", True):
            continue
        scope = definition.get("scope") or {}
        if "trace" not in (scope.get("step_types") or []):
            continue
        # An empty/absent stages list means the control applies to every stage.
        stages.update(scope.get("stages") or ["pre", "post"])
    return stages & {"pre", "post"}


def _step_from_record(record: dict):
    """Convert a plain trace/span dict into the Step tree the SDK expects."""
    from agent_control_models import Step

    record_type = str(record["type"])
    children = [
        _step_from_record(child)
        for child in (record.get("spans") or [])
        if isinstance(child, dict)
    ]
    step_input = record.get("input")
    if record_type == "tool" and not isinstance(step_input, dict):
        # Step rejects non-object tool input, and that ValidationError would
        # otherwise fail the whole turn open with no control spans.
        step_input = {} if step_input in (None, "") else {"value": step_input}
    return Step(
        type=record_type,
        name=str(record["name"]),
        input=step_input,
        output=record.get("output"),
        children=children or None,
    )


def _summarize_matches(items: Any) -> list:
    summaries: list = []
    for item in items or []:
        result = _field(item, "result", {})
        summaries.append(
            {
                "control": _field(item, "control_name"),
                "action": _field(item, "action"),
                "confidence": _field(result, "confidence"),
                "message": _field(result, "message"),
                "error": _field(result, "error"),
                # The operator's correction text for a steer lives here, not in
                # `message` - `message` is the scorer's own verdict string.
                "steering_context": _field(item, "steering_context"),
            }
        )
    return summaries


def _allow(reason: str) -> dict:
    return {"decision": "allow", "reason": reason, "message": "", "steering_instructions": ""}


def _trace_steering_instructions(steer: dict) -> str:
    """Pull the operator's correction text out of a matched steer control."""
    context = steer.get("steering_context")
    if isinstance(context, str):
        return context if context.strip() else _GENERIC_STEER_INSTRUCTIONS
    message = _field(context, "message") if context is not None else None
    if message and str(message).strip():
        return str(message)
    # The scorer's own verdict ("Luna score [...] contains threshold 'address'")
    # gives the model nothing actionable, so say something it can act on.
    return _GENERIC_STEER_INSTRUCTIONS


def build_turn_trace_record(user_input: str, final_text: Optional[str], messages=None) -> dict:
    """Assemble one turn as a trace record with its LLM/tool children.

    At PRE stage there is no answer and no children yet, so `final_text` is
    None and `messages` is empty - the scorer sees only the user's request.
    """
    from langchain_core.messages import AIMessage, ToolMessage

    tool_args: dict = {}
    for msg in messages or []:
        if isinstance(msg, AIMessage):
            for call in getattr(msg, "tool_calls", None) or []:
                call_id = call.get("id") if isinstance(call, dict) else getattr(call, "id", None)
                args = call.get("args") if isinstance(call, dict) else getattr(call, "args", None)
                tool_args[call_id] = args if isinstance(args, dict) else {}

    spans: list = []
    for msg in messages or []:
        if isinstance(msg, ToolMessage):
            content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
            spans.append(
                {
                    "type": "tool",
                    "name": getattr(msg, "name", None) or "tool",
                    "input": tool_args.get(getattr(msg, "tool_call_id", ""), {}),
                    "output": content,
                }
            )
        elif isinstance(msg, AIMessage):
            text = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
            spans.append(
                {"type": "llm", "name": "Assistant", "input": user_input, "output": text}
            )

    return {
        "type": "trace",
        "name": TRACE_STEP_NAME,
        # Plain text so an SLM scorer receives the request as its query rather
        # than a serialized wrapper object.
        "input": user_input,
        "output": final_text,
        "spans": spans,
    }


async def evaluate_trace_controls(
    record: dict,
    *,
    trace_id: Optional[str],
    span_id: Optional[str],
    stage: str = "post",
) -> dict:
    """Evaluate trace controls for one turn at the given stage.

    Unlike @control, `evaluate_controls` returns the outcome instead of
    raising, so enforcement is the caller's job. `trace_id`/`span_id` must be
    the concrete Galileo UUIDs: the observability bridge drops events whose
    context does not match its active hierarchy, which silently costs the
    control spans even when the evaluation itself succeeded.
    """
    if not _initialized:
        return _allow("agent_control_not_initialized")
    if not trace_id or not span_id:
        return _allow("no_trace_context")

    agent_name = os.environ.get("AGENT_CONTROL_AGENT_NAME")
    try:
        step = _step_from_record(record)
        result = await asyncio.wait_for(
            agent_control.evaluate_controls(
                TRACE_STEP_NAME,
                input=step.input,
                output=step.output,
                children=step.children,
                step_type="trace",
                stage=stage,  # type: ignore[arg-type]
                agent_name=agent_name,
                trace_id=trace_id,
                span_id=span_id,
            ),
            timeout=TRACE_CONTROL_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        print(
            f"  ⚠️ {stage.upper()} trace evaluation timed out after "
            f"{TRACE_CONTROL_TIMEOUT_SECONDS}s - allowing the turn through."
        )
        return _allow("timeout")
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠️ {stage.upper()} trace evaluation failed: {type(exc).__name__}: {exc}")
        return _allow(f"error: {exc}")

    return _decision_from_result(result, stage=stage)


def _decision_from_result(result: Any, *, stage: str) -> dict:
    """Turn an EvaluationResult into a deny/steer/allow decision, and log it.

    Evaluator errors are reported but do not block: a judge that crashed has
    not found a violation, and failing closed would take the demo down.
    """
    matches = _summarize_matches(_field(result, "matches", []))
    errors = _summarize_matches(_field(result, "errors", []))
    for failure in errors:
        print(
            f"  ⚠️ {stage.upper()} trace control {failure.get('control')!r} "
            f"errored: {failure.get('error')}"
        )
    if not matches:
        if not errors:
            # "Nothing matched" and "nothing was evaluated" look identical from
            # the outside. non_matches names the controls that actually ran, so
            # an empty list here means no control applied to this step.
            non_matches = _summarize_matches(_field(result, "non_matches", []))
            if non_matches:
                print(
                    f"  ✅ No {stage.upper()} trace control matched; evaluated and passed: "
                    + ", ".join(
                        f"{item.get('control')} (confidence={item.get('confidence')})"
                        for item in non_matches
                    )
                )
            else:
                print(
                    f"  ⚠️ No {stage.upper()} trace control was evaluated - "
                    "none applied to this step."
                )
        return _allow("no_match")

    print(
        f"  🚫 {stage.upper()} trace control matched: "
        + ", ".join(f"{m.get('control')} -> {m.get('action')}" for m in matches)
    )

    deny = next((m for m in matches if m.get("action") == "deny"), None)
    if deny:
        return {
            "decision": "deny",
            "reason": "matched",
            "message": str(deny.get("message") or deny.get("control") or ""),
            "steering_instructions": "",
        }
    steer = next((m for m in matches if m.get("action") == "steer"), None)
    if steer:
        return {
            "decision": "steer",
            "reason": "matched",
            "message": str(steer.get("message") or steer.get("control") or ""),
            "steering_instructions": _trace_steering_instructions(steer),
        }
    return _allow("matched_without_action")
