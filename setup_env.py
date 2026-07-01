"""
Environment Setup - Load secrets and set environment variables
"""
import os
import toml
import yaml
from pathlib import Path
from typing import Optional


def _derive_galileo_api_url(console_url: str, explicit_url: str = "") -> str:
    """Derive Galileo API URL from console URL when not set explicitly."""
    if explicit_url:
        return explicit_url.rstrip("/")
    console_url = (console_url or "").rstrip("/")
    if not console_url:
        return ""
    if "console." in console_url:
        return console_url.replace("console.", "api.", 1)
    return ""


def _derive_agent_control_url(console_url: str, explicit_url: str = "") -> str:
    """Derive hosted Agent Control proxy URL from Galileo console URL."""
    if explicit_url:
        return explicit_url.rstrip("/")
    console_url = (console_url or "").rstrip("/")
    if not console_url:
        return ""
    return f"{console_url}/api/agent-control"


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
    
    if not secrets_path.exists():
        print("⚠️  .streamlit/secrets.toml not found. Please create it with your API keys.")

        secrets_path = Path("../.streamlit/secrets.toml")
        if not secrets_path.exists():
            return
    
    try:
        # Load secrets
        secrets = toml.load(secrets_path)

        console_url = secrets.get("galileo_console_url", "https://app.galileo.ai")
        galileo_api_url = _derive_galileo_api_url(
            console_url, secrets.get("galileo_api_url", "")
        )
        agent_control_url = _derive_agent_control_url(
            console_url, secrets.get("agent_control_url", "")
        )
        galileo_api_key = secrets.get("galileo_api_key", "")
        
        # Base environment variables (always set)
        env_vars = {
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
            "GALILEO_API_KEY": galileo_api_key,
            "GALILEO_API_URL": galileo_api_url,
            "GALILEO_CONSOLE_URL": console_url,
            "AGENT_CONTROL_URL": agent_control_url,
            "AGENT_CONTROL_API_KEY": galileo_api_key,
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
