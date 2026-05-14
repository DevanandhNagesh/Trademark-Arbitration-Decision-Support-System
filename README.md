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

## Test Scenarios

Two test scenarios are provided in `tests/test_cases/`:

### Scenario 1 — NOT ARBITRABLE (Parle/Oreo type)
No contract between parties. Pure trademark infringement against a stranger.
- File: `tests/test_cases/scenario_1.json`
- Expected: **NOT ARBITRABLE** (routes to civil court)

### Scenario 2 — ARBITRABLE (Hero Electric/License type)
Distribution agreement with arbitration clause. Post-expiry unauthorized use.
- File: `tests/test_cases/scenario_2.json`
- Expected: **ARBITRABLE** (full DSS report with award framework)

To test, load scenario details manually via the web form at `http://localhost:8000`.

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
├── agents/                # Core logic agents
├── api/                   # FastAPI application
├── data/                  # Raw PDFs and intermediate text assets
├── frontend/              # Single-file UI
├── knowledge_base/        # ChromaDB persistence (local only)
├── output/                # Generated reports (local only)
├── scripts/               # Knowledge base build scripts
├── tests/                 # Test scenarios
├── config.py              # Configuration and landmark registry
├── requirements.txt
└── .env.template
```

## API Endpoints

- `GET /find-lawyers?city=Mumbai&dispute_type=trademark`
- `GET /find-lawyers-by-location?lat=...&lng=...&dispute_type=trademark`

## Disclaimer

This project is a decision support tool and does not provide legal advice. Arbitrators and practitioners must exercise independent judgment and verify all sources.

## Attribution

Powered by IndiaKanoon.
