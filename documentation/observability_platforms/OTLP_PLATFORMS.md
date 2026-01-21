# OpenTelemetry Platforms (Phoenix & Arize AX)

This guide explains how OpenTelemetry (OTLP) platforms work in the Galileo Golden Demo.

## Overview

The demo supports two OpenTelemetry-based observability platforms:
- **Phoenix** (Arize's hosted OpenTelemetry platform)
- **Arize AX** (Arize Platform with OpenTelemetry)

These platforms use the OpenTelemetry Protocol (OTLP) and OpenInference instrumentation to capture LangChain traces automatically.

## How It Works

### Switchable Architecture

The demo uses a "switchable span processor" that allows changing OTLP platforms at runtime **without restarting the server**:

1. OpenTelemetry instrumentation is initialized once at startup
2. A switchable processor routes spans to the active platform
3. Users can toggle between Phoenix, Arize AX, or None instantly via the UI
4. Traces flow to the selected platform immediately

### Project Names

**Arize AX**: Project name changes dynamically based on the current domain (e.g., `galileo-demo-finance`, `galileo-demo-healthcare`). This is set via the `arize.project.name` span attribute.

**Phoenix**: Project name is fixed at `galileo-demo` for all domains. This is a technical limitation - Phoenix reads the project from OpenTelemetry resource attributes, which are set once at initialization time before a domain is selected.

> **Note**: If you need Phoenix to use a different project name, set the `PHOENIX_PROJECT_NAME` environment variable before starting the app.

## Configuration

### Phoenix Setup

1. Add credentials to `.streamlit/secrets.toml`:
```toml
PHOENIX_ENDPOINT = "https://app.phoenix.arize.com/v1/traces"
PHOENIX_API_KEY = "your_api_key"
# Optional: Set a custom project name (default: galileo-demo)
# PHOENIX_PROJECT_NAME = "my-custom-project"
```

2. Start the app
3. Click "Phoenix" in the Observability Platforms section
4. Traces flow to Phoenix immediately

### Arize AX Setup

1. Add credentials to `.streamlit/secrets.toml`:
```toml
ARIZE_API_KEY = "your_api_key"
ARIZE_SPACE_ID = "your_space_id"
```

2. Start the app
3. Click "Arize AX" in the Observability Platforms section
4. Traces flow to Arize with domain-specific project names

## Technical Details

### Initialization Flow

```
app.py (module load)
├─ Load environment variables
├─ initialize_otlp_tracing()
│
tracing_setup.py
├─ Create SwitchableSpanProcessor
├─ Check Phoenix/Arize credentials availability
├─ Create TracerProvider with switchable processor
│  └─ Resource includes openinference.project.name (for Phoenix)
├─ Instrument LangChain with tracer provider
│
└─ Import LangChain (now instrumented!)

At runtime (user clicks platform button):
├─ switch_otlp_platform("phoenix" or "arize")
├─ Create exporter for selected platform
├─ Switchable processor routes spans to new exporter
└─ Traces flow to selected platform
```

### Phoenix Implementation

- **Endpoint**: Configured via `PHOENIX_ENDPOINT`
- **Authentication**: Bearer token via `PHOENIX_API_KEY`
- **Project**: Set via `openinference.project.name` resource attribute (fixed at startup)
- **Limitation**: Cannot change project per-domain at runtime

### Arize AX Implementation

- **Endpoint**: `https://otlp.arize.com/v1/traces`
- **Authentication**: API key + Space ID in headers
- **Project**: Set via `arize.project.name` span attribute (dynamic per-domain)
- **Advantage**: Project changes automatically when switching domains

### SwitchableSpanProcessor

The key to runtime switching is the `SwitchableSpanProcessor` class:

```python
class SwitchableSpanProcessor:
    # Routes spans to the active platform
    # Adds platform-specific attributes (arize.project.name for Arize)
    # Can switch between phoenix/arize/none without restart
```

## Comparison to Callback Platforms

| Feature | OTLP Platforms | Callback Platforms |
|---------|----------------|-------------------|
| **Examples** | Phoenix, Arize AX | LangSmith, Braintrust |
| **Switching** | Instant (no reload) | Instant |
| **Multiple Active** | No (mutually exclusive) | Yes |
| **Dynamic Project (Arize)** | Yes | Yes |
| **Dynamic Project (Phoenix)** | No (fixed at startup) | N/A |
| **Implementation** | OpenTelemetry + OpenInference | LangChain callbacks |

## Project Name Behavior

| Platform | Project Name | Can Change Per-Domain? |
|----------|-------------|----------------------|
| Galileo | `galileo-demo-{domain}` | ✅ Yes |
| LangSmith | `galileo-demo-{domain}` | ✅ Yes |
| Braintrust | `galileo-demo-{domain}` | ✅ Yes |
| Arize AX | `galileo-demo-{domain}` | ✅ Yes |
| Phoenix | `galileo-demo` | ❌ No (fixed) |

## Troubleshooting

### Platform not appearing as available
- **Check credentials**: Ensure credentials are in `.streamlit/secrets.toml`
- **Check terminal**: Look for `Phoenix: available` or `Arize: available` at startup

### Traces not appearing in Arize
- **Check project name**: Terminal should show `[OTLP] Creating Arize processor with project_name: galileo-demo-{domain}`
- **Verify span attribute**: Check that `arize.project.name` is being set

### Phoenix traces going to wrong project
- **This is expected**: Phoenix uses a fixed project name set at startup
- **To change**: Set `PHOENIX_PROJECT_NAME` environment variable and restart

### Both platforms' credentials configured
- Only one OTLP platform can be active at a time
- Use the buttons to select which one to activate
- If no selection made, no platform activates (default)

## FAQs

**Q: Why can't Phoenix change projects per-domain like Arize?**  
A: Phoenix reads the project from OpenTelemetry resource attributes, which are set once when the TracerProvider is created at startup. Arize reads from span attributes, which can be set per-span at runtime. This is a fundamental difference in how the platforms work.

**Q: Can I use both Phoenix and Arize AX at the same time?**  
A: No, they are mutually exclusive OTLP platforms. You can only have one active at a time. However, you can use an OTLP platform alongside callback-based platforms (LangSmith, Braintrust, and Galileo is always on).

**Q: Do I need to restart the server to switch between Phoenix and Arize?**  
A: No! The switchable architecture allows instant switching. Just click the platform button in the UI.

**Q: Will my conversation history be lost when switching OTLP platforms?**  
A: No, conversation history is preserved. Only a page rerun happens, not a full server restart.
