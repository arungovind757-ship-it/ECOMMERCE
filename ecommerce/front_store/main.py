import sys
import os
import math
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

# Add storefront dir to path to ensure relative imports of database/models work
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from database import get_db, init_db
from models import Product, Order, OrderItem, OrderStatus, StoreSetting, Offer

app = FastAPI(title="AeroShield PVC Blinds Storefront")

# Dynamically resolve paths relative to storefront folder
STATIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "static"))
TEMPLATES_DIR = os.path.abspath(os.path.join(BASE_DIR, "templates"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Helper to fetch shop info and active offer
def get_store_context(db: Session):
    settings = db.query(StoreSetting).first()
    if not settings:
        settings = StoreSetting(
            phone="+91 98765 43210",
            email="sales@pvcblinds.com",
            address="123 Blinds Factory Road, Bengaluru, KA 560001",
            working_hours="Mon - Sat: 9:00 AM - 7:00 PM",
            announcement_banner="Monsoon Special Offer! Get flat 10% off on all frosted privacy orders today!"
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        
    offer = db.query(Offer).filter(Offer.is_active == 1).first()
    return settings, offer

# Custom helper to calculate blind configuration
def calculate_blind_config(width_ft: float, height_ft: float, base_price: float, quantity: int):
    # Validation checks
    if width_ft < 1.0:
        raise ValueError("Width must be at least 1.0 ft.")
    if height_ft < 1.0:
        raise ValueError("Height must be at least 1.0 ft.")
    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    # 1. Automatic Roll Selection Algorithm (Removed 6 ft raw roll option)
    if width_ft <= 4.0:
        roll_width_used = 4.0
        panels_count = 1
    elif width_ft <= 5.0:
        roll_width_used = 5.0
        panels_count = 1
    else:
        panels_count = math.ceil(width_ft / 5.0)
        panel_width = width_ft / panels_count
        if panel_width <= 4.0:
            roll_width_used = 4.0
        else:
            roll_width_used = 5.0

    # 2. Price Calculation
    total_selected_roll_width = roll_width_used * panels_count
    billable_sqft = total_selected_roll_width * height_ft
    actual_sqft = width_ft * height_ft
    
    # Minimum Billable Area of 10.0 sq. ft. per blind
    chargeable_sqft = max(billable_sqft, 10.0)
    total_price = chargeable_sqft * base_price * quantity

    # Configuration Note
    if panels_count == 1:
        note = f"1 panel of {width_ft:.2f} ft cut from a standard {roll_width_used:.0f} ft roll."
    else:
        panel_width_ft = width_ft / panels_count
        panel_width_in = panel_width_ft * 12
        note = f"{panels_count} panels of {panel_width_ft:.2f} ft ({panel_width_in:.1f} in) cut from standard {roll_width_used:.0f} ft rolls."

    return {
        "roll_used": roll_width_used,
        "panels_count": panels_count,
        "billable_sqft": billable_sqft,
        "actual_sqft": actual_sqft,
        "total_price": total_price,
        "configuration_note": note
    }

# Pydantic schemas for APIs
class PriceCalcRequest(BaseModel):
    product_id: int
    width_ft: float
    height_ft: float
    quantity: int = Field(..., ge=1)

class CheckoutItem(BaseModel):
    product_id: int
    section_name: Optional[str] = "Main Section"
    width_ft: float
    height_ft: float
    color: str
    quantity: int = Field(..., ge=1)

class CheckoutRequest(BaseModel):
    customer_name: str = Field(..., min_length=1)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    shipping_address: str = Field(..., min_length=5)
    items: List[CheckoutItem]
    coupon_code: Optional[str] = None

# Storefront HTML view
@app.get("/", response_class=HTMLResponse)
def view_storefront(request: Request, db: Session = Depends(get_db)):
    products = db.query(Product).all()
    # Format prices for templates
    for p in products:
        p.formatted_price = f"₹ {p.base_price:.2f}"
    settings, offer = get_store_context(db)
    return templates.TemplateResponse(request, "customer.html", {"products": products, "settings": settings, "offer": offer})

# Quote Calculator page view
@app.get("/quote", response_class=HTMLResponse)
def view_quote_calculator(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.formatted_price = f"₹ {product.base_price:.2f}"
    settings, offer = get_store_context(db)
    
    # Load all products and map their colors to their respective product specs
    all_products = db.query(Product).all()
    color_map = []
    for p in all_products:
        for c in p.colors.split(","):
            color_name = c.strip()
            if color_name:
                color_map.append({
                    "color": color_name,
                    "product_id": p.id,
                    "base_price": p.base_price,
                    "product_name": p.name
                })
                
    offer_dict = None
    if offer:
        offer_dict = {
            "id": offer.id,
            "title": offer.title,
            "discount_percent": offer.discount_percent,
            "code": offer.code,
            "description": offer.description,
            "is_active": offer.is_active
        }
                
    return templates.TemplateResponse(
        request, 
        "quote.html", 
        {
            "product": product,
            "color_map": color_map,
            "settings": settings,
            "offer": offer_dict
        }
    )

# Price Calculator API
@app.post("/api/calculate-price")
def calculate_price(payload: PriceCalcRequest, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        calc = calculate_blind_config(
            width_ft=payload.width_ft,
            height_ft=payload.height_ft,
            base_price=product.base_price,
            quantity=payload.quantity
        )
        return calc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Checkout API
@app.post("/api/checkout")
def checkout(payload: CheckoutRequest, db: Session = Depends(get_db)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    try:
        total_amount = 0.0
        order_items = []
        
        for item in payload.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product with id {item.product_id} not found")
            
            calc = calculate_blind_config(
                width_ft=item.width_ft,
                height_ft=item.height_ft,
                base_price=product.base_price,
                quantity=item.quantity
            )
            
            order_item = OrderItem(
                product_id=item.product_id,
                section_name=item.section_name or "Main Section",
                width_ft=item.width_ft,
                height_ft=item.height_ft,
                panels_count=calc["panels_count"],
                roll_width_used=calc["roll_used"],
                color=item.color,
                quantity=item.quantity,
                price=calc["total_price"]
            )
            total_amount += calc["total_price"]
            order_items.append(order_item)
            
        # Apply coupon code if active and valid
        if payload.coupon_code:
            from sqlalchemy import func
            offer = db.query(Offer).filter(
                func.upper(Offer.code) == func.upper(payload.coupon_code), 
                Offer.is_active == 1
            ).first()
            if offer:
                discount = (offer.discount_percent / 100.0) * total_amount
                total_amount -= discount
            
        new_order = Order(
            customer_name=payload.customer_name,
            email=payload.email,
            phone=payload.phone,
            shipping_address=payload.shipping_address,
            total_amount=total_amount,
            status=OrderStatus.PENDING,
            items=order_items
        )
        
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        
        return {"status": "success", "order_id": new_order.id, "total_price": total_amount}
        
    except HTTPException as e:
        db.rollback()
        raise e
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during checkout: {e}")
