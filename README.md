# Trademark Arbitration Decision Support System (Trademark DSS)

A decision support system for arbitrators handling trademark disputes in India. The system combines deterministic legal logic, retrieval over landmark Indian cases, and LLM-based drafting to produce structured Word reports for independent decision-making.

Includes a nearby trademark lawyer finder with city search or browser-based location lookup.

Powered by IndiaKanoon.

## Features

- Deterministic arbitrability analysis based on Indian law
- Landmark case retrieval with fact mapping (RAG)
- Structured DOCX report generation with six legal sections
- Adversarial law-first analysis module
- Lawyer finder with city or geolocation search
- Multi-LLM fallback (Gemini primary, Groq or local backup)

## Architecture

1. Input intake (case facts, agreement details, arbitration clause)
2. Arbitrability decision engine (statute-first logic)
3. Landmark retrieval (ChromaDB + sentence-transformer embeddings)
4. LLM drafting (structured analysis and report sections)
5. Report assembly (DOCX)
6. Lawyer finder (Google Places API with fallback link)

## Tech Stack

- **Backend:** FastAPI (Python 3.11+; tested on 3.14)
- **LLM:** Google Gemini 2.5 Flash (primary) / Groq llama-3.3-70b-versatile (backup) / LM Studio deepseek-r1-7b (local backup)
- **Vector DB:** ChromaDB (persistent, local)
- **Embeddings:** sentence-transformers all-MiniLM-L6-v2
- **Document Generation:** python-docx
- **PDF Parsing:** PyMuPDF (fitz)
- **Frontend:** Pure HTML + CSS + JavaScript (single file)
- **Places API:** Google Places API (lawyer finder)
- **Case Database:** IndiaKanoon (Powered by IndiaKanoon)

## Screenshots

- App home (placeholder)
- Arbitrability summary (placeholder)
- Report preview (placeholder)
- Lawyer finder results (placeholder)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the template and add your API keys:

```bash
copy .env.template .env
```

Edit `.env` and set values:
```
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_PLACES_API_KEY=your_google_places_key_here
INDIAKANOON_API_KEY=your_india_kanoon_key_here
```

Get your Gemini API key from [https://aistudio.google.com](https://aistudio.google.com).
For Places API, enable it in Google Cloud Console and create an API key.
For IndiaKanoon, obtain a key from their official portal and comply with their terms.

### 3. Build Knowledge Base (Run Once)

Run these scripts in order from the project root:

```bash
python scripts/extract_pdf.py
python scripts/clean_text.py
python scripts/chunk_documents.py
python scripts/load_chroma.py
```

This will:
1. Extract text from PDFs in `data/raw_pdfs/`
2. Clean the extracted text
3. Chunk the text into 800-word segments with 100-word overlap
4. Load chunks into ChromaDB with sentence-transformer embeddings

### 4. Run the Application

```bash
cd api
uvicorn main:app --reload --port 8000
```

### 5. Open in Browser

Navigate to [http://localhost:8000](http://localhost:8000)

## LLM Backup (Optional)

If the Gemini API is unavailable or rate-limited, the system falls back to Groq or a local LM Studio server.

### Groq fallback

1. Create a Groq key at [https://console.groq.com](https://console.groq.com)
2. Add it to `.env`:
```
GROQ_API_KEY=your_groq_key_here
```

### LM Studio fallback

1. Install [LM Studio](https://lmstudio.ai/)
2. Load the `deepseek-r1-7b` model
3. Start the local server (default: `http://localhost:1234/v1`)

## Test Scenarios & Configuration Modes

Two primary test scenarios are provided in `tests/test_cases/` (with 28 total scenario JSON cases available for batch testing):

- **Scenario 1 — NOT ARBITRABLE (Parle/Oreo type):** No contract. Pure trademark infringement against a stranger.
  - File: `tests/test_cases/scenario_1.json`
  - Expected: **NOT ARBITRABLE** (routes to civil court)
- **Scenario 2 — ARBITRABLE (Hero Electric/License type):** Distribution agreement with arbitration clause.
  - File: `tests/test_cases/scenario_2.json`
  - Expected: **ARBITRABLE** (full DSS report generated)

To test a scenario, load its details manually via the web form at `http://localhost:8000`.

---

### Running in Different Modes (API Toggles)

You can toggle or disable external API dependencies (iKanoon, Gemini LLM, Google Places) to run in online, local-only, or budget-friendly modes.

#### 1. Running with or without iKanoon (Online vs. Offline Retrieval)
* **Online Mode (Default):** Requires `INDIAKANOON_API_KEY` set in `.env`. Fetches live real-time judgments from the Indian courts.
* **Offline Mode (Rs. 0 Cost):** Unset your key to force the retrieval agent to bypass live calls and search the local vector database (ChromaDB) and static fallbacks.
  * **Windows Command Prompt:**
    ```bash
    set INDIAKANOON_API_KEY=&& cd api && uvicorn main:app --reload --port 8000
    ```
  * **Windows PowerShell:**
    ```powershell
    $env:INDIAKANOON_API_KEY=""; cd api; uvicorn main:app --reload --port 8000
    ```

#### 2. Running with or without Gemini (LLM Analysis)
* **With Gemini (Default):** Set `GEMINI_API_KEY` in `.env` to enable full award framework drafting and adversarial analysis generation.
* **Without Gemini (Rule Engine + Retrieval Only):** Run tests or evaluations in fast rule-only mode by passing the `--skip-llm` flag to the evaluation harness.

#### 3. Bypassing Google Places API (Lawyer Finder API Cost Control)
If you want to test the Lawyer Finder without incurring Google Places API usage costs or if you do not have a key:
* Simply leave `GOOGLE_PLACES_API_KEY` empty or unset in your `.env` file.
* The backend will automatically detect this and fallback gracefully to returning a direct web search link for trademark advocates in the target city (producing Rs. 0 cost).

---

## Quantitative Evaluation Harness

The system includes a batch evaluation harness to compare classification rules, SVM prediction models, LLM classification capabilities, and case retrieval accuracy across all 28 test cases.

To run the harness, use:

```bash
# Run Part A & Part B (Fast Mode, un-metered, skipping LLM classifications)
python evaluation/evaluation_harness.py --skip-llm

# Run full evaluation (Part A classification + Part B retrieval under both Online/Offline modes)
python evaluation/evaluation_harness.py
```

* **Output Markdown Report:** `evaluation/evaluation_report.md` (paper-ready tables containing Precision, Recall, F1, and tier breakdowns)
* **Output JSON File:** `evaluation/evaluation_results.json` (raw metric payload)

## Commands Reference

### 1. Launching the Application
```bash
# Start FastAPI backend (serves API and frontend on port 8000)
uvicorn api.main:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

### 2. Running Tests
```bash
# Run full pytest suite
python -m pytest tests -v
```

### 3. Running Data Pipeline & Model Training
```bash
# Step 1: Extract text from raw legal PDFs (data/raw_pdfs/ -> data/extracted_text/)
python scripts/extract_pdf.py

# Step 2: Clean and normalize extracted text (data/extracted_text/ -> data/cleaned_text/)
python scripts/clean_text.py

# Step 3: Chunk cleaned text with sliding window (data/cleaned_text/ -> data/chunks/)
python scripts/chunk_documents.py

# Step 4: Embed chunks with all-MiniLM-L6-v2 and index into ChromaDB
python scripts/load_chroma.py

# Step 5: Compile training data from test scenarios (-> data/training/dispute_training_data.json)
python scripts/prepare_training_data.py

# Step 6: Train and evaluate dispute classifier (models/dispute_classifier.joblib)
python agents/dispute_classifier.py --data data/training/dispute_training_data.json --save models/dispute_classifier.joblib
```

## Output

Generated Word documents are saved to `output/` with timestamped filenames:
```
DSS_Report_{PartyA}_v_{PartyB}_{YYYYMMDD_HHMMSS}.docx
```

## Report Structure

Each report contains 6 sections:
1. **Arbitrability Determination** — statute-first headings + Booz Allen / Vidya Drolia tests
2. **Landmark Case Analysis Matrix** — top 3 similar cases with fact mapping
3. **Issues for Determination** — 4 "Whether..." legal issues
4. **Applicable Statutory Provisions and Judicial Interpretations** — statute text + case interpretation + application
5. **Award Framework** — jurisdiction, findings, relief, operative portion, signature block
6. **Adversarial Legal Analysis** — law for claimant, law against claimant, options if law is against, overall position

## Project Structure

```
trademark-arbitration-dss/
├── agents/                # Neuro-symbolic decision, classification, retrieval, drafting & reporting agents
├── api/                   # FastAPI application routes, middleware, and server endpoints
├── data/                  # Source legal PDF repository, extracted/cleaned texts, chunks, and training data
├── docs/                  # Academic documents, IEEE paper drafts, review reports, and UI audit assets
│   ├── assets/            # Documentation screenshots and UI audit captures
│   ├── paper/             # IEEE conference paper drafts and working texts
│   └── review_1/          # Review 1 submission report (.docx, .md) and document generator
├── evaluation/            # Quantitative evaluation harness, retrieval diagnostics, and benchmark reports
├── frontend/              # HTML/CSS/JavaScript single-page arbitrator dashboard and auth interfaces
├── knowledge_base/        # Persistent ChromaDB vector database index files
├── logs/                  # Application event logs and classification disagreement traces
├── models/                # Serialized machine learning models (TF-IDF + LinearSVC pipeline)
├── output/                # Generated Word (.docx) preliminary arbitral decision reports
├── scratch/               # Local experiments, scratch extracts, and temporary developer scripts
├── scripts/               # Legal dataset ingestion, text cleaning, chunking, and embedding pipelines
│   └── dev/               # Development testing scripts (Playwright UI verification, screenshot audits)
├── tests/                 # Pytest test suite for arbitrability rules, auth, citations, and scenarios
│   └── test_cases/        # 28 Canonical trademark dispute ground-truth scenarios
├── .env.example           # Template for required environment variables and API keys
├── auth.py                # JWT authentication, role authorization, and password security
├── config.py              # System constants, threshold settings, and landmark case registry
├── db.py                  # SQLite database engine, session management, and ORM models
├── logging_config.py      # Structured application logging configuration
├── pydantic_v1_compat.py  # Backward-compatibility layer for Pydantic v1/v2 interoperability
└── requirements.txt       # Project Python package dependencies
```

## API Endpoints

- `GET /find-lawyers?city=Mumbai&dispute_type=trademark`
- `GET /find-lawyers-by-location?lat=...&lng=...&dispute_type=trademark`

## Disclaimer

This project is a decision support tool and does not provide legal advice. Arbitrators and practitioners must exercise independent judgment and verify all sources.

## Attribution

Powered by IndiaKanoon.
