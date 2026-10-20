"""
diagnose_retrieval_anomaly.py
Diagnostic script to investigate why "hms_mauritz" appears in almost all retrieval results.
"""

import os
import sys
import json
import random
import glob
import math

from pathlib import Path

# Add workspace root to python path to import config
_REPO_ROOT = str(Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pydantic_v1_compat  # Must be before chromadb
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config import CHROMA_PATH, CHROMA_COLLECTION, EMBEDDING_MODEL, LANDMARK_CASES

def cosine_similarity(v1, v2):
    try:
        import numpy as np
        v1 = np.array(v1)
        v2 = np.array(v2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    except ImportError:
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

def calculate_median(values):
    sorted_val = sorted(values)
    n = len(sorted_val)
    if n == 0:
        return 0
    if n % 2 == 1:
        return sorted_val[n // 2]
    else:
        return (sorted_val[n // 2 - 1] + sorted_val[n // 2]) / 2.0

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    print("=" * 80)
    print("CHROMADB RETRIEVAL ANOMALY DIAGNOSTIC RUN")
    print("=" * 80)

    # Initialize ChromaDB client
    if not os.path.exists(CHROMA_PATH):
        print(f"Error: ChromaDB path does not exist: {CHROMA_PATH}")
        sys.exit(1)

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    collection = client.get_collection(name=CHROMA_COLLECTION, embedding_function=embedding_fn)

    # 1. Fetch ALL chunks from DB to compute baseline statistics
    print("\nRetrieving all chunks from database...")
    all_db = collection.get(include=["embeddings", "metadatas", "documents"])
    
    total_chunks = len(all_db["ids"])
    print(f"Total chunks in ChromaDB: {total_chunks}")
    
    if total_chunks == 0:
        print("Error: No chunks found in the database.")
        sys.exit(1)

    # Group chunks by case_key and get word count stats
    chunks_by_case = {}
    word_counts = []
    
    for i in range(total_chunks):
        meta = all_db["metadatas"][i]
        case_key = meta.get("case_key", "unknown")
        word_count = meta.get("word_count", 0)
        
        # In case word_count is not in metadata or is 0, estimate it
        if not word_count and all_db["documents"][i]:
            word_count = len(all_db["documents"][i].split())
            
        word_counts.append(word_count)
        
        if case_key not in chunks_by_case:
            chunks_by_case[case_key] = []
        chunks_by_case[case_key].append({
            "id": all_db["ids"][i],
            "document": all_db["documents"][i],
            "metadata": meta,
            "embedding": all_db["embeddings"][i] if all_db["embeddings"] is not None else None,
            "word_count": word_count
        })

    # Compute database-wide chunk length statistics
    median_length = calculate_median(word_counts)
    mean_length = sum(word_counts) / len(word_counts)
    min_length = min(word_counts)
    max_length = max(word_counts)
    
    print("\n--- Database Chunk Length Statistics ---")
    print(f"Mean Word Count   : {mean_length:.2f}")
    print(f"Median Word Count : {median_length:.2f}")
    print(f"Min Word Count    : {min_length}")
    print(f"Max Word Count    : {max_length}")
    
    anomaly_low_threshold = 50
    anomaly_high_threshold = 2 * median_length
    print(f"Anomaly thresholds: Under {anomaly_low_threshold} words OR Over {anomaly_high_threshold:.2f} words (2x median)")

    # 2. Print total chunk count per case across the entire DB as a sorted table
    print("\n--- Chunk Count Per Case ---")
    sorted_cases = sorted(chunks_by_case.items(), key=lambda x: len(x[1]), reverse=True)
    print(f"{'Case Key / ID':<25} | {'Chunk Count':<12}")
    print("-" * 42)
    for case_key, chunks in sorted_cases:
        print(f"{case_key:<25} | {len(chunks):<12}")

    # 3. Print details for target cases and comparison baseline cases
    target_cases = ["hms_mauritz", "marico_parachute", "golden_tobie", "eros_telemax", "amritdhara"]
    
    print("\n" + "=" * 80)
    print("DETAILED CHUNK ANALYSIS FOR CASES")
    print("=" * 80)
    
    for case_key in target_cases:
        print(f"\n>>> CASE: {case_key} <<<")
        if case_key not in chunks_by_case:
            print(f"Warning: No chunks found for case_key '{case_key}'")
            continue
            
        case_chunks = chunks_by_case[case_key]
        print(f"Number of Chunks: {len(case_chunks)}")
        
        for idx, chunk in enumerate(case_chunks):
            w_count = chunk["word_count"]
            is_anomaly = w_count < anomaly_low_threshold or w_count > anomaly_high_threshold
            anomaly_flag = " [!] ANOMALY" if is_anomaly else ""
            print(f"\n  Chunk #{idx+1} (ID: {chunk['id']}, Word Count: {w_count}){anomaly_flag}")
            print(f"  Metadata: {chunk['metadata']}")
            print("-" * 40)
            # Print raw text with indented format
            text_indented = "\n".join("      " + line for line in chunk["document"].splitlines())
            print(text_indented)
            print("-" * 40)

    # 4. Compute cosine similarities
    print("\n" + "=" * 80)
    print("EMBEDDING SIMILARITY ANALYSIS")
    print("=" * 80)

    # (a) Mean embedding of all other chunks in the DB (excluding target cases to be clean)
    excluded_targets = {"hms_mauritz", "marico_parachute"}
    other_embeddings = []
    for c_key, chunks in chunks_by_case.items():
        if c_key in excluded_targets:
            continue
        for chunk in chunks:
            if chunk["embedding"] is not None:
                other_embeddings.append(chunk["embedding"])
                
    if not other_embeddings:
        print("Error: No other chunk embeddings found in database.")
        sys.exit(1)
        
    import numpy as np
    mean_other_embedding = np.mean(other_embeddings, axis=0)

    # (b) Load 10 random scenario dispute_description queries
    scenarios_pattern = os.path.join(_REPO_ROOT, "tests", "test_cases", "scenario_*.json")
    scenario_files = glob.glob(scenarios_pattern)
    
    if not scenario_files:
        print("Warning: No scenario files found in tests/test_cases/")
        scenario_queries = []
    else:
        # Load all dispute descriptions
        all_scenarios = []
        for s_file in scenario_files:
            try:
                with open(s_file, "r", encoding="utf-8") as f:
                    scen_data = json.load(f)
                    if "dispute_description" in scen_data:
                        all_scenarios.append({
                            "name": os.path.basename(s_file),
                            "description": scen_data["dispute_description"]
                        })
            except Exception as e:
                print(f"Error loading scenario {s_file}: {e}")
                
        # Randomly sample 10 scenarios
        random.seed(42)  # For reproducibility
        sampled_scenarios = random.sample(all_scenarios, min(10, len(all_scenarios)))
        print(f"\nSampled {len(sampled_scenarios)} scenario dispute descriptions:")
        for idx, s in enumerate(sampled_scenarios):
            print(f"  [{idx+1}] {s['name']}: {s['description'][:80]}...")

        # Compute embeddings for these scenario queries
        query_texts = [s["description"] for s in sampled_scenarios]
        query_embeddings = embedding_fn(query_texts)

    # Now calculate similarities for each target analysis case
    target_analysis_cases = ["hms_mauritz", "marico_parachute"]
    for target in target_analysis_cases:
        print("\n" + "-" * 80)
        print(f"SIMILARITY ANALYSIS FOR {target.upper()}")
        print("-" * 80)
        
        if target not in chunks_by_case:
            print(f"Warning: '{target}' chunks not found in DB.")
            continue
            
        t_chunks = chunks_by_case[target]
        t_embeddings = [c["embedding"] for c in t_chunks if c["embedding"] is not None]
        
        if not t_embeddings:
            print(f"Warning: '{target}' chunks do not have embeddings.")
            continue
            
        print(f"\n--- Cosine Similarity: {target} chunks vs Mean of Other DB Chunks ---")
        for idx, t_emb in enumerate(t_embeddings):
            sim_to_mean = cosine_similarity(t_emb, mean_other_embedding)
            print(f"  {target} Chunk #{idx+1} (ID: {t_chunks[idx]['id']}) vs Mean Other DB Chunks: {sim_to_mean:.4f}")

        if scenario_files and sampled_scenarios:
            print(f"\n--- Cosine Similarity: {target} chunks vs Scenario Dispute Queries ---")
            for t_idx, t_emb in enumerate(t_embeddings):
                print(f"\n{target} Chunk #{t_idx+1} (ID: {t_chunks[t_idx]['id']}):")
                similarities = []
                for q_idx, q_emb in enumerate(query_embeddings):
                    sim = cosine_similarity(t_emb, q_emb)
                    similarities.append(sim)
                    print(f"  vs {sampled_scenarios[q_idx]['name']:<18}: {sim:.4f}")
                print(f"  Mean similarity across queries: {sum(similarities)/len(similarities):.4f}")
                print(f"  Min similarity across queries : {min(similarities):.4f}")
                print(f"  Max similarity across queries : {max(similarities):.4f}")

    # Also compute and print mean cosine similarity of other baseline cases against scenarios for comparison
    print("\n" + "-" * 80)
    print("BASELINE COMPARISON: MEAN SCENARIO SIMILARITY")
    print("-" * 80)
    for case_key in ["golden_tobie", "eros_telemax", "amritdhara"]:
        if case_key in chunks_by_case:
            baseline_chunks = chunks_by_case[case_key]
            baseline_embs = [c["embedding"] for c in baseline_chunks if c["embedding"] is not None]
            if baseline_embs:
                mean_sims = []
                for b_emb in baseline_embs:
                    sims = [cosine_similarity(b_emb, q_emb) for q_emb in query_embeddings]
                    mean_sims.append(sum(sims)/len(sims))
                overall_mean = sum(mean_sims)/len(mean_sims)
                print(f"  {case_key:<15} (mean across its {len(baseline_embs)} chunks): {overall_mean:.4f}")

    print("\n" + "=" * 80)
    print("DIAGNOSTIC RUN COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    main()
