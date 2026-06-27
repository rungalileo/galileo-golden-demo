#!/usr/bin/env bash
# Rebuild pgvector indexes for all domains (required after switching embedding models).
set -euo pipefail

cd "$(dirname "$0")"

for domain in bank healthcare insurance restaurant; do
  echo "=== Rebuilding ${domain} ==="
  python helpers/setup_vectordb.py "${domain}" local
done

echo "Done. All domain vector indexes rebuilt with OpenAI embeddings."
