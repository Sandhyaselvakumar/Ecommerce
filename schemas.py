from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .models import ChannelName


class ProductCreate(BaseModel):
    sku: str
    name: str
    price: float
    stock_quantity: int = 0
    low_stock_threshold: int = 5


class ProductOut(ProductCreate):
    id: int

    class Config:
        from_attributes = True


class OrderItemIn(BaseModel):
    sku: str
    quantity: int
    unit_price: float


class WebhookOrderIn(BaseModel):
    """Payload shape mimics a simplified marketplace webhook (Shopify/Amazon style)."""
    external_order_id: str
    customer_name: Optional[str] = None
    items: List[OrderItemIn]


class OrderOut(BaseModel):
    id: int
    channel: ChannelName
    external_order_id: str
    customer_name: Optional[str]
    status: str
    total_amount: float
    created_at: datetime

    class Config:
        from_attributes = True


class SyncLogOut(BaseModel):
    id: int
    channel: ChannelName
    sku: str
    previous_qty: int
    new_qty: int
    reason: str
    synced_at: datetime

    class Config:
        from_attributes = True
