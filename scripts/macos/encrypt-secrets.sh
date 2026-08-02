#!/bin/bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=lib/common.sh
. "$SCRIPT_DIR/lib/common.sh"

INPUT="$REPO_DIR/.env"
OUTPUT="$REPO_DIR/transfer/executive-secrets.env.age"
RECIPIENT=""
RECIPIENT_FILE=""
PASSPHRASE=0
FORCE=0

usage() {
  cat <<'USAGE'
Usage: encrypt-secrets.sh [options]

  --input PATH             Plaintext dotenv input (default: repo .env)
  --output PATH            age output (default: transfer/executive-secrets.env.age)
  --recipient AGE_OR_SSH   Executive's age or SSH public key (recommended)
  --recipient-file PATH    File containing one or more age/SSH recipients
  --passphrase             Interactively encrypt with a separately shared passphrase
  --force                  Replace an existing output file

Use exactly one of --recipient, --recipient-file, or --passphrase. Never send a
passphrase in the same channel as the encrypted file.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --input) [ "$#" -ge 2 ] || die "--input needs a path"; INPUT="$2"; shift 2 ;;
    --output) [ "$#" -ge 2 ] || die "--output needs a path"; OUTPUT="$2"; shift 2 ;;
    --recipient) [ "$#" -ge 2 ] || die "--recipient needs a value"; RECIPIENT="$2"; shift 2 ;;
    --recipient-file) [ "$#" -ge 2 ] || die "--recipient-file needs a path"; RECIPIENT_FILE="$2"; shift 2 ;;
    --passphrase) PASSPHRASE=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

choice_count=0
[ -z "$RECIPIENT" ] || choice_count=$((choice_count + 1))
[ -z "$RECIPIENT_FILE" ] || choice_count=$((choice_count + 1))
[ "$PASSPHRASE" != "1" ] || choice_count=$((choice_count + 1))
[ "$choice_count" -eq 1 ] || die "Choose exactly one encryption mode."
[ -f "$INPUT" ] || die "Plaintext secrets file not found: $INPUT"
[ ! -e "$OUTPUT" ] || [ "$FORCE" = "1" ] || die "$OUTPUT exists; use --force to replace it."
command_exists age || die "age is not installed. Run: brew install age"

ensure_directory "$(dirname "$OUTPUT")"
TEMP_OUTPUT="$(mktemp "$(dirname "$OUTPUT")/.executive-secrets.XXXXXX")"
trap 'rm -f "$TEMP_OUTPUT"' EXIT

if [ -n "$RECIPIENT" ]; then
  age -r "$RECIPIENT" "$INPUT" > "$TEMP_OUTPUT"
elif [ -n "$RECIPIENT_FILE" ]; then
  [ -f "$RECIPIENT_FILE" ] || die "Recipient file not found: $RECIPIENT_FILE"
  age -R "$RECIPIENT_FILE" "$INPUT" > "$TEMP_OUTPUT"
else
  age -p "$INPUT" > "$TEMP_OUTPUT"
fi

chmod 600 "$TEMP_OUTPUT"
mv -f "$TEMP_OUTPUT" "$OUTPUT"
trap - EXIT
success "Encrypted secrets written to $OUTPUT"
printf 'Verify before sending: age --decrypt <options> %q\n' "$OUTPUT"
