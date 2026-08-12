from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Product, StoreSetting, Offer

import os
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "blinds.db"))
    DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        # Enable WAL mode for SQLite to handle concurrent reads/writes from two applications safely
        from sqlalchemy import text
        db.execute(text("PRAGMA journal_mode=WAL;"))
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Seed products
        if db.query(Product).count() == 0:
            products = [
                Product(
                    article_code="PVC-CLR-120",
                    name="Classic Clear PVC Blind",
                    description="High-transparency heavy-duty PVC blind. Ideal for balconies and outdoor patios to protect against rain, wind, and dust while retaining clear outdoor visibility.",
                    base_price=120.0,
                    colors="Transparent Clear",
                    image_url="/static/images/clear_blind.jpg"
                ),
                Product(
                    article_code="PVC-CHR-140",
                    name="Charcoal Tinted PVC Blind",
                    description="Premium charcoal-tinted PVC blind. Offers excellent heat reduction, UV shielding, and glare cut-off, making it perfect for sun-exposed spaces.",
                    base_price=140.0,
                    colors="Charcoal Tinted,Amber Tinted",
                    image_url="/static/images/tinted_blind.jpg"
                ),
                Product(
                    article_code="PVC-FRST-155",
                    name="Frosted Privacy PVC Blind",
                    description="Frosted/translucent PVC privacy blind. Diffuses harsh sun glare while allowing soft ambient light through. High privacy level.",
                    base_price=155.0,
                    colors="Frosted Translucent,Opal White",
                    image_url="/static/images/frosted_blind.jpg"
                )
            ]
            db.add_all(products)
            db.commit()
            
        # Seed store settings
        if db.query(StoreSetting).count() == 0:
            default_setting = StoreSetting(
                phone="+91 98765 43210",
                email="sales@pvcblinds.com",
                address="123 Blinds Factory Road, Bengaluru, KA 560001",
                working_hours="Mon - Sat: 9:00 AM - 7:00 PM",
                announcement_banner="Monsoon Special Offer! Get flat 10% off on all frosted privacy orders today!",
                storefront_title="AeroShield PVC Weather Blinds",
                storefront_description="Configure custom heavy-duty PVC roller blinds cut to your exact balcony and patio specifications."
            )
            db.add(default_setting)
            db.commit()
            
        # Seed default offer
        if db.query(Offer).count() == 0:
            default_offer = Offer(
                title="Monsoon Special 10% Off",
                discount_percent=10.0,
                code="MONSOON10",
                description="Get 10% discount on orders today",
                is_active=1
            )
            db.add(default_offer)
            db.commit()

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()
