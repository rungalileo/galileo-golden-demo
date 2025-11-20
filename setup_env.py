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
            "ENVIRONMENT": secrets.get("environment", "local"),
            # OpenTelemetry configuration
            "OTEL_SERVICE_NAME": secrets.get("otel_service_name", "galileo-golden-demo"),
            "OTEL_EXPORTER_OTLP_ENDPOINT": secrets.get("otel_exporter_otlp_endpoint", ""),
            # Use OTEL_EXPORTER_OTLP_TRACES_HEADERS (Galileo format) or fallback to OTEL_EXPORTER_OTLP_HEADERS
            "OTEL_EXPORTER_OTLP_TRACES_HEADERS": secrets.get("otel_exporter_otlp_traces_headers", ""),
            "OTEL_EXPORTER_OTLP_HEADERS": secrets.get("otel_exporter_otlp_headers", ""),  # Fallback format
            "OTEL_CONSOLE_EXPORTER": secrets.get("otel_console_exporter", "false"),
            "OTEL_ENABLE_OPENINFERENCE": secrets.get("otel_enable_openinference", "true")
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
