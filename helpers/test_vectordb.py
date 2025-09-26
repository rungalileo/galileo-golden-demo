import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from setup_env import setup_environment
setup_environment()

# from dotenv import load_dotenv
# load_dotenv()

import getpass
import os

if not os.environ.get("OPENAI_API_KEY"):
  os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter API key for OpenAI: ")

from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
from langchain_chroma import Chroma

vector_store = Chroma(
    collection_name="finance_collection",
    embedding_function=embeddings,
    persist_directory="/Users/michaelbranconier/galileo/galileo-demo-official/domains/finance/chroma_db",
)

results = vector_store.similarity_search(
    "Tell me about ebay", # paste 
    k=2,
)
print(results)
for res in results:
    print(f"* {res.page_content} [{res.metadata}]")