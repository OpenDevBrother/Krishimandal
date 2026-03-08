"""
KrishiMandal — Seed the database with initial data.
Run: python -m src.seed_db
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta

from src.database import SessionLocal, init_db
from src.db_models import Crop, Farm, Farmer, InventoryItem, Notification, PriceRecord, Scheme
from src.dummy_data import MAHARASHTRA_CROPS, MAHARASHTRA_MANDIS, SCHEMES


def seed():
    init_db()
    db = SessionLocal()

    try:
        # ── Schemes (prefer real data) ────────────────────────────────────
        existing_schemes = db.query(Scheme).count()
        if existing_schemes == 0:
            # Try loading from real_schemes.json first
            real_schemes_loaded = False
            try:
                from pathlib import Path
                schemes_file = Path(__file__).parent.parent / "data" / "real_schemes.json"
                if schemes_file.exists():
                    with open(schemes_file, "r", encoding="utf-8") as f:
                        real_schemes = json.load(f)
                    for s in real_schemes:
                        deadline = None
                        if s.get("deadline"):
                            try:
                                deadline = date.fromisoformat(s["deadline"])
                            except (ValueError, TypeError):
                                deadline = None
                        db.add(Scheme(
                            id=s["id"],
                            name=s["name"],
                            benefits_inr=s["benefits_inr"],
                            deadline=deadline,
                            requirements_json=json.dumps(s.get("requirements", [])),
                            url=s.get("application_url", ""),
                            description=s.get("description", ""),
                            is_active=s.get("is_active", True),
                            eligibility_json=json.dumps(s.get("eligibility", {})),
                            category=s.get("category", "general"),
                        ))
                    db.commit()
                    print(f"Seeded {len(real_schemes)} real schemes from real_schemes.json.")
                    real_schemes_loaded = True
            except Exception as e:
                print(f"Real schemes load failed ({e}), falling back to dummy.")
                db.rollback()

            if not real_schemes_loaded:
                for s in SCHEMES:
                    db.add(Scheme(
                        id=s["id"],
                        name=s["name"],
                        benefits_inr=s["benefits"],
                        deadline=date.today() + timedelta(days=random.randint(30, 180)),
                        requirements_json=json.dumps(["Aadhaar", "Land Record", "Bank Passbook"]),
                        url=s["url"],
                        is_active=True,
                    ))
                db.commit()
                print(f"Seeded {len(SCHEMES)} dummy schemes.")
        else:
            print(f"Schemes already exist ({existing_schemes}), skipping.")

        # ── Sample farmers + farms + crops ───────────────────────────────
        sample_farmers = [
            {"id": "F1001", "name": "Rajesh Patil", "phone": "+919876543210", "lang": "hi-IN",
             "lat": 19.076, "lng": 72.877, "area": 2.5, "soil": "black", "irrigation": "borewell",
             "crop": "wheat", "variety": "HD-2967"},
            {"id": "F1002", "name": "Sunita Deshmukh", "phone": "+919876543211", "lang": "mr-IN",
             "lat": 19.997, "lng": 73.780, "area": 1.8, "soil": "red", "irrigation": "canal",
             "crop": "cotton", "variety": "BT Hybrid"},
            {"id": "F1003", "name": "Anil Jadhav", "phone": "+919876543212", "lang": "hi-IN",
             "lat": 21.146, "lng": 79.088, "area": 3.2, "soil": "alluvial", "irrigation": "drip",
             "crop": "soybean", "variety": "JS-9560"},
            {"id": "F1004", "name": "Kavita Shinde", "phone": "+919876543213", "lang": "mr-IN",
             "lat": 17.677, "lng": 75.298, "area": 1.2, "soil": "black", "irrigation": "rainfed",
             "crop": "jowar", "variety": "CSH-14"},
            {"id": "F1005", "name": "Prakash Kulkarni", "phone": "+919876543214", "lang": "hi-IN",
             "lat": 18.520, "lng": 73.856, "area": 4.0, "soil": "laterite", "irrigation": "sprinkler",
             "crop": "sugarcane", "variety": "Co-86032"},
        ]

        existing_farmers = db.query(Farmer).count()
        if existing_farmers == 0:
            for f in sample_farmers:
                farmer = Farmer(id=f["id"], name=f["name"], phone=f["phone"], preferred_language=f["lang"])
                db.add(farmer)
                db.flush()

                farm = Farm(
                    id=f"FARM-{f['id']}",
                    farmer_id=f["id"],
                    location_lat=f["lat"],
                    location_lng=f["lng"],
                    area_hectares=f["area"],
                    soil_type=f["soil"],
                    irrigation_type=f["irrigation"],
                )
                db.add(farm)
                db.flush()

                # Current crop
                db.add(Crop(
                    farm_id=farm.id,
                    crop_type=f["crop"],
                    variety=f["variety"],
                    planting_date=date.today() - timedelta(days=random.randint(40, 90)),
                    expected_harvest=date.today() + timedelta(days=random.randint(20, 60)),
                    area_hectares=f["area"] * 0.8,
                    growth_stage=random.choice(["vegetative", "flowering", "maturity"]),
                    health_score=round(random.uniform(65, 95), 1),
                    is_current=True,
                ))

                # Historical crops
                historical = [
                    ("Kharif 2025", "soybean", 12.5),
                    ("Rabi 2024-25", "wheat", 18.0),
                    ("Kharif 2024", "cotton", 8.3),
                ]
                for season, crop_type, yield_q in historical:
                    db.add(Crop(
                        farm_id=farm.id,
                        crop_type=crop_type,
                        variety="",
                        planting_date=date.today() - timedelta(days=random.randint(200, 500)),
                        area_hectares=f["area"] * 0.7,
                        growth_stage="harvested",
                        is_current=False,
                        season=season,
                        yield_quintals=yield_q,
                    ))

            db.commit()
            print(f"Seeded {len(sample_farmers)} farmers with farms and crops.")
        else:
            print(f"Farmers already exist ({existing_farmers}), skipping.")

        # ── Sample price records ─────────────────────────────────────────
        existing_prices = db.query(PriceRecord).count()
        if existing_prices == 0:
            price_bases = {
                "wheat": 2425, "cotton": 7521, "soybean": 4892, "sugarcane": 3150,
                "jowar": 3180, "bajra": 2500, "tur": 7000, "gram": 5440,
                "onion": 1800, "grapes": 4500,
            }
            records = []
            for crop in MAHARASHTRA_CROPS:
                base = price_bases.get(crop, 2500)
                for mandi in random.sample(MAHARASHTRA_MANDIS, k=5):
                    for days_ago in range(0, 30):
                        price = round(base * random.uniform(0.90, 1.12), 0)
                        records.append(PriceRecord(
                            crop=crop,
                            mandi=mandi,
                            price=price,
                            recorded_at=date.today() - timedelta(days=days_ago),
                        ))
            db.add_all(records)
            db.commit()
            print(f"Seeded {len(records)} price records.")
        else:
            print(f"Price records already exist ({existing_prices}), skipping.")

        # ── Sample inventory items ────────────────────────────────────────
        existing_inventory = db.query(InventoryItem).count()
        if existing_inventory == 0:
            inventory_items = [
                # F1001 — 6 items
                InventoryItem(farmer_id="F1001", name="Wheat Seeds (HD-2967)", category="seed", quantity=50, unit="kg", alert_threshold=10, purchase_price=45, purchase_date=date.today() - timedelta(days=60)),
                InventoryItem(farmer_id="F1001", name="DAP Fertilizer", category="fertilizer", quantity=25, unit="kg", alert_threshold=5, purchase_price=1350, purchase_date=date.today() - timedelta(days=30)),
                InventoryItem(farmer_id="F1001", name="Urea", category="fertilizer", quantity=3, unit="bags", alert_threshold=5, purchase_price=267),
                InventoryItem(farmer_id="F1001", name="Chlorpyrifos 20% EC", category="pesticide", quantity=2, unit="liters", alert_threshold=1, purchase_price=450),
                InventoryItem(farmer_id="F1001", name="Wheat Harvest (Rabi 2025)", category="harvest", quantity=18, unit="quintals", purchase_price=0),
                InventoryItem(farmer_id="F1001", name="Knapsack Sprayer", category="equipment", quantity=1, unit="units", purchase_price=1800),
                # F1002 — 2 items
                InventoryItem(farmer_id="F1002", name="BT Cotton Seeds", category="seed", quantity=5, unit="kg", alert_threshold=2, purchase_price=800),
                InventoryItem(farmer_id="F1002", name="NPK 10-26-26", category="fertilizer", quantity=30, unit="kg", alert_threshold=10, purchase_price=1200),
                # F1003 — 2 items
                InventoryItem(farmer_id="F1003", name="Soybean Seeds (JS-9560)", category="seed", quantity=40, unit="kg", alert_threshold=8, purchase_price=90),
                InventoryItem(farmer_id="F1003", name="Drip Irrigation Pipes", category="equipment", quantity=200, unit="units", purchase_price=5500),
            ]
            db.add_all(inventory_items)
            db.commit()
            print(f"Seeded {len(inventory_items)} inventory items.")
        else:
            print(f"Inventory items already exist ({existing_inventory}), skipping.")

        # ── Sample notifications ─────────────────────────────────────────
        existing_notifications = db.query(Notification).count()
        if existing_notifications == 0:
            notifications = [
                # F1001 — 10 notifications (8 unread, 2 read)
                Notification(farmer_id="F1001", type="scheme_deadline", title="PM-KISAN Deadline Approaching", message="PM-KISAN installment application deadline is in 15 days. Submit your documents now to avoid missing the deadline.", related_entity_type="scheme", related_entity_id="PMKISAN"),
                Notification(farmer_id="F1001", type="price_alert", title="Wheat Price Rising", message="Wheat prices in Pune mandi have risen 8% in the last week. Consider selling your stored wheat for maximum profit.", related_entity_type="crop", related_entity_id="wheat"),
                Notification(farmer_id="F1001", type="pest_warning", title="Aphid Alert", message="Aphid activity detected in your region. Check wheat fields and apply neem oil spray if needed."),
                Notification(farmer_id="F1001", type="inventory_alert", title="Low Stock: Urea", message="Your urea stock is running low (3 bags remaining). Restock before the next fertilizer application window.", related_entity_type="inventory_item"),
                Notification(farmer_id="F1001", type="weather_alert", title="Heatwave Warning", message="Temperatures expected to exceed 42°C for the next 3 days. Ensure adequate irrigation for your wheat crop."),
                Notification(farmer_id="F1001", type="scheme", title="PM Fasal Bima Yojana — Last Date", message="Crop insurance enrollment for Rabi season closes in 7 days. Enroll now to protect your harvest.", related_entity_type="scheme", related_entity_id="PMFBY"),
                Notification(farmer_id="F1001", type="crop", title="Harvest Ready: Wheat", message="Your wheat crop has reached maturity stage. Optimal harvest window is within the next 10 days for best quality grade."),
                Notification(farmer_id="F1001", type="subsidy", title="Subsidy Credited: PM-KISAN", message="Rs. 2,000 PM-KISAN installment has been credited to your bank account ending in 4521.", related_entity_type="scheme", related_entity_id="PMKISAN"),
                Notification(farmer_id="F1001", type="price_alert", title="Cotton Prices Surging", message="Cotton prices at Solapur mandi jumped 12% this week due to export demand. Good time to sell if you have stock.", related_entity_type="crop", related_entity_id="cotton"),
                Notification(farmer_id="F1001", type="general", title="New: AI Crop Advisory", message="KrishiMandal now offers AI-powered crop advisory. Ask questions about pest management, irrigation, and more in the chat.", is_read=True),
                # F1002 — 2 notifications
                Notification(farmer_id="F1002", type="weather_alert", title="Heavy Rain Expected", message="Heavy rainfall expected in Nashik district for the next 3 days. Protect cotton crops."),
                Notification(farmer_id="F1002", type="general", title="Scheme Enrollment", message="You have been auto-matched to 3 government schemes. Check your schemes tab."),
                # F1003 — 1 notification
                Notification(farmer_id="F1003", type="price_alert", title="Soybean Price Drop", message="Soybean prices dropped 5% in Nagpur mandi. Consider holding stock.", related_entity_type="crop", related_entity_id="soybean"),
            ]
            db.add_all(notifications)
            db.commit()
            print(f"Seeded {len(notifications)} notifications.")
        else:
            print(f"Notifications already exist ({existing_notifications}), skipping.")

        print("Database seeding complete!")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
