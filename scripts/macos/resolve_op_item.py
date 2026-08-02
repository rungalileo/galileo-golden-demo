#!/usr/bin/env python3
"""Convert one canonical 1Password deployment item to a private dotenv file.

The 1Password item JSON is read from stdin and secret values are never printed.
Only explicitly supported field labels are written.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path


SCHEMA_VERSION = "1"
ALLOWED_FIELDS = {
    "ADMIN_KEY",
    "AGENT_CONTROL_AGENT_NAME",
    "AGENT_CONTROL_API_KEY_HEADER",
    "AGENT_CONTROL_RUNTIME_AUTH_MODE",
    "AGENT_CONTROL_TARGET_TYPE",
    "AGENT_CONTROL_URL",
    "ALPHA_VANTAGE_API_KEY",
    "AWS_REGION",
    "BEDROCK_API_KEY",
    "BEDROCK_DEFAULT_CHAT_MODEL",
    "BEDROCK_EMBEDDING_MODEL",
    "CONFIG_ENVIRONMENT",
    "CONFIG_SCHEMA_VERSION",
    "GALILEO_API_KEY",
    "GALILEO_API_URL",
    "GALILEO_CONSOLE_URL",
    "GALILEO_DOMAIN",
    "GALILEO_LOG_STREAM",
    "GALILEO_LOG_STREAM_ID",
    "GALILEO_LOG_STREAM_URL",
    "GALILEO_PROJECT",
    "GALILEO_PROJECT_ID",
    "GALILEO_PROJECT_URL",
    "OPENAI_API_KEY",
    "OPENAI_DEFAULT_CHAT_MODEL",
    "OPENAI_EMBEDDING_DIMENSIONS",
    "OPENAI_EMBEDDING_MODEL",
    "OPEN_WEBUI_SECRET_KEY",
    "POSTGRES_DB",
    "POSTGRES_PASSWORD",
    "POSTGRES_USER",
}
REQUIRED_FIELDS = {
    "AGENT_CONTROL_AGENT_NAME",
    "AGENT_CONTROL_API_KEY_HEADER",
    "AGENT_CONTROL_RUNTIME_AUTH_MODE",
    "AGENT_CONTROL_TARGET_TYPE",
    "AGENT_CONTROL_URL",
    "CONFIG_ENVIRONMENT",
    "CONFIG_SCHEMA_VERSION",
    "GALILEO_API_KEY",
    "GALILEO_API_URL",
    "GALILEO_CONSOLE_URL",
    "GALILEO_DOMAIN",
    "GALILEO_LOG_STREAM",
    "GALILEO_LOG_STREAM_ID",
    "GALILEO_LOG_STREAM_URL",
    "GALILEO_PROJECT",
    "GALILEO_PROJECT_ID",
    "GALILEO_PROJECT_URL",
    "OPENAI_API_KEY",
    "OPENAI_DEFAULT_CHAT_MODEL",
    "OPENAI_EMBEDDING_DIMENSIONS",
    "OPENAI_EMBEDDING_MODEL",
    "OPEN_WEBUI_SECRET_KEY",
    "POSTGRES_DB",
    "POSTGRES_PASSWORD",
    "POSTGRES_USER",
}
IMMUTABLE_REFRESH_FIELDS = {"POSTGRES_DB", "POSTGRES_PASSWORD", "POSTGRES_USER"}
BUILTIN_LABELS = {
    "credential",
    "expires",
    "filename",
    "hostname",
    "notesPlain",
    "type",
    "username",
    "valid from",
}


def dotenv_string(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]*", value):
        return value
    return "'" + value.replace("'", "'\\''") + "'"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def item_values(item: dict) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in item.get("fields", []):
        label = str(field.get("label", "")).strip()
        if not label or label in BUILTIN_LABELS:
            continue
        if label not in ALLOWED_FIELDS:
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", label):
                raise ValueError(f"unsupported deployment field {label!r}")
            continue
        if label in values:
            raise ValueError(f"duplicate deployment field {label!r}")
        raw = field.get("value", "")
        values[label] = "" if raw is None else str(raw).strip()
    return values


def dotenv_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in ALLOWED_FIELDS:
            continue
        value = value.strip()
        if value.startswith(("'", '"')):
            parsed = shlex.split(value, posix=True)
            if len(parsed) != 1:
                raise ValueError(f"{path}:{number}: invalid quoted value")
            value = parsed[0]
        values[key] = value
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--previous-dotenv", type=Path)
    args = parser.parse_args()

    item = json.load(sys.stdin)
    values = item_values(item)
    missing = sorted(key for key in REQUIRED_FIELDS if not values.get(key))
    if missing:
        raise ValueError("canonical 1Password item is missing: " + ", ".join(missing))
    if values["CONFIG_SCHEMA_VERSION"] != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported CONFIG_SCHEMA_VERSION={values['CONFIG_SCHEMA_VERSION']!r}; "
            f"expected {SCHEMA_VERSION!r}"
        )
    if not values["GALILEO_PROJECT_URL"].startswith(values["GALILEO_CONSOLE_URL"].rstrip("/")):
        raise ValueError("GALILEO_PROJECT_URL does not belong to GALILEO_CONSOLE_URL")
    if not values["GALILEO_LOG_STREAM_URL"].startswith(values["GALILEO_PROJECT_URL"].rstrip("/")):
        raise ValueError("GALILEO_LOG_STREAM_URL does not belong to GALILEO_PROJECT_URL")
    if args.previous_dotenv:
        previous = dotenv_values(args.previous_dotenv)
        changed = sorted(
            key for key in IMMUTABLE_REFRESH_FIELDS
            if previous.get(key) and previous[key] != values[key]
        )
        if changed:
            raise ValueError(
                "refusing in-place database identity change: " + ", ".join(changed)
                + "; use a planned database migration"
            )

    body = "# Resolved from the canonical 1Password deployment item. Do not commit.\n" + "".join(
        f"{key}={dotenv_string(values[key])}\n" for key in sorted(values) if values[key]
    )
    atomic_write(args.output, body)
    title = str(item.get("title", "canonical deployment item"))
    print(f"Resolved {len(values)} configuration fields from {title!r}; values were not displayed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
