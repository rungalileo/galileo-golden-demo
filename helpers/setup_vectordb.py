"""
Dynamic Vector Database Setup Script
Supports any domain by reading configuration from domain config files.
Uses PostgreSQL with pgvector for vector storage.

Usage:
    python setup_vectordb.py <domain_name> [ollama|openai|both]

Example:
    python setup_vectordb.py finance          # builds BOTH indexes (default)
    python setup_vectordb.py finance both
    python setup_vectordb.py finance ollama   # only the Ollama index
    python setup_vectordb.py finance openai   # only the OpenAI index

Ollama and OpenAI embeddings can't share a single index — different embedding
models produce different vector spaces even at the same dimension count, so
similarity search across them silently returns wrong results. Instead this
script builds ONE index per provider:
    {domain}_local_index   (Ollama)
    {domain}_hosted_index  (OpenAI)
so the app can switch between providers via the UI toggle without any extra
setup — it just queries whichever prebuilt index matches the active provider.

By default (no argument, or `both`) it auto-detects what's available at run
time and builds accordingly:
    - Ollama running AND a real OPENAI_API_KEY set -> builds BOTH indexes
    - only Ollama available                        -> builds the Ollama index
    - only OpenAI available                        -> builds the OpenAI index
    - neither available                            -> builds nothing, errors
Unavailable backends are skipped with a warning rather than failing the whole
run. Requesting a single backend explicitly (`ollama`/`openai`) still fails
if that one backend isn't available.
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
    embedding_backend_available,
    get_domain_embedding_model,
    get_embedding_dimensions,
    get_embeddings,
    get_ollama_base_url,
)
from langchain_core.documents import Document
from helpers.pgvector_utils import create_pgvector_store, get_collection_name
from helpers.sql_utils import load_domain_relational_csvs
import getpass
import uuid
import pandas as pd

# CLI-facing names -> the list of internal providers to build for.
_CLI_TO_PROVIDERS = {
    "both": ["local", "hosted"],
    "ollama": ["local"],
    "local": ["local"],
    "openai": ["hosted"],
    "hosted": ["hosted"],
}

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
    return "openai" if provider == "hosted" else "ollama"


def _backend_unavailable_reason(provider: str) -> str:
    """Human-readable reason a backend can't be used for index building."""
    if provider == "local":
        return f"Ollama not reachable at {get_ollama_base_url()}"
    return "OPENAI_API_KEY not configured in .streamlit/secrets.toml (missing or placeholder)"


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


def setup_vectordb_for_domain(domain_name: str, providers: List[str]):
    """
    Build one pgvector index per requested provider for a domain.

    The same documents are embedded once per provider into a separate
    collection ({domain}_local_index / {domain}_hosted_index), so the app can
    switch providers at query time with no extra setup.

    Args:
        domain_name: Name of the domain (e.g., 'finance')
        providers: Internal provider ids to build for — any of {'local','hosted'}.
    """
    invalid = [p for p in providers if p not in ("local", "hosted")]
    if invalid:
        print(f"❌ Invalid provider(s): {invalid}. Use 'ollama', 'openai', or 'both'.")
        return False

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

    # Detect which embedding backends are actually available right now, and
    # build indexes only for those. With the default 'both', this means:
    # both available -> both indexes; only one available -> just that one.
    print("Detecting available embedding backends...")
    ollama_ok = embedding_backend_available("local")
    openai_ok = embedding_backend_available("hosted")
    print(f"  • Ollama (local):  {'available' if ollama_ok else 'not available'}")
    print(f"  • OpenAI (hosted): {'available' if openai_ok else 'not available'}")

    explicit_single = len(providers) == 1
    available: List[str] = []
    for provider in providers:
        if embedding_backend_available(provider):
            available.append(provider)
        else:
            reason = _backend_unavailable_reason(provider)
            if explicit_single:
                # User explicitly asked for exactly this backend — respect it.
                print(f"❌ Cannot build the {_cli_name(provider)} index: {reason}.")
                return False
            print(f"⚠️  Skipping {_cli_name(provider)} index: {reason}.")

    if not available:
        print(
            "❌ No embedding backend available; nothing was built. Start Ollama "
            "or set a real openai_api_key in .streamlit/secrets.toml, then re-run."
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
        else:
            print(f"   Using OpenAI embeddings ({get_embedding_dimensions()} dimensions).")

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
        "provider",
        nargs="?",
        choices=sorted(_CLI_TO_PROVIDERS),
        default="both",
        help=(
            "Which index(es) to build: 'both' (default), 'ollama' (local), or "
            "'openai' (hosted). Unavailable backends are skipped with a warning "
            "when building 'both'."
        ),
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

    providers = _CLI_TO_PROVIDERS[args.provider]
    success = setup_vectordb_for_domain(args.domain, providers)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
