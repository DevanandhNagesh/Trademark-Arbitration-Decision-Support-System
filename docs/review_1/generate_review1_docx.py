"""
generate_review1_docx.py
Standalone NLP course deliverable script — scratch only.
Generates docs/Review_1_Report.docx using python-docx.
Does NOT import or modify any DSS production file.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

# ── Output path (docs/review_1 folder) ──────────────────────────
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Review_1_Report.docx")

# ── Colour palette ───────────────────────────────────────────────────
NAVY  = RGBColor(27,  58, 107)
WHITE = RGBColor(255, 255, 255)
GREY  = RGBColor(230, 235, 245)
BLACK = RGBColor(0,   0,   0)
RED   = RGBColor(192, 0,   0)

# ── Helpers ──────────────────────────────────────────────────────────

def _set_shading(cell, hex_colour: str):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_colour}" w:color="auto" w:val="clear"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def add_title(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = NAVY


def add_subtitle(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.font.size = Pt(11)
    run.font.color.rgb = NAVY
    run.italic = True


def add_section(doc, number, heading):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    run = p.add_run(f"{number}. {heading.upper()}")
    run.bold = True
    run.font.size = Pt(13)
    run.font.color.rgb = NAVY


def add_sub(doc, heading):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    run = p.add_run(heading)
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = NAVY


def add_body(doc, text, space_after=4):
    p = doc.add_paragraph(text)
    p.paragraph_format.space_after = Pt(space_after)
    for run in p.runs:
        run.font.size = Pt(11)
    return p


def add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    run = p.add_run(text)
    run.font.size = Pt(11)


def add_numbered(doc, text):
    p = doc.add_paragraph(style="List Number")
    run = p.add_run(text)
    run.font.size = Pt(11)


def add_table(doc, headers, rows, col_widths=None):
    n_cols = len(headers)
    table = doc.add_table(rows=1, cols=n_cols)
    table.style = "Table Grid"

    # Header row
    hdr_row = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr_row.cells[i]
        _set_shading(cell, "1B3A6B")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = WHITE

    # Data rows
    for ri, row_data in enumerate(rows):
        row = table.add_row()
        for ci, val in enumerate(row_data):
            cell = row.cells[ci]
            if ri % 2 == 1:
                _set_shading(cell, "E6EBF5")
            p = cell.paragraphs[0]
            run = p.add_run(str(val))
            run.font.size = Pt(10)

    # Column widths
    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Inches(w)

    doc.add_paragraph()  # spacing after table


def hr(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'<w:bottom w:val="single" w:sz="6" w:space="1" w:color="1B3A6B"/>'
        f'</w:pBdr>'
    )
    pPr.append(pBdr)


# ════════════════════════════════════════════════════════════════════
# BUILD DOCUMENT
# ════════════════════════════════════════════════════════════════════
doc = Document()

# Page margins
for section in doc.sections:
    section.top_margin    = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin   = Cm(2.5)
    section.right_margin  = Cm(2.5)

# Default font
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(11)

# ── Cover ────────────────────────────────────────────────────────────
doc.add_paragraph()
add_title(doc, "REVIEW – 1 PROJECT REPORT")
doc.add_paragraph()
add_title(doc, "Trademark Arbitration Decision Support System")
add_subtitle(doc, "NLP-Based Dispute Classification and Legal Precedent Retrieval")
doc.add_paragraph()
add_subtitle(doc, "M.Tech Integrated Software Engineering")
add_subtitle(doc, "Course: Natural Language Processing")
doc.add_paragraph()
hr(doc)
doc.add_paragraph()

# ════════════════════════════════════════════════════════════════════
# SECTION 1 – PROJECT TITLE
# ════════════════════════════════════════════════════════════════════
add_section(doc, 1, "Project Title")
add_body(doc,
    "A Neuro-Symbolic Decision Support System for Arbitrability "
    "Determination in Indian Trademark Disputes")
hr(doc)

# ════════════════════════════════════════════════════════════════════
# SECTION 2 – PROBLEM STATEMENT
# ════════════════════════════════════════════════════════════════════
add_section(doc, 2, "Problem Statement")
add_body(doc,
    "When a trademark dispute is brought to arbitration in India, the arbitrator "
    "must first decide whether the dispute is even legally allowed to be arbitrated — "
    "a question called arbitrability. Getting this wrong can invalidate the entire "
    "proceeding. Under the Arbitration and Conciliation Act, 1996, disputes that "
    "involve rights enforceable against the public (rights in rem) — such as trademark "
    "registration or cancellation — cannot be arbitrated and must go to civil court. "
    "Only disputes arising from a private contract (rights in personam), such as a "
    "licensing or distribution agreement, can proceed in arbitration.")
add_body(doc,
    "Currently, making this determination requires manually reading through lengthy "
    "court judgments and legal statutes. Relevant case law is hard to find through "
    "keyword search because similar legal concepts are often described using different "
    "words across cases. There is no structured tool to assist arbitrators, lawyers, or "
    "students with this analysis.")
add_body(doc,
    "This project builds the Trademark Arbitration Decision Support System (Trademark "
    "DSS) — a software tool that takes a dispute description as input and produces a "
    "structured legal analysis report. The system classifies the dispute, checks "
    "arbitrability using coded rules, retrieves relevant landmark cases using NLP "
    "techniques, and drafts a structured report using a Large Language Model. It is "
    "a decision support tool and does not give legally binding outputs or replace "
    "qualified legal professionals.")
hr(doc)

# ════════════════════════════════════════════════════════════════════
# SECTION 3 – JUSTIFICATION ANALYSIS
# ════════════════════════════════════════════════════════════════════
add_section(doc, 3, "Justification Analysis")

add_sub(doc, "Why Is This Problem Difficult?")
add_body(doc,
    "Trademark disputes can involve statutory infringement, contractual breach, or "
    "common law passing off — sometimes all three at once. Deciding which legal "
    "framework applies, and whether arbitration is valid, requires reading across "
    "multiple acts and case judgments. Traditional keyword search tools often miss "
    "relevant cases when the wording differs. Manual research is slow and error-prone.")

add_sub(doc, "Why NLP?")
add_body(doc,
    "NLP techniques such as TF-IDF, sentence embeddings, and vector similarity search "
    "allow the system to find semantically similar cases — ones discussing the same "
    "legal concept even if phrased differently. This makes precedent retrieval faster "
    "and more relevant than keyword matching alone.")

add_sub(doc, "Why a Neuro-Symbolic Design?")
add_body(doc,
    "Large Language Models (LLMs) are useful for drafting text but can hallucinate — "
    "making up case citations or misstating legal rules. For a legally sensitive output "
    "like an arbitrability determination, this is unacceptable. The system therefore "
    "separates the decision (handled by a hard-coded rule engine) from the drafting "
    "(handled by the LLM). The rule engine always produces an auditable, explainable "
    "answer based on Indian court tests; the LLM is only used for narrative generation "
    "downstream of that decision.")

add_sub(doc, "Scope")
add_body(doc,
    "The system covers Indian trademark law only. The five dispute categories supported "
    "are: Trademark Infringement, Brand Similarity / Deceptive Resemblance, Passing Off, "
    "Assignment Dispute, and Licensing / Distribution Dispute.")
hr(doc)

# ════════════════════════════════════════════════════════════════════
# SECTION 4 – LITERATURE SURVEY
# ════════════════════════════════════════════════════════════════════
add_section(doc, 4, "Literature Survey")
add_body(doc,
    "The following techniques and prior works are relevant to this project:")

lit_rows = [
    ("TF-IDF + SVM",
     "Sparse text vectorization + supervised classifier",
     "Used for dispute-type classification from free-text descriptions. "
     "Well-suited for short legal text with limited training data."),
    ("Sentence Embeddings\n(all-MiniLM-L6-v2)",
     "Dense vector representation of text meaning",
     "Encodes legal chunk text and dispute descriptions into 384-dim vectors "
     "for semantic similarity retrieval in ChromaDB."),
    ("ChromaDB / Vector Search",
     "Local persistent vector database",
     "Stores embeddings of case chunks and statutes; retrieves top-k semantically "
     "similar passages in response to a dispute query."),
    ("Retrieval-Augmented\nGeneration (RAG)",
     "External document context fed to an LLM",
     "Grounds the LLM's report drafting in retrieved statutory text and case law, "
     "reducing hallucination risk. Introduced by Lewis et al. (NeurIPS 2020)."),
    ("Neuro-Symbolic AI",
     "Combination of rule-based and neural components",
     "Deterministic rule engine handles the binary arbitrability decision; "
     "neural components (embeddings, LLM) handle retrieval and drafting. "
     "Follows Wei et al. (2025) and Colelough & Regli (2025)."),
    ("NER / Dependency\nParsing (spaCy)",
     "Structural linguistic analysis of legal text",
     "Planned: NER to extract parties, statutes, and jurisdictions; "
     "dependency parsing to extract subject-verb-object triples from dispute facts. "
     "Will be explored as standalone NLP course deliverables."),
]
add_table(doc,
    ["Technique / Concept", "What It Does", "Relevance to This Project"],
    lit_rows,
    col_widths=[1.6, 1.8, 3.1])

add_body(doc,
    "Key related works include: Goel et al. (2026) — Domain-Partitioned Hybrid RAG "
    "for Indian legal reasoning; Mubeen et al. (2025) — LegalEase RAG system on "
    "ChromaDB; Magesh et al. (Stanford RegLab, 2024) — empirical study showing "
    "hallucination persists in legal RAG tools; Pipitone & Alami (2024) — LegalBench-RAG "
    "benchmark for retrieval quality.")
hr(doc)

# ════════════════════════════════════════════════════════════════════
# SECTION 5 – DATASET ANALYSIS
# ════════════════════════════════════════════════════════════════════
add_section(doc, 5, "Dataset Analysis")
add_body(doc,
    "The knowledge base of the system is built from raw legal PDF documents stored "
    "in data/raw_pdfs/. These are the primary source documents for the RAG pipeline — "
    "not synthetic data. There are 32 PDFs in total: 3 statutes and 29 landmark "
    "Indian court judgments on trademark and arbitration law.")

add_sub(doc, "Statutes and Reference Documents")
statute_rows = [
    ("Arbitration and Conciliation Act 1996.pdf", "PDF", "Defines arbitrability rules, Sections 7 and 34"),
    ("Trademarks-act-1999.pdf",                   "PDF", "Statutory definitions of infringement, passing off, registration"),
    ("Indian Contract Act 1872.pdf",               "PDF", "Framework for contractual relationships and privity"),
    ("Compendium-on-Landmark-cases.pdf",           "PDF", "Secondary reference summarising major IP/ADR principles"),
]
add_table(doc,
    ["Document", "Format", "Role in Knowledge Base"],
    statute_rows,
    col_widths=[3.2, 0.7, 2.6])

add_sub(doc, "Landmark Case Judgments (sample)")
case_rows = [
    ("Booz Allen & Hamilton Inc. v. SBI Home Finance Ltd. (2011)", "Establishes Right in Rem vs. Right in Personam arbitrability test"),
    ("Vidya Drolia v. Durga Trading Corporation (2020)",            "Establishes the Fourfold Test for arbitrability"),
    ("K. Mangayarkarasi v. N.J. Sundaresan (2025)",                "Most recent SC ruling confirming arbitrability of contractual trademark disputes"),
    ("Hero Electric Vehicles Pvt. Ltd. v. Lectro E-Mobility (2021)","Arbitrability of trademark licensing disputes"),
    ("Cadila Healthcare Ltd. v. Cadila Pharmaceuticals Ltd. (2001)","Higher confusion standard for pharmaceutical marks"),
    ("Parle Products (P) Ltd. v. J.P. & Co., Mysore (1972)",       "Deceptive similarity test using imperfect recollection"),
    ("The Coca-Cola Company v. Bisleri International (2009)",       "Finality of trademark assignments"),
    ("N.R. Dongre v. Whirlpool Corporation (1996)",                 "Transborder reputation without local registration"),
    ("… and 21 further landmark judgments",                         "Covering passing off, phonetic similarity, territoriality, rectification, etc."),
]
add_table(doc,
    ["Case", "Legal Principle Covered"],
    case_rows,
    col_widths=[3.3, 3.2])

add_sub(doc, "Processing Pipeline (Planned / In Progress)")
steps = [
    "Text Extraction — PyMuPDF extracts text from each PDF into data/extracted_text/",
    "Cleaning — Whitespace normalization, header/footer removal → data/cleaned_text/",
    "Chunking — Sliding window of 800 words, 100-word overlap → data/chunks/",
    "Embedding — all-MiniLM-L6-v2 encodes each chunk into a 384-dim vector",
    "Indexing — Chunks loaded into ChromaDB at knowledge_base/chroma_db",
    "Retrieval — Dispute description is embedded and top-3 chunks are returned at query time",
]
for s in steps:
    add_bullet(doc, s)
doc.add_paragraph()
hr(doc)

# ════════════════════════════════════════════════════════════════════
# SECTION 6 – PROPOSED METHODOLOGY
# ════════════════════════════════════════════════════════════════════
add_section(doc, 6, "Proposed Methodology")
add_body(doc,
    "The system is being built as a sequential modular pipeline. Each module is "
    "independently developed and tested. The overall flow is:")

pipeline_rows = [
    ("1", "Case Intake",
     "Web form collects party names, trademark, contract status, arbitration clause "
     "presence, right source (statute / contract), third-party impact, and a free-text "
     "dispute description.",
     "Frontend (index.html) + FastAPI endpoint (api/main.py)"),
    ("2", "Dispute Classification",
     "TF-IDF vectorization of the dispute description is fed to a trained Linear SVM "
     "to predict the dispute category (Infringement / Brand Similarity / Passing Off / "
     "Assignment / Licensing). Falls back to regex heuristics if the model file is absent.",
     "agents/dispute_classifier.py — DisputeClassifier class; config.py — USE_HYBRID_CLASSIFICATION flag"),
    ("3", "Arbitrability Decision Engine",
     "Deterministic rule engine applies the Booz Allen right-in-rem/personam test and "
     "the Vidya Drolia Fourfold Test using only structured form fields. Zero LLM calls. "
     "Outputs ARBITRABLE / NOT ARBITRABLE with statutory justification.",
     "agents/arbitrability_agent.py — apply_booz_allen_test(), apply_vidya_drolia_test()"),
    ("4", "Tiered Precedent Retrieval (RAG)",
     "Tier 1: Live IndiaKanoon API query. "
     "Tier 2: ChromaDB semantic vector search (all-MiniLM-L6-v2). "
     "Tier 3: Curated landmark case registry from config.py. "
     "Top 3 retrieved case chunks form the RAG context.",
     "agents/landmark_retrieval_agent.py; config.py — LANDMARK_CASES registry"),
    ("5", "Constrained LLM Drafting",
     "Retrieved context + arbitrability result are passed to Gemini 2.5 Flash with a "
     "statutory-first prompt constraint (statute text must be cited before case law). "
     "Falls back to Groq → LM Studio → hardcoded template.",
     "agents/gemini_agents.py; agents/adversarial_legal_agent.py"),
    ("6", "Report Synthesis",
     "Outputs are assembled into a .docx file with 6 structured legal sections: "
     "Arbitrability Determination, Landmark Case Matrix, Issues for Determination, "
     "Applicable Provisions, Award Framework, Adversarial Analysis.",
     "agents/report_generator.py (python-docx)"),
    ("7", "Lawyer Finder",
     "User enters a city; the system queries Google Places API for nearby IP advocates. "
     "Falls back to a web search link if the API key is absent.",
     "agents/lawyer_finder_agent.py; api/main.py — /find-lawyers endpoint"),
]
add_table(doc,
    ["Step", "Module", "Description", "Key Source Files"],
    pipeline_rows,
    col_widths=[0.4, 1.4, 2.8, 2.0])
hr(doc)

# ════════════════════════════════════════════════════════════════════
# SECTION 7 – ALGORITHM SELECTION
# ════════════════════════════════════════════════════════════════════
add_section(doc, 7, "Algorithm Selection")

algo_rows = [
    # Implemented
    ("TF-IDF Vectorization\n+ Linear SVM",
     "Dispute Type Classification\n(Module 2)",
     "Implemented",
     "SVMs work well on sparse high-dimensional text features. Runs locally with no "
     "API cost. Implemented in agents/dispute_classifier.py using sklearn's TfidfVectorizer "
     "+ LinearSVC wrapped in CalibratedClassifierCV for confidence scores."),
    ("Keyword / Regex Heuristic",
     "Dispute Classification Fallback",
     "Implemented",
     "Lightweight rule-based fallback in landmark_retrieval_agent.py used when the "
     "trained .joblib model file is unavailable."),
    ("Symbolic Rule Engine\n(Booz Allen + Vidya Drolia)",
     "Arbitrability Assessment\n(Module 3)",
     "Implemented",
     "Deterministic Python logic in agents/arbitrability_agent.py. No ML involved — "
     "guarantees an auditable, legally grounded binary output every time."),
    ("Sentence Transformers\n(all-MiniLM-L6-v2)",
     "Document Embedding for RAG\n(Module 4)",
     "Implemented",
     "384-dim dense vectors for all legal chunks. Loaded via the sentence-transformers "
     "library in scripts/load_chroma.py and at query time in the retrieval agent."),
    ("ChromaDB\nVector Similarity Search",
     "Semantic Precedent Retrieval\n(Module 4)",
     "Implemented",
     "Local persistent vector store. Cosine similarity search returns the top-3 "
     "most semantically relevant legal chunks from the indexed PDF corpus."),
    ("IndiaKanoon API",
     "Live Case Retrieval\n(Module 4 – Tier 1)",
     "Implemented",
     "Primary retrieval source for real-time Indian court judgments. Configured via "
     "INDIAKANOON_API_KEY in .env; bypassed gracefully when key is absent."),
    ("Retrieval-Augmented\nGeneration (RAG)",
     "Constrained LLM Drafting\n(Module 5)",
     "Implemented",
     "Retrieved statutory chunks + case text are injected as context into the LLM "
     "prompt, grounding the generated report in actual source documents."),
    ("Google Gemini 2.5 Flash\n(+ Groq / LM Studio fallbacks)",
     "Report Narrative Generation\n(Module 5)",
     "Implemented",
     "Primary LLM with a statutory-first constraint. Fallback chain: Groq (llama-3.3-70b) "
     "→ LM Studio (deepseek-r1-7b) → hardcoded template. Implemented in agents/gemini_agents.py."),
    ("python-docx\nDocument Synthesis",
     "Structured .docx Report Output\n(Module 6)",
     "Implemented",
     "Programmatically assembles a 6-section legal report with styled headings, tables, "
     "and borders in agents/report_generator.py."),
    ("Google Places API",
     "Nearby Lawyer Finder\n(Module 7)",
     "Implemented",
     "Geocodes a city name and searches for trademark advocates via the Places Nearby "
     "Search endpoint. Web-search fallback when API key is absent."),
    # Planned NLP deliverables
    ("Named Entity Recognition\n(spaCy NER + EntityRuler)",
     "Entity Extraction from\nDispute Text & Case Chunks",
     "Planned\n(NLP Deliverable)",
     "Planned standalone script ner_analysis.py (in scratch). Will use spaCy "
     "(en_core_web_sm) with a custom EntityRuler to tag ORG (parties), LAW (statutes), "
     "GPE (jurisdictions), DATE, and PERSON across dispute descriptions and retrieved "
     "case text. Custom patterns needed because spaCy's default model does not reliably "
     "detect Indian legal citations such as 'Section 29 of the Trade Marks Act 1999'."),
    ("POS Tagging &\nPOS-Feature Ablation",
     "Feature Engineering for\nDispute Classifier",
     "Planned\n(NLP Deliverable)",
     "Planned script pos_feature_ablation.py (in scratch). Will add NOUN-VERB-NOUN "
     "POS n-gram features to the TF-IDF baseline and compare precision/recall/F1 of "
     "word-TF-IDF-only vs. word-TF-IDF + POS features using the existing dispute "
     "training data. Decoupled from production dispute_classifier.py."),
    ("Dependency Parsing\n(spaCy DepParse + displaCy)",
     "Subject-Verb-Object Extraction\nfrom Legal Sentences",
     "Planned\n(NLP Deliverable)",
     "Planned standalone script dependency_analysis.py (in scratch). Will extract "
     "SVO triples (nsubj, ROOT, dobj/pobj) from dispute descriptions and retrieved "
     "judgment text. Dependency trees will be rendered to HTML using displaCy. "
     "Framed as future-work input for auto-populating structured intake fields."),
]

add_table(doc,
    ["Algorithm / Technique", "Component / Module", "Status", "Rationale & Implementation Notes"],
    algo_rows,
    col_widths=[1.5, 1.4, 0.85, 2.8])
hr(doc)

# ════════════════════════════════════════════════════════════════════
# SECTION 8 – WORK PLAN
# ════════════════════════════════════════════════════════════════════
add_section(doc, 8, "Work Plan")

wp_rows = [
    ("Phase 1", "Problem Definition & Statutory Mapping",
     "Formalised Booz Allen and Vidya Drolia tests as implementable rule logic",
     "Done"),
    ("Phase 2", "Legal Dataset Collection",
     "32 raw PDF files (statutes + landmark judgments) assembled in data/raw_pdfs/",
     "Done"),
    ("Phase 3", "PDF Text Extraction & Cleaning",
     "scripts/extract_pdf.py and scripts/clean_text.py producing cleaned text files",
     "Done"),
    ("Phase 4", "Document Chunking",
     "scripts/chunk_documents.py — 800-word sliding window chunks with 100-word overlap",
     "Done"),
    ("Phase 5", "Vector Store Setup",
     "scripts/load_chroma.py — embeddings loaded into ChromaDB knowledge base",
     "Done"),
    ("Phase 6", "Dispute Classifier Training",
     "TF-IDF + LinearSVC model trained and saved (models/dispute_classifier.joblib)",
     "Done"),
    ("Phase 7", "Arbitrability Rule Engine",
     "agents/arbitrability_agent.py — deterministic Booz Allen + Drolia logic",
     "Done"),
    ("Phase 8", "LLM Drafting Layer",
     "agents/gemini_agents.py + agents/adversarial_legal_agent.py with fallback chain",
     "In Progress"),
    ("Phase 9", "Report Generator",
     "agents/report_generator.py — .docx assembly with 6 legal sections",
     "In Progress"),
    ("Phase 10", "Lawyer Finder",
     "agents/lawyer_finder_agent.py — Google Places API with web-search fallback",
     "In Progress"),
    ("Phase 11", "Web Interface",
     "frontend/index.html + api/main.py FastAPI backend",
     "In Progress"),
    ("Phase 12", "NLP Course Deliverables\n(NER, POS, Dependency Parsing)",
     "Standalone scripts in scratch/ for NER analysis, POS ablation, SVO extraction",
     "Planned"),
    ("Phase 13", "Labelled Dataset & Validation",
     "Curated ground-truth fact patterns verified by IP domain expert; ablation study",
     "Planned"),
    ("Phase 14", "Final Documentation & Demo",
     "Complete project report, system walkthrough, and live demo",
     "Planned"),
]
add_table(doc,
    ["Phase", "Activity", "Expected Output", "Status"],
    wp_rows,
    col_widths=[0.7, 2.0, 2.8, 1.1])
hr(doc)

# ════════════════════════════════════════════════════════════════════
# SECTION 9 – EXPECTED RESULTS
# ════════════════════════════════════════════════════════════════════
add_section(doc, 9, "Expected Results")
add_body(doc,
    "On successful completion the project is expected to produce:")

results = [
    "A working web-based decision support tool for trademark dispute arbitrability assessment.",
    "A trained TF-IDF + SVM classifier that categorises dispute descriptions into one of five categories.",
    "A deterministic arbitrability engine that applies the Booz Allen and Vidya Drolia tests to a given set of dispute facts.",
    "Semantic precedent retrieval over the curated corpus of 32 legal PDFs using ChromaDB.",
    "An LLM-drafted, structured Word report (.docx) covering six legal sections — generated from retrieved context rather than from model memory alone.",
    "A nearby trademark lawyer lookup utility using Google Places API.",
    "Standalone NLP analysis scripts (NER extraction, POS feature ablation, dependency parsing) as course deliverables, demonstrating the application of core NLP techniques to legal text.",
]
for r in results:
    add_bullet(doc, r)

doc.add_paragraph()
add_body(doc,
    "The system is explicitly not intended to produce legally binding outputs, replace "
    "legal counsel, or serve as a substitute for professional judgment. All generated "
    "reports are labelled FOR ARBITRATOR USE ONLY and are designed to support, "
    "not replace, independent human decision-making.")
hr(doc)

# ── Save ─────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
doc.save(OUTPUT)
print(f"Saved: {OUTPUT}")
