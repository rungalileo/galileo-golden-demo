# Galileo Golden Demo: executive Mac installation

This setup gives one Mac a private, local Galileo demo stack:

- Galileo Golden Demo at `http://127.0.0.1:8501` (or the next free port)
- Open WebUI at `http://127.0.0.1:3000` (or the next free port)
- Gemma 4 served locally by MLX-LM on Apple Silicon
- OpenAI models in both the demo and Open WebUI
- PostgreSQL 16 with pgvector in Docker/Colima
- Galileo Cloud logging and Agent Control
- pgvector indexes and relational tables for bank, healthcare, insurance, and restaurant

Everything binds to `127.0.0.1`; it is not exposed to the office network. The
installer is safe to rerun and preserves the database and Open WebUI volumes.

## What you need

- A Mac running a currently supported macOS release
- At least 16 GiB unified memory for local MLX; 24 GiB or more is preferred
- At least 45 GiB free disk space
- Administrator permission for Apple's developer tools and Homebrew
- The repository address and access to it
- The encrypted `executive-secrets.env.age` note
- The matching age/SSH private key, or a passphrase received separately

Intel Macs are supported only in hosted OpenAI mode (`--openai-only`).

## Fast path with a Codex agent

1. Save `bootstrap.sh` and the encrypted secrets note in Downloads.
2. Open Codex and paste the prompt below, replacing the repository URL and key
   details:

   > Follow `documentation/CODEX_AGENT_MACOS_RUNBOOK.md` from the Galileo Golden
   > Demo repository. Install the full stack on this Mac. The repo is
   > `rungalileo/galileo-golden-demo`, the requested branch is
   > `codex/macos-full-stack-installer`, and the encrypted secrets are at
   > `~/Downloads/executive-secrets.env.age`. Use my age identity at
   > `~/.config/age/keys.txt`. Ask before GitHub or 1Password login and do not
   > print any secret values.

3. Approve macOS prompts only when they match the runbook: Apple Command Line
   Tools, Homebrew, GitHub browser login if requested, and 1Password Touch ID if
   using the Cisco vault.
4. When setup finishes, create the first Open WebUI account. The first local
   account becomes its administrator; use a strong unique password.

## Manual installation

Decrypt the note into a private temporary file:

```bash
chmod +x ./decrypt-secrets.sh ./bootstrap.sh
./decrypt-secrets.sh \
  --input ~/Downloads/executive-secrets.env.age \
  --identity ~/.config/age/keys.txt \
  --output ~/Downloads/executive-secrets.env
```

Then bootstrap the repository and stack:

```bash
./bootstrap.sh \
  --repo-url rungalileo/galileo-golden-demo \
  --branch codex/macos-full-stack-installer \
  --github-login \
  -- \
  --config-file ~/Downloads/executive-secrets.env
```

After the installer reports success, securely delete the decrypted copy using
Finder (move it to Trash, empty Trash) or your company's approved secure-file
procedure. The encrypted `.age` file can be retained as a backup.

For the team-managed Cisco 1Password setup instead of an encrypted note:

```bash
scripts/macos/install.sh \
  --team-config \
  --github-login
```

The script asks 1Password Desktop for authorization and never checks secrets
into Git. See `documentation/ONEPASSWORD_TEAM_CONFIG.md` for the field contract.

To deliberately pull changed team settings and redeploy them later:

```bash
scripts/macos/refresh-config.sh
```

## Model chosen for the Mac

The default `balanced` policy is deliberately conservative:

| Unified memory | Local model |
|---|---|
| Under 20 GiB | `mlx-community/gemma-4-e4b-it-4bit` |
| 20 GiB or more | `mlx-community/gemma-4-26b-a4b-it-4bit` |

On a Mac with 48 GiB or more, `--model-profile quality` selects the larger 31B
model. Use `--model MODEL_ID` only after that model has been tested with MLX-LM.

## Daily use

Start everything and open both pages:

```bash
scripts/macos/run.sh --open
```

Check all components:

```bash
scripts/macos/doctor.sh
```

Stop the app services while preserving all data:

```bash
scripts/macos/stop.sh
```

Add `--colima` only if Colima is not used by any other local project.

## Recovery

The installer can be rerun with the same arguments. It will reuse existing
containers and volumes. Useful diagnostics:

```bash
scripts/macos/doctor.sh
tail -n 100 "$HOME/Library/Logs/GalileoGoldenDemo/mlx.error.log"
tail -n 100 "$HOME/Library/Logs/GalileoGoldenDemo/streamlit.error.log"
docker logs --tail 100 golden-demo-postgres
docker logs --tail 100 galileo-open-webui
```

Use `--recreate-services` only when a named app container is corrupt or built
from the wrong image. It recreates the containers but retains their named data
volumes. Do not delete volumes unless a backup and explicit data-loss approval
exist.
