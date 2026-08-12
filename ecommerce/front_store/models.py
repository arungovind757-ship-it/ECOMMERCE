import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Enum, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class OrderStatus(str, enum.Enum):
    PENDING = "Pending"
    IN_PRODUCTION = "In Production"
    DISPATCHED = "Dispatched"
    DELIVERED = "Delivered"

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    article_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    base_price = Column(Float, nullable=False)  # Base Price per SqFt in INR
    colors = Column(String(200), nullable=False)  # Comma-separated list of colors
    image_url = Column(String(255), nullable=True)
    
    order_items = relationship("OrderItem", back_populates="product")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    shipping_address = Column(Text, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    section_name = Column(String(100), nullable=True)  # Section label (e.g. Balcony Front)
    width_ft = Column(Float, nullable=False)
    height_ft = Column(Float, nullable=False)
    panels_count = Column(Integer, nullable=False)
    roll_width_used = Column(Float, nullable=False)
    color = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class StoreSetting(Base):
    __tablename__ = "store_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(50), default="+91 98765 43210", nullable=False)
    email = Column(String(100), default="sales@pvcblinds.com", nullable=False)
    address = Column(Text, default="123 Blinds Factory Road, Bengaluru, KA 560001", nullable=False)
    working_hours = Column(String(100), default="Mon - Sat: 9:00 AM - 7:00 PM", nullable=False)
    announcement_banner = Column(String(200), default="Monsoon Special Offer! Get flat 10% off on all frosted privacy orders today!", nullable=True)
    storefront_title = Column(String(150), default="AeroShield PVC Weather Blinds", nullable=False)
    storefront_description = Column(Text, default="Configure custom heavy-duty PVC roller blinds cut to your exact balcony and patio specifications.", nullable=False)

class Offer(Base):
    __tablename__ = "offers"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    discount_percent = Column(Float, nullable=False, default=0.0)
    code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Integer, default=1, nullable=False)  # 1 = active, 0 = inactive
