# Review-1 Project Report: Trademark Arbitration Decision Support System

## 1. PROJECT TITLE
**A Neuro-Symbolic Decision Support System for Arbitrability Determination in Indian Trademark Disputes**

---

## 2. PROBLEM STATEMENT

In the field of alternative dispute resolution (ADR) in India, arbitral tribunals are frequently faced with a critical jurisdictional question before they can address the merits of a dispute: **Is the subject matter of the dispute capable of settlement by arbitration under the law in force?** 

Under Section 34(2)(b)(i) of the Arbitration and Conciliation Act, 1996, an arbitral award may be set aside by a court if the subject matter of the dispute was not capable of settlement by arbitration. Subject matter non-arbitrability is a threshold jurisdictional defect that cannot be cured by party consent. Consequently, an arbitrator who proceeds to decide a dispute that was never arbitrable risks producing an award with no legal effect, resulting in a significant waste of time, legal costs, and administrative resources.

Within the domain of intellectual property, and specifically trademark disputes governed by the Trade Marks Act, 1999, determining arbitrability is exceptionally challenging. Indian jurisprudence has developed complex, multi-tiered tests to distinguish between:
* **Rights in Rem**: Rights enforceable against the world at large (e.g., trademark registration, cancellation, or rectification), which are generally non-arbitrable and reserved for specialized public forums.
* **Rights in Personam**: Personal rights arising from contractual relationships (e.g., trademark licensing, franchise breaches, or assignment disputes), which are amenable to private arbitration.

Currently, legal practitioners, arbitrators, and corporate counsel must manually review extensive legal texts, historical precedents, and statutory provisions to make a preliminary assessment of arbitrability. This process is:
1. **Time-Consuming**: Requires parsing dense legal judgments and cross-referencing multiple statutory acts.
2. **Prone to Human Error**: Overlooking subtle factual distinctions (such as the presence of a valid arbitration clause or the exact nature of the relief sought) can lead to incorrect jurisdictional conclusions.
3. **Inefficient**: Keyword-based search tools often fail to retrieve conceptually similar precedents if they use different wording.

### System Scope and Boundaries
To address these challenges, this project introduces the **Trademark Arbitration Decision Support System (Trademark DSS)**. 

The Trademark DSS is designed strictly as a **decision support system**. It does **NOT** make legally binding decisions, write enforceable arbitral awards, or replace lawyers, arbitrators, judges, or courts. Instead, it assists legal research and provides structured decision support by:
* Classifying trademark disputes from natural-language descriptions.
* Deterministically assessing arbitrability based on established judicial tests.
* Semantically retrieving relevant landmark precedents and statutory rules.
* Generating structured preliminary reports to guide independent human decision-making.

---

## 3. JUSTIFICATION ANALYSIS

### Why Trademark Dispute Analysis is Difficult
Trademark disputes rarely present themselves as simple, isolated issues. They frequently involve a hybrid of:
1. **Contractual Claims**: Licensing terms, franchise agreements, royalties, and territorial limitations.
2. **Statutory Infringements**: Unauthorized use of registered marks under the Trade Marks Act, 1999.
3. **Common Law Remedies**: Actions for passing off to protect unregistered marks or goodwill.

Determining whether such disputes can be arbitrated requires analyzing the intersection of the contract (the arbitration agreement) and the statutory boundaries of intellectual property law.

### Limitations of Keyword-Based Precedent Search
Traditional legal databases rely heavily on keyword indexing. If a researcher searches for "trademark license breach," they may miss critical landmark cases that discuss "franchise agreements" or "brand assignment," even though the underlying legal principles regarding rights *in personam* and arbitrability are identical. Furthermore, keyword search cannot assess the semantic context of case facts, leading to high-volume, low-relevance search results that require manual filtering.

### Why NLP and Semantic Retrieval are Appropriate
Natural Language Processing (NLP) and vector embeddings enable the system to understand the semantic meaning of free-text dispute descriptions. By representing legal text as dense vectors, the system can perform semantic similarity searches. This allows it to identify cases that discuss similar legal concepts (e.g., phonetic similarity, deceptive trade dress, or contractual privity) even when the specific terminology, party names, or factual scenarios differ.

### Rationale for a Neuro-Symbolic Architecture
Large Language Models (LLMs) are highly capable of drafting fluent narratives and summarizing text. However, in legal domains, LLMs are prone to "hallucinations"—generating non-existent case citations, misstating statutory sections, or shifting legal determinations due to probabilistic text generation. 

To overcome this, the Trademark DSS implements a **neuro-symbolic framework**:
* **Symbolic Layer (Deterministic Rule Engine)**: Operationalizes the strict legal tests for arbitrability (Booz Allen and Vidya Drolia tests) outside the LLM. It guarantees that the core jurisdictional determination is rule-bound, auditable, and mathematically consistent.
* **Neural Layer (LLM & Embeddings)**: Processes natural-language dispute facts, performs semantic similarity searches across the legal corpus, and drafts the surrounding report text under strict constraints.

### Project Scope Boundaries
The scope of the Trademark DSS is restricted to **Indian trademark and arbitration law**. The system supports five canonical trademark dispute categories:
1. **Infringement**: Unauthorized use of a registered trademark.
2. **Brand Similarity**: Deceptive trade dress or visual/phonetic similarity between competing marks without a contract.
3. **Passing Off**: Common law misrepresentation of goods/services.
4. **Assignment**: Contested transfer of trademark ownership.
5. **Licensing**: License, distribution, or franchise breaches containing an arbitration clause.

---

## 4. LITERATURE SURVEY

The development of the Trademark DSS is informed by several core technologies and academic literature in legal AI, natural language processing, and online dispute resolution.

### TF-IDF (Term Frequency-Inverse Document Frequency)
* **What it does**: TF-IDF is a numerical statistic that reflects how important a word is to a document in a collection. It scales down words that appear frequently across all documents (like "court" or "trademark") and scales up words that are highly specific to a class of documents.
* **Why it is relevant**: In the Trademark DSS, TF-IDF is used to vectorize free-text dispute descriptions. These vector representations serve as inputs to the offline-trained machine learning classifier to determine the dispute category without relying on external API calls.

### Support Vector Machine (SVM)
* **What it does**: SVM is a supervised machine learning algorithm that finds an optimal hyperplane in a high-dimensional space to classify data points into distinct categories.
* **Why it is relevant**: The system utilizes a **Linear Support Vector Classifier (Linear SVM)** trained on TF-IDF features. It classifies incoming dispute descriptions into one of the five canonical dispute categories. This classification runs locally with zero LLM API calls, ensuring high speed and predictability.

### Text and Transformer-Based Embeddings
* **What it does**: Transformer-based models (such as BERT or Sentence-Transformers) map sentences or paragraphs to dense, low-dimensional vector representations that capture semantic meaning and context.
* **Why it is relevant**: The system uses the **`all-MiniLM-L6-v2`** sentence-transformer model. This model converts cleaned legal chunks and user dispute descriptions into 384-dimensional dense vectors, enabling semantic comparison rather than exact keyword matching.

### Semantic Information Retrieval and Vector Databases
* **What it does**: A vector database stores vector embeddings and performs fast similarity searches (e.g., Cosine Similarity) to retrieve the nearest neighbors to a query vector.
* **Why it is relevant**: **ChromaDB** is used as the local, persistent vector database. The processed text chunks of raw Indian judgments and statutes are indexed in ChromaDB. During the retrieval phase, the user's dispute description is embedded and queried against ChromaDB to extract the top 3 most semantically relevant legal chunks.

### Retrieval-Augmented Generation (RAG)
* **What it does**: RAG is an architecture where an LLM is provided with external, authoritative document chunks as context to ground its response, rather than relying solely on its pre-trained weights.
* **Why it is relevant**: RAG forms the core of the DSS drafting layer. The system retrieves statutory text (from the Trade Marks Act, 1999) and judicial interpretations, embeds them in the prompt context, and instructs the LLM to draft report sections based *only* on the provided context, preventing generative drift.

### Core Literature Context

The architecture of the system builds on recent legal NLP research, specifically:
* **Goel et al. (2026)** [5] propose a *Domain-Partitioned Hybrid RAG* system for general legal reasoning in India, using an agentic query router. The Trademark DSS adapts this concept but restricts the scope to trademark arbitrability, replacing the agentic routing of jurisdictional queries with a strict symbolic rule engine.
* **Mubeen et al. (2025)** [8] introduce *LegalEase*, a RAG system on ChromaDB for simplifying legal terms. While LegalEase focuses on lay accessibility, Trademark DSS targets professional arbitrators by generating structured, formal reports.
* **Wei et al. (2025)** [11] present a *neuro-symbolic framework for civil legal judgment prediction*, combining LLM fact extraction with first-order logic. Trademark DSS shares this philosophy but applies it to the threshold question of *arbitrability* rather than predicting final case outcomes.
* **Magesh et al. (Stanford RegLab, 2024)** [12] and **Pipitone & Alami (2024)** [15] analyze legal RAG failures, demonstrating that retrieval quality must be separated from generation quality, and showing that unconstrained LLM legal tools suffer from high hallucination rates. This empirical work justifies the DSS's architecture of isolating the binary arbitrability determination from the LLM drafting layer.

---

## 5. DATASET ANALYSIS

### Dataset Overview and Characterization
The primary dataset for the retrieval component of the Trademark DSS consists of the **raw legal source documents** stored locally within the system's knowledge base. 

Rather than using synthetic or evaluation scenario data, the system is grounded in the **actual legislative Acts and landmark judgments** of Indian courts. These raw PDFs are parsed, cleaned, chunked, and indexed to form the knowledge base.

| Dataset Category | Source Document (Filename) | Format | Role in RAG / Knowledge Base |
| :--- | :--- | :--- | :--- |
| **Statute / Legislative** | `Arbitration and Conciliation Act 1996.pdf` | PDF | Statutory reference for arbitration procedures and Section 7/34 definitions. |
| **Statute / Legislative** | `Trademarks-act-1999.pdf` | PDF | Statutory text for infringement, passing off, and registration rules. |
| **Statute / Legislative** | `Indian Contract Act 1872.pdf` | PDF | Legal framework for contractual relationships and privity. |
| **Legal Reference** | `Compendium-on-Landmark-cases.pdf` | PDF | Curated secondary reference text summarizing major IP and ADR principles. |
| **Landmark Judgments** | `Booz_Allen_Hamilton_Inc_vs_Sbi_Home_Finance_Ltd_Ors_on_15_April_2011.PDF` | PDF | Primary authority establishing the "Right in Rem vs. Right in Personam" test. |
| **Landmark Judgments** | `Vidya_Drolia_vs_Durga_Trading_Corporation_on_14_December_2020.PDF` | PDF | Primary authority establishing the "Fourfold Test" for arbitrability. |
| **Landmark Judgments** | `K_Mangayarkarasi_vs_N_J_Sundaresan_on_9_May_2025.PDF` | PDF | Landmark Supreme Court ruling (2025) confirming arbitrability of contractual trademark disputes. |
| **Landmark Judgments** | `Hero_Electric_Vehicles_Private_Limited_vs_Lectro_E_Mobility_Private_Limited_on_2_March_2021.PDF` | PDF | Landmark judgment on arbitrability of trademark licensing disputes. |
| **Landmark Judgments** | `M_S_Golden_Tobacco_Limited_vs_M_S_Golden_Tobie_Private_Limited_on_24_September_2021.PDF` | PDF | Precedent on arbitrability of brand name assignment disputes. |
| **Landmark Judgments** | `Eros_International_Media_Limited_vs_Telemax_Links_India_Pvt_Limited_And_7_Ors_on_12_April_2016.PDF` | PDF | High Court precedent on the arbitrability of intellectual property licensing. |
| **Landmark Judgments** | `The_Coca_Cola_Company_vs_Bisleri_International_Pvt_Ltd_Ors_on_20_October_2009.PDF` | PDF | Authority on finality of trademark assignments. |
| **Landmark Judgments** | `Amritdhara_Pharmacy_vs_Satyadeo_Gupta_on_27_April_1962.PDF` | PDF | Authority on phonetic similarity and deceptive resemblance. |
| **Landmark Judgments** | `Bata_India_Limited_vs_Pyare_Lal_Co_Meerut_City_And_Ors_on_23_January_1985.PDF` | PDF | High Court precedent on passing off across different classes of goods. |
| **Landmark Judgments** | `Cadila_Healthcare_Limited_vs_Cadila_Pharmaceuticals_Limited_on_26_March_2001.PDF` | PDF | Precedent establishing higher standard of confusion in pharmaceutical marks. |
| **Landmark Judgments** | `Christian_Louboutin_Sas_vs_Mr_Pawan_Kumar_Ors_on_12_December_2017.PDF` | PDF | Precedent protecting single-color trademarks with secondary meaning. |
| **Landmark Judgments** | `Exphar_Sa_Anr_vs_Eupharma_Laboratories_Ltd_Anr_on_20_February_2004.PDF` | PDF | Precedent on demurrer pleadings in territorial jurisdiction. |
| **Landmark Judgments** | `H_M;_Hennes_Mauritz_Ab_Anr_vs_Hm_Megabrands_Pvt_Ltd_Ors_on_31_May_2018.PDF` | PDF | Precedent protecting transborder fashion brand reputation. |
| **Landmark Judgments** | `K_R_Chinna_Krishna_Chettiar_vs_Sri_Ambal_Co_Madras_Anr_on_14_April_1969.PDF` | PDF | Supreme Court ruling on phonetic similarity despite visual packaging differences. |
| **Landmark Judgments** | `Kaviraj_Pandit_Durga_Dutt_Sharma_vs_Navaratna_Pharmaceutical_on_20_October_1964.PDF` | PDF | Supreme Court ruling on burden of proof in infringement vs. passing off. |
| **Landmark Judgments** | `Laxmikant_V_Patel_vs_Chetanbhat_Shah_Anr_on_4_December_2001.PDF` | PDF | Classic Supreme Court ruling defining the three elements of passing off. |
| **Landmark Judgments** | `M_S_Dhodha_House_vs_S_K_Maingi_on_15_December_2005.PDF` | PDF | Supreme Court precedent on territorial jurisdiction for "carrying on business". |
| **Landmark Judgments** | `Mahendra_And_Mahendra_Paper_Mills_Ltd_vs_Mahindra_And_Mahindra_Ltd_on_9_November_2001.PDF` | PDF | Precedent on corporate name dilution and passing off. |
| **Landmark Judgments** | `Marico_Limited_vs_Agro_Tech_Foods_Limited_on_1_November_2010.PDF` | PDF | Precedent on lack of monopoly over common descriptive terms. |
| **Landmark Judgments** | `Milmet_Oftho_Industries_Ors_vs_Allergan_Inc_on_7_May_2004.PDF` | PDF | Precedent on transborder reputation of medicinal marks. |
| **Landmark Judgments** | `N_R_Dongre_And_Ors_vs_Whirlpool_Corporation_And_Anr_on_30_August_1996.PDF` | PDF | Classic precedent protecting transborder reputation without local sales. |
| **Landmark Judgments** | `Parle_Products_P_Ltd_vs_J_P_Co_Mysore_on_28_January_1972.PDF` | PDF | Core test for deceptive similarity based on imperfect recollection of consumers. |
| **Landmark Judgments** | `Patel_Field_Marshal_Agencies_And_Anr_vs_P_M_Diesels_Ltd_And_Ors_on_29_November_2017.PDF` | PDF | Authority on Section 124 rectification procedures during pending suits. |
| **Landmark Judgments** | `Rohan Builders India vs Berger Paints 2024.pdf` | PDF | Precedent on procedural timelines (Section 29A) in arbitration proceedings. |
| **Landmark Judgments** | `Ruston_Hornsby_Ltd_vs_The_Zamindara_Engineering_Co_on_9_September_1969.PDF` | PDF | Distinguishing statutory infringement remedies from common law passing off. |
| **Landmark Judgments** | `S_Syed_Mohideen_vs_P_Sulochana_Bai_on_17_March_2015.PDF` | PDF | Precedent affirming that prior common law user rights override registration. |
| **Landmark Judgments** | `Toyota_Jidosha_Kabushiki_Kaisha_vs_M_S_Prius_Auto_Industries_Limited_on_14_December_2017.PDF` | PDF | Authority establishing territoriality and the requirement of local goodwill. |

### Dataset Processing Ingestion Pipeline

To prepare this unstructured PDF dataset for semantic search, the system runs a multi-stage ingestion pipeline:

1. **Text Extraction**: Text is extracted from raw PDF files using PyMuPDF (`fitz`), preserving structural layout and characters, writing files to `data/extracted_text/`.
2. **Cleaning & Preprocessing**: The system normalizes whitespaces, strips page headers/footers, and cleans formatting artifacts using regex, writing outputs to `data/cleaned_text/`.
3. **Chunking**: To maintain semantic relevance and fit embedding context windows, files are split into overlapping chunks of **800 words with a 100-word overlap**, saved to `data/chunks/`.
4. **Vector DB Loading**: Using `sentence-transformers`, chunks are embedded and indexed into a persistent local **ChromaDB** instance stored at `knowledge_base/chroma_db`.

### Importance of Curated Datasets
Basing the system's retrieval on primary legal sources (rather than synthetic data or pre-trained LLM memory) is crucial. It ensures that any legal advice generated is grounded in actual judicial prose.

While this dataset represents the landmark case law on trademark arbitrability and similarity, it is a **curated selection** and is **not legally exhaustive** of all Indian trademark litigation.

---

## 6. PROPOSED METHODOLOGY

The Trademark DSS processes a trademark dispute through a sequential, modular pipeline. This architecture isolates the high-risk jurisdictional decision-making from the creative writing tasks of the generative model.

### Module 1: Case Intake
The user interfaces with a single-page web dashboard to submit dispute details:
* **Party A & Party B**: Names of the disputing entities.
* **Trademark in Dispute**: The disputed brand mark or trade dress.
* **Contract Presence**: Boolean indicating whether a written contract exists.
* **Arbitration Clause**: Boolean indicating whether an arbitration clause is present in the contract.
* **Right Source**: Choice between "statute" (rights arising from registration under the Trade Marks Act) or "contract" (rights arising from a licensing/distribution/assignment agreement).
* **Third Party Impact**: Boolean indicating if the dispute affects third parties or public rights.
* **Dispute Description**: Natural language text detailing the factual scenario.

### Module 2: Dispute Classification
The system determines the category of the dispute (Infringement, Brand Similarity, Passing Off, Assignment, or Licensing). If the environment variable `USE_HYBRID_CLASSIFICATION` is set to `true`, the system loads a trained **Linear SVM classifier** (`dispute_classifier.joblib`). The SVM predicts the class from the TF-IDF representation of the dispute description. If disabled or if the model file is missing, the system falls back to a **regex-based keyword heuristic**.

### Module 3: Arbitrability Decision Engine
This symbolic module operates with **zero LLM calls** using deterministic logical statements.
1. **Booz Allen Test**: Checks if the dispute is *in rem* or *in personam*. It classifies it as *in rem* (non-arbitrable) if there is no contract, if the right source is "statute," or if the dispute category matches inherently *in rem* tasks (e.g., registration, cancellation, rectification, or passing off against a stranger).
2. **Vidya Drolia Fourfold Test**: Evaluates the four conditions:
   * Is it an action *in rem*?
   * Does it affect third-party rights?
   * Does it require centralized statutory adjudication (e.g., Trade Marks Registry)?
   * Is it explicitly/impliedly barred by statute?
   
If any of these conditions are met, or if there is no contract/arbitration clause, the engine flags the dispute as **NOT ARBITRABLE** and routes it to civil courts. If all tests pass, the dispute is flagged as **ARBITRABLE**.

### Module 4: Precedent Retrieval Layer (RAG)
The system retrieves relevant case law using a tiered strategy:
* **Tier 1 (Online - Primary)**: Queries the **IndiaKanoon API** (if an API key is provided) to fetch real-time judgments from Indian courts matching the dispute keywords.
* **Tier 2 (Offline - Secondary Fallback)**: Queries the local **ChromaDB** vector database using `all-MiniLM-L6-v2` embeddings of the dispute description to extract the top 3 semantically similar case chunks.
* **Tier 3 (Registry - Tertiary Fallback)**: Pulls directly from a curated dictionary of landmark cases in `config.py` based on the predicted dispute category.

### Module 5: Constrained LLM Drafting Layer
The retrieved chunks, dispute facts, and arbitrability determinations are combined into a system prompt. The prompt forces the LLM to follow a **statutory-first constraint**: it must cite the text of the Trade Marks Act, 1999, and the Arbitration and Conciliation Act, 1996, *before* presenting case law interpretations. 
To guarantee availability:
* **Primary LLM**: Hosted Google Gemini 2.5 Flash.
* **Secondary Backup**: Groq API hosting `llama-3.3-70b-versatile`.
* **Tertiary Backup**: Local LM Studio server hosting `deepseek-r1-7b`.
* **Quaternary Backup**: Hardcoded fallback template matching the symbolic output.

### Module 6: Report Synthesis Engine
The system compiles all outputs into a structured Microsoft Word document using `python-docx`. The generated report contains exactly **6 legal sections**:
1. **Arbitrability Determination**: The symbolic engine's final decision, showing the Booz Allen and Vidya Drolia test results.
2. **Landmark Case Analysis Matrix**: A table mapping the facts of the current dispute against the top 3 retrieved cases.
3. **Issues for Determination**: Four legal issues framed in standard judicial format.
4. **Applicable Legal Principles**: Key statutes and case interpretations.
5. **Award Framework**: Jurisdictional findings, relief guidance (injunctions/damages), and operative portion templates.
6. **Adversarial Legal Analysis**: Arguments for and against the claimant's position.

### Module 7: Lawyer Finder
To complete ODR decision support, a utility module takes the arbitrator's target city (e.g., "Mumbai") and queries the **Google Places API** to find nearby intellectual property advocates. If the Google API key is missing, it falls back to generating a direct web search link for trademark lawyers in that city.

---

## 7. ALGORITHM SELECTION

The technology stack and algorithms used by the Trademark DSS are selected to balance deterministic safety, semantic retrieval power, and narrative generation fluency.

| Component | Selected Algorithm / Technique | Rationale for Selection |
| :--- | :--- | :--- |
| **Dispute Categorization** | **TF-IDF Vectorization** + **Linear SVM** | The Linear Support Vector Classifier operates locally with zero runtime API dependency. SVMs perform exceptionally well on sparse text classification tasks (like legal descriptions) with minimal training data. |
| **Dispute Categorization (Fallback)** | **Regular Expression Heuristics** | Provides a lightweight, rule-based backup for classifying disputes if the trained machine learning model file (`dispute_classifier.joblib`) is missing or corrupted. |
| **Arbitrability Assessment** | **Symbolic Decision Trees (Rule Engine)** | Arbitrability is a strict binary legal question. Probabilistic models (LLMs) cannot guarantee 100% compliance with jurisdictional rules. Hardcoded rule mapping of the Booz Allen and Vidya Drolia tests ensures absolute auditability. |
| **Document Text Embeddings** | **`all-MiniLM-L6-v2`** | A 384-dimensional Sentence-Transformer model that strikes an optimal balance between embedding speed, local computation footprint, and semantic retrieval accuracy in English. |
| **Vector DB Storage** | **ChromaDB** | A persistent, lightweight, and local vector database. ChromaDB integrates directly with Python, eliminating the need to set up external database servers and ensuring low-latency retrieval. |
| **Precedent Retrieval (Primary)** | **IndiaKanoon Search API** | Serves as the primary link to live, real-time judgments of Indian courts, ensuring the system can retrieve cases decided after the vector database was compiled. |
| **Drafting Layer (Primary)** | **Google Gemini 2.5 Flash** | Chosen as the primary generative model due to its massive context window, high instruction-following accuracy (necessary for statutory-first constraints), and low latency. |
| **Drafting Layer (Backups)** | **Llama-3.3-70b** (Groq) & **DeepSeek-R1-7b** (LM Studio) | Llama-3.3-70b provides a hosted secondary fallback. DeepSeek-R1-7b, running locally via LM Studio, ensures the system remains functional even during total internet outages. |
| **Report Document Synthesis** | **`python-docx` Document Generation** | Word (.docx) is the industry standard for legal drafting. `python-docx` allows the system to programmatically inject custom styles, borders, tables, and colors to create a professional legal report. |
| **Lawyer Lookup** | **Google Places API** | Standard API for retrieving real-time local business listings, reviews, ratings, and maps URLs. |

---

## 8. WORK PLAN

The following work plan illustrates the development lifecycle of the Trademark DSS, indicating completed components and future validation milestones.

| Phase | Activity / Task | Expected Output | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Problem Formulation & Statutory Mapping | Formalized definition of Booz Allen / Vidya Drolia tests for Indian trademark law. | **Completed** |
| **Phase 2** | Precedent Dataset Collection | Assembly of 32 core PDF files including statutes and landmark Supreme Court judgments. | **Completed** |
| **Phase 3** | Text Preprocessing Ingestion Pipeline | PyMuPDF extraction scripts, text normalizers, and text chunking routines. | **Completed** |
| **Phase 4** | Semantic Indexing Setup | Local vector store database (ChromaDB) initialized with `all-MiniLM-L6-v2` embeddings. | **Completed** |
| **Phase 5** | Dispute Classifier Training | Trained TF-IDF + Linear SVM classifier saved to `models/dispute_classifier.joblib`. | **Completed** |
| **Phase 6** | Symbolic Rule Engine Implementation | Rule sets executing deterministic arbitrability checks. | **Completed** |
| **Phase 7** | Constrained Drafting & Fallback Agents | LLM prompt engineering, multi-LLM fallback logic, and LM Studio offline integrations. | **Completed** |
| **Phase 8** | Structured Report Synthesis | `python-docx` template generator writing structured Word files to `output/`. | **Completed** |
| **Phase 9** | Lawyer Finder Implementation | Google Places API client with city/geolocation lookups and search fallback. | **Completed** |
| **Phase 10** | Web Dashboard Interface | FastAPI backend endpoints and pure HTML/CSS/JS frontend dashboard. | **Completed** |
| **Phase 11** | Dataset Expansion & Legal Verification | Labelled dataset of trademark fact patterns verified by independent IP counsel. | *In Progress* |
| **Phase 12** | Ablation Studies & Expert Review | Comparative study against LLM-only baselines and evaluation of report quality by arbitrators. | *Planned* |

---

## 9. EXPECTED RESULTS

The development of the Trademark DSS is expected to yield the following deliverables:
1. **Interactive Web Interface**: A dashboard where users can input dispute particulars and view structured analyses.
2. **Predictable Dispute Classifier**: A local model that categorizes trademark disputes with high accuracy and zero API overhead.
3. **Symbolic Arbitrability Engine**: An explainable rule execution layer that details why a case is or is not arbitrable, citing Supreme Court authorities.
4. **Context-Grounded Precedent Matrix**: A mapping table of relevant landmark judgments matched semantically to the dispute's facts.
5. **Professional Word Reports**: Exportable `.docx` reports containing structured legal reasoning, drafted statutory text, and award templates.
6. **Integrated Lawyer Finder**: A tool providing names, ratings, and maps locations of IP advocates in the target Indian city.

### System Safety Commitments and Non-Goals
To align with academic and ethical AI standards, the system commits to the following boundaries:
* **No Binding Decisions**: The system will **never** output a binding arbitral award or legal order. All reports are clearly watermarked: *"FOR ARBITRATOR USE ONLY — CONFIDENTIAL"*.
* **No Legal Representation**: The system does not act as a legal representative. The lawyer finder directory is a search utility, not an endorsement or legal service.
* **No Claim of Legal Infallibility**: The report outputs are designed for decision support. Practitioners must independently verify all statutory references and retrieved case citations.
* **No Replacement of Human Oversight**: The system's target user is a human arbitrator or legal professional who exercises independent judgment over the synthesized reports.
