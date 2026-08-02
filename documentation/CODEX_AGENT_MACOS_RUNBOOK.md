# Runbook for a Codex agent: install Galileo Golden Demo on macOS

## Objective and safety contract

Install a complete local stack and stop only when `scripts/macos/doctor.sh`
passes. Never print, log, commit, or paste secret values. Do not source the
secrets file. Do not delete Docker volumes or replace unrelated containers.
Request the user's approval for GUI/login actions and any command that the local
sandbox requires them to authorize.

This runbook intentionally ignores Ollama. Use MLX-LM on Apple Silicon and
hosted OpenAI on Intel.

## 1. Preflight

Run read-only checks:

```bash
uname -s
uname -m
sw_vers
sysctl -n hw.memsize
df -h /
```

Confirm that the OS is macOS. If the architecture is `x86_64`, add
`--openai-only`. Confirm at least 45 GiB free for the normal MLX installation.
Do not assume a fixed port; the installer resolves conflicts.

Identify how secrets will be supplied:

- Encrypted note: decrypt to a mode-0600 file with
  `scripts/macos/decrypt-secrets.sh`.
- Cisco 1Password: use `--op-item ITEM --op-vault VAULT --op-account ACCOUNT`.
  The canonical schema is in `documentation/ONEPASSWORD_TEAM_CONFIG.md`. The user must open
  and unlock 1Password, enable Settings > Developer > Integrate with 1Password
  CLI, and approve the Touch ID request.

The full cloud-connected install requires nonempty `OPENAI_API_KEY`,
`GALILEO_API_KEY`, and `GALILEO_CONSOLE_URL`. Never inspect their values; test
only for presence.

## 2. Repository access

If the repository is absent, run the standalone bootstrap. Add
`--github-login` only after the user opts in:

```bash
./bootstrap.sh \
  --repo-url rungalileo/galileo-golden-demo \
  --branch codex/macos-full-stack-installer \
  --github-login \
  -- \
  --config-file /absolute/private/path/executive-secrets.env
```

If already cloned, verify the worktree before changing branches. Preserve local
changes and stop for the user if they overlap installer files.

## 3. Install

From the repository root:

```bash
chmod +x scripts/macos/*.sh
scripts/macos/install.sh --config-file /absolute/private/path/executive-secrets.env
```

Expected user-visible actions are Apple Command Line Tools installation,
Homebrew authorization, optional GitHub browser login, and optional 1Password
authorization. Model downloads are large and may take time without producing
frequent output; continue monitoring rather than restarting them.

The installer performs these idempotent stages:

1. Installs Homebrew, Git, GitHub CLI, Python 3.12, uv, Colima, Docker,
   Docker Compose, age, and jq.
2. Creates a project virtualenv and installs the tested Apple-Silicon lock file
   (`requirements-macos.lock`; Intel uses `requirements.txt`).
3. Parses the dotenv allow-list and atomically writes `.env`,
   `.streamlit/secrets.toml`, and private container env files with mode 0600.
4. Selects and downloads a Gemma 4 MLX model based on unified memory.
5. Starts PostgreSQL 16/pgvector and Open WebUI in named Docker containers.
6. Creates user launch agents for MLX-LM and Streamlit.
7. Builds local and hosted pgvector indexes plus relational tables for bank,
   healthcare, insurance, and restaurant.
8. Runs the health doctor.

For a linked installation, refresh changed configuration only with
`scripts/macos/refresh-config.sh` (or the explicit `--force-config` installer
flag). A normal rerun intentionally keeps the cached local snapshot.

Do not replace the installer with ad hoc `pip`, `docker`, or `launchctl`
commands unless diagnosing a concrete failure; keep reruns reproducible.

## 4. Acceptance tests

Run:

```bash
scripts/macos/doctor.sh
scripts/macos/test.sh
```

All doctor checks and repository tests must pass. Then make one smoke request
without exposing content:

```bash
curl -fsS http://127.0.0.1:8501/_stcore/health
curl -fsS http://127.0.0.1:3000/health
curl -fsS http://127.0.0.1:8080/v1/models | jq -e '.data | length > 0'
```

Read actual ports from
`~/Library/Application Support/GalileoGoldenDemo/stack.env`; the defaults above
may have shifted because of port conflicts.

Open the app and test both provider paths:

1. Local (MLX): a normal factual question must return prose, not a raw JSON
   object.
2. Hosted (OpenAI): a normal factual question must succeed.
3. RAG: the healthcare page must return an answer with retrieved context.
4. Galileo: verify a new trace in the configured Galileo Cloud project/log
   stream. Opening the Galileo console is allowed; never paste the API key into
   a page other than the expected trusted console.

## 5. Handoff

Tell the user the two local URLs, selected MLX model, actual ports, doctor/test
results, and log directory. Remind them that the first Open WebUI account is the
local administrator and that the decrypted transfer file should be removed
with the company's approved secure-file procedure.

Do not claim completion if a required cloud provider, Galileo trace, pgvector
index, or health check is missing. Record the exact failing component without
including credentials.
