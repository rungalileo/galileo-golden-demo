"""
OpenTelemetry Setup - Configure OpenTelemetry instrumentation for the app
"""
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# Import OpenInference instrumentations for LangChain
from openinference.instrumentation.openai import OpenAIInstrumentor as OpenInferenceOpenAIInstrumentor
from openinference.instrumentation.langchain import LangChainInstrumentor

# Try to import LangGraphInstrumentor if available
try:
    from openinference.instrumentation.langgraph import LangGraphInstrumentor
    LANGGRAPH_INSTRUMENTOR_AVAILABLE = True
except ImportError:
    LANGGRAPH_INSTRUMENTOR_AVAILABLE = False


def setup_opentelemetry(
    service_name: str = "galileo-golden-demo",
    otlp_endpoint: str = None,
    otlp_headers: dict = None,
    enable_console_exporter: bool = False,
    enable_openinference: bool = True
):
    """
    Set up OpenTelemetry instrumentation for the application.
    
    Args:
        service_name: Name of the service for tracing
        otlp_endpoint: Optional OTLP endpoint URL (e.g., "http://localhost:4318/v1/traces")
                      If None, only console exporter will be used (if enabled)
        otlp_headers: Optional headers for OTLP exporter (e.g., {"Authorization": "Bearer token"})
        enable_console_exporter: Whether to enable console span exporter for debugging
        enable_openinference: Whether to enable OpenInference instrumentations for LangChain
    """
    # Create resource with service name
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
    })
    
    # Set up tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # Add console exporter if enabled (useful for debugging)
    if enable_console_exporter:
        console_exporter = ConsoleSpanExporter()
        tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        print("✅ OpenTelemetry console exporter enabled")
    
    # Add OTLP exporter if endpoint is provided
    if otlp_endpoint:
        try:
            # OTLPSpanExporter can use headers from environment variable OTEL_EXPORTER_OTLP_TRACES_HEADERS
            # or from the headers parameter. We'll use the headers parameter if provided.
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                headers=otlp_headers or {}  # Add headers if needed for authentication
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            print(f"✅ OpenTelemetry OTLP exporter configured: {otlp_endpoint}")
        except Exception as e:
            print(f"⚠️  Failed to configure OTLP exporter: {e}")
    
    # Instrument OpenAI (standard OpenTelemetry)
    try:
        OpenAIInstrumentor().instrument()
        print("✅ OpenAI instrumentation enabled")
    except Exception as e:
        print(f"⚠️  Failed to instrument OpenAI: {e}")
    
    # Instrument HTTP clients
    try:
        HTTPXClientInstrumentor().instrument()
        RequestsInstrumentor().instrument()
        print("✅ HTTP client instrumentation enabled")
    except Exception as e:
        print(f"⚠️  Failed to instrument HTTP clients: {e}")
    
    # Enable OpenInference instrumentations for better LangChain support
    if enable_openinference:
        try:
            # OpenInference OpenAI instrumentation (enhanced for LangChain)
            # Pass tracer_provider to ensure proper tracing context
            OpenInferenceOpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
            
            # LangChain instrumentation
            LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
            
            # LangGraph instrumentation (if available) - per Galileo docs
            if LANGGRAPH_INSTRUMENTOR_AVAILABLE:
                LangGraphInstrumentor().instrument(tracer_provider=tracer_provider)
                print("✅ OpenInference instrumentations enabled (OpenAI + LangChain + LangGraph)")
            else:
                print("✅ OpenInference instrumentations enabled (OpenAI + LangChain)")
        except Exception as e:
            print(f"⚠️  Failed to enable OpenInference instrumentations: {e}")
    
    print("🔧 OpenTelemetry setup complete!")
    return tracer_provider


def setup_opentelemetry_from_env():
    """
    Set up OpenTelemetry using environment variables.
    
    Environment variables:
    - OTEL_SERVICE_NAME: Service name (default: "galileo-golden-demo")
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint URL
    - OTEL_EXPORTER_OTLP_TRACES_HEADERS: Headers for OTLP (Galileo format: "key=value,key2=value2")
    - OTEL_CONSOLE_EXPORTER: Enable console exporter ("true" or "1")
    - OTEL_ENABLE_OPENINFERENCE: Enable OpenInference ("true" or "1", default: true)
    
    For Galileo's OTLP endpoint, set:
    - OTEL_EXPORTER_OTLP_ENDPOINT=https://api.galileo.ai/otel/traces
    - OTEL_EXPORTER_OTLP_TRACES_HEADERS=Galileo-API-Key=YOUR_KEY,project=YOUR_PROJECT,logstream=YOUR_LOG_STREAM
    
    Per Galileo documentation: https://v2docs.galileo.ai/how-to-guides/third-party-integrations/otel
    """
    service_name = os.environ.get("OTEL_SERVICE_NAME", "galileo-golden-demo")
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    # Use OTEL_EXPORTER_OTLP_TRACES_HEADERS (Galileo's format) or fallback to OTEL_EXPORTER_OTLP_HEADERS
    otlp_headers_str = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_HEADERS") or os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "")
    enable_console = os.environ.get("OTEL_CONSOLE_EXPORTER", "").lower() in ("true", "1")
    enable_openinference = os.environ.get("OTEL_ENABLE_OPENINFERENCE", "true").lower() in ("true", "1")
    
    # Parse headers if provided (Galileo format: "key=value,key2=value2")
    otlp_headers = {}
    if otlp_headers_str:
        try:
            # Support Galileo format: "key=value,key2=value2"
            for header_pair in otlp_headers_str.split(","):
                if "=" in header_pair:
                    key, value = header_pair.split("=", 1)
                    otlp_headers[key.strip()] = value.strip()
                elif ":" in header_pair:
                    # Fallback support for "key: value" format
                    key, value = header_pair.split(":", 1)
                    otlp_headers[key.strip()] = value.strip()
        except Exception as e:
            print(f"⚠️  Failed to parse OTLP headers: {e}")
    
    # Auto-configure Galileo headers if using Galileo endpoint (per Galileo docs)
    if otlp_endpoint and "galileo.ai" in otlp_endpoint:
        galileo_api_key = os.environ.get("GALILEO_API_KEY")
        galileo_project = os.environ.get("GALILEO_PROJECT")
        galileo_log_stream = os.environ.get("GALILEO_LOG_STREAM", "default")
        
        # Build headers in Galileo's required format
        if galileo_api_key and "Galileo-API-Key" not in otlp_headers:
            otlp_headers["Galileo-API-Key"] = galileo_api_key
        if galileo_project and "project" not in otlp_headers:
            otlp_headers["project"] = galileo_project
        if galileo_log_stream and "logstream" not in otlp_headers:
            otlp_headers["logstream"] = galileo_log_stream
        
        # Set environment variable in Galileo's required format (for OTLP exporter)
        if otlp_headers:
            os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = ",".join(
                [f"{k}={v}" for k, v in otlp_headers.items()]
            )
            print("✅ Auto-configured Galileo OTLP headers (Galileo-API-Key, project, logstream)")
    
    return setup_opentelemetry(
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        otlp_headers=otlp_headers if otlp_headers else None,
        enable_console_exporter=enable_console,
        enable_openinference=enable_openinference
    )


if __name__ == "__main__":
    # Test the setup
    print("Testing OpenTelemetry setup...")
    setup_opentelemetry_from_env()
    
    # Create a test span
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test_span") as span:
        span.set_attribute("test.attribute", "test_value")
        print("✅ Test span created successfully")

