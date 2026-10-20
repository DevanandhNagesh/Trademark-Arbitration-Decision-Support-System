import os
import sys
from pathlib import Path
_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
import pydantic_v1_compat

import chromadb
print("ChromaDB imported successfully!")
chroma_path = os.path.join(_REPO_ROOT, "knowledge_base", "chroma_db")
client = chromadb.PersistentClient(path=chroma_path)
print(f"ChromaDB client created: {client}")
