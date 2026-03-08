"""
KrishiMandal — RAG Knowledge Ingestion Script
Seeds the Pinecone vector store with agricultural knowledge documents
using Gemini embeddings.

Usage:
    python -m src.ingest_knowledge
"""
from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-28s | %(levelname)-5s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Knowledge corpus ─────────────────────────────────────────────────────────
# Each document has: topic, source, and content text.
# In production these would come from S3 (government PDFs, ICAR bulletins, etc.)

KNOWLEDGE_DOCUMENTS = [
    {
        "topic": "pest_control",
        "source": "ICAR Technical Bulletin No. 45 — Integrated Pest Management for Field Crops",
        "text": (
            "Integrated Pest Management (IPM) is the recommended approach for sustainable agriculture. "
            "Step 1: Monitor fields weekly for pest signs — check leaf undersides, stems, and soil. "
            "Step 2: Use pheromone traps and yellow sticky traps for early detection of bollworm, whitefly, and aphids. "
            "Step 3: Apply neem-based bio-pesticides (Azadirachtin 0.03%) as first line of defense. "
            "Step 4: Use chemical pesticides only when the Economic Threshold Level (ETL) is crossed. "
            "For wheat: Aphid ETL is 5 aphids per ear head. For cotton: Bollworm ETL is 1 larva per plant. "
            "Step 5: Rotate pesticide groups to prevent resistance buildup. "
            "Banned chemicals — NEVER use DDT, endosulfan, monocrotophos, or methyl parathion. "
            "These are banned by the Government of India under the Insecticides Act."
        ),
    },
    {
        "topic": "pest_control",
        "source": "ICAR — Pest Management for Wheat Crops in Central India",
        "text": (
            "Common wheat pests in Maharashtra and Madhya Pradesh: "
            "1. Aphids (Sitobion avenae): Appear during ear-head stage. Spray Imidacloprid 17.8 SL @ 0.5ml/litre. "
            "2. Leaf Rust (Puccinia triticina): Brown pustules on leaves. Spray Propiconazole 25 EC @ 0.1%. "
            "3. Termites: Apply Chlorpyrifos 20 EC near base at sowing. "
            "4. Pink Stem Borer: Light traps in November. Spray Cartap hydrochloride 50 SP. "
            "Preventive measures: Seed treatment with Vitavax 75 WP @ 2.5g/kg seed. "
            "Use resistant varieties: HD-2967, GW-322, LOK-1 for central zone. "
            "Crop rotation with legumes (chickpea, lentil) breaks pest cycles."
        ),
    },
    {
        "topic": "organic_farming",
        "source": "NPOP Guidelines, APEDA — Organic Farming Practices Manual",
        "text": (
            "To start organic farming: "
            "1. Stop chemical inputs immediately and begin a 3-year conversion period (In-Conversion 1, 2, 3). "
            "2. Prepare compost using farm waste, cow dung, and crop residue — target C:N ratio of 25:1. "
            "3. Use Jeevamrutha (fermented microbial culture): 200L water + 10kg cow dung + 10L cow urine + "
            "2kg jaggery + 2kg pulse flour + handful of soil. Ferment 48 hours. Apply per acre. "
            "4. Apply Panchagavya as foliar spray: cow dung + cow urine + milk + curd + ghee, fermented 7 days. "
            "5. Use green manuring with dhaincha (Sesbania) or sun hemp (Crotalaria juncea) — "
            "fixes 60-80 kg nitrogen per hectare. "
            "6. Get certified through NPOP (National Programme for Organic Production) via APEDA-accredited agencies. "
            "Cost of certification: ₹5,000-15,000 for small farms. "
            "Premium: Organic produce fetches 20-40% higher prices in domestic and 50-100% in export markets."
        ),
    },
    {
        "topic": "drip_irrigation",
        "source": "IARI Extension Bulletin — Micro-Irrigation for Indian Agriculture",
        "text": (
            "Drip irrigation saves 30-50% water and increases yield by 20-30% compared to flood irrigation. "
            "System components: Water source → Pump → Filter (sand/disc) → Mainline (PVC 63mm) → "
            "Sub-mainline (PVC 50mm) → Laterals (LDPE 12/16mm) → Drippers (2/4/8 LPH). "
            "Spacing: Cotton — 150cm row × 45cm dripper. Sugarcane — 150cm × 60cm. Vegetables — 60cm × 30cm. "
            "Fertigation: Use water-soluble fertilizers (19:19:19, 13:0:45, Calcium Nitrate). "
            "Inject via venture injector or fertilizer tank. Never mix Calcium with Sulphate fertilizers. "
            "Government subsidy: 55% for general farmers, 70% for SC/ST and small/marginal under PMKSY-PDMC. "
            "Apply through mahadbt.maharashtra.gov.in (Maharashtra) or respective state portals. "
            "Maintenance: Flush laterals monthly, clean filters weekly, check for clogging."
        ),
    },
    {
        "topic": "soil_health",
        "source": "Soil Health Card Scheme — Dept. of Agriculture & Farmers' Welfare",
        "text": (
            "Get a free Soil Health Card from the government. Test every 2 years at designated labs. "
            "Key parameters measured: pH, Electrical Conductivity (EC), Organic Carbon (OC), "
            "Available Nitrogen (N), Phosphorus (P), Potassium (K), Sulphur (S), Zinc (Zn), Boron (B), Iron (Fe). "
            "Ideal ranges for Maharashtra black soil: pH 6.5-8.0, OC > 0.5%, N > 280 kg/ha, "
            "P > 25 kg/ha, K > 280 kg/ha. "
            "To improve organic carbon: Apply FYM (5-10 tonnes/hectare), vermi-compost (2-3 tonnes/ha), "
            "green manure with dhaincha. Target OC > 0.75% in 3 years. "
            "Crop rotation with legumes (gram, tur, moong) fixes nitrogen naturally — "
            "saves ₹2,000-3,000/ha on urea. "
            "Avoid over-tilling — adopt zero-till or minimum tillage. Saves diesel, retains moisture, "
            "improves soil structure. Government subsidy available on Happy Seeder (80% subsidy)."
        ),
    },
    {
        "topic": "water_management",
        "source": "CWRDM & ICAR — Water Management in Rainfed Agriculture",
        "text": (
            "Rainwater harvesting: Build farm ponds (30m × 30m × 3m) to capture ~27 lakh litres. "
            "Lined pond cost: ₹1.5-3 lakh. Subsidy available under MGNREGA (90 person-days) and PMKSY. "
            "Mulching reduces evaporation by 25-30%. Use crop residue (free) or plastic mulch (₹8,000/ha). "
            "Black plastic mulch for vegetables, silver mulch for pest repellence. "
            "Crop water requirements (total seasonal): "
            "Wheat 450mm, Cotton 700mm, Sugarcane 1800mm, Soybean 450mm, Onion 550mm, Rice 1200mm. "
            "Schedule irrigation based on crop ET (evapotranspiration) — use IWM app or local KVK advisory. "
            "Critical irrigation stages: Wheat — CRI + flowering + milking. Rice — transplanting + tillering + flowering. "
            "Use tensiometer (₹500-1000) or capacitance sensor for precision scheduling. "
            "Deficit irrigation strategy: Apply 80% of full requirement during vegetative stage — "
            "saves 20% water with only 5-8% yield reduction."
        ),
    },
    {
        "topic": "pm_kisan",
        "source": "PM-KISAN Official Guidelines — Ministry of Agriculture",
        "text": (
            "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) provides ₹6,000 per year to eligible farmer families. "
            "Payment: 3 instalments of ₹2,000 each (April-July, August-November, December-March). "
            "Direct Benefit Transfer (DBT) into Aadhaar-linked bank account. "
            "Eligibility: All land-holding farmer families (husband, wife, and minor children). "
            "No minimum land requirement. "
            "Exclusions: Institutional landholders, former/present constitutional post holders, "
            "government employees (above multi-tasking staff), income-tax payers, professionals "
            "(doctors, engineers, lawyers, CAs) with monthly income > ₹10,000. "
            "Required documents: Aadhaar card (mandatory), bank account with IFSC code, "
            "land ownership records (7/12 extract in Maharashtra). "
            "Application: Online at pmkisan.gov.in or via Common Service Centre (CSC). "
            "Status check: Enter Aadhaar number or mobile number on pmkisan.gov.in/beneficiarystatus. "
            "Helpline: 155261 or 011-24300606 (Mon-Fri, 9:30 AM - 6:00 PM)."
        ),
    },
    {
        "topic": "pmfby",
        "source": "PMFBY Operational Guidelines — Dept. of Agriculture",
        "text": (
            "Pradhan Mantri Fasal Bima Yojana (PMFBY) provides comprehensive crop insurance. "
            "Premium rates: Kharif crops — 2% of sum insured. Rabi crops — 1.5%. "
            "Commercial and horticultural crops — 5% (actuarial rate, govt pays rest). "
            "Coverage: All food crops, oilseeds, annual commercial and horticultural crops. "
            "Risks covered: Natural calamities (drought, flood, hailstorm, cyclone, fire), "
            "pest/disease attacks, post-harvest losses up to 14 days after harvest. "
            "Claim process: Report crop loss within 72 hours via Crop Insurance App, "
            "toll-free number 1800-200-7710, or nearest bank/CSC/agriculture office. "
            "Assessment methods: CCE (Crop Cutting Experiments), satellite remote sensing, "
            "drones, smartphones — Smart Sampling for faster settlement. "
            "Enrolment period: Kharif — April 1 to July 31. Rabi — October 1 to December 31. "
            "Apply via: Bank branch (for loanee farmers — auto-enrolled), CSC, insurance company, "
            "or PMFBY portal/app (for non-loanee farmers). Voluntary since Kharif 2020."
        ),
    },
    {
        "topic": "cotton_farming",
        "source": "Central Institute for Cotton Research (CICR) — Best Practices",
        "text": (
            "Cotton cultivation best practices for Maharashtra: "
            "Recommended varieties: Bt Cotton hybrids (Bollgard II), NHH-44 (non-Bt). "
            "Sowing time: June 15 to July 15 (after onset of monsoon). "
            "Spacing: 90cm × 60cm (rain-fed), 120cm × 60cm (irrigated). Seed rate: 2.5 kg/ha. "
            "Fertiliser: Basal — 25 kg N + 50 kg P2O5 + 25 kg K2O per ha. "
            "Top dress: 25 kg N at 30 days and 25 kg N at 60 days after sowing. "
            "Irrigation: First at 3 weeks if no rain. Critical stages: Square formation, flowering, boll development. "
            "Picking: Start when 60% bolls are open. Pick early morning when dew is absent. "
            "Avoid mixing grades (fully open vs partially open). "
            "Market: Sell through CCI (Cotton Corporation of India) at MSP or through FPO for premium. "
            "MSP 2025-26: ₹7,521/quintal (medium staple), ₹7,921/quintal (long staple)."
        ),
    },
    {
        "topic": "wheat_farming",
        "source": "ICAR-IIWBR — Wheat Cultivation Guide for Central Zone",
        "text": (
            "Wheat cultivation guide for Maharashtra and central India: "
            "Recommended varieties: HD-2967 (timely sown), HD-3086 (late sown), GW-322 (irrigated). "
            "Sowing: Timely — November 1-25. Late — December 1-25. Seed rate: 100 kg/ha (timely), 125 kg/ha (late). "
            "Seed treatment: Vitavax 75 WP @ 2.5g/kg + Chlorpyrifos 20 EC @ 4ml/kg. "
            "Fertiliser: 120-60-40 kg NPK/ha (irrigated). Apply 1/2 N + full P + full K at sowing, "
            "remaining N split at first (CRI) and second irrigation. "
            "Irrigation schedule (5 irrigations): CRI (21 days), tillering (40-45 days), "
            "late jointing (60-65 days), flowering (80-85 days), milking (100-105 days). "
            "Weed management: Pendimethalin 30 EC @ 1.0 kg/ha pre-emergence. "
            "Harvest: When grain moisture drops below 20%. Use combine harvester. "
            "Yield potential: 45-55 quintals/ha (irrigated), 25-30 quintals/ha (rain-fed). "
            "MSP 2025-26: ₹2,425 per quintal."
        ),
    },
    {
        "topic": "soybean_farming",
        "source": "ICAR-IISR — Soybean Production Technology",
        "text": (
            "Soybean cultivation for Maharashtra (major soybean state): "
            "Recommended varieties: JS-9560, JS-2034 (Vidarbha), MACS-1407, KDS-726. "
            "Sowing: June 20 to July 10 (with onset of monsoon). Don't delay beyond July 15. "
            "Seed rate: 65-75 kg/ha. Row spacing: 30-45 cm. "
            "Seed treatment: Thiram 2g + Carbendazim 1g per kg seed. Then Rhizobium + PSB inoculation. "
            "Fertiliser: 30-60-30 kg NPK/ha as basal. No top dressing needed (nitrogen-fixing crop). "
            "Weed management: Pendimethalin 30 EC @ 1.0 kg/ha pre-emergence (within 2 days of sowing). "
            "Critical pest: Girdle beetle — Spray Profenofos 50 EC @ 1.5 ml/litre at pod formation. "
            "Harvest: When 95% pods turn brown and leaves shed. Moisture should be below 13%. "
            "Avoid delay — pod shattering losses increase after maturity. "
            "Yield: 20-25 quintals/ha. MSP 2025-26: ₹4,892 per quintal."
        ),
    },
    {
        "topic": "government_schemes",
        "source": "Ministry of Agriculture — Compiled Scheme Directory 2025",
        "text": (
            "Key government schemes for farmers (2025-26): "
            "1. PM-KISAN: ₹6,000/year in 3 instalments. All land-holding families eligible. "
            "2. PMFBY: Crop insurance at 2% (Kharif), 1.5% (Rabi) premium. "
            "3. PM-KUSUM: Solar pumps with 60% subsidy (30% central + 30% state). "
            "4. KCC (Kisan Credit Card): Crop loans at 4% interest (with 3% interest subvention). "
            "Max limit: ₹3 lakh. Apply at any commercial/cooperative bank. "
            "5. PMKSY (Per Drop More Crop): 55-70% subsidy on micro-irrigation (drip/sprinkler). "
            "6. Soil Health Card: Free soil testing every 2 years. "
            "7. e-NAM: Sell produce online across 1,000+ mandis. Register at enam.gov.in. "
            "8. NFSM (National Food Security Mission): Seed, fertilizer, and equipment subsidies. "
            "9. RKVY (Rashtriya Krishi Vikas Yojana): State-level flexible agriculture funding. "
            "10. Maharashtra-specific: Mahadbt portal (mahadbt.maharashtra.gov.in) — "
            "consolidated portal for 40+ state agricultural subsidies."
        ),
    },
]


def ingest_knowledge():
    """Embed and upsert all knowledge documents into Pinecone."""
    from src.config import settings
    from src.services.embeddings_service import get_embeddings
    from src.services.vector_store import get_vector_store

    embeddings_svc = get_embeddings()
    vector_store = get_vector_store()

    if not embeddings_svc.is_available:
        logger.error("❌ Gemini Embeddings not available. Set GEMINI_API_KEY in .env")
        sys.exit(1)

    if not vector_store.is_available:
        logger.error("❌ Pinecone Vector Store not available. Set PINECONE_API_KEY in .env")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  🌾 KrishiMandal — Knowledge Ingestion")
    print(f"  Documents: {len(KNOWLEDGE_DOCUMENTS)}")
    print(f"  Vector DB: Pinecone ({settings.PINECONE_INDEX_NAME})")
    print(f"  Embeddings: Gemini ({settings.GEMINI_EMBEDDING_MODEL})")
    print(f"{'='*60}\n")

    # Step 1: Generate embeddings
    print("📐 Generating Gemini embeddings...")
    texts = [doc["text"] for doc in KNOWLEDGE_DOCUMENTS]
    embeddings = embeddings_svc.embed_batch(texts, task_type="retrieval_document")
    print(f"   ✅ Generated {len(embeddings)} embeddings (dim={len(embeddings[0])})")

    # Step 2: Prepare metadata
    metadatas = [
        {
            "topic": doc["topic"],
            "source": doc["source"],
        }
        for doc in KNOWLEDGE_DOCUMENTS
    ]

    # Step 3: Upsert into Pinecone
    print("📤 Upserting into Pinecone...")
    count = vector_store.upsert_documents(
        texts=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        namespace="knowledge",
    )
    print(f"   ✅ Upserted {count} vectors")

    # Step 4: Verify
    print("\n📊 Index stats:")
    stats = vector_store.get_index_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")

    # Step 5: Test search
    print("\n🔍 Test search: 'how to control pests in wheat'")
    query_emb = embeddings_svc.embed_query("how to control pests in wheat")
    results = vector_store.search(query_emb, top_k=3)
    for i, r in enumerate(results, 1):
        print(f"   {i}. [score={r['score']:.3f}] {r['source']}")
        print(f"      {r['text'][:120]}...")

    print(f"\n{'='*60}")
    print(f"  ✅ Knowledge ingestion complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    ingest_knowledge()
