"""
Register the golden-demo Agent Control agent and seed demo guardrails.

Run once (or again to update controls in place):
    python helpers/setup_agent_control.py

Requires .streamlit/secrets.toml with galileo_api_key, galileo_console_url, and
agent_control_agent_name (defaults to golden-demo-agent).
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent_control import AgentControlClient
from agent_control import agents as agents_api
from agent_control import controls as controls_api

from domain_manager import DomainManager
from helpers.agent_control_helpers import build_agent_control_steps
from setup_env import setup_environment

LOOKUP_SQL_STEPS = [
    "get_customer_info",
    "get_patient_info",
    "get_schedule_info",
]
DELETE_SQL_STEPS = [
    "delete_customer_record",
    "delete_patient_record",
    "delete_schedule_record",
]

CONTROL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "golden-sql-select-only",
        "data": {
            "description": "Only allow SELECT queries on customer/patient/schedule lookups",
            "enabled": True,
            "execution": "server",
            "scope": {
                "step_types": ["tool"],
                "step_names": LOOKUP_SQL_STEPS,
                "stages": ["pre"],
            },
            "condition": {
                "selector": {"path": "input.sql"},
                "evaluator": {
                    "name": "sql",
                    "config": {"allowed_operations": ["SELECT"]},
                },
            },
            "action": {"decision": "deny"},
            "tags": ["sql-safety", "golden-demo"],
        },
    },
    {
        "name": "golden-sql-require-limit",
        "data": {
            "description": "Require LIMIT clause and cap lookup queries at 50 rows",
            "enabled": True,
            "execution": "server",
            "scope": {
                "step_types": ["tool"],
                "step_names": LOOKUP_SQL_STEPS,
                "stages": ["pre"],
            },
            "condition": {
                "selector": {"path": "input.sql"},
                "evaluator": {
                    "name": "sql",
                    "config": {"require_limit": True, "max_limit": 50},
                },
            },
            "action": {"decision": "deny"},
            "tags": ["sql-safety", "performance", "golden-demo"],
        },
    },
    {
        "name": "golden-sql-delete-only",
        "data": {
            "description": "Only allow DELETE (no SELECT/DROP) on delete-record tools",
            "enabled": True,
            "execution": "server",
            "scope": {
                "step_types": ["tool"],
                "step_names": DELETE_SQL_STEPS,
                "stages": ["pre"],
            },
            "condition": {
                "selector": {"path": "input.sql"},
                "evaluator": {
                    "name": "sql",
                    "config": {"allowed_operations": ["DELETE"]},
                },
            },
            "action": {"decision": "deny"},
            "tags": ["sql-safety", "golden-demo"],
        },
    },
]


def _collect_agent_steps() -> list[dict[str, str]]:
    """Gather unique LLM + tool steps across all demo domains."""
    dm = DomainManager(domains_dir=str(_ROOT / "domains"))
    merged: dict[str, dict[str, str]] = {}

    for domain_name in dm.list_domains():
        domain_config = dm.load_domain_config(domain_name)
        llm_step_name = f"{domain_name.title()} Assistant"
        tool_names = domain_config.config.get("tools", [])
        for step in build_agent_control_steps(llm_step_name, tool_names):
            merged[step["name"]] = step

    return list(merged.values())


async def _upsert_control(
    client: AgentControlClient, name: str, data: dict[str, Any]
) -> int:
    try:
        result = await controls_api.create_control(client, name=name, data=data)
        control_id = result["control_id"]
        print(f"  ✓ Created '{name}' (ID: {control_id})")
        return control_id
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 409:
            raise
        listing = await controls_api.list_controls(client, name=name, limit=5)
        match = next(
            (c for c in listing.get("controls", []) if c.get("name") == name),
            None,
        )
        if not match:
            raise RuntimeError(f"Control '{name}' reported 409 but not found in listing")
        control_id = match["id"]
        await controls_api.set_control_data(client, control_id=control_id, data=data)
        print(f"  ✓ Updated '{name}' (ID: {control_id})")
        return control_id


async def setup_agent_control() -> None:
    setup_environment()

    server_url = os.environ.get("AGENT_CONTROL_URL", "")
    agent_name = os.environ.get("AGENT_CONTROL_AGENT_NAME", "golden-demo-agent")
    api_key = os.environ.get("GALILEO_API_KEY", "")
    api_key_header = os.environ.get("AGENT_CONTROL_API_KEY_HEADER", "Galileo-API-Key")

    if not all([server_url, api_key]):
        raise SystemExit(
            "Missing AGENT_CONTROL_URL or GALILEO_API_KEY. "
            "Check .streamlit/secrets.toml and run setup_env first."
        )

    steps = _collect_agent_steps()
    step_names = ", ".join(s["name"] for s in steps)

    print("=" * 60)
    print("Setting up Agent Control for Golden Demo")
    print("=" * 60)
    print(f"\nServer : {server_url}")
    print(f"Agent  : {agent_name}")
    print(f"Steps  : {step_names}\n")

    async with AgentControlClient(
        base_url=server_url,
        api_key=api_key,
        api_key_header=api_key_header,
    ) as client:
        print("🔒 Creating/updating controls...")
        control_ids: list[int] = []
        for ctrl in CONTROL_DEFINITIONS:
            control_id = await _upsert_control(client, ctrl["name"], ctrl["data"])
            control_ids.append(control_id)

        print(f"\n🤖 Registering agent '{agent_name}'...")
        agent_payload = {
            "agent": {
                "agent_name": agent_name,
                "agent_description": "Galileo golden demo multi-domain agent",
            },
            "steps": steps,
            "conflict_mode": "overwrite",
            "force_replace": True,
        }
        resp = await client.http_client.post("/api/v1/agents/initAgent", json=agent_payload)
        if not resp.is_success:
            print(f"  ✗ initAgent failed {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        result = resp.json()
        status = "created" if result.get("created") else "updated"
        print(f"  ✓ Agent '{agent_name}' {status}")

        print(f"\n🎯 Linking controls to agent '{agent_name}'...")
        for control_id in control_ids:
            try:
                await agents_api.add_agent_control(client, agent_name, control_id)
                print(f"  ✓ Control {control_id} linked")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409:
                    print(f"  ℹ️  Control {control_id} already linked")
                else:
                    raise

    print("\n" + "=" * 60)
    print("✅ Agent Control setup complete")
    print("=" * 60)
    print(
        "\nNext: in the Galileo UI, clone/attach these controls to each log stream "
        "(bank, healthcare, restaurant, insurance) under project galileo-demo."
    )


if __name__ == "__main__":
    asyncio.run(setup_agent_control())
