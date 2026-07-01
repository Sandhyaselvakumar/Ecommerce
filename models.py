from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base


class ChannelName(str, enum.Enum):
    shopify = "shopify"
    amazon = "amazon"
    flipkart = "flipkart"
    website = "website"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer, nullable=False, default=5)

    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(Enum(ChannelName), nullable=False)
    external_order_id = Column(String(128), nullable=False)
    customer_name = Column(String(255), nullable=True)
    status = Column(String(32), nullable=False, default="received")
    total_amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(Enum(ChannelName), nullable=False)
    sku = Column(String(64), nullable=False)
    previous_qty = Column(Integer, nullable=False)
    new_qty = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=False)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())
