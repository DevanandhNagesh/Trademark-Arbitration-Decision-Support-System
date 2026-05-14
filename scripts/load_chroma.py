"""Load chunks into ChromaDB with sentence-transformer embeddings."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pydantic_v1_compat  # noqa: F401 — must be before chromadb
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config import CHROMA_PATH, CHROMA_COLLECTION, EMBEDDING_MODEL

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_FILE = os.path.join(BASE_DIR, "data", "chunks", "all_chunks.json")
BATCH_SIZE = 100


def load_chunks_to_chroma():
    # Load chunks
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        all_chunks = json.load(f)

    print(f"Loaded {len(all_chunks)} chunks from {CHUNKS_FILE}\n")

    # Initialize ChromaDB
    os.makedirs(CHROMA_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    # Delete existing collection if it exists
    try:
        client.delete_collection(name=CHROMA_COLLECTION)
        print(f"Deleted existing collection '{CHROMA_COLLECTION}'")
    except Exception:
        pass

    # Create fresh collection
    collection = client.create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=embedding_fn,
        metadata={"description": "Trademark arbitration landmark cases and statutes"},
    )
    print(f"Created collection '{CHROMA_COLLECTION}'\n")

    # Load in batches
    total = len(all_chunks)
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        batch = all_chunks[start:end]

        ids = [chunk["id"] for chunk in batch]
        documents = [chunk["text"] for chunk in batch]
        metadatas = [
            {
                "case_key": chunk["case_key"],
                "doc_type": chunk["doc_type"],
                "filename": chunk["filename"],
                "chunk_index": chunk["chunk_index"],
                "total_chunks": chunk["total_chunks"],
                "word_count": chunk["word_count"],
            }
            for chunk in batch
        ]

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"  Loaded batch {start + 1}-{end} of {total}")

    print(f"\nAll {total} chunks loaded into ChromaDB at {CHROMA_PATH}")

    # Run test queries
    print("\n" + "=" * 60)
    print("RUNNING TEST QUERIES")
    print("=" * 60)

    test_queries = [
        "trademark dispute arising from contract between two parties",
        "deceptive similarity biscuit wrapper average consumer confusion",
        "right in rem right in personam arbitrability India Supreme Court",
        "trademark assignment assignor cannot reuse assigned mark",
    ]

    for query in test_queries:
        print(f"\nQuery: \"{query}\"")
        results = collection.query(query_texts=[query], n_results=2)

        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            distance = results["distances"][0][i]
            case_key = results["metadatas"][0][i]["case_key"]
            preview = results["documents"][0][i][:150].replace("\n", " ")
            print(f"  [{i + 1}] {chunk_id} (case: {case_key}, dist: {distance:.4f})")
            print(f"      {preview}...")

    print("\n✓ ChromaDB loaded and verified successfully.")


if __name__ == "__main__":
    load_chunks_to_chroma()
