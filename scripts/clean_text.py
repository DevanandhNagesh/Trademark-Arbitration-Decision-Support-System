"""Clean extracted text files: remove noise, fix formatting."""

import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "data", "extracted_text")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "cleaned_text")


def clean_text(text: str) -> str:
    # Remove page markers like --- PAGE 1 ---
    text = re.sub(r"\n?--- PAGE \d+ ---\n?", "\n", text)

    # Remove form feed characters
    text = text.replace("\x0c", "")

    # Remove standalone page numbers (line with just a number)
    text = re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)

    # Remove repeated court headers (e.g., "SUPREME COURT OF INDIA" appearing on every page)
    text = re.sub(
        r"(?:SUPREME COURT OF INDIA|HIGH COURT OF [\w\s]+|INDIAN LAW REPORTS)\s*\n",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Fix hyphenated line breaks (word- \n continuation)
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

    # Collapse excessive blank lines (max 2 consecutive)
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # Strip leading/trailing whitespace from each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Strip leading/trailing whitespace from entire text
    text = text.strip()

    return text


def clean_all_files():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    txt_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")]

    if not txt_files:
        print("No text files found in", INPUT_DIR)
        return

    print(f"Found {len(txt_files)} text files. Cleaning...\n")

    for txt_file in sorted(txt_files):
        input_path = os.path.join(INPUT_DIR, txt_file)
        output_path = os.path.join(OUTPUT_DIR, txt_file)

        with open(input_path, "r", encoding="utf-8") as f:
            original_text = f.read()

        cleaned = clean_text(original_text)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned)

        original_size = len(original_text)
        cleaned_size = len(cleaned)
        reduction = (
            ((original_size - cleaned_size) / original_size * 100)
            if original_size > 0
            else 0
        )
        print(
            f"  {txt_file}: {original_size:,} → {cleaned_size:,} chars "
            f"({reduction:.1f}% reduction)"
        )

    print(f"\nCleaning complete. Output saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    clean_all_files()
