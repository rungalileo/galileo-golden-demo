"""
Create the "Lisinopril dosage" Agent Control programmatically.

Why this exists:
    The console's control form only allows ONE evaluator per control, and the
    regex evaluator uses Google RE2 (no lookahead/lookbehind). The rule we want —
    "deny a Lisinopril answer UNLESS it contains the correct 10-40 mg dosage" —
    needs a boolean condition tree (AND + NOT), which the UI can't build but the
    API can.

What it creates:
    A server-side control named (default) "dosage-hallucination":
        Deny when:
            output CONTAINS "lisinopril"
            AND NOT( output CONTAINS "10-40 mg" )
        Scope: POST stage, llm step, step name "Healthcare Final Answer".

    IMPORTANT — why the "Healthcare Final Answer" step:
        The agent evaluates its FINAL text answer through a dedicated pass-through
        review step named "Healthcare Final Answer" (see agent.py
        _review_final_answer). Scoping the control to that step means it only sees
        the real answer text — never an intermediate tool-call message (whose
        arguments mention the drug but have no dosage), which was the false
        positive that used to block normal runs and tool calls.

After running:
    The control appears on the Controls page like any UI-made control. Attach it
    to the healthcare log stream (Control tab -> add) and toggle it on/off there.
    Do NOT re-save its condition from the UI form (the single-evaluator form can't
    represent the AND/NOT tree). Re-run this script to change the logic instead.

Usage:
    python helpers/create_dosage_control.py
    python helpers/create_dosage_control.py --name dosage-hallucination \
        --step-name "Healthcare Final Answer"
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import tomllib
from pathlib import Path

import agent_control
from agent_control_models.controls import (
    ConditionNode,
    ControlAction,
    ControlDefinition,
    ControlScope,
    ControlSelector,
    EvaluatorSpec,
)

SECRETS_PATH = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"

# The single source of truth for the correct dosage. Variants guard against
# spacing / dash differences in the model's wording.
CORRECT_DOSAGE_VARIANTS = ["10-40 mg", "10-40mg", "10 to 40 mg", "10–40 mg"]
DRUG_KEYWORD = "lisinopril"


def load_secrets() -> dict:
    if not SECRETS_PATH.exists():
        sys.exit(f"❌ Could not find {SECRETS_PATH}")
    with open(SECRETS_PATH, "rb") as f:
        return tomllib.load(f)


def _list_leaf(values: list[str]) -> ConditionNode:
    """A condition that matches when the output CONTAINS any of `values`."""
    return ConditionNode(
        selector=ControlSelector(path="output"),
        evaluator=EvaluatorSpec(
            name="list",
            config={
                "values": values,
                "match_mode": "contains",
                "case_sensitive": False,
                "logic": "any",
                "match_on": "match",
            },
        ),
    )


def build_control(step_name: str, description: str) -> ControlDefinition:
    condition = ConditionNode(
        and_=[
            # 1) the answer is about Lisinopril
            _list_leaf([DRUG_KEYWORD]),
            # 2) AND it does NOT contain the correct dosage
            ConditionNode(not_=_list_leaf(CORRECT_DOSAGE_VARIANTS)),
        ]
    )
    return ControlDefinition(
        description=description,
        execution="server",
        scope=ControlScope(
            step_types=["llm"],
            step_names=[step_name],
            stages=["post"],
        ),
        condition=condition,
        action=ControlAction(decision="deny"),
    )


async def _create(name: str, data: ControlDefinition, secrets: dict) -> dict:
    return await agent_control.create_control(
        name=name,
        data=data,
        server_url=secrets["agent_control_url"],
        api_key=secrets["galileo_api_key"],
        api_key_header=secrets.get("agent_control_api_key_header", "Galileo-API-Key"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the Lisinopril dosage control.")
    parser.add_argument("--name", default="dosage-hallucination", help="Control name.")
    parser.add_argument(
        "--step-name",
        default="Healthcare Final Answer",
        help="LLM step name to scope to (default: 'Healthcare Final Answer').",
    )
    args = parser.parse_args()

    secrets = load_secrets()
    for key in ("agent_control_url", "galileo_api_key"):
        if not secrets.get(key):
            sys.exit(f"❌ '{key}' is missing from {SECRETS_PATH}")

    description = (
        "Deny Lisinopril answers that do not state the correct 10-40 mg dosage "
        "(AND/NOT list conditions; created via SDK because the UI form allows only "
        "one evaluator)."
    )
    control = build_control(args.step_name, description)

    print(f"Creating control '{args.name}' on {secrets['agent_control_url']} ...")
    try:
        result = asyncio.run(_create(args.name, control, secrets))
    except Exception as e:  # noqa: BLE001 - surface the server error clearly
        msg = str(e)
        if "409" in msg or "already exists" in msg.lower():
            sys.exit(
                f"⚠️ A control named '{args.name}' already exists. "
                "Delete it in the console (or pass --name <other>) and re-run."
            )
        sys.exit(f"❌ Failed to create control: {e}")

    control_id = result.get("control_id", result)
    print(f"✅ Created control '{args.name}' (id={control_id}).")
    print(
        "\nNext steps (in the Galileo console):\n"
        "  1. Go to the healthcare log stream -> Control tab -> add this control.\n"
        "  2. Toggle it on when you want to demo the block; off otherwise.\n"
        "  Note: don't re-save its condition from the single-evaluator UI form — "
        "re-run this script to change the logic."
    )


if __name__ == "__main__":
    main()
