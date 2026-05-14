import sys
sys.path.insert(0, '.')
import pydantic_v1_compat

import chromadb
print("ChromaDB imported successfully!")
client = chromadb.PersistentClient(path="knowledge_base/chroma_db")
print(f"ChromaDB client created: {client}")
