"""
Jev (TypeSafe System One) tool selection.

The LLM path asks a chat model to emit tool_calls. This module replaces that
decision with one call to Jev: a Choice question over the domain's tools, a
Noul per policy signal, and a Choice per ambiguous argument — all in a single
request, evaluated in parallel.

Jev returns typed values and calibrated probabilities but never free text, so
arguments are resolved in three ways, declared per argument in the domain's
tools/jev_spec.json:

  entity        candidates are pulled out of the conversation with a regex;
                Jev only picks between them when there is more than one
  user_message  the latest user turn is passed through verbatim
  (unresolved)  the tool needs a value we could not find, so we hand back to
                the LLM rather than guessing

Confidence gates are per tool, so a destructive tool can demand a much higher
bar than a read-only one. Anything that fails a gate falls back to the LLM.
"""
import json
import os
import re
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Question id for the "which tool" Choice. Namespaced so it cannot collide
# with a tool named in the spec.
ROUTE_QUESTION = "__route__"

# Choice option meaning "no tool; let the model answer from the conversation".
NO_TOOL_OPTION = "none"

DEFAULT_MODEL = "jev-latest"
DEFAULT_MIN_CONFIDENCE = 0.55


@dataclass
class ToolDecision:
    """The outcome of one Jev routing call, plus everything needed to trace it."""

    tool: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    tool_probabilities: Dict[str, float] = field(default_factory=dict)
    signals: Dict[str, float] = field(default_factory=dict)
    argument_confidence: Dict[str, float] = field(default_factory=dict)
    # Set when we decline to act on Jev's answer and defer to the LLM instead.
    fell_back: bool = False
    # True only when the API call itself failed, as opposed to a gate rejecting
    # a perfectly good answer.
    errored: bool = False
    reason: str = ""
    # Guidance surfaced to the LLM when we route to it instead of a tool.
    hint: str = ""
    latency_ms: float = 0.0
    model: str = ""
    usage: Dict[str, Any] = field(default_factory=dict)

    def as_trace_payload(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "arguments": self.arguments,
            "confidence": round(self.confidence, 4),
            "tool_probabilities": {
                k: round(v, 4) for k, v in self.tool_probabilities.items()
            },
            "signals": {k: round(v, 4) for k, v in self.signals.items()},
            "argument_confidence": {
                k: round(v, 4) for k, v in self.argument_confidence.items()
            },
            "fell_back_to_llm": self.fell_back,
            "reason": self.reason,
            "model": self.model,
            "latency_ms": round(self.latency_ms, 1),
            "usage": self.usage,
        }


def sdk_available() -> bool:
    """True when typesafe-sdk is installed."""
    try:
        import typesafe_sdk  # noqa: F401
    except ImportError:
        return False
    return True


def jev_configured() -> Tuple[bool, str]:
    """Whether Jev routing can run, and why not when it cannot."""
    if not sdk_available():
        return False, "typesafe-sdk is not installed (pip install typesafe-sdk)"
    if not os.environ.get("TYPESAFE_API_KEY", "").strip():
        return False, "typesafe_api_key is not set in .streamlit/secrets.toml"
    return True, ""


def load_jev_spec(domain_config) -> Optional[dict]:
    """Load a domain's tools/jev_spec.json, or None when the domain has no spec."""
    spec_path = Path(domain_config.tools_dir) / "jev_spec.json"
    if not spec_path.exists():
        return None
    try:
        with open(spec_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️  Could not read {spec_path}: {e}")
        return None


def _conversation_state(messages: List[Dict[str, str]], max_turns: int) -> dict:
    """Build the state Jev evaluates: recent turns plus the latest user message."""
    turns = [m for m in messages if m.get("role") in ("user", "assistant")]
    recent = turns[-max_turns:] if max_turns > 0 else turns
    latest_user = next(
        (m["content"] for m in reversed(turns) if m.get("role") == "user"), ""
    )
    return {
        "conversation": [
            {"speaker": "customer" if m["role"] == "user" else "assistant",
             "text": m["content"]}
            for m in recent
        ],
        "latest_customer_message": latest_user,
    }


def _extract_entity_candidates(
    messages: List[Dict[str, str]], pattern: str, normalize: str
) -> List[str]:
    """Find candidate argument values in the conversation, most recent first.

    Only user turns are scanned. An id the assistant echoed back is not
    evidence that the customer asked about it.
    """
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        print(f"⚠️  Invalid entity pattern {pattern!r}: {e}")
        return []

    seen: List[str] = []
    for message in reversed(messages):
        if message.get("role") != "user":
            continue
        for match in compiled.findall(message.get("content", "")):
            value = match if isinstance(match, str) else match[0]
            if normalize == "upper":
                value = value.upper()
            elif normalize == "lower":
                value = value.lower()
            if value not in seen:
                seen.append(value)
    return seen


def _ssl_context():
    """Build an explicit SSL context for the TypeSafe client.

    typesafe-sdk talks over httpx2, whose default `verify=True` builds a
    `truststore.SSLContext` to read the OS trust store. Under Anaconda that
    recurses until the stack blows: Anaconda ships a patched `ssl.py` whose
    `verify_mode` setter re-enters itself when truststore drives it through
    `_original_super_SSLContext`. Handing httpx2 a context we built ourselves
    keeps full certificate verification and never reaches truststore.

    SSL_CERT_FILE / SSL_CERT_DIR still win, so a corporate CA bundle works.
    """
    import ssl

    cafile = os.environ.get("SSL_CERT_FILE", "").strip()
    if cafile:
        return ssl.create_default_context(cafile=cafile)

    capath = os.environ.get("SSL_CERT_DIR", "").strip()
    if capath:
        return ssl.create_default_context(capath=capath)

    import certifi

    return ssl.create_default_context(cafile=certifi.where())


def _noul_criteria(raw: Optional[dict]) -> Optional[dict]:
    """Map spec criteria onto the SDK's true/false keys.

    yes/no reads more naturally in a spec file, so both spellings are accepted.
    """
    if not raw:
        return None
    aliases = {"yes": "true", "true": "true", "no": "false", "false": "false"}
    criteria = {}
    for key, value in raw.items():
        mapped = aliases.get(str(key).lower())
        if mapped is None:
            print(f"⚠️  Ignoring noul criteria key {key!r}; expected true/false")
            continue
        criteria[mapped] = value
    return criteria or None


def _entity_question_id(arg_name: str) -> str:
    """Entity questions are shared across tools so the same id is asked once."""
    return f"__entity__.{arg_name}"


def _build_questions(
    spec: dict,
    messages: List[Dict[str, str]],
    available_tools: List[str],
) -> Tuple[dict, Dict[str, List[str]], List[str]]:
    """Build every question for one request.

    Returns the questions, the entity candidates found per argument, and the
    tool options offered (so the caller knows what Jev could have picked).
    """
    from typesafe_sdk import Choice, Noul

    route = spec.get("route", {})
    options = {
        name: description
        for name, description in route.get("options", {}).items()
        if name == NO_TOOL_OPTION or name in available_tools
    }

    questions: dict = {
        ROUTE_QUESTION: Choice(
            instructions=route.get(
                "instructions", "What is the user asking the assistant to do?"
            ),
            criteria=options,
        )
    }

    # Policy signals. These are cheap and evaluated in parallel, so we ask them
    # on every turn regardless of which tool wins (speculative fan-out).
    for signal_id, cfg in spec.get("signals", {}).items():
        questions[f"__signal__.{signal_id}"] = Noul(
            instructions=cfg["instructions"],
            criteria=_noul_criteria(cfg.get("criteria")),
        )

    # Entity arguments. Jev is only asked to disambiguate when the regex found
    # more than one candidate; one candidate needs no judgment, and zero means
    # there is nothing to choose between.
    candidates_by_arg: Dict[str, List[str]] = {}
    for tool_name, tool_cfg in spec.get("tools", {}).items():
        if tool_name not in available_tools:
            continue
        for arg_name, arg_cfg in tool_cfg.get("arguments", {}).items():
            if arg_cfg.get("source") != "entity":
                continue
            if arg_name in candidates_by_arg:
                continue
            candidates = _extract_entity_candidates(
                messages,
                arg_cfg.get("pattern", ""),
                arg_cfg.get("normalize", ""),
            )
            candidates_by_arg[arg_name] = candidates
            if len(candidates) > 1:
                questions[_entity_question_id(arg_name)] = Choice(
                    instructions=arg_cfg.get(
                        "question", f"Which {arg_name} is the request about?"
                    ),
                    criteria={value: None for value in candidates},
                )

    return questions, candidates_by_arg, list(options)


def _resolve_arguments(
    spec: dict,
    tool_name: str,
    answers,
    candidates_by_arg: Dict[str, List[str]],
    state: dict,
) -> Tuple[Dict[str, Any], Dict[str, float], List[str]]:
    """Fill the chosen tool's arguments. Returns values, per-argument confidence,
    and the names of any required arguments we could not resolve."""
    arguments: Dict[str, Any] = {}
    confidences: Dict[str, float] = {}
    unresolved: List[str] = []

    tool_cfg = spec.get("tools", {}).get(tool_name, {})
    for arg_name, arg_cfg in tool_cfg.get("arguments", {}).items():
        source = arg_cfg.get("source")

        if source == "user_message":
            value = state.get("latest_customer_message", "").strip()
            if value:
                arguments[arg_name] = value
            elif arg_cfg.get("required", True):
                unresolved.append(arg_name)
            continue

        if source == "entity":
            candidates = candidates_by_arg.get(arg_name, [])
            if len(candidates) == 1:
                arguments[arg_name] = candidates[0]
                # A single candidate is a code-level fact, not a judgment.
                confidences[arg_name] = 1.0
            elif len(candidates) > 1:
                answer = answers.get(_entity_question_id(arg_name))
                if answer is not None:
                    arguments[arg_name] = answer.choice
                    confidences[arg_name] = float(answer.confidence)
                else:
                    unresolved.append(arg_name)
            elif arg_cfg.get("required", True):
                unresolved.append(arg_name)
            continue

        if source == "constant":
            arguments[arg_name] = arg_cfg.get("value")
            continue

        print(f"⚠️  Unknown argument source {source!r} for {tool_name}.{arg_name}")
        if arg_cfg.get("required", True):
            unresolved.append(arg_name)

    return arguments, confidences, unresolved


def _apply_policies(spec: dict, signals: Dict[str, float]) -> Optional[dict]:
    """Return the first policy whose signal crosses its threshold, if any.

    Policies let code enforce a rule the system prompt can only request. The
    bank prompt asks the model to defer cancellations to a human; a policy
    makes that deterministic.
    """
    for policy in spec.get("policies", []):
        signal_id = policy.get("signal")
        threshold = policy.get("above")
        if signal_id is None or threshold is None:
            continue
        if signals.get(signal_id, 0.0) > float(threshold):
            return policy
    return None


def _gate_for(spec: dict, tool_name: str) -> dict:
    gates = spec.get("gates", {})
    return {
        "min_confidence": gates.get("default_min_confidence", DEFAULT_MIN_CONFIDENCE),
        **gates.get("tools", {}).get(tool_name, {}),
    }


async def select_tool(
    spec: dict,
    messages: List[Dict[str, str]],
    available_tools: List[str],
    model: Optional[str] = None,
) -> ToolDecision:
    """Ask Jev which tool to call and with what arguments.

    Never raises: any failure comes back as a decision with fell_back set, so
    the agent can hand the turn to the LLM.
    """
    from typesafe_sdk import AsyncTypeSafeClient

    model = model or os.environ.get("TYPESAFE_DEFAULT_MODEL") or DEFAULT_MODEL
    state = _conversation_state(messages, spec.get("max_conversation_turns", 8))

    try:
        questions, candidates_by_arg, options = _build_questions(
            spec, messages, available_tools
        )
    except Exception as e:
        return ToolDecision(
            fell_back=True, reason=f"Could not build Jev questions: {e}"
        )

    started = time.time()
    try:
        import httpx2

        client_kwargs: Dict[str, Any] = {"model": model}
        base_url = os.environ.get("TYPESAFE_BASE_URL", "").strip()
        if base_url:
            client_kwargs["base_url"] = base_url
        # Fresh clients per call: the app runs each query in its own event
        # loop, so a cached async client would outlive the loop it was bound to.
        async with httpx2.AsyncClient(verify=_ssl_context()) as http_client:
            async with AsyncTypeSafeClient(
                http_client=http_client, **client_kwargs
            ) as client:
                response = await client.system_one(state, questions)
    except Exception as e:
        # Print the traceback: the message alone hides where a failure in the
        # HTTP or TLS stack actually came from.
        traceback.print_exc()
        return ToolDecision(
            fell_back=True,
            errored=True,
            reason=f"Jev request failed ({type(e).__name__}: {e})",
            latency_ms=(time.time() - started) * 1000,
            model=model,
        )

    latency_ms = (time.time() - started) * 1000
    answers = response.answers

    decision = ToolDecision(
        latency_ms=latency_ms,
        model=getattr(response, "model", model) or model,
        usage=_usage_dict(response),
    )

    route = answers[ROUTE_QUESTION]
    decision.tool_probabilities = dict(route.probabilities)
    decision.signals = {
        qid.split(".", 1)[1]: float(answer.noul)
        for qid, answer in answers.items()
        if qid.startswith("__signal__.")
    }

    policy = _apply_policies(spec, decision.signals)
    if policy is not None:
        decision.tool = None
        decision.confidence = float(route.confidence)
        decision.reason = policy.get("reason", f"Policy on signal {policy['signal']}")
        decision.hint = policy.get("hint", "")
        return decision

    if route.choice == NO_TOOL_OPTION:
        decision.tool = None
        decision.confidence = float(route.confidence)
        decision.reason = "Jev judged that no tool is needed"
        return decision

    gate = _gate_for(spec, route.choice)
    if float(route.confidence) < float(gate["min_confidence"]):
        decision.fell_back = True
        decision.confidence = float(route.confidence)
        decision.reason = (
            f"Tool confidence {route.confidence:.2f} is below the "
            f"{gate['min_confidence']} gate for {route.choice}"
        )
        return decision

    for signal_id, minimum in gate.get("require_signals", {}).items():
        observed = decision.signals.get(signal_id, 0.0)
        if observed < float(minimum):
            decision.fell_back = True
            decision.confidence = float(route.confidence)
            decision.reason = (
                f"{route.choice} requires {signal_id} >= {minimum}, got {observed:.2f}"
            )
            return decision

    arguments, arg_confidence, unresolved = _resolve_arguments(
        spec, route.choice, answers, candidates_by_arg, state
    )
    if unresolved:
        decision.confidence = float(route.confidence)
        decision.reason = (
            f"{route.choice} is missing required argument(s): {', '.join(unresolved)}"
        )
        decision.hint = (
            spec.get("tools", {})
            .get(route.choice, {})
            .get("missing_argument_hint", "")
        )
        return decision

    decision.tool = route.choice
    decision.arguments = arguments
    decision.argument_confidence = arg_confidence
    # The call is only as trustworthy as its least certain part, so confidence
    # is the weakest judgment rather than the product of all of them.
    decision.confidence = min([float(route.confidence), *arg_confidence.values()])
    decision.reason = "Selected by Jev"
    return decision


def _usage_dict(response) -> Dict[str, Any]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    return {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }


SPAN_NAME = "Jev Tool Selection"


def _span_metadata(decision: ToolDecision) -> Dict[str, str]:
    return {
        "selected_tool": str(decision.tool),
        "confidence": f"{decision.confidence:.4f}",
        "fell_back_to_llm": str(decision.fell_back),
        "reason": decision.reason,
    }


def _galileo_node_handler(config) -> Tuple[Any, Any]:
    """Find the GalileoCallback's node registry and this node's run id.

    GalileoCallback builds its span tree in its own registry and only commits
    it to the logger when the root chain ends. So a span logged directly on
    the logger mid-run attaches to the trace root rather than to the node it
    happened inside, which is why it renders after the whole agent subtree.
    Registering with the same registry instead gets it committed in place.
    """
    callbacks = (config or {}).get("callbacks")
    if callbacks is None:
        return None, None

    run_id = getattr(callbacks, "parent_run_id", None)
    if run_id is None:
        return None, None

    candidates = list(getattr(callbacks, "handlers", None) or [])
    candidates += list(getattr(callbacks, "inheritable_handlers", None) or [])
    for candidate in candidates:
        registry = getattr(candidate, "_handler", None)
        if registry is None or not hasattr(registry, "start_node"):
            continue

        # The handler rewrites UUID7 run ids to UUID4 before registering, so
        # the id LangGraph hands us is not necessarily the registry key. Take
        # whichever form is actually present; without a match, start_node
        # would drop our span from the tree without saying so.
        nodes = registry.get_nodes()
        for key in _run_id_forms(run_id):
            if str(key) in nodes:
                return registry, key
        print(f"ℹ️  Jev span: node {str(run_id)[:8]} is not in the Galileo registry")
    return None, None


def _run_id_forms(run_id):
    """The run id as the Galileo handler may have keyed it."""
    forms = [run_id]
    try:
        from galileo.utils.uuid_utils import convert_uuid_if_uuid7

        converted = convert_uuid_if_uuid7(run_id)
        if converted is not None and converted != run_id:
            forms.append(converted)
    except Exception:
        pass
    return forms


def start_jev_span(config, state_input: Any) -> Optional[dict]:
    """Open an LLM span parented to the LangGraph node we are running inside.

    Returns None when the Galileo callback is not available, in which case the
    caller falls back to logging on the logger directly.
    """
    registry, parent_run_id = _galileo_node_handler(config)
    if registry is None or parent_run_id is None:
        return None

    run_id = uuid.uuid4()
    try:
        registry.start_node(
            "llm",
            parent_run_id,
            run_id,
            name=SPAN_NAME,
            input=json.dumps(state_input, default=str),
            model=os.environ.get("TYPESAFE_DEFAULT_MODEL") or DEFAULT_MODEL,
            temperature=0.0,
            tags=["jev", "tool-selection"],
        )
    except Exception as e:
        print(f"ℹ️  Could not open a nested Jev span ({e}); will log at trace root")
        return None
    return {"registry": registry, "run_id": run_id}


def finish_jev_span(
    span: Optional[dict],
    decision: ToolDecision,
    state_input: Any,
    galileo_logger=None,
) -> None:
    """Close the nested span, or log at the trace root if we never opened one."""
    usage = decision.usage or {}
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    total = (
        (input_tokens or 0) + (output_tokens or 0)
        if (input_tokens is not None or output_tokens is not None)
        else None
    )

    if span is not None:
        try:
            span["registry"].end_node(
                span["run_id"],
                output=json.dumps(decision.as_trace_payload(), default=str),
                model=decision.model or None,
                # Report the measured API time rather than the wall time around
                # the call; end_node's own value is overwritten by this kwarg.
                duration_ns=int(decision.latency_ms * 1_000_000),
                num_input_tokens=input_tokens,
                num_output_tokens=output_tokens,
                total_tokens=total,
                status_code=500 if decision.errored else 200,
                metadata=_span_metadata(decision),
                tags=["jev", "tool-selection"],
            )
            return
        except Exception as e:
            print(f"⚠️  Could not close the nested Jev span ({e}); logging at trace root")

    log_jev_span(galileo_logger, decision, state_input)


def log_jev_span(galileo_logger, decision: ToolDecision, state_input: Any) -> None:
    """Log the routing call straight on the logger.

    Fallback only. This lands at the trace root rather than under the routing
    node, because the LangChain callback has not committed its tree yet.
    """
    if not galileo_logger:
        return

    try:
        galileo_logger.add_llm_span(
            input=json.dumps(state_input, default=str),
            output=json.dumps(decision.as_trace_payload(), default=str),
            model=decision.model,
            name=SPAN_NAME,
            duration_ns=int(decision.latency_ms * 1_000_000),
            num_input_tokens=decision.usage.get("input_tokens"),
            num_output_tokens=decision.usage.get("output_tokens"),
            metadata=_span_metadata(decision),
            tags=["jev", "tool-selection"],
        )
    except Exception as e:
        print(f"⚠️  Could not log the Jev span to Galileo: {e}")
