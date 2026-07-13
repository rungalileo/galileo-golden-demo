"""
Dynamic Vector Database Setup Script
Supports any domain by reading configuration from domain config files.
Uses PostgreSQL with pgvector for vector storage.

Usage:
    python setup_vectordb.py <domain_name>

Example:
    python setup_vectordb.py finance

Which indexes get built is derived entirely from the credentials present in
.streamlit/secrets.toml — there are no provider arguments. For each provider
whose credential is set, one index is built:
    - ollama_base_url set AND Ollama reachable -> {domain}_local_index    (Ollama)
    - openai_api_key set                       -> {domain}_hosted_index   (OpenAI)
    - bedrock_api_key set                      -> {domain}_bedrock_index  (Bedrock)

Different embedding models can't share a single index — they produce different
vector spaces even at the same dimension count, so similarity search across them
silently returns wrong results. Building ONE index per configured provider lets
the app switch between providers via the UI toggle without any extra setup — it
just queries whichever prebuilt index matches the active provider.

Each provider is built independently, so a runtime failure in one (e.g. Ollama
not running, or an invalid key) is reported but doesn't abort the others.
"""
import argparse
import sys
import os
from pathlib import Path
from typing import List

# Add parent directory to path to import from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from setup_env import setup_environment
from domain_manager import DomainManager
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from helpers.llm_utils import (
    bedrock_configured,
    get_domain_embedding_model,
    get_embedding_dimensions,
    get_embeddings,
    get_ollama_base_url,
    is_ollama_available,
    openai_api_key_configured,
)
from langchain_core.documents import Document
from helpers.pgvector_utils import create_pgvector_store, get_collection_name
from helpers.sql_utils import load_domain_relational_csvs
import getpass
import uuid
import pandas as pd

# All providers, in build order. Which ones are actually built is decided at
# run time from the credentials present in secrets.toml (see _configured_providers).
_ALL_PROVIDERS = ("local", "hosted", "bedrock")

# Domains whose docs are a structured qa.csv (embedded as FAQ Q&A) plus
# relational CSVs loaded into SQL. Value: (FAQ title, question label, answer label).
_QA_DOMAINS = {
    "bank": ("Online Bank FAQ", "Question", "Answer"),
    "healthcare": ("Healthcare FAQ", "Medication", "Information"),
    "restaurant": ("Restaurant FAQ", "Question", "Answer"),
    "insurance": ("Insurance FAQ", "Question", "Answer"),
}


def _cli_name(provider: str) -> str:
    """Map internal provider id to the CLI-facing backend name."""
    return {"hosted": "openai", "bedrock": "bedrock"}.get(provider, "ollama")


def _not_configured_reason(provider: str) -> str:
    """Human-readable reason a provider's index won't be built."""
    if provider == "local":
        if not os.environ.get("OLLAMA_BASE_URL", "").strip():
            return "ollama_base_url not set in .streamlit/secrets.toml"
        # base_url is set but the server didn't respond.
        return f"Ollama not reachable at {get_ollama_base_url()} (is `ollama serve` running?)"
    return {
        "hosted": "openai_api_key not set in .streamlit/secrets.toml (missing or placeholder)",
        "bedrock": "bedrock_api_key not set in .streamlit/secrets.toml",
    }.get(provider, "not configured")


def _configured_providers() -> List[str]:
    """Return the providers to build for, based on credentials in secrets.toml.

    setup_environment() must have been called first so the secrets are loaded
    into the environment. A provider is built when its credential is present:
      - local:   ollama_base_url set AND the Ollama server is reachable
      - hosted:  openai_api_key set (and not a placeholder)
      - bedrock: bedrock_api_key set
    """
    configured = {
        "local": bool(os.environ.get("OLLAMA_BASE_URL", "").strip()) and is_ollama_available(),
        "hosted": openai_api_key_configured(),
        "bedrock": bedrock_configured(),
    }
    return [p for p in _ALL_PROVIDERS if configured[p]]


def _build_qa_documents(domain_name: str, docs_dir: str) -> List[Document]:
    """Build FAQ documents from a domain's qa.csv (question/answer columns)."""
    title, q_label, a_label = _QA_DOMAINS[domain_name]
    df = pd.read_csv(os.path.join(docs_dir, "qa.csv"))
    documents: List[Document] = []
    for _, row in df.iterrows():
        question = str(row.get("question", "") or "").strip()
        answer = str(row.get("answer", "") or "")
        body = f"[FAQ] {title}. {q_label}: {question}. {a_label}: {answer}. "
        documents.append(
            Document(
                page_content=body,
                metadata={
                    "doc_family": domain_name,
                    "question": question,
                    "answer": answer,
                },
            )
        )
    return documents


def _load_and_split_generic(
    docs_dir: str, chunk_size: int, chunk_overlap: int
) -> List[Document]:
    """Load every file in docs_dir and split it into chunks (generic domains)."""
    non_csv_loader = DirectoryLoader(docs_dir, exclude=["**/*.csv"])
    non_csv_docs = non_csv_loader.load()
    print(f"✓ Loaded {len(non_csv_docs)} non-CSV documents")

    csv_loader = DirectoryLoader(docs_dir, glob="**/*.csv", loader_cls=CSVLoader)
    csv_docs = csv_loader.load()
    print(f"✓ Loaded {len(csv_docs)} CSV documents")

    if not non_csv_docs and not csv_docs:
        return []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    split_docs = text_splitter.split_documents(non_csv_docs)
    all_docs = split_docs + csv_docs
    print(f"✓ Total document chunks: {len(all_docs)}")
    return all_docs


def setup_vectordb_for_domain(domain_name: str):
    """
    Build one pgvector index per configured provider for a domain.

    Which providers are built is derived from the credentials in secrets.toml
    (see _configured_providers). The same documents are embedded once per
    provider into a separate collection ({domain}_local_index /
    {domain}_hosted_index / {domain}_bedrock_index), so the app can switch
    providers at query time with no extra setup.

    Args:
        domain_name: Name of the domain (e.g., 'finance')
    """
    # Load domain configuration and secrets.
    domain_manager = DomainManager()
    try:
        domain_config = domain_manager.load_domain_config(domain_name)
        print(f"✓ Loaded configuration for domain: {domain_config.description}")
    except ValueError as e:
        print(f"❌ Error loading domain '{domain_name}': {e}")
        print(f"Available domains: {', '.join(domain_manager.list_domains())}")
        return False

    setup_environment(domain_name, domain_config.config)

    # Decide which indexes to build from the credentials in secrets.toml.
    print("Detecting configured providers from secrets.toml...")
    available = _configured_providers()
    for provider in _ALL_PROVIDERS:
        if provider in available:
            print(
                f"  • {_cli_name(provider)}: configured -> will build "
                f"{get_collection_name(domain_name, provider)}"
            )
        else:
            print(f"  • {_cli_name(provider)}: skipped ({_not_configured_reason(provider)})")

    if not available:
        print(
            "❌ No provider credentials found in .streamlit/secrets.toml; nothing "
            "was built. Set ollama_base_url, openai_api_key, and/or bedrock_api_key, "
            "then re-run."
        )
        return False

    print(
        f"Setting up vector database for domain: {domain_name} "
        f"(building: {', '.join(_cli_name(p) for p in available)})"
    )

    rag_config = domain_config.config.get("rag", {})
    vectorstore_config = domain_config.config.get("vectorstore", {})
    chunk_size = rag_config.get("chunk_size", 1000)
    chunk_overlap = rag_config.get("chunk_overlap", 200)

    docs_dir = domain_config.docs_dir
    if not os.path.exists(docs_dir):
        print(f"❌ Docs directory not found: {docs_dir}")
        return False

    print(f"Loading documents from: {docs_dir}")

    # Build the documents ONCE, then embed them into each provider's index.
    load_relational = False
    if domain_name in _QA_DOMAINS:
        documents = _build_qa_documents(domain_name, docs_dir)
        load_relational = True
        print(f"✓ Built {len(documents)} FAQ documents from qa.csv")
    elif domain_name == "mgm_marketing":
        documents = []
        print("✓ mgm_marketing: skipping generic DirectoryLoader (custom ingestion)")
    else:
        documents = _load_and_split_generic(docs_dir, chunk_size, chunk_overlap)
        if not documents:
            print(f"⚠️  No documents found in {docs_dir}")
            return False
        print("\nDocument preview:")
        for i, doc in enumerate(documents[:3]):
            print(f"Doc {i+1}: {doc.page_content[:100]}...")
            print(f"Metadata: {doc.metadata}")
            print("-" * 50)

    if not os.environ.get("POSTGRES_PASSWORD"):
        os.environ["POSTGRES_PASSWORD"] = getpass.getpass("Enter PostgreSQL password: ")

    # Embed the documents into one collection per available provider. Each
    # provider is built independently so a runtime failure in one (e.g. Ollama
    # up but the embedding model not pulled, or an invalid OpenAI key) doesn't
    # abort the other — the working index still gets built.
    built = []
    failed = []
    for provider in available:
        model = get_domain_embedding_model(vectorstore_config, provider=provider)
        collection_name = get_collection_name(domain_name, provider)
        print(f"\n▶ Building {collection_name} with {_cli_name(provider)} embeddings (model: {model})")
        if provider == "local":
            print(f"   If the model is missing, run: ollama pull {model}")
        elif provider == "hosted":
            print(f"   Using OpenAI embeddings ({get_embedding_dimensions()} dimensions).")
        else:
            print("   Using Bedrock embeddings (native model dimensionality).")

        try:
            embeddings = get_embeddings(model, provider=provider)
            vector_store, collection_name = create_pgvector_store(
                embeddings,
                domain_name,
                provider,
                pre_delete_collection=True,
                collection_metadata={
                    "embedding_provider": provider,
                    "embedding_model": model,
                },
            )
            if documents:
                ids = [uuid.uuid4() for _ in documents]
                vector_store.add_documents(documents=documents, ids=ids)
            built.append((collection_name, provider, model, len(documents)))
        except Exception as exc:
            failed.append((provider, str(exc)))
            print(f"❌ Failed to build the {_cli_name(provider)} index: {exc}")

    if not built:
        print(f"\n❌ No index was built for {domain_name}. See errors above.")
        return False

    # Relational tables are provider-independent — load them once, only if at
    # least one index was built.
    if load_relational:
        print(f"\nLoading relational tables for {domain_name}...")
        load_domain_relational_csvs(docs_dir, domain_name)

    print(f"\n✅ Vector database ready for {domain_name}")
    for collection_name, provider, model, count in built:
        print(f"   • {collection_name}  ({_cli_name(provider)} / {model}) — {count} documents")
    for provider, err in failed:
        print(f"   ✗ {_cli_name(provider)} index NOT built: {err}")

    return True


def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(
        description="Set up vector database for a specific domain using PostgreSQL/pgvector"
    )
    parser.add_argument(
        "domain",
        help="Domain name (e.g., 'finance')"
    )
    parser.add_argument(
        "--list-domains",
        action="store_true",
        help="List available domains"
    )

    args = parser.parse_args()

    if args.list_domains:
        domain_manager = DomainManager()
        domains = domain_manager.list_domains()
        print("Available domains:")
        for domain in domains:
            print(f"  - {domain}")
        return

    success = setup_vectordb_for_domain(args.domain)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
