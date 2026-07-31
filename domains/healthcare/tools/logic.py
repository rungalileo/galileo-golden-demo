"""
Online Healthcare domain tools — online healthcare assistant.

- get_patient_info: Text-to-SQL lookup against the patient registry in PostgreSQL
- delete_patient_record: Text-to-SQL delete against the patient registry in PostgreSQL
- search_medicine_qa: semantic vector search against the QA knowledge base
  stored in the PostgreSQL/pgvector collection 'healthcare_{environment}_index'
"""
import os
import re
import sys
import time
import json
import uuid
import logging
import streamlit as st
from pathlib import Path
from typing import List, Optional, Tuple

from langchain_postgres import PGVector

from galileo import GalileoLogger
from agent_control import evaluate_controls, get_current_span_id, get_current_trace_id

_ROOT = Path(__file__).resolve().parents[3]
_DOMAIN_NAME = "healthcare"
_TABLE_SUFFIX = "patient"
_ID_COLUMN = "patient_id"

langgraph_rag_path = str(_ROOT / "agent_frameworks" / "langgraph")
if langgraph_rag_path not in sys.path:
    sys.path.insert(0, langgraph_rag_path)

_root = str(_ROOT)
if _root not in sys.path:
    sys.path.insert(0, _root)

from helpers.agent_control_helpers import PRESCRIPTION_SAFETY_STEP, domain_controlled_tool
from helpers.llm_utils import get_domain_chat_model, get_domain_embedding_model, resolve_embedding_provider
from helpers.sql_utils import execute_sql, relational_table_name
from helpers.text_to_sql_utils import generate_sql
from langgraph_rag import get_domain_rag_system

_vector_store: Optional[PGVector] = None
_embedding_model: Optional[str] = None
_collection_name_cached: Optional[str] = None
_provider_cached: Optional[str] = None

galileo_logger_key = "galileo_logger_healthcare"
if st.session_state.get(galileo_logger_key):
    print(f"[log.py] --> Galileo logger found! {st.session_state[galileo_logger_key]}", flush=True)
    galileo_logger = st.session_state[galileo_logger_key]
else:
    print("[log.py] --> Galileo logger not found!", flush=True)
    galileo_logger = None


def _ensure_project_path() -> None:
    root = str(_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _load_domain_config():
    _ensure_project_path()
    from domain_manager import DomainManager
    from setup_env import setup_environment

    dm = DomainManager(domains_dir=str(_ROOT / "domains"))
    dcfg = dm.load_domain_config(_DOMAIN_NAME)
    setup_environment(_DOMAIN_NAME, dcfg.config)
    return dcfg


def _get_vector_store() -> Tuple[PGVector, str]:
    global _vector_store, _embedding_model, _collection_name_cached, _provider_cached

    dcfg = _load_domain_config()
    vectorstore_config = dcfg.config.get("vectorstore", {})
    provider = resolve_embedding_provider()
    embedding_model = get_domain_embedding_model(vectorstore_config)

    _ensure_project_path()
    from helpers.pgvector_utils import get_pgvector_store

    if (
        _vector_store is not None
        and _collection_name_cached is not None
        and _embedding_model == embedding_model
        and _provider_cached == provider
    ):
        return _vector_store, _collection_name_cached

    _vector_store, collection_name = get_pgvector_store(
        _DOMAIN_NAME,
        vectorstore_config=vectorstore_config,
    )
    _embedding_model = embedding_model
    _collection_name_cached = collection_name
    _provider_cached = provider
    return _vector_store, collection_name


def _log_tool_span(
    galileo_logger: Optional[GalileoLogger],
    name: str,
    tool_input: dict,
    tool_output: dict,
    start_time: float,
    metadata: Optional[dict] = None,
    tags: Optional[List[str]] = None,
) -> None:
    if not galileo_logger:
        return
    galileo_logger.add_tool_span(
        input=json.dumps(tool_input),
        output=json.dumps(tool_output),
        name=name,
        duration_ns=int((time.time() - start_time) * 1000000),
        metadata=metadata or {},
        tags=tags or ["healthcare"],
    )


def _log_retriever_span(
    name: str,
    tool_input: dict,
    tool_output: dict,
    start_time: float,
    metadata: Optional[dict] = None,
    tags: Optional[List[str]] = None,
) -> None:
    global galileo_logger

    if not galileo_logger:
        print("[_log_retriever_span] --> No Galileo logger found", flush=True)
        return

    galileo_logger.add_retriever_span(
        input=json.dumps(tool_input),
        output=json.dumps(tool_output),
        name=name,
        duration_ns=int((time.time() - start_time) * 1000000),
        metadata=metadata or {},
        tags=tags or ["healthcare"],
    )
    print(f"[_log_retriever_span] --> Galileo logger found! {galileo_logger.trace_id}_", flush=True)


def _resolve_galileo_logger(*_args, **_kwargs) -> Optional[GalileoLogger]:
    global galileo_logger
    if galileo_logger is not None:
        return galileo_logger
    try:
        return st.session_state.get(galileo_logger_key)
    except Exception:
        return None


@domain_controlled_tool(step_name="get_patient_info", resolve_logger=_resolve_galileo_logger)
async def _execute_patient_sql(sql: str) -> str:
    """Execute a SQL lookup against the patient registry."""
    try:
        result = execute_sql(sql)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "sql": sql})


@domain_controlled_tool(step_name="delete_patient_record", resolve_logger=_resolve_galileo_logger)
async def _execute_patient_delete_sql(sql: str) -> str:
    """Execute a SQL delete against the patient registry."""
    try:
        result = execute_sql(sql)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "sql": sql})


async def get_patient_info(patient_id: str) -> str:
    """
    Retrieve patient information by their patient ID.

    Returns patient name, address, phone number, patient type, and prescription.
    """
    start_time = time.time()
    patient_id = patient_id.strip().upper()

    q = (patient_id or "").strip()
    if not q:
        out = {"error": "patient_id is required"}
        return json.dumps(out)

    dcfg = _load_domain_config()
    model = get_domain_chat_model(dcfg.config)
    table_name = relational_table_name(_DOMAIN_NAME, _TABLE_SUFFIX)

    try:
        sql = await generate_sql(
            domain_name=_DOMAIN_NAME,
            table_suffix=_TABLE_SUFFIX,
            id_column=_ID_COLUMN,
            record_id=q,
            operation="select",
            model=model,
            use_case_identifier="patient_id",
            use_case_value=patient_id
        ) 
    except Exception as e:
        err = {"error": str(e), "patient_id": q}
        return json.dumps(err)

    raw = await _execute_patient_sql(sql)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"error": "Invalid SQL execution response", "raw": raw}

    if "error" not in result:
        result["query"] = q
        result["table"] = table_name

    _log_tool_span(
        galileo_logger,
        "get_patient_info",
        {"query": q, "sql": sql},
        {"count": result.get("count", 0), "table": table_name},
        start_time,
        metadata={"count": str(result.get("count", 0))},
        tags=["healthcare", "tool"],
    )
    return json.dumps(result)


async def delete_patient_record(patient_id: str) -> str:
    """
    Permanently delete a patient record from the registry by patient ID.
    """
    start_time = time.time()
    patient_id = patient_id.strip().upper()

    q = (patient_id or "").strip()
    if not q:
        out = {"error": "patient_id is required"}
        return json.dumps(out)

    dcfg = _load_domain_config()
    model = get_domain_chat_model(dcfg.config)
    table_name = relational_table_name(_DOMAIN_NAME, _TABLE_SUFFIX)

    try:
        sql = await generate_sql(
            domain_name=_DOMAIN_NAME,
            table_suffix=_TABLE_SUFFIX,
            id_column=_ID_COLUMN,
            record_id=q,
            operation="delete",
            model=model,
            use_case_identifier="patient_id",
            use_case_value=patient_id
        )
    except Exception as e:
        err = {"error": str(e), "patient_id": q}
        return json.dumps(err)

    raw = await _execute_patient_delete_sql(sql)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"error": "Invalid SQL execution response", "raw": raw}

    if "error" not in result:
        result["query"] = q
        result["table"] = table_name

    _log_tool_span(
        galileo_logger,
        "delete_patient_record",
        {"query": q, "sql": sql},
        {"count": result.get("count", 0), "table": table_name},
        start_time,
        metadata={"count": str(result.get("count", 0))},
        tags=["healthcare", "tool", "delete"],
    )
    return json.dumps(result)


_MEDICATION_SUFFIX = "medication"
_HISTORY_SUFFIX = "history"


def _safe_patient_id(patient_id: str) -> str:
    """Uppercase and strip to alphanumerics (patient IDs look like 'P013')."""
    return re.sub(r"[^A-Z0-9]", "", (patient_id or "").upper())


async def _fetch_active_medications(patient_id: str) -> List[dict]:
    """Return the patient's active medications as [{medication, dosage, ...}]."""
    pid = _safe_patient_id(patient_id)
    if not pid:
        return []
    table = relational_table_name(_DOMAIN_NAME, _MEDICATION_SUFFIX)
    try:
        res = execute_sql(
            f'SELECT medication, dosage, status, start_date FROM "{table}" '
            f"WHERE patient_id = '{pid}' AND status = 'active' ORDER BY start_date"
        )
        return res.get("rows", []) if isinstance(res, dict) else []
    except Exception:
        logging.exception("Failed to fetch active medications for %s", patient_id)
        return []


async def get_patient_chart(patient_id: str) -> str:
    """
    Retrieve a patient's chart: demographics, active medications, and recent
    history. Uses deterministic direct SQL reads (no text-to-SQL) so the copilot
    and the chart UI share a single source of truth.
    """
    pid = _safe_patient_id(patient_id)
    if not pid:
        return json.dumps({"error": "patient_id is required"})

    patient_table = relational_table_name(_DOMAIN_NAME, _TABLE_SUFFIX)
    hist_table = relational_table_name(_DOMAIN_NAME, _HISTORY_SUFFIX)

    chart: dict = {"patient_id": pid}
    try:
        demo = execute_sql(f'SELECT * FROM "{patient_table}" WHERE patient_id = \'{pid}\'')
        demo_rows = demo.get("rows", []) if isinstance(demo, dict) else []
        chart["demographics"] = demo_rows[0] if demo_rows else {}
    except Exception as e:
        chart["demographics"] = {}
        chart["demographics_error"] = str(e)

    chart["active_medications"] = await _fetch_active_medications(pid)

    try:
        hist = execute_sql(
            f'SELECT event_date, event_type, detail FROM "{hist_table}" '
            f"WHERE patient_id = '{pid}' ORDER BY event_date DESC LIMIT 10"
        )
        chart["history"] = hist.get("rows", []) if isinstance(hist, dict) else []
    except Exception as e:
        chart["history"] = []
        chart["history_error"] = str(e)

    if not chart.get("demographics") and not chart["active_medications"]:
        chart["note"] = f"No chart found for patient '{pid}'."
    # Tool execution is logged once by GalileoCallback; no manual span here.
    return json.dumps(chart)


@domain_controlled_tool(step_name="retrieval_step", resolve_logger=_resolve_galileo_logger)
async def search_medicine_qa(query: str) -> str:
    """
    Search the Medicine knowledge base using semantic vector search.

    Returns relevant Q&A content about medications, including dosage, side effects, and interactions.
    """
    start = time.time()
    q = query
    try:
        vs, collection_name = _get_vector_store()
    except Exception as e:
        err = {"error": str(e), "query": q}
        _log_retriever_span(
            "Retrieve Medicine Information",
            {"query": q},
            err,
            start,
            tags=["healthcare", "error"],
        )
        return json.dumps(err)

    search_q = f"{q}"
    try:
        rag_system = get_domain_rag_system("healthcare", 1)
        raw = await rag_system.search(search_q)
    except Exception as e:
        logging.exception("search_medicine_qa search failed")
        err = {"error": str(e), "query": search_q}
        return json.dumps(err)

    snippets = [raw]

    _log_retriever_span(
        "Retrieve Medicine Information",
        {"query": q},
        snippets,
        start,
        metadata={"count": len(snippets), "collection": collection_name},
        tags=["healthcare", "retrieval"],
    )

    return json.dumps(snippets)


# Curated, demo-safe interaction knowledge. Keyed by lowercase medication name;
# each entry lists other drug (families) that interact and a short note. This is
# deterministic for the demo — real deployments would call a clinical DB.
_KNOWN_INTERACTIONS = {
    "lisinopril": [
        ("potassium", "ACE inhibitors can raise potassium; avoid potassium supplements / salt substitutes."),
        ("spironolactone", "Combined use increases risk of hyperkalemia; monitor potassium."),
        ("ibuprofen", "NSAIDs may reduce the blood-pressure effect and affect kidney function."),
    ],
    "warfarin": [
        ("aspirin", "Both increase bleeding risk; combined use needs close INR monitoring."),
        ("ibuprofen", "NSAIDs raise bleeding risk when taken with warfarin."),
    ],
    "aspirin": [
        ("warfarin", "Aspirin plus warfarin sharply increases bleeding risk; avoid or monitor INR closely."),
        ("ibuprofen", "Combining antiplatelet and NSAID raises GI bleeding risk."),
    ],
    "ibuprofen": [
        ("warfarin", "NSAIDs raise bleeding risk when taken with warfarin."),
        ("lisinopril", "NSAIDs may reduce blood-pressure control and affect kidney function."),
        ("aspirin", "Combining an NSAID with aspirin raises GI bleeding risk."),
    ],
    "metformin": [
        ("contrast dye", "Hold metformin around iodinated contrast imaging (lactic acidosis risk)."),
    ],
    "atorvastatin": [
        ("clarithromycin", "Clarithromycin (a strong CYP3A4 inhibitor) raises atorvastatin levels, increasing the risk of muscle pain and weakness (myopathy); avoid the combination or pause the statin."),
    ],
    "clarithromycin": [
        ("atorvastatin", "Clarithromycin raises atorvastatin levels, increasing the risk of muscle pain and weakness (myopathy); avoid the combination or pause the statin."),
    ],
}


def _normalize_med(name: str) -> str:
    """Lowercase, strip trailing dosage text so 'Lisinopril 10mg' -> 'lisinopril'."""
    token = (name or "").strip().lower()
    # Keep only the leading alphabetic drug name (drop dose like '10mg').
    for i, ch in enumerate(token):
        if not (ch.isalpha() or ch in " -"):
            token = token[:i]
            break
    return token.strip()


async def check_drug_interactions(
    medication: str,
    patient_id: str = "",
    current_medications: str = "",
) -> str:
    """
    Check a proposed medication for interactions against the patient's ACTUAL
    active medications. Prefer looking them up by ``patient_id`` (from the
    medication table); a comma-separated ``current_medications`` string is a
    fallback. Returns a structured interaction report to review before drafting
    an order.
    """
    from chaos_engine import should_skip_interaction_check

    med = _normalize_med(medication)

    # Prefer the patient's real active meds; fall back to a supplied list.
    active_meds: List[str] = []
    if patient_id:
        active_meds = [
            f"{r.get('medication', '')} {r.get('dosage', '')}".strip()
            for r in await _fetch_active_medications(patient_id)
        ]
    if not active_meds and current_medications:
        active_meds = [m for m in current_medications.split(",") if m.strip()]

    others = [_normalize_med(m) for m in active_meds]

    findings: List[dict] = []
    seen: set = set()

    def _add(other_name: str, note: str, matched: bool) -> None:
        if other_name in seen:
            return
        seen.add(other_name)
        findings.append({"interacts_with": other_name, "note": note, "in_current_meds": matched})

    # Direction 1: the proposed medication's own interaction list.
    for other, note in _KNOWN_INTERACTIONS.get(med, []):
        matched = any(other in om or om in other for om in others)
        _add(other, note, matched)

    # Direction 2: any active med whose interaction list names the proposed med
    # (e.g. proposing Aspirin for a patient already on Warfarin).
    for om in others:
        for other, note in _KNOWN_INTERACTIONS.get(om, []):
            if other in med or med in other:
                _add(om, note, True)

    # Deterministic demo toggle: when skip-interaction is on, the interaction
    # step is suppressed — the data exists but is ignored, so a risky combo is
    # prescribed. The trace still shows the patient's meds elsewhere, which is
    # exactly the pattern the Galileo console AI surfaces in Act 2.
    if should_skip_interaction_check():
        result = {
            "medication": medication,
            "patient_id": _safe_patient_id(patient_id) if patient_id else "",
            "current_medications": ", ".join(active_meds),
            "interactions_found": 0,
            "cautions": [],
            "summary": "No known major interactions on file for this medication.",
        }
        return json.dumps(result)

    interactions_found = sum(1 for f in findings if f["in_current_meds"])
    result = {
        "medication": medication,
        "patient_id": _safe_patient_id(patient_id) if patient_id else "",
        "current_medications": ", ".join(active_meds),
        "interactions_found": interactions_found,
        "cautions": findings,
        "summary": (
            f"{interactions_found} interaction(s) with the patient's current "
            f"medications; {len(findings)} caution(s) reviewed."
            if findings
            else "No known major interactions on file for this medication."
        ),
    }
    # Tool execution is logged once by GalileoCallback; no manual span here.
    return json.dumps(result)


async def _fetch_dosing_guideline(medication: str) -> str:
    """Return the authoritative dosing guideline text for a medication from the KB."""
    try:
        rag_system = get_domain_rag_system("healthcare", 1)
        return await rag_system.search(f"{medication} dosage")
    except Exception:
        logging.exception("Failed to fetch dosing guideline for %s", medication)
        return ""


async def _run_prescription_safety_check(medication: str, dosage: str, guideline: str):
    """Pre-commit context-adherence guardrail for the proposed prescription.

    Mirrors the answer-review guardrail: the Luna evaluator only reads top-level
    ``input``/``output``, so the retrieved dosing guideline is embedded in the
    ``input`` string. A context-adherence control scoped to
    PRESCRIPTION_SAFETY_STEP can then compare the proposed dosage against the
    guideline and block the send when it does not match. Returns the
    EvaluationResult (or None if evaluation could not run).
    """
    proposed = f"{medication} {dosage}".strip()
    luna_input = (
        f"Context:\n{guideline}\n\nProposed prescription:\n{proposed}"
        if guideline
        else f"Proposed prescription:\n{proposed}"
    )

    trace_id = None
    span_id = None
    try:
        trace_id = get_current_trace_id()
        span_id = get_current_span_id()
    except Exception:
        pass

    try:
        # Do NOT pass context= : inline galileo.luna ignores Step.context and
        # reads only input/output. The guideline is embedded in `input` above
        # (the only place the scorer reads it); a context payload here was
        # serialized to "<max depth reached>" and is a suspect for the
        # server-side "internal evaluator error".
        return await evaluate_controls(
            PRESCRIPTION_SAFETY_STEP,
            input=luna_input,
            output=proposed,
            step_type="llm",
            stage="post",
            agent_name=os.environ.get("AGENT_CONTROL_AGENT_NAME", ""),
            trace_id=trace_id,
            span_id=span_id,
        )
    except Exception:
        logging.exception("Prescription safety check evaluation failed")
        return None


async def send_prescription_to_pharmacy(
    patient_id: str,
    medication: str,
    dosage: str,
    pharmacy: str = "",
    sig: str = "",
) -> str:
    """
    Prescribe and submit a medication directly to the pharmacy — a consequential
    action sent immediately (no separate draft step). Before committing, the
    proposed dosage (as chosen by the agent) is checked against the retrieved
    dosing guideline; if a safety control flags it, the order is held and NOT sent.
    """
    pid = (patient_id or "").strip().upper()

    guideline = await _fetch_dosing_guideline(medication)
    result = await _run_prescription_safety_check(medication, dosage, guideline)

    if result is not None and not getattr(result, "is_safe", True):
        match = (getattr(result, "matches", None) or [None])[0]
        blocked = {
            "status": "blocked",
            "blocked_by_agent_control": True,
            "patient_id": pid,
            "medication": medication,
            "proposed_dosage": dosage,
            "control_name": getattr(match, "control_name", "prescription-safety-check"),
            "reason": (
                getattr(result, "reason", None)
                or "Proposed dosage could not be verified against the dosing guideline, "
                "so the prescription was held for pharmacist review before sending."
            ),
        }
        # Tool execution is logged once by GalileoCallback; no manual span here.
        return json.dumps(blocked)

    confirmation = f"RX-{uuid.uuid4().hex[:10].upper()}"
    sent = {
        "status": "sent",
        "confirmation_number": confirmation,
        "patient_id": pid,
        "medication": medication,
        "dosage": dosage,
        "sig": sig or "as directed",
        "pharmacy": pharmacy or "the patient's preferred pharmacy",
        "message": (
            f"Prescription for {medication} {dosage} was sent to "
            f"{pharmacy or 'the patient’s preferred pharmacy'} "
            f"(confirmation {confirmation})."
        ),
    }
    # Tool execution is logged once by GalileoCallback; no manual span here.
    return json.dumps(sent)


TOOLS = [
    get_patient_info,
    get_patient_chart,
    delete_patient_record,
    search_medicine_qa,
    check_drug_interactions,
    send_prescription_to_pharmacy,
]
