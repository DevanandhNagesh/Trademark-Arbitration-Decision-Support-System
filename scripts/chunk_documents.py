"""Chunk cleaned text files for vector DB ingestion."""

import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "data", "cleaned_text")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "chunks")

# Filename keyword → case_key mapping
FILENAME_TO_CASE_KEY = {
    "booz": "booz_allen",
    "vidya": "vidya_drolia",
    "hero": "hero_electric",
    "golden": "golden_tobie",
    "parle": "parle_products",
    "coca": "coca_cola_bisleri",
    "toyota": "toyota_prius",
    "amritdhara": "amritdhara",
    "cadila": "cadila",
    "dongre": "dongre_whirlpool",
    "eros": "eros_telemax",
    "mangayarkarasi": "mangayarkarasi_2025",
    "rohan": "rohan_builders",
    "trademark": "trade_marks_act",
    "arbitration": "arbitration_act",
    "contract": "contract_act",
    "compendium": "iiprd_compendium",
}

# case_key → doc_type mapping
DOC_TYPE_MAP = {
    "booz_allen": "judgment",
    "vidya_drolia": "judgment",
    "hero_electric": "judgment",
    "golden_tobie": "judgment",
    "parle_products": "judgment",
    "coca_cola_bisleri": "judgment",
    "toyota_prius": "judgment",
    "amritdhara": "judgment",
    "cadila": "judgment",
    "dongre_whirlpool": "judgment",
    "eros_telemax": "judgment",
    "mangayarkarasi_2025": "judgment",
    "rohan_builders": "judgment",
    "trade_marks_act": "statute",
    "arbitration_act": "statute",
    "contract_act": "statute",
    "iiprd_compendium": "compendium",
}

MAX_WORDS = 800
OVERLAP_WORDS = 100


def get_case_key(filename: str) -> str:
    fname_lower = filename.lower()
    for keyword, case_key in FILENAME_TO_CASE_KEY.items():
        if keyword in fname_lower:
            return case_key
    return "unknown"


def split_into_sentences(text: str) -> list:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(text: str, max_words: int = MAX_WORDS, overlap_words: int = OVERLAP_WORDS) -> list:
    sentences = split_into_sentences(text)
    chunks = []
    current_chunk_sentences = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())

        if current_word_count + sentence_words > max_words and current_chunk_sentences:
            chunk_text_str = " ".join(current_chunk_sentences)
            chunks.append(chunk_text_str)

            # Build overlap from the end of the current chunk
            overlap_sentences = []
            overlap_count = 0
            for s in reversed(current_chunk_sentences):
                s_words = len(s.split())
                if overlap_count + s_words > overlap_words:
                    break
                overlap_sentences.insert(0, s)
                overlap_count += s_words

            current_chunk_sentences = overlap_sentences
            current_word_count = overlap_count

        current_chunk_sentences.append(sentence)
        current_word_count += sentence_words

    # Add final chunk
    if current_chunk_sentences:
        chunk_text_str = " ".join(current_chunk_sentences)
        chunks.append(chunk_text_str)

    return chunks


def chunk_all_files():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    txt_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")]

    if not txt_files:
        print("No cleaned text files found in", INPUT_DIR)
        return

    print(f"Found {len(txt_files)} cleaned text files. Chunking...\n")

    all_chunks = []
    chunk_id_counter = 0

    for txt_file in sorted(txt_files):
        input_path = os.path.join(INPUT_DIR, txt_file)
        case_key = get_case_key(txt_file)
        doc_type = DOC_TYPE_MAP.get(case_key, "unknown")

        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_text(text)
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks):
            chunk_id_counter += 1
            chunk_entry = {
                "id": f"chunk_{chunk_id_counter:04d}",
                "text": chunk,
                "case_key": case_key,
                "doc_type": doc_type,
                "filename": txt_file,
                "chunk_index": i,
                "total_chunks": total_chunks,
                "word_count": len(chunk.split()),
            }
            all_chunks.append(chunk_entry)

        print(f"  {txt_file} → {total_chunks} chunks (case_key: {case_key})")

    output_path = os.path.join(OUTPUT_DIR, "all_chunks.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"\nTotal chunks generated: {len(all_chunks)}")
    print(f"Output saved to {output_path}")


if __name__ == "__main__":
    chunk_all_files()
