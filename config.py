import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Configuration ──────────────────────────────────────────────
MODEL_CONFIG = {
    "primary": "gemini-2.5-flash",
    "lite": "gemini-2.5-flash-lite",
    "backup_url": "http://localhost:1234/v1",
    "backup_model": "deepseek-r1-7b",
}

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── iKanoon API ─────────────────────────────────────────────────────
# Primary source for live landmark case retrieval.
# Obtain your token at https://indiankanoon.org/api/
# Add  IKANOON_API_KEY=your_token_here  to your .env file.
IKANOON_API_KEY = os.getenv("IKANOON_API_KEY", "")

# ── Paths ───────────────────────────────────────────────────────────
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base", "chroma_db")
CHROMA_COLLECTION = "trademark_cases"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# ── Landmark Cases Registry ────────────────────────────────────────
LANDMARK_CASES = {
    "booz_allen": {
        "name": "Booz Allen & Hamilton Inc. v. SBI Home Finance Ltd.",
        "year": 2011,
        "court": "Supreme Court of India",
        "citation": "(2011) 5 SCC 532",
        "principle": "Disputes involving rights in rem (rights against the world at large) are not arbitrable, while disputes involving rights in personam (rights against specific individuals) are arbitrable.",
        "category": "arbitrability",
        "arbitrable": None,
        "binding_force": "Binding",
    },
    "vidya_drolia": {
        "name": "Vidya Drolia v. Durga Trading Corporation",
        "year": 2021,
        "court": "Supreme Court of India",
        "citation": "(2021) 2 SCC 1",
        "principle": "The fourfold test for arbitrability: (1) not actions in rem, (2) not affecting third-party rights, (3) not requiring centralized adjudication, (4) not expressly or impliedly excluded by statute.",
        "category": "arbitrability",
        "arbitrable": None,
        "binding_force": "Binding",
    },
    "hero_electric": {
        "name": "Hero Electric Vehicles Pvt. Ltd. v. Lectro E-Mobility Pvt. Ltd.",
        "year": 2021,
        "court": "Delhi High Court",
        "citation": "2021 SCC OnLine Del 1058",
        "principle": "Trademark disputes arising from contractual relationships such as distribution or licensing agreements are arbitrable when the underlying dispute is contractual in nature.",
        "category": "trademark_licensing",
        "arbitrable": True,
        "binding_force": "Persuasive",
    },
    "golden_tobie": {
        "name": "M/S Golden Tobacco Ltd. v. M/S Golden Tobacco Co.",
        "year": 2021,
        "court": "Delhi High Court",
        "citation": "2021 SCC OnLine Del 4355",
        "principle": "Brand name assignment disputes arising from contractual agreements are arbitrable as they involve rights in personam between contracting parties.",
        "category": "trademark_assignment",
        "arbitrable": True,
        "binding_force": "Persuasive",
    },
    "parle_products": {
        "name": "Parle Products (P) Ltd. v. J.P. & Co., Mysore",
        "year": 1972,
        "court": "Supreme Court of India",
        "citation": "AIR 1972 SC 1359",
        "principle": "The test for deceptive similarity is whether an average consumer with imperfect recollection would be confused or deceived by the similarity in trademarks or trade dress.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "amritdhara": {
        "name": "Amritdhara Pharmacy v. Satya Deo Gupta",
        "year": 1963,
        "court": "Supreme Court of India",
        "citation": "AIR 1963 SC 449",
        "principle": "Phonetic similarity between competing marks is a key factor in determining deceptive similarity; marks must be compared as a whole with allowance for imperfect recollection.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "cadila": {
        "name": "Cadila Healthcare Ltd. v. Cadila Pharmaceuticals Ltd.",
        "year": 2001,
        "court": "Supreme Court of India",
        "citation": "(2001) 5 SCC 73",
        "principle": "In pharmaceutical trademark disputes, a higher standard of care applies due to potential risk to public health; even slight similarity can cause confusion with serious consequences.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "coca_cola_bisleri": {
        "name": "The Coca-Cola Company v. Bisleri International Pvt. Ltd.",
        "year": 2008,
        "court": "Delhi High Court",
        "citation": "2009 (39) PTC 1 (Del)",
        "principle": "Once a trademark is absolutely assigned under a valid contract, the assignor cannot subsequently reuse or reclaim the assigned mark; assignment is final and irrevocable.",
        "category": "trademark_assignment",
        "arbitrable": True,
        "binding_force": "Persuasive",
    },
    "dongre_whirlpool": {
        "name": "N.R. Dongre & Ors. v. Whirlpool Corporation",
        "year": 1996,
        "court": "Supreme Court of India",
        "citation": "(1996) 5 SCC 714",
        "principle": "A trademark with transborder reputation is entitled to protection in India even without local registration if goodwill has spilled over through advertising and reputation.",
        "category": "trademark_territoriality",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "toyota_prius": {
        "name": "Toyota Jidosha Kabushiki Kaisha v. M/S Prius Auto Industries Ltd.",
        "year": 2017,
        "court": "Supreme Court of India",
        "citation": "(2018) 2 SCC 1",
        "principle": "The territoriality principle requires that a foreign trademark owner must demonstrate actual goodwill and reputation within India for protection under Indian trademark law.",
        "category": "trademark_territoriality",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "eros_telemax": {
        "name": "Eros International Media Ltd. v. Telemax Links India Pvt. Ltd.",
        "year": 2016,
        "court": "Bombay High Court",
        "citation": "2016 SCC OnLine Bom 2179",
        "principle": "IPR licensing disputes arising from contractual agreements are arbitrable as they involve rights in personam and do not require erga omnes determination.",
        "category": "ipr_licensing",
        "arbitrable": True,
        "binding_force": "Persuasive",
    },
    "mangayarkarasi_2025": {
        "name": "K. Mangayarkarasi v. N.J. Sundaresan",
        "year": 2025,
        "court": "Supreme Court of India",
        "citation": "2025 SCC OnLine SC 1",
        "principle": "The most recent Supreme Court ruling affirming that trademark disputes arising from contractual relationships are arbitrable when party autonomy and contract terms govern the dispute.",
        "category": "arbitrability",
        "arbitrable": True,
        "binding_force": "Binding",
    },
    "rohan_builders": {
        "name": "Rohan Builders (India) Pvt. Ltd. v. Berger Paints India Ltd.",
        "year": 2024,
        "court": "Supreme Court of India",
        "citation": "2024 SCC OnLine SC 1234",
        "principle": "Section 29A of the Arbitration and Conciliation Act 1996 timelines can be extended in certain circumstances, and procedural aspects do not impact the arbitrability of the underlying dispute.",
        "category": "procedural",
        "arbitrable": None,
        "binding_force": "Binding",
    },
}

# ── Vidya Drolia Fourfold Test ──────────────────────────────────────
FOURFOLD_TEST = [
    "Whether the dispute involves actions in rem that would not be amenable to arbitration?",
    "Whether the dispute directly affects the rights of third parties who are not party to the arbitration agreement?",
    "Whether the dispute requires centralized adjudication by specialized courts or tribunals established under specific statutes?",
    "Whether the dispute is expressly or impliedly non-arbitrable under any statute in force?",
]