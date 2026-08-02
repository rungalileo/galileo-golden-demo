# Canonical 1Password team deployment item

The complete cloud configuration lives in one structured 1Password item. Team
members fetch it through 1Password Desktop authorization during installation;
no secret references or field-by-field templates are required.

## Canonical location

- Account: `cisco.1password.com`
- Vault: `1P-Eng-Splunk-AI-Resilience`
- Item: `Galileo Golden Demo - Team Deployment (demo-v2)`
- Item ID: `74krvvljdnxea7jzi2ncqzglgy`
- [Open the canonical item in 1Password](https://start.1password.com/open/i?a=G6IKAWUWOVDMRADYFVHDEIL7AU&v=lnvcpvdd5un3eoa6s72uiotysm&i=74krvvljdnxea7jzi2ncqzglgy&h=cisco.1password.com)
- Schema version: `1`

The vault already grants the `1P-Eng-Splunk-AI-Resilience` group permission to
view and copy secrets. Membership and vault access remain team-admin concerns;
the installer never changes 1Password access control.

## Field contract

Every field label is exact and case-sensitive. Secret fields use 1Password's
`CONCEALED` type; configuration fields use `STRING`.

| Field | Type | Required | Purpose |
|---|---|---:|---|
| `CONFIG_SCHEMA_VERSION` | STRING | Yes | Must be `1` |
| `CONFIG_ENVIRONMENT` | STRING | Yes | Human-readable deployment name |
| `OPENAI_API_KEY` | CONCEALED | Yes | Hosted chat and embeddings |
| `OPENAI_DEFAULT_CHAT_MODEL` | STRING | Yes | Hosted chat default |
| `OPENAI_EMBEDDING_MODEL` | STRING | Yes | Hosted RAG embeddings |
| `OPENAI_EMBEDDING_DIMENSIONS` | STRING | Yes | Index dimensionality |
| `GALILEO_API_KEY` | CONCEALED | Yes | Galileo and Agent Control auth |
| `GALILEO_CONSOLE_URL` | STRING | Yes | Galileo console origin |
| `GALILEO_API_URL` | STRING | Yes | Galileo API origin |
| `GALILEO_DOMAIN` | STRING | Yes | Domain receiving canonical metadata |
| `GALILEO_PROJECT` | STRING | Yes | Project name |
| `GALILEO_PROJECT_ID` | STRING | Yes | Stable project identifier |
| `GALILEO_PROJECT_URL` | STRING | Yes | Direct project link |
| `GALILEO_LOG_STREAM` | STRING | Yes | Log-stream name |
| `GALILEO_LOG_STREAM_ID` | STRING | Yes | Stable log-stream identifier |
| `GALILEO_LOG_STREAM_URL` | STRING | Yes | Direct trace link |
| `AGENT_CONTROL_URL` | STRING | Yes | Runtime guardrail endpoint |
| `AGENT_CONTROL_AGENT_NAME` | STRING | Yes | Server-side control binding |
| `AGENT_CONTROL_RUNTIME_AUTH_MODE` | STRING | Yes | Normally `jwt` |
| `AGENT_CONTROL_API_KEY_HEADER` | STRING | Yes | Normally `Galileo-API-Key` |
| `AGENT_CONTROL_TARGET_TYPE` | STRING | Yes | Normally `log_stream` |
| `POSTGRES_USER` | STRING | Yes | Local database bootstrap user |
| `POSTGRES_PASSWORD` | CONCEALED | Yes | Stable local database password |
| `POSTGRES_DB` | STRING | Yes | Local database name |
| `OPEN_WEBUI_SECRET_KEY` | CONCEALED | Yes | Stable Open WebUI session signing |
| `ADMIN_KEY` | CONCEALED | No | Demo administrative action key |

## Install from the item

```bash
scripts/macos/install.sh --team-config
```

The first install pulls the item and writes private mode-0600 `.env`, Streamlit,
PostgreSQL, and Open WebUI configuration. Subsequent installer reruns use the
cached local configuration unless explicitly refreshed.

## Force a configuration refresh

Once linked, run:

```bash
scripts/macos/refresh-config.sh
```

This reauthorizes through 1Password Desktop, validates schema version and
required fields, atomically replaces local generated configuration, recreates
the Open WebUI container while preserving its volume, restarts the app, and
rebuilds provider indexes. Use `--skip-indexes` only for a change that cannot
affect provider credentials or embedding settings.

Equivalent low-level command:

```bash
scripts/macos/install.sh \
  --op-item 'Galileo Golden Demo - Team Deployment (demo-v2)' \
  --op-vault '1P-Eng-Splunk-AI-Resilience' \
  --op-account cisco.1password.com \
  --force-config
```

Never change `POSTGRES_PASSWORD` for an existing named data volume through a
configuration refresh. The resolver refuses changes to the PostgreSQL user,
password, or database before replacing any local file. Database credential
rotation is a separate migration.
