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
        if verbose:
            print("⚠️  .streamlit/secrets.toml not found. Please create it with your API keys.")
        return
    
    try:
        # Load secrets
        secrets = toml.load(secrets_path)
        
        # Convert all secrets to uppercase environment variable names
        # and set them as environment variables
        vars_set = 0
        vars_skipped = 0
        
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
