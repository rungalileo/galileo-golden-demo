"""
Environment Setup - Load secrets and set environment variables
"""
import os
import toml
from pathlib import Path


def setup_environment():
    """Load secrets from .streamlit/secrets.toml and set environment variables"""
    secrets_path = Path(".streamlit/secrets.toml")
    
    if not secrets_path.exists():
        print("⚠️  .streamlit/secrets.toml not found. Please create it with your API keys.")
        return
    
    try:
        # Load secrets
        secrets = toml.load(secrets_path)
        
        # Set environment variables
        env_vars = {
            "OPENAI_API_KEY": secrets.get("openai_api_key", ""),
            "GALILEO_API_KEY": secrets.get("galileo_api_key", ""),
            "GALILEO_PROJECT": secrets.get("galileo_project", ""),
            "GALILEO_LOG_STREAM": secrets.get("galileo_log_stream", ""),
            "GALILEO_CONSOLE_URL": secrets.get("galileo_console_url", "https://app.galileo.ai"),
            "ADMIN_KEY": secrets.get("admin_key", ""),
            "PINECONE_API_KEY_LOCAL": secrets.get("pinecone_api_key_local", ""),
            "PINECONE_API_KEY_HOSTED": secrets.get("pinecone_api_key_hosted", ""),
            "ENVIRONMENT": secrets.get("environment", "local")
        }
        
        for key, value in env_vars.items():
            if value:  # Only set if value is not empty
                os.environ[key] = value
                # print(f"✅ Set {key}")
            else:
                print(f"⚠️  {key} not set (empty value)")
        
        print("🔧 Environment setup complete!")
        
    except Exception as e:
        print(f"❌ Error loading secrets: {e}")


if __name__ == "__main__":
    setup_environment()
