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
            "OPENAI_API_KEY": _resolve("openai_api_key", "OPENAI_API_KEY"),
            "GALILEO_API_KEY": _resolve("galileo_api_key", "GALILEO_API_KEY"),
            "GALILEO_STAGE": _resolve("galileo_stage", "GALILEO_STAGE", "protect-prompt-injection-stage"),
            "GALILEO_CONSOLE_URL": _resolve("galileo_console_url", "GALILEO_CONSOLE_URL", "https://app.galileo.ai"),
            "ADMIN_KEY": _resolve("admin_key", "ADMIN_KEY"),
            "PINECONE_API_KEY_LOCAL": _resolve("pinecone_api_key_local", "PINECONE_API_KEY_LOCAL"),
            "PINECONE_API_KEY_HOSTED": _resolve("pinecone_api_key_hosted", "PINECONE_API_KEY_HOSTED"),
            "ENVIRONMENT": _resolve("environment", "ENVIRONMENT", "local"),
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
