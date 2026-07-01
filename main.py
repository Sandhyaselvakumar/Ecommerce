"""
Multichannel Order & Inventory Sync API
----------------------------------------
Simulates the core integration pattern used by ecommerce operations
platforms (e.g. Base.com/BaseLinker style tools): marketplace channels
(Shopify, Amazon, Flipkart, website) push order webhooks in, the
platform reconciles inventory centrally, and low-stock / sync events
are logged for downstream automation (alerts, reordering, etc).
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import os

from . import models, schemas
from .database import engine, get_db, Base

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Multichannel Ecommerce Order & Inventory Sync API",
    description="Simulates webhook-driven order ingestion and centralized "
                "inventory reconciliation across marketplace channels.",
    version="1.0.0",
)


# ---------- Products / Inventory ----------

@app.post("/products", response_model=schemas.ProductOut, tags=["inventory"])
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Product).filter(models.Product.sku == product.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")
    db_product = models.Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.get("/products", response_model=List[schemas.ProductOut], tags=["inventory"])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).all()


@app.get("/products/low-stock", response_model=List[schemas.ProductOut], tags=["inventory"])
def low_stock_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    return [p for p in products if p.stock_quantity <= p.low_stock_threshold]


# ---------- Webhooks (simulated marketplace order ingestion) ----------

@app.post("/webhooks/{channel}/orders", response_model=schemas.OrderOut, tags=["webhooks"])
def receive_order_webhook(
    channel: models.ChannelName,
    payload: schemas.WebhookOrderIn,
    db: Session = Depends(get_db),
):
    """
    Simulates an inbound order webhook from a marketplace channel.
    On receipt: creates the order, decrements matching inventory, and
    writes a sync log entry per SKU so every stock change is auditable.
    """
    total = 0.0
    order = models.Order(
        channel=channel,
        external_order_id=payload.external_order_id,
        customer_name=payload.customer_name,
        status="received",
    )
    db.add(order)
    db.flush()  # get order.id before committing

    for item in payload.items:
        product = db.query(models.Product).filter(models.Product.sku == item.sku).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Unknown SKU: {item.sku}")
        if product.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock for {item.sku}: have {product.stock_quantity}, need {item.quantity}",
            )

        previous_qty = product.stock_quantity
        product.stock_quantity -= item.quantity

        db.add(models.OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item.quantity,
            unit_price=item.unit_price,
        ))
        db.add(models.SyncLog(
            channel=channel,
            sku=item.sku,
            previous_qty=previous_qty,
            new_qty=product.stock_quantity,
            reason=f"order {payload.external_order_id} fulfilled",
        ))
        total += item.quantity * item.unit_price

    order.total_amount = total
    order.status = "confirmed"
    db.commit()
    db.refresh(order)
    return order


# ---------- Orders ----------

@app.get("/orders", response_model=List[schemas.OrderOut], tags=["orders"])
def list_orders(channel: models.ChannelName | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Order)
    if channel:
        query = query.filter(models.Order.channel == channel)
    return query.order_by(models.Order.created_at.desc()).all()


# ---------- Sync / Reconciliation ----------

@app.get("/sync-logs", response_model=List[schemas.SyncLogOut], tags=["sync"])
def list_sync_logs(db: Session = Depends(get_db)):
    return db.query(models.SyncLog).order_by(models.SyncLog.synced_at.desc()).all()


@app.post("/inventory/{sku}/restock", response_model=schemas.ProductOut, tags=["inventory"])
def restock_product(sku: str, quantity: int, db: Session = Depends(get_db)):
    """Manual restock endpoint — mirrors a supplier/warehouse sync event."""
    product = db.query(models.Product).filter(models.Product.sku == sku).first()
    if not product:
        raise HTTPException(status_code=404, detail="SKU not found")
    previous_qty = product.stock_quantity
    product.stock_quantity += quantity
    db.add(models.SyncLog(
        channel=models.ChannelName.website,
        sku=sku,
        previous_qty=previous_qty,
        new_qty=product.stock_quantity,
        reason="manual restock",
    ))
    db.commit()
    db.refresh(product)
    return product


@app.get("/", tags=["meta"])
def root():
    return {
        "service": "Multichannel Ecommerce Order & Inventory Sync API",
        "docs": "/docs",
        "dashboard": "/dashboard",
    }


# ---------- Analytics (feeds the JS dashboard) ----------

@app.get("/analytics/summary", tags=["analytics"])
def analytics_summary(db: Session = Depends(get_db)):
    orders_by_channel = (
        db.query(
            models.Order.channel,
            func.count(models.Order.id).label("order_count"),
            func.coalesce(func.sum(models.Order.total_amount), 0).label("revenue"),
        )
        .group_by(models.Order.channel)
        .all()
    )

    inventory = db.query(models.Product).all()
    low_stock = [p for p in inventory if p.stock_quantity <= p.low_stock_threshold]
    recent_syncs = (
        db.query(models.SyncLog)
        .order_by(models.SyncLog.synced_at.desc())
        .limit(10)
        .all()
    )
    total_orders = db.query(func.count(models.Order.id)).scalar() or 0
    total_revenue = db.query(func.coalesce(func.sum(models.Order.total_amount), 0)).scalar() or 0

    return {
        "totals": {
            "orders": total_orders,
            "revenue": round(total_revenue, 2),
            "skus_tracked": len(inventory),
            "low_stock_count": len(low_stock),
        },
        "orders_by_channel": [
            {"channel": c, "order_count": oc, "revenue": round(rev, 2)}
            for c, oc, rev in orders_by_channel
        ],
        "inventory": [
            {"sku": p.sku, "name": p.name, "stock_quantity": p.stock_quantity,
             "low_stock_threshold": p.low_stock_threshold}
            for p in inventory
        ],
        "low_stock": [{"sku": p.sku, "name": p.name, "stock_quantity": p.stock_quantity} for p in low_stock],
        "recent_syncs": [
            {"channel": s.channel, "sku": s.sku, "previous_qty": s.previous_qty,
             "new_qty": s.new_qty, "reason": s.reason, "synced_at": s.synced_at.isoformat()}
            for s in recent_syncs
        ],
    }


# ---------- Dashboard (static JS frontend) ----------

_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/dashboard", tags=["analytics"])
def dashboard():
    return FileResponse(os.path.join(_static_dir, "dashboard.html"))
