import sys
import os
import shutil
import time
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Add admin dir to path to ensure relative imports of database/models work
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from database import get_db, init_db
from models import Product, Order, OrderItem, OrderStatus, StoreSetting, Offer

app = FastAPI(title="Samrudhi PVC Blinds Admin Dashboard")

# Dynamically resolve paths relative to admin folder
STATIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "static"))
TEMPLATES_DIR = os.path.abspath(os.path.join(BASE_DIR, "templates"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["STOREFRONT_URL"] = os.getenv("STOREFRONT_URL", "https://ecommerce3-rxkq.onrender.com")

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

# Pydantic schemas for APIs
class StatusUpdateRequest(BaseModel):
    status: OrderStatus

# Redirect root path to dashboard
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/admin")

# Admin Dashboard HTML view
@app.get("/admin", response_class=HTMLResponse)
def view_dashboard(request: Request, db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    products = db.query(Product).all()
    settings, offer = get_store_context(db)
    
    # Calculate simple KPI metrics
    total_revenue = sum(o.total_amount for o in orders)
    pending_orders = sum(1 for o in orders if o.status == OrderStatus.PENDING)
    in_production_orders = sum(1 for o in orders if o.status == OrderStatus.IN_PRODUCTION)
    completed_orders = sum(1 for o in orders if o.status in (OrderStatus.DISPATCHED, OrderStatus.DELIVERED))
    
    # Calculate material requirements (linear feet) for active orders (No 6 ft roll option)
    roll_4_needed = 0.0
    roll_5_needed = 0.0
    
    def format_meas(val: float) -> str:
        rounded = round(val, 1)
        if rounded.is_integer():
            return str(int(rounded))
        return str(rounded)

    # Format each order item with cutting plan and detailed strings
    for order in orders:
        order.formatted_total = f"₹ {order.total_amount:,.2f}"
        order.formatted_date = order.created_at.strftime("%Y-%m-%d %H:%M")
        for item in order.items:
            # Total panels to cut = panels per blind * quantity of blinds
            item.total_panels_to_cut = item.panels_count * item.quantity
            
            panel_width_ft = item.width_ft / item.panels_count
            item.width_inches = panel_width_ft * 12
            item.height_inches = item.height_ft * 12
            item.formatted_price = f"₹ {item.price:,.2f}"
            
            # Rounded formatted properties for templates (removing trailing zeros)
            item.formatted_width_ft = format_meas(item.width_ft)
            item.formatted_height_ft = format_meas(item.height_ft)
            item.formatted_roll_width = format_meas(item.roll_width_used)
            item.formatted_width_inches = format_meas(item.width_inches)
            item.formatted_height_inches = format_meas(item.height_inches)
            
            # Calculate per-panel and total panel SqFt in feet
            panel_sqft = item.roll_width_used * item.height_ft
            total_item_sqft = panel_sqft * item.total_panels_to_cut
            item.formatted_panel_sqft = format_meas(panel_sqft)
            item.formatted_total_item_sqft = format_meas(total_item_sqft)
            
            # Accumulate material demands for Active orders
            if order.status in (OrderStatus.PENDING, OrderStatus.IN_PRODUCTION):
                linear_ft_item = item.height_ft * item.total_panels_to_cut
                if item.roll_width_used == 4.0:
                    roll_4_needed += linear_ft_item
                elif item.roll_width_used == 5.0:
                    roll_5_needed += linear_ft_item
            
    return templates.TemplateResponse(
        request,
        "dashboard.html", 
        {
            "orders": orders,
            "products": products,
            "settings": settings,
            "offer": offer,
            "total_revenue": f"₹ {total_revenue:,.2f}",
            "pending_orders": pending_orders,
            "in_production_orders": in_production_orders,
            "completed_orders": completed_orders,
            "roll_4_needed": f"{format_meas(roll_4_needed)} ft",
            "roll_5_needed": f"{format_meas(roll_5_needed)} ft",
            "OrderStatus": OrderStatus,
            "is_admin": True
        }
    )

# Admin API to update order status
@app.post("/api/admin/order/{order_id}/status")
def update_order_status(order_id: int, payload: StatusUpdateRequest, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = payload.status
    db.commit()
    return {"status": "success", "new_status": order.status}

# Admin API to update product catalog (including photo upload)
@app.post("/api/admin/product/{product_id}/update")
async def update_product(
    product_id: int,
    name: str = Form(...),
    article_code: str = Form(...),
    base_price: float = Form(...),
    colors: str = Form(...),
    description: Optional[str] = Form(""),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if base_price <= 0.0:
        raise HTTPException(status_code=400, detail="Base price must be a positive number.")
    
    # Check if article code is already taken by another product
    existing = db.query(Product).filter(Product.article_code == article_code, Product.id != product_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"A product with article code '{article_code}' already exists.")
    
    # Validate photo extension first if uploaded
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            raise HTTPException(status_code=400, detail="Only JPG, JPEG, or PNG images are allowed.")
    
    product.name = name
    product.article_code = article_code
    product.base_price = base_price
    product.colors = colors
    product.description = description
    
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        # Save photo into root static folder since it is shared
        static_images_dir = os.path.join(STATIC_DIR, "images")
        os.makedirs(static_images_dir, exist_ok=True)
        filename = f"uploaded_product_{product_id}{ext}"
        file_path = os.path.join(static_images_dir, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        
        # Save image URL relative path with cache buster query string
        product.image_url = f"/static/images/{filename}?t={int(time.time())}"
        
    db.commit()
    return {"status": "success", "message": "Product updated successfully"}

# Admin API to create a new product catalog item (including photo upload)
@app.post("/api/admin/product/create")
async def create_product(
    name: str = Form(...),
    article_code: str = Form(...),
    base_price: float = Form(...),
    colors: str = Form(...),
    description: Optional[str] = Form(""),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    existing = db.query(Product).filter(Product.article_code == article_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"A product with article code '{article_code}' already exists.")
        
    if base_price <= 0.0:
        raise HTTPException(status_code=400, detail="Base price must be a positive number.")
        
    # Validate photo extension first if uploaded
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            raise HTTPException(status_code=400, detail="Only JPG, JPEG, or PNG images are allowed.")
            
    product = Product(
        name=name,
        article_code=article_code,
        base_price=base_price,
        colors=colors,
        description=description,
        image_url="/static/images/clear_blind.jpg"
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        # Save photo into root static folder since it is shared
        static_images_dir = os.path.join(STATIC_DIR, "images")
        os.makedirs(static_images_dir, exist_ok=True)
        filename = f"uploaded_product_{product.id}{ext}"
        file_path = os.path.join(static_images_dir, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        
        product.image_url = f"/static/images/{filename}?t={int(time.time())}"
        db.commit()
        
    return {"status": "success", "message": "Product created successfully", "product_id": product.id}

# Admin API to update store info settings
@app.post("/api/admin/settings/update")
def update_settings(
    phone: str = Form(...),
    email: str = Form(...),
    address: str = Form(...),
    working_hours: str = Form(...),
    announcement_banner: Optional[str] = Form(""),
    storefront_title: str = Form(...),
    storefront_description: str = Form(...),
    db: Session = Depends(get_db)
):
    settings = db.query(StoreSetting).first()
    if not settings:
        settings = StoreSetting()
        db.add(settings)
    
    settings.phone = phone
    settings.email = email
    settings.address = address
    settings.working_hours = working_hours
    settings.announcement_banner = announcement_banner
    settings.storefront_title = storefront_title
    settings.storefront_description = storefront_description
    
    db.commit()
    return {"status": "success", "message": "Settings updated successfully"}

# Admin API to update special offers
@app.post("/api/admin/offers/update")
def update_offers(
    title: str = Form(...),
    discount_percent: float = Form(...),
    code: str = Form(...),
    description: Optional[str] = Form(""),
    is_active: int = Form(1),
    db: Session = Depends(get_db)
):
    if discount_percent < 0.0 or discount_percent > 100.0:
        raise HTTPException(status_code=400, detail="Discount percentage must be between 0% and 100%.")

    offer = db.query(Offer).first()
    if not offer:
        offer = Offer()
        db.add(offer)
        
    offer.title = title
    offer.discount_percent = discount_percent
    offer.code = code
    offer.description = description
    offer.is_active = is_active
    
    db.commit()
    return {"status": "success", "message": "Offers updated successfully"}
