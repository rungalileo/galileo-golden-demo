#!/usr/bin/env python3
"""Export an existing private Streamlit TOML file as transfer dotenv data."""

from __future__ import annotations

import argparse
import os
import re
import secrets as secrets_module
import tempfile
import tomllib
from pathlib import Path


MAPPING = {
    "admin_key": "ADMIN_KEY",
    "agent_control_agent_name": "AGENT_CONTROL_AGENT_NAME",
    "agent_control_api_key_header": "AGENT_CONTROL_API_KEY_HEADER",
    "agent_control_runtime_auth_mode": "AGENT_CONTROL_RUNTIME_AUTH_MODE",
    "agent_control_target_type": "AGENT_CONTROL_TARGET_TYPE",
    "agent_control_url": "AGENT_CONTROL_URL",
    "alpha_vantage_api_key": "ALPHA_VANTAGE_API_KEY",
    "aws_region": "AWS_REGION",
    "bedrock_api_key": "BEDROCK_API_KEY",
    "bedrock_default_chat_model": "BEDROCK_DEFAULT_CHAT_MODEL",
    "bedrock_embedding_model": "BEDROCK_EMBEDDING_MODEL",
    "galileo_api_key": "GALILEO_API_KEY",
    "galileo_api_url": "GALILEO_API_URL",
    "galileo_console_url": "GALILEO_CONSOLE_URL",
    "galileo_domain": "GALILEO_DOMAIN",
    "galileo_log_stream": "GALILEO_LOG_STREAM",
    "galileo_log_stream_id": "GALILEO_LOG_STREAM_ID",
    "galileo_log_stream_url": "GALILEO_LOG_STREAM_URL",
    "galileo_project": "GALILEO_PROJECT",
    "galileo_project_id": "GALILEO_PROJECT_ID",
    "galileo_project_url": "GALILEO_PROJECT_URL",
    "openai_api_key": "OPENAI_API_KEY",
    "openai_default_chat_model": "OPENAI_DEFAULT_CHAT_MODEL",
    "openai_embedding_dimensions": "OPENAI_EMBEDDING_DIMENSIONS",
    "openai_embedding_model": "OPENAI_EMBEDDING_MODEL",
    "postgres_db": "POSTGRES_DB",
    "postgres_password": "POSTGRES_PASSWORD",
    "postgres_user": "POSTGRES_USER",
}

PLACEHOLDERS = {"", "...", "replace-me", "replace_before_encrypting"}


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path(".streamlit/secrets.toml"))
    parser.add_argument("--output", type=Path, default=Path("transfer/executive-secrets.env"))
    args = parser.parse_args()

    with args.input.open("rb") as handle:
        source = tomllib.load(handle)
    exported: dict[str, str] = {}
    for toml_key, env_key in MAPPING.items():
        raw = str(source.get(toml_key, "")).strip()
        if raw.lower() not in PLACEHOLDERS:
            exported[env_key] = raw
    exported["OPEN_WEBUI_SECRET_KEY"] = secrets_module.token_urlsafe(48)

    body = "# Private transfer source. Encrypt before sending; never commit.\n" + "".join(
        f"{key}={dotenv_string(exported[key])}\n" for key in sorted(exported)
    )
    atomic_write(args.output, body)
    missing = [key for key in ("OPENAI_API_KEY", "GALILEO_API_KEY") if key not in exported]
    print(f"Wrote {args.output} with mode 0600")
    if missing:
        print("Incomplete for full cloud setup; missing: " + ", ".join(missing))
        return 2
    print("Transfer source contains both required cloud credentials (values not shown).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
