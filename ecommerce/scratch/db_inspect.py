import sys
sys.path.append('c:/Users/Arch Office/Downloads/ecommerce')
from database import SessionLocal, init_db
from models import Product, Order, OrderItem, StoreSetting, Offer

init_db()
db = SessionLocal()

print("PRODUCTS:")
for p in db.query(Product).all():
    print(f"ID={p.id}, Code={p.article_code}, Name={p.name}, Price={p.base_price}, Colors={p.colors}")

print("\nSTORE SETTINGS:")
settings = db.query(StoreSetting).first()
if settings:
    print(f"Title={settings.storefront_title}, Phone={settings.phone}, Email={settings.email}")
else:
    print("None")

print("\nOFFERS:")
for o in db.query(Offer).all():
    print(f"ID={o.id}, Title={o.title}, Code={o.code}, Active={o.is_active}, Discount={o.discount_percent}%")

print("\nORDERS:")
for ord in db.query(Order).all():
    print(f"ID={ord.id}, Customer={ord.customer_name}, Total={ord.total_amount}, Status={ord.status}")
    for item in ord.items:
        print(f"  Item: ProdID={item.product_id}, Section={item.section_name}, Price={item.price}, Panels={item.panels_count}, Roll={item.roll_width_used}")

db.close()
