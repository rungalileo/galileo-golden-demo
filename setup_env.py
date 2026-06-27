"""
Environment Setup - Load secrets and set environment variables
"""
import os
import toml
from pathlib import Path


def setup_environment(verbose=True):
    """Load secrets from .streamlit/secrets.toml and set environment variables"""
    secrets_path = Path(".streamlit/secrets.toml")
    
    if not secrets_path.exists():
<<<<<<< Updated upstream
        if verbose:
            print("⚠️  .streamlit/secrets.toml not found. Please create it with your API keys.")
        return
=======
        print("⚠️  .streamlit/secrets.toml not found. Please create it with your API keys.")

        secrets_path = Path("../.streamlit/secrets.toml")
        if not secrets_path.exists():
            return
>>>>>>> Stashed changes
    
    try:
        # Load secrets
        secrets = toml.load(secrets_path)
        
<<<<<<< Updated upstream
        # Convert all secrets to uppercase environment variable names
        # and set them as environment variables
        vars_set = 0
        vars_skipped = 0
=======
        # Base environment variables (always set)
        env_vars = {
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
        }
>>>>>>> Stashed changes
        
        for key, value in secrets.items():
            if isinstance(value, (str, int, float, bool)):
                # Convert key to uppercase for environment variable
                env_key = key.upper()
                
                # Convert value to string
                env_value = str(value)
                
                if env_value and env_value.lower() != "none":
                    os.environ[env_key] = env_value
                    vars_set += 1
                else:
                    vars_skipped += 1
                    if key == "admin_key" and verbose:  # Only warn for expected empty values
                        print(f"⚠️  {env_key} not set (empty value)")
        
        if verbose:
            print(f"🔧 Environment setup complete! ({vars_set} variables loaded)")
        
    except Exception as e:
        if verbose:
            print(f"❌ Error loading secrets: {e}")


if __name__ == "__main__":
    setup_environment()
