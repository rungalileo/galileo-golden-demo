"""
Online restaurant domain tools — online restaurant assistant.

- get_schedule_info: Text-to-SQL lookup against the schedule registry in PostgreSQL
- delete_schedule_record: Text-to-SQL delete against the schedule registry in PostgreSQL
- search_kitchen_qa: semantic vector search against the QA knowledge base
  stored in the PostgreSQL/pgvector collection 'restaurant_{environment}_index'
"""
import sys
import time
import json
import logging
import streamlit as st
from pathlib import Path
from typing import List, Optional, Tuple

from langchain_postgres import PGVector

from galileo import GalileoLogger

_ROOT = Path(__file__).resolve().parents[3]
_DOMAIN_NAME = "restaurant"
_TABLE_SUFFIX = "schedule"
_ID_COLUMN = "id"

langgraph_rag_path = str(_ROOT / "agent_frameworks" / "langgraph")
if langgraph_rag_path not in sys.path:
    sys.path.insert(0, langgraph_rag_path)

_root = str(_ROOT)
if _root not in sys.path:
    sys.path.insert(0, _root)

from helpers.agent_control_helpers import domain_controlled_tool
from helpers.sql_utils import execute_sql, relational_table_name
from helpers.text_to_sql_utils import generate_sql
from langgraph_rag import get_domain_rag_system

_vector_store: Optional[PGVector] = None
_embedding_model: Optional[str] = None
_collection_name_cached: Optional[str] = None

galileo_logger_key = "galileo_logger_restaurant"
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
    global _vector_store, _embedding_model, _collection_name_cached

    dcfg = _load_domain_config()
    embedding_model = (
        dcfg.config.get("vectorstore", {}).get("embedding_model") or "text-embedding-3-large"
    )

    _ensure_project_path()
    from helpers.pgvector_utils import get_pgvector_store

    if (
        _vector_store is not None
        and _collection_name_cached is not None
        and _embedding_model == embedding_model
    ):
        return _vector_store, _collection_name_cached

    _vector_store, collection_name = get_pgvector_store(_DOMAIN_NAME, embedding_model)
    _embedding_model = embedding_model
    _collection_name_cached = collection_name
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
        tags=tags or ["restaurant"],
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
        tags=tags or ["restaurant"],
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


@domain_controlled_tool(step_name="get_schedule_info", resolve_logger=_resolve_galileo_logger)
async def _execute_schedule_sql(sql: str) -> str:
    """Execute a SQL lookup against the schedule registry."""
    try:
        result = execute_sql(sql)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "sql": sql})


@domain_controlled_tool(step_name="delete_schedule_record", resolve_logger=_resolve_galileo_logger)
async def _execute_schedule_delete_sql(sql: str) -> str:
    """Execute a SQL delete against the schedule registry."""
    try:
        result = execute_sql(sql)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "sql": sql})


async def get_schedule_info(period_name: str, user_prompt: str = "") -> str:
    """
    Retrieve schedule information by their period name.

    Returns period name, person, role, and hours per shift.
    """
    print(f"get_schedule_info: period_name: {period_name}, user_prompt: {user_prompt}", flush=True)
    start_time = time.time()
    period_name = period_name.strip().upper()

    q = (period_name or "").strip()
    if not q:
        out = {"error": "period_name is required"}
        return json.dumps(out)

    dcfg = _load_domain_config()
    model = dcfg.config.get("model", {}).get("default_model", "gpt-4o-mini")
    table_name = relational_table_name(_DOMAIN_NAME, _TABLE_SUFFIX)

    try:
        sql = await generate_sql(
            domain_name=_DOMAIN_NAME,
            table_suffix=_TABLE_SUFFIX,
            id_column=_ID_COLUMN,
            record_id=q,
            operation="select",
            model=model,
            use_case_identifier="period",
            use_case_value=period_name
        )
    except Exception as e:
        err = {"error": str(e), "period_name": q}
        return json.dumps(err)
    print(f"get_schedule_info: sql: {sql}", flush=True)
    raw = await _execute_schedule_sql(sql)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"error": "Invalid SQL execution response", "raw": raw}

    if "error" not in result:
        result["query"] = q
        result["table"] = table_name

    _log_tool_span(
        galileo_logger,
        "get_schedule_info",
        {"query": q, "sql": sql},
        {"count": result.get("count", 0), "table": table_name},
        start_time,
        metadata={"count": str(result.get("count", 0))},
        tags=["restaurant", "tool"],
    )
    return json.dumps(result)


async def delete_schedule_record(period_id: str) -> str:
    """
    Permanently delete a schedule record from the registry by period ID.
    """
    start_time = time.time()
    # period_name = period_name.strip().upper()

    q = (period_id or "").strip()
    if not q:
        out = {"error": "period_id is required"}
        return json.dumps(out)

    dcfg = _load_domain_config()
    model = dcfg.config.get("model", {}).get("default_model", "gpt-4o-mini")
    table_name = relational_table_name(_DOMAIN_NAME, _TABLE_SUFFIX)

    try:
        sql = await generate_sql(
            domain_name=_DOMAIN_NAME,
            table_suffix=_TABLE_SUFFIX,
            id_column=_ID_COLUMN,
            record_id=q,
            operation="delete",
            model=model,
            use_case_identifier="id",
            use_case_value=period_id
        )
    except Exception as e:
        err = {"error": str(e), "period_name": q}
        return json.dumps(err)

    raw = await _execute_schedule_delete_sql(sql)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"error": "Invalid SQL execution response", "raw": raw}

    if "error" not in result:
        result["query"] = q
        result["table"] = table_name

    _log_tool_span(
        galileo_logger,
        "delete_schedule_record",
        {"query": q, "sql": sql},
        {"count": result.get("count", 0), "table": table_name},
        start_time,
        metadata={"count": str(result.get("count", 0))},
        tags=["restaurant", "tool", "delete"],
    )
    return json.dumps(result)


@domain_controlled_tool(step_name="retrieval_step", resolve_logger=_resolve_galileo_logger)
async def search_kitchen_qa(query: str) -> str:
    """
    Search the Kitchen knowledge base using semantic vector search.

    Returns relevant Q&A content about kitchen operations, including closing checklist, prep sheets, recognition methods, etc.
    """
    start = time.time()
    q = query
    try:
        vs, collection_name = _get_vector_store()
    except Exception as e:
        err = {"error": str(e), "query": q}
        _log_retriever_span(
            "Retrieve Kitchen Information",
            {"query": q},
            err,
            start,
            tags=["restaurant", "error"],
        )
        return json.dumps(err)

    search_q = f"{q}"
    try:
        rag_system = get_domain_rag_system("restaurant", 1)
        raw = await rag_system.search(search_q)
    except Exception as e:
        logging.exception("search_kitchen_qa search failed")
        err = {"error": str(e), "query": search_q}
        return json.dumps(err)

    snippets = [raw]

    _log_retriever_span(
        "Retrieve Kitchen Information",
        {"query": q},
        snippets,
        start,
        metadata={"count": len(snippets), "collection": collection_name},
        tags=["restaurant", "retrieval"],
    )

    return json.dumps(snippets)


TOOLS = [get_schedule_info, delete_schedule_record, search_kitchen_qa]
