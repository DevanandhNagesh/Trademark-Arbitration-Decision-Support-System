"""Extract text from all PDFs in data/raw_pdfs/ using PyMuPDF."""

import os
import fitz  # PyMuPDF

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "data", "raw_pdfs")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "extracted_text")


def extract_all_pdfs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("No PDF files found in", INPUT_DIR)
        return

    print(f"Found {len(pdf_files)} PDF files. Extracting...\n")

    for pdf_file in sorted(pdf_files):
        pdf_path = os.path.join(INPUT_DIR, pdf_file)
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            text_parts = []
            for page_num in range(page_count):
                page = doc[page_num]
                page_text = page.get_text("text")
                text_parts.append(f"\n--- PAGE {page_num + 1} ---\n")
                text_parts.append(page_text)
            doc.close()

            full_text = "".join(text_parts)
            txt_filename = os.path.splitext(pdf_file)[0] + ".txt"
            txt_path = os.path.join(OUTPUT_DIR, txt_filename)

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            print(f"  {pdf_file} → {txt_filename} ({page_count} pages)")

        except Exception as e:
            print(f"  ERROR processing {pdf_file}: {e}")

    print(f"\nExtraction complete. Output saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    extract_all_pdfs()
