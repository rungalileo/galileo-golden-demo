"""Environment Setup - Load secrets and set environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import toml


def get_domain_project_name(domain_name: str, domain_config: Optional[dict] = None) -> str:
    """Get the Galileo project name for a domain."""
    if domain_config and "galileo" in domain_config and "project" in domain_config["galileo"]:
        return domain_config["galileo"]["project"]
    return f"galileo-demo-{domain_name}"


def setup_environment(domain_name: Optional[str] = None, domain_config: Optional[dict] = None) -> None:
    """Load .streamlit/secrets.toml and set environment variables.

    - Prefers existing environment variables.
    - Falls back to .streamlit/secrets.toml.
    - Applies sensible defaults for local development.

    If domain_name is provided, sets GALILEO_PROJECT / GALILEO_LOG_STREAM.
    """

    secrets_path = Path(".streamlit/secrets.toml")
    secrets: dict = {}

    if secrets_path.exists():
        try:
            secrets = toml.load(secrets_path)
        except Exception as exc:
            print(f"❌ Error loading secrets from {secrets_path}: {exc}")
            secrets = {}
    else:
        print("ℹ️  .streamlit/secrets.toml not found; using environment variables.")

    def _resolve(secret_key: str, env_key: str, default: str = "") -> str:
        """Prefer existing env var, then secrets.toml, then default."""
        return os.environ.get(env_key) or str(secrets.get(secret_key, default) or "")

    env_vars = {
        # Ollama (local)
        "OLLAMA_BASE_URL": _resolve("ollama_base_url", "OLLAMA_BASE_URL", "http://localhost:11434"),
        "OLLAMA_DEFAULT_CHAT_MODEL": _resolve(
            "ollama_default_chat_model", "OLLAMA_DEFAULT_CHAT_MODEL", "gemma4"
        ),
        "OLLAMA_EMBEDDING_MODEL": _resolve(
            "ollama_embedding_model", "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"
        ),
        # OpenAI (hosted)
        "OPENAI_API_KEY": _resolve("openai_api_key", "OPENAI_API_KEY", ""),
        "OPENAI_DEFAULT_CHAT_MODEL": _resolve(
            "openai_default_chat_model", "OPENAI_DEFAULT_CHAT_MODEL", "gpt-4o"
        ),
        "OPENAI_EMBEDDING_MODEL": _resolve(
            "openai_embedding_model", "OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"
        ),
        # Galileo
        "GALILEO_API_KEY": _resolve("galileo_api_key", "GALILEO_API_KEY", ""),
        "GALILEO_API_URL": _resolve("galileo_api_url", "GALILEO_API_URL", ""),
        "GALILEO_CONSOLE_URL": _resolve(
            "galileo_console_url", "GALILEO_CONSOLE_URL", "https://app.galileo.ai"
        ),
        "GALILEO_STAGE": _resolve(
            "galileo_stage", "GALILEO_STAGE", "protect-prompt-injection-stage"
        ),
        # Admin / runtime
        "ADMIN_KEY": _resolve("admin_key", "ADMIN_KEY", ""),
        "ENVIRONMENT": _resolve("environment", "ENVIRONMENT", "local"),
        # Postgres (pgvector)
        "POSTGRES_HOST": _resolve("postgres_host", "POSTGRES_HOST", "localhost"),
        "POSTGRES_PORT": _resolve("postgres_port", "POSTGRES_PORT", "5432"),
        "POSTGRES_USER": _resolve("postgres_user", "POSTGRES_USER", "postgres"),
        "POSTGRES_PASSWORD": _resolve("postgres_password", "POSTGRES_PASSWORD", ""),
        "POSTGRES_DB": _resolve("postgres_db", "POSTGRES_DB", "vectordb"),
        # Agent Control (optional)
        "AGENT_CONTROL_URL": _resolve("agent_control_url", "AGENT_CONTROL_URL", ""),
        "AGENT_CONTROL_AGENT_NAME": _resolve(
            "agent_control_agent_name", "AGENT_CONTROL_AGENT_NAME", ""
        ),
        "AGENT_CONTROL_API_KEY_HEADER": _resolve(
            "agent_control_api_key_header",
            "AGENT_CONTROL_API_KEY_HEADER",
            "Galileo-API-Key",
        ),
        "AGENT_CONTROL_RUNTIME_AUTH_MODE": _resolve(
            "agent_control_runtime_auth_mode", "AGENT_CONTROL_RUNTIME_AUTH_MODE", "jwt"
        ),
        "AGENT_CONTROL_TARGET_TYPE": _resolve(
            "agent_control_target_type", "AGENT_CONTROL_TARGET_TYPE", "log_stream"
        ),
    }

    if domain_name:
        project_name = get_domain_project_name(domain_name, domain_config)
        log_stream = "default"
        if domain_config and "galileo" in domain_config and "log_stream" in domain_config["galileo"]:
            log_stream = domain_config["galileo"]["log_stream"]

        env_vars["GALILEO_PROJECT"] = project_name
        env_vars["GALILEO_LOG_STREAM"] = log_stream

    for key, value in env_vars.items():
        if value:
            os.environ[key] = value
        else:
            # Don't crash on missing optional secrets; warn so users know what to set.
            print(f"⚠️  {key} not set (empty value)")

    if domain_name:
        project_name = get_domain_project_name(domain_name, domain_config)
        print(f"🔧 Environment setup complete for domain: {domain_name} (project: {project_name})")
    else:
        print("🔧 Environment setup complete (domain-agnostic mode)")


if __name__ == "__main__":
    setup_environment()
