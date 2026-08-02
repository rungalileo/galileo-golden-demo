#!/usr/bin/env python3
"""Safely render an allow-listed dotenv file into app configuration.

The input is parsed as data; it is never sourced by a shell. Unknown keys are
rejected to catch typos and prevent a transferred file from changing installer
behavior unexpectedly.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import shlex
import tempfile
from pathlib import Path


ALLOWED_KEYS = {
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
    "EMBEDDING_PROVIDER",
    "ENVIRONMENT",
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
    "LOCAL_LLM_BACKEND",
    "MLX_API_KEY",
    "MLX_BASE_URL",
    "MLX_DEFAULT_CHAT_MODEL",
    "MLX_EMBEDDING_MODEL",
    "OLLAMA_BASE_URL",
    "OLLAMA_DEFAULT_CHAT_MODEL",
    "OLLAMA_EMBEDDING_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_DEFAULT_CHAT_MODEL",
    "OPENAI_EMBEDDING_DIMENSIONS",
    "OPENAI_EMBEDDING_MODEL",
    "OPEN_WEBUI_SECRET_KEY",
    "POSTGRES_DB",
    "POSTGRES_HOST",
    "POSTGRES_PASSWORD",
    "POSTGRES_PORT",
    "POSTGRES_USER",
}

KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"{path}:{number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not KEY_RE.fullmatch(key):
            raise ValueError(f"{path}:{number}: invalid key {key!r}")
        if key not in ALLOWED_KEYS:
            raise ValueError(f"{path}:{number}: unsupported key {key!r}")
        if value.startswith(("'", '"')):
            parsed = shlex.split(value, posix=True)
            if len(parsed) != 1:
                raise ValueError(f"{path}:{number}: invalid quoted value")
            value = parsed[0]
        values[key] = value
    return values


def toml_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def value(values: dict[str, str], key: str, default: str = "") -> str:
    return values.get(key, default)


def render_toml(values: dict[str, str]) -> str:
    ordered = [
        ("local_llm_backend", value(values, "LOCAL_LLM_BACKEND", "mlx")),
        ("ollama_base_url", value(values, "OLLAMA_BASE_URL")),
        ("ollama_default_chat_model", value(values, "OLLAMA_DEFAULT_CHAT_MODEL", "gemma4")),
        ("ollama_embedding_model", value(values, "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")),
        ("mlx_base_url", value(values, "MLX_BASE_URL", "http://127.0.0.1:8080/v1")),
        ("mlx_api_key", value(values, "MLX_API_KEY", "local")),
        ("mlx_default_chat_model", value(values, "MLX_DEFAULT_CHAT_MODEL")),
        ("mlx_embedding_model", value(values, "MLX_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")),
        ("openai_api_key", value(values, "OPENAI_API_KEY")),
        ("openai_default_chat_model", value(values, "OPENAI_DEFAULT_CHAT_MODEL", "gpt-4o")),
        ("openai_embedding_model", value(values, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")),
        ("openai_embedding_dimensions", value(values, "OPENAI_EMBEDDING_DIMENSIONS", "768")),
        ("bedrock_api_key", value(values, "BEDROCK_API_KEY")),
        ("aws_region", value(values, "AWS_REGION", "us-east-1")),
        ("bedrock_default_chat_model", value(values, "BEDROCK_DEFAULT_CHAT_MODEL", "mistral.ministral-3-14b-instruct")),
        ("bedrock_embedding_model", value(values, "BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")),
        ("galileo_api_key", value(values, "GALILEO_API_KEY")),
        ("galileo_console_url", value(values, "GALILEO_CONSOLE_URL", "https://console.demo-v2.galileocloud.io/")),
        ("galileo_api_url", value(values, "GALILEO_API_URL")),
        ("galileo_domain", value(values, "GALILEO_DOMAIN")),
        ("galileo_project", value(values, "GALILEO_PROJECT")),
        ("galileo_project_id", value(values, "GALILEO_PROJECT_ID")),
        ("galileo_project_url", value(values, "GALILEO_PROJECT_URL")),
        ("galileo_log_stream", value(values, "GALILEO_LOG_STREAM")),
        ("galileo_log_stream_id", value(values, "GALILEO_LOG_STREAM_ID")),
        ("galileo_log_stream_url", value(values, "GALILEO_LOG_STREAM_URL")),
        ("agent_control_url", value(values, "AGENT_CONTROL_URL")),
        ("agent_control_agent_name", value(values, "AGENT_CONTROL_AGENT_NAME", "golden-demo-agent")),
        ("agent_control_runtime_auth_mode", value(values, "AGENT_CONTROL_RUNTIME_AUTH_MODE", "jwt")),
        ("agent_control_api_key_header", value(values, "AGENT_CONTROL_API_KEY_HEADER", "Galileo-API-Key")),
        ("agent_control_target_type", value(values, "AGENT_CONTROL_TARGET_TYPE", "log_stream")),
        ("postgres_host", value(values, "POSTGRES_HOST", "127.0.0.1")),
        ("postgres_port", value(values, "POSTGRES_PORT", "5432")),
        ("postgres_user", value(values, "POSTGRES_USER", "postgres")),
        ("postgres_password", value(values, "POSTGRES_PASSWORD")),
        ("postgres_db", value(values, "POSTGRES_DB", "vectordb")),
        ("environment", value(values, "ENVIRONMENT", "local")),
        ("alpha_vantage_api_key", value(values, "ALPHA_VANTAGE_API_KEY")),
        ("admin_key", value(values, "ADMIN_KEY")),
    ]
    embedding_provider = value(values, "EMBEDDING_PROVIDER")
    if embedding_provider:
        ordered.append(("embedding_provider", embedding_provider))
    return "# Generated by scripts/macos/render_secrets.py. Do not commit.\n" + "".join(
        f"{key} = {toml_string(item)}\n" for key, item in ordered
    )


def render_runtime_env(values: dict[str, str]) -> str:
    keys = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")
    return "".join(f"{key}={docker_env_string(values[key])}\n" for key in keys)


def docker_env_string(item: str) -> str:
    if "\n" in item or "\r" in item:
        raise ValueError("Docker environment values cannot contain newlines")
    return item


def render_webui_env(values: dict[str, str], openai_only: bool, mlx_port: int) -> str:
    base_urls: list[str] = []
    api_keys: list[str] = []
    if not openai_only:
        base_urls.append(f"http://host.docker.internal:{mlx_port}/v1")
        api_keys.append("local")
    if values.get("OPENAI_API_KEY"):
        base_urls.append("https://api.openai.com/v1")
        api_keys.append(values["OPENAI_API_KEY"])
    settings = {
        "ENABLE_OLLAMA_API": "False",
        "ENABLE_OPENAI_API": "True",
        "ENABLE_PERSISTENT_CONFIG": "False",
        "OPENAI_API_BASE_URLS": ";".join(base_urls),
        "OPENAI_API_KEYS": ";".join(api_keys),
        "WEBUI_NAME": "Galileo-Local-AI",
        "WEBUI_SECRET_KEY": values["OPEN_WEBUI_SECRET_KEY"],
    }
    return "".join(f"{key}={docker_env_string(item)}\n" for key, item in settings.items())


def dotenv_string(item: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]*", item):
        return item
    return "'" + item.replace("'", "'\\''") + "'"


def render_dotenv(values: dict[str, str]) -> str:
    return "# Generated by scripts/macos/render_secrets.py. Do not commit.\n" + "".join(
        f"{key}={dotenv_string(values[key])}\n" for key in sorted(values)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--toml-output", required=True, type=Path)
    parser.add_argument("--dotenv-output", required=True, type=Path)
    parser.add_argument("--runtime-env-output", required=True, type=Path)
    parser.add_argument("--webui-env-output", required=True, type=Path)
    parser.add_argument("--mlx-model", required=True)
    parser.add_argument("--mlx-port", required=True, type=int)
    parser.add_argument("--postgres-port", required=True, type=int)
    parser.add_argument("--openai-only", action="store_true")
    args = parser.parse_args()

    values = parse_dotenv(args.input)
    values.setdefault("POSTGRES_USER", "postgres")
    values.setdefault("POSTGRES_DB", "vectordb")
    if not values.get("POSTGRES_PASSWORD"):
        values["POSTGRES_PASSWORD"] = secrets.token_urlsafe(32)
    if not values.get("OPEN_WEBUI_SECRET_KEY") and args.webui_env_output.exists():
        for line in args.webui_env_output.read_text(encoding="utf-8").splitlines():
            if line.startswith("WEBUI_SECRET_KEY="):
                existing = line.split("=", 1)[1].strip()
                if re.fullmatch(r"[A-Za-z0-9_-]{32,}", existing):
                    values["OPEN_WEBUI_SECRET_KEY"] = existing
                break
    if not values.get("OPEN_WEBUI_SECRET_KEY"):
        values["OPEN_WEBUI_SECRET_KEY"] = secrets.token_urlsafe(48)
    values["POSTGRES_PORT"] = str(args.postgres_port)
    values["POSTGRES_HOST"] = "127.0.0.1"
    if args.openai_only:
        values["LOCAL_LLM_BACKEND"] = "ollama"
        values["MLX_BASE_URL"] = ""
        values["MLX_DEFAULT_CHAT_MODEL"] = ""
    else:
        values["LOCAL_LLM_BACKEND"] = "mlx"
        values["MLX_BASE_URL"] = f"http://127.0.0.1:{args.mlx_port}/v1"
        values["MLX_API_KEY"] = "local"
        values["MLX_DEFAULT_CHAT_MODEL"] = args.mlx_model

    if not values.get("OPENAI_API_KEY") and args.openai_only:
        raise ValueError("OPENAI_API_KEY is required with --openai-only")

    atomic_write(args.toml_output, render_toml(values))
    atomic_write(args.dotenv_output, render_dotenv(values))
    atomic_write(args.runtime_env_output, render_runtime_env(values))
    atomic_write(
        args.webui_env_output,
        render_webui_env(values, args.openai_only, args.mlx_port),
    )
    print(
        f"Wrote {args.toml_output}, {args.dotenv_output}, and "
        f"{args.runtime_env_output}, and {args.webui_env_output} with mode 0600"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
