import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Configuration ──────────────────────────────────────────────
MODEL_CONFIG = {
    "primary": "gemini-2.5-flash",
    "lite": "gemini-2.5-flash-lite",
    "backup_url": os.getenv("BACKUP_LLM_URL", "http://localhost:1234/v1"),
    "backup_model": os.getenv("BACKUP_LLM_MODEL", "deepseek-r1-7b"),
}

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── iKanoon API ─────────────────────────────────────────────────────
# Primary source for live landmark case retrieval.
# Obtain your token at https://indiankanoon.org/api/
# Add  IKANOON_API_KEY=your_token_here  to your .env file.
IKANOON_API_KEY = os.getenv("IKANOON_API_KEY", "")
ALLOWED_ORIGINS_RAW = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
ALLOWED_ORIGINS = [orig.strip() for orig in ALLOWED_ORIGINS_RAW.split(",") if orig.strip()]

# ── Paths ───────────────────────────────────────────────────────────
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base", "chroma_db")
CHROMA_COLLECTION = "trademark_cases"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# ── Dispute Classification ───────────────────────────────────────────
# Toggle hybrid ML + keyword classification for dispute type detection.
# True  → uses DisputeClassifier (SVM) with keyword fallback (production default).
# False → uses the original keyword-only heuristic (for A/B evaluation / paper).
# Override at runtime via env: USE_HYBRID_CLASSIFICATION=false
USE_HYBRID_CLASSIFICATION: bool = (
    os.getenv("USE_HYBRID_CLASSIFICATION", "true").strip().lower() == "true"
)

# Absolute path to the trained DisputeClassifier joblib model file.
CLASSIFIER_MODEL_PATH: str = os.path.join(
    os.path.dirname(__file__), "models", "dispute_classifier.joblib"
)

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
    "laxmikant_patel": {
        "name": "Laxmikant V. Patel v. Chetanbhai Shah",
        "year": 2002,
        "court": "Supreme Court of India",
        "citation": "(2002) 3 SCC 65",
        "principle": "The three elements of passing off are reputation/goodwill, misrepresentation, and likelihood of damage. Injunction must be granted if these are prima facie proved.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "mahendra_mahendra": {
        "name": "Mahendra & Mahendra Paper Mills Ltd. v. Mahindra & Mahindra Ltd.",
        "year": 2001,
        "court": "Supreme Court of India",
        "citation": "(2001) 7 SCC 300",
        "principle": "A corporate name or trading style that is deceptively similar to a well-known registered trademark of another company constitutes trademark dilution and passing off.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "ruston_hornsby": {
        "name": "Ruston & Hornsby Ltd. v. Zamindara Engineering Co.",
        "year": 1969,
        "court": "Supreme Court of India",
        "citation": "(1969) 2 SCC 727",
        "principle": "Distinguishes between trademark infringement and passing off; infringement is a statutory right whereas passing off is a common law remedy based on deceptively similar representation.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "kaviraj_pandit": {
        "name": "Kaviraj Pandit Durga Dutt Sharma v. Navaratna Pharmaceutical Laboratories",
        "year": 1965,
        "court": "Supreme Court of India",
        "citation": "AIR 1965 SC 980",
        "principle": "Determines the burden of proof in infringement actions. Where the two marks are nearly identical, no further proof of likelihood of confusion is required for statutory infringement.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "hms_mauritz": {
        "name": "H&M Hennes & Mauritz AB v. HM Megabrands Pvt. Ltd.",
        "year": 2018,
        "court": "Delhi High Court",
        "citation": "2018 SCC OnLine Del 9369",
        "principle": "Deceptive adoption of a well-known fashion mark (H&M) by using a phonetically and visually similar abbreviation (HM) constitutes trademark infringement and passing off; a defendant cannot claim honest concurrent adoption where the plaintiff's mark has acquired transborder reputation and goodwill prior to the defendant's use.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Persuasive",
    },
    "syed_mohideen": {
        "name": "S. Syed Mohideen v. P. Sulochana Bai",
        "year": 2016,
        "court": "Supreme Court of India",
        "citation": "(2016) 2 SCC 683",
        "principle": "Common law prior user rights are superior to statutory registration. A prior unregistered user of a mark can seek an injunction against a subsequent registered proprietor.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "chinna_krishna": {
        "name": "K.R. Chinna Krishna Chettiar v. Shri Ambal & Co.",
        "year": 1970,
        "court": "Supreme Court of India",
        "citation": "AIR 1970 SC 146",
        "principle": "Phonetic similarity between competing marks (e.g., 'Ambal' and 'Andal') is sufficient to cause deceptive similarity and public confusion, despite distinct visual packaging.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "dhodha_house": {
        "name": "Dhodha House v. S.K. Maingi",
        "year": 2006,
        "court": "Supreme Court of India",
        "citation": "(2006) 9 SCC 41",
        "principle": "To establish territorial jurisdiction on the basis of 'carrying on business', the plaintiff must show control, a physical presence, or substantial business activity in that territory.",
        "category": "trademark_territoriality",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "exphar_sa": {
        "name": "Exphar SA v. Eupharma Laboratories Ltd.",
        "year": 2004,
        "court": "Supreme Court of India",
        "citation": "(2004) 3 SCC 688",
        "principle": "When deciding territorial jurisdiction based on a demurrer (preliminary objection), the court must assume all statements and facts pleaded in the plaint to be true.",
        "category": "trademark_territoriality",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "patel_field_marshal": {
        "name": "Patel Field Marshal Agencies v. P.M. Diesels Ltd.",
        "year": 2018,
        "court": "Supreme Court of India",
        "citation": "(2018) 2 SCC 112",
        "principle": "Under Section 124 of the Trademarks Act, if a suit is pending, rectification of the register can only be sought after the court finds the plea of invalidity prima facie tenable.",
        "category": "trademark_rectification",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "bata_india": {
        "name": "Bata India Ltd. v. Pyare Lal & Co.",
        "year": 1985,
        "court": "Allahabad High Court",
        "citation": "AIR 1985 All 242",
        "principle": "Passing off can be established even when competing products belong to completely different classes of goods (shoes vs lungis) if the mark has enormous public reputation.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Persuasive",
    },
    "allergan_ocuflox": {
        "name": "Milmet Oftho Industries v. Allergan Inc.",
        "year": 2004,
        "court": "Supreme Court of India",
        "citation": "(2004) 12 SCC 624",
        "principle": "The first to enter the world market with a trademark is protected against local copycats in medicine, recognizing transborder reputation even prior to active sales in India.",
        "category": "trademark_territoriality",
        "arbitrable": False,
        "binding_force": "Binding",
    },
    "marico_parachute": {
        "name": "Marico Limited v. Agro Tech Foods Limited",
        "year": 2010,
        "court": "Delhi High Court",
        "citation": "2010 (44) PTC 54 (Del)",
        "principle": "Descriptive words or common phrases used in a trademark cannot claim exclusive monopoly unless they have acquired a distinct secondary meaning in the minds of consumers.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Persuasive",
    },
    "christian_louboutin": {
        "name": "Christian Louboutin Sas v. Pawan Kumar",
        "year": 2017,
        "court": "Delhi High Court",
        "citation": "2017 (72) PTC 1 (Del)",
        "principle": "A single-color trademark (specifically, the red sole of high-fashion women's shoes) is protectable as a well-known mark if it has acquired significant distinctiveness.",
        "category": "trademark_similarity",
        "arbitrable": False,
        "binding_force": "Persuasive",
    },
}

# ── Vidya Drolia Fourfold Test ──────────────────────────────────────
FOURFOLD_TEST = [
    "Whether the dispute involves actions in rem that would not be amenable to arbitration?",
    "Whether the dispute directly affects the rights of third parties who are not party to the arbitration agreement?",
    "Whether the dispute requires centralized adjudication by specialized courts or tribunals established under specific statutes?",
    "Whether the dispute is expressly or impliedly non-arbitrable under any statute in force?",
]