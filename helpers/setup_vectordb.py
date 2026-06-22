"""Dynamic Vector Database Setup Script

Builds a local PostgreSQL/pgvector-backed vector index for a given domain by
loading that domain's docs and embedding them with the local Ollama embedding model.

Usage:
  python helpers/setup_vectordb.py <domain_name> [local]

Example:
  python helpers/setup_vectordb.py healthcare local
  python helpers/setup_vectordb.py bank
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
import getpass

# Add parent directory to path to import from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from setup_env import setup_environment
from domain_manager import DomainManager

from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from helpers.llm_utils import get_domain_embedding_model, get_embeddings
from helpers.pgvector_utils import create_pgvector_store, get_collection_name


def setup_vectordb_for_domain(domain_name: str, environment: str = "local") -> bool:
    """Create (or recreate) the pgvector collection for a domain."""

    requested_env = str(environment or "local").strip().lower()
    environment = "local"
    print(f"Setting up vector database for domain: {domain_name}")
    if requested_env != "local":
        print(f"⚠️  Ignoring environment '{requested_env}'; only 'local' indexes are supported.")

    domain_manager = DomainManager()

    try:
        domain_config = domain_manager.load_domain_config(domain_name)
        print(f"✓ Loaded configuration for domain: {domain_config.description}")
    except ValueError as exc:
        print(f"❌ Error loading domain '{domain_name}': {exc}")
        print(f"Available domains: {', '.join(domain_manager.list_domains())}")
        return False

    # Load secrets + set env vars (includes POSTGRES_* defaults)
    setup_environment(domain_name, domain_config.config)

    rag_config = domain_config.config.get("rag", {})
    vectorstore_config = domain_config.config.get("vectorstore", {})

    chunk_size = rag_config.get("chunk_size", 1000)
    chunk_overlap = rag_config.get("chunk_overlap", 200)

    embedding_model = get_domain_embedding_model(vectorstore_config)

    print(f"Using chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap}")
    print(f"Using embedding model: {embedding_model}")
    print(f"If the model is missing, run: ollama pull {embedding_model}")

    docs_dir = domain_config.docs_dir
    if not os.path.exists(docs_dir):
        print(f"❌ Docs directory not found: {docs_dir}")
        return False

    print(f"Loading documents from: {docs_dir}")

    # Load documents
    # NOTE: DirectoryLoader defaults to UnstructuredFileLoader for many file types,
    # which requires the optional `unstructured` dependency. To keep local setup
    # lightweight, we explicitly load common text formats with TextLoader.

    txt_loader = DirectoryLoader(docs_dir, glob="**/*.txt", loader_cls=TextLoader)
    txt_docs = txt_loader.load()

    md_loader = DirectoryLoader(docs_dir, glob="**/*.md", loader_cls=TextLoader)
    md_docs = md_loader.load()

    csv_loader = DirectoryLoader(docs_dir, glob="**/*.csv", loader_cls=CSVLoader)
    csv_docs = csv_loader.load()

    non_csv_docs = txt_docs + md_docs
    print(f"✓ Loaded {len(non_csv_docs)} text documents (.txt/.md)")
    print(f"✓ Loaded {len(csv_docs)} CSV documents")

    if len(non_csv_docs) == 0 and len(csv_docs) == 0:
        print(f"⚠️  No documents found in {docs_dir}")
        return False

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    split_docs = text_splitter.split_documents(non_csv_docs)

    all_docs = split_docs + csv_docs
    print(f"✓ Total document chunks: {len(all_docs)}")

    # Ensure Postgres password is set (for local docker compose / dev)
    if not os.environ.get("POSTGRES_PASSWORD"):
        os.environ["POSTGRES_PASSWORD"] = getpass.getpass("Enter PostgreSQL password: ")

    embeddings = get_embeddings(embedding_model, provider="local")

    collection_name = get_collection_name(domain_name, environment)
    print(f"Creating PostgreSQL/pgvector collection: {collection_name}")

    vector_store, _ = create_pgvector_store(
        embeddings,
        domain_name,
        environment,
        pre_delete_collection=True,
    )

    print("Adding documents to pgvector...")
    ids = [str(uuid.uuid4()) for _ in range(len(all_docs))]
    vector_store.add_documents(documents=all_docs, ids=ids)

    print(f"✅ Successfully created vector database for {domain_name}")
    print(f"📊 Total documents embedded: {len(all_docs)}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up vector database for a specific domain using PostgreSQL + pgvector"
    )
    parser.add_argument("domain", help="Domain name (e.g., 'finance')")
    parser.add_argument(
        "environment",
        nargs="?",
        default="local",
        help="Vector index environment (always 'local')",
    )
    parser.add_argument("--list-domains", action="store_true", help="List available domains")

    args = parser.parse_args()

    if args.list_domains:
        domain_manager = DomainManager()
        domains = domain_manager.list_domains()
        print("Available domains:")
        for domain in domains:
            print(f"  - {domain}")
        return

    success = setup_vectordb_for_domain(args.domain, args.environment)
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
