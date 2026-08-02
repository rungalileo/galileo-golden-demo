# Executive secrets transfer staging

Generated secret material in this directory is intentionally ignored by Git.
Only this README and the redacted example are versioned.

Recommended transfer:

1. Prepare a private transfer source from the current working configuration:

   ```bash
   scripts/macos/export_secrets.py
   ```

   The command reports missing required key *names* without printing values.
   Add any missing OpenAI/Galileo credential to
   `transfer/executive-secrets.env`, then keep it mode 0600.
2. Ask the recipient for an `age` public key or an SSH public key. Public keys
   are safe to send in ordinary email or chat.
3. From the repository root, run:

   ```bash
   scripts/macos/encrypt-secrets.sh \
     --input transfer/executive-secrets.env \
     --recipient 'age1...'
   ```

   An SSH recipient such as `ssh-ed25519 AAAA...` also works.
4. Verify decryption locally before sending the file.
5. Send only `transfer/executive-secrets.env.age`. Do not send `.env`,
   `.streamlit/secrets.toml`, an age private key, or a passphrase.

If public-key encryption is not possible, use `--passphrase` and communicate the
passphrase through a different channel (for example, file over email and
passphrase by voice). Never store both together.

The real encrypted artifact cannot be created until the executive supplies a
recipient public key or a separately communicated passphrase is chosen.
