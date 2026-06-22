"""
Environment Setup - Load secrets and set environment variables
"""
import os
import toml
import yaml
from pathlib import Path
from typing import Optional


def get_domain_project_name(domain_name: str, domain_config: Optional[dict] = None) -> str:
    """
    Get the Galileo project name for a domain.
    
    Priority:
    1. If domain_config has a 'galileo.project' field, use that (explicit)
    2. Otherwise, use default: "galileo-demo-{domain_name}"
    
    Args:
        domain_name: Name of the domain (e.g., "finance")
        domain_config: Loaded domain config dict (optional, for explicit project name)
    
    Returns:
        Project name for the domain
    """
    # Check if domain config explicitly specifies a project
    if domain_config and "galileo" in domain_config and "project" in domain_config["galileo"]:
        return domain_config["galileo"]["project"]
    
    # Default convention: galileo-demo-{domain_name}
    return f"galileo-demo-{domain_name}"


def setup_environment(domain_name: Optional[str] = None, domain_config: Optional[dict] = None):
    """
    Load secrets from .streamlit/secrets.toml and set environment variables.
    
    If domain_name is provided:
        - Sets domain-specific GALILEO_PROJECT (from config or default)
        - Sets domain-specific GALILEO_LOG_STREAM (from config or default)
    
    If domain_name is None (for CLI scripts):
        - Only sets API keys and non-domain-specific settings
        - Project name should be set by the calling script after loading domain config
    
    Args:
        domain_name: Name of the domain to set up (e.g., "finance"). Optional for CLI scripts.
        domain_config: Loaded domain config dict (optional, for domain-specific settings)
    """
    secrets_path = Path(".streamlit/secrets.toml")
    secrets: dict = {}

    if secrets_path.exists():
        try:
            secrets = toml.load(secrets_path)
        except Exception as e:
            print(f"❌ Error loading secrets from {secrets_path}: {e}")
            secrets = {}
    else:
        # CI / non-Streamlit contexts: fall back to environment variables.
        # No-op if those are also unset; the empty-value check below will warn.
        print("ℹ️  .streamlit/secrets.toml not found; using environment variables.")

    def _resolve(secret_key: str, env_key: str, default: str = "") -> str:
        """Prefer existing env var, then secrets.toml, then default."""
        return os.environ.get(env_key) or secrets.get(secret_key, default)

    try:
        # Base environment variables (always set)
        env_vars = {
<<<<<<< Updated upstream
            "OPENAI_API_KEY": _resolve("openai_api_key", "OPENAI_API_KEY"),
            "GALILEO_API_KEY": _resolve("galileo_api_key", "GALILEO_API_KEY"),
            "GALILEO_STAGE": _resolve("galileo_stage", "GALILEO_STAGE", "protect-prompt-injection-stage"),
            "GALILEO_CONSOLE_URL": _resolve("galileo_console_url", "GALILEO_CONSOLE_URL", "https://app.galileo.ai"),
            "ADMIN_KEY": _resolve("admin_key", "ADMIN_KEY"),
            "PINECONE_API_KEY_LOCAL": _resolve("pinecone_api_key_local", "PINECONE_API_KEY_LOCAL"),
            "PINECONE_API_KEY_HOSTED": _resolve("pinecone_api_key_hosted", "PINECONE_API_KEY_HOSTED"),
            "ENVIRONMENT": _resolve("environment", "ENVIRONMENT", "local"),
=======
            "OLLAMA_BASE_URL": secrets.get("ollama_base_url", "http://localhost:11434"),
            "OLLAMA_DEFAULT_CHAT_MODEL": secrets.get(
                "ollama_default_chat_model", "gemma4"
            ),
            "OLLAMA_EMBEDDING_MODEL": secrets.get(
                "ollama_embedding_model", "nomic-embed-text"
            ),
            "OPENAI_API_KEY": secrets.get("openai_api_key", ""),
            "OPENAI_DEFAULT_CHAT_MODEL": secrets.get(
                "openai_default_chat_model", "gpt-4o"
            ),
            "OPENAI_EMBEDDING_MODEL": secrets.get(
                "openai_embedding_model", "text-embedding-3-large"
            ),
            "GALILEO_API_KEY": secrets.get("galileo_api_key", ""),
            "GALILEO_API_URL": secrets.get("galileo_api_url", ""),
            "GALILEO_CONSOLE_URL": secrets.get("galileo_console_url", "https://app.galileo.ai"),
            "AGENT_CONTROL_URL": secrets.get("agent_control_url", ""),
            "AGENT_CONTROL_AGENT_NAME": secrets.get("agent_control_agent_name", ""),
            "AGENT_CONTROL_API_KEY_HEADER": secrets.get("agent_control_api_key_header", "Galileo-API-Key"),
            "AGENT_CONTROL_RUNTIME_AUTH_MODE": secrets.get("agent_control_runtime_auth_mode", "jwt"),
            "AGENT_CONTROL_TARGET_TYPE": secrets.get("agent_control_target_type", "log_stream"),
            "ADMIN_KEY": secrets.get("admin_key", ""),
            "POSTGRES_HOST": secrets.get("postgres_host", "localhost"),
            "POSTGRES_PORT": secrets.get("postgres_port", "5432"),
            "POSTGRES_USER": secrets.get("postgres_user", "postgres"),
            "POSTGRES_PASSWORD": secrets.get("postgres_password", ""),
            "POSTGRES_DB": secrets.get("postgres_db", "vectordb"),
            "ENVIRONMENT": secrets.get("environment", "local")
>>>>>>> Stashed changes
        }
        
        # If domain is specified, add domain-specific settings
        if domain_name:
            project_name = get_domain_project_name(domain_name, domain_config)
            log_stream = "default"
            if domain_config and "galileo" in domain_config and "log_stream" in domain_config["galileo"]:
                log_stream = domain_config["galileo"]["log_stream"]
            
            env_vars["GALILEO_PROJECT"] = project_name
            env_vars["GALILEO_LOG_STREAM"] = log_stream
        
        for key, value in env_vars.items():
            if value:  # Only set if value is not empty
                os.environ[key] = value
                # print(f"✅ Set {key}")
            else:
                print(f"⚠️  {key} not set (empty value)")
        
        if domain_name:
            project_name = get_domain_project_name(domain_name, domain_config)
            print(f"🔧 Environment setup complete for domain: {domain_name} (project: {project_name})")
        else:
            print("🔧 Environment setup complete (domain-agnostic mode)")
        
    except Exception as e:
        print(f"❌ Error loading secrets: {e}")


if __name__ == "__main__":
    setup_environment()
