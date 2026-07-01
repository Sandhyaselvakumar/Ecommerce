# Multichannel Ecommerce Order & Inventory Sync API

A REST API that simulates the core integration pattern used by ecommerce
operations platforms (Shopify/Amazon/Flipkart-style order sync,
BaseLinker-style multichannel inventory management): marketplace
channels push order webhooks in, inventory is reconciled centrally in
real time, and every stock change is logged for audit and automation.

## Why this project

Built to demonstrate the exact workflow ecommerce SaaS integration
platforms run in production:
1. A marketplace (Shopify, Amazon, Flipkart, website) sends a webhook
   when an order is placed.
2. The API validates stock availability, deducts inventory, and
   records the order — atomically, per SKU.
3. Every inventory change is written to an auditable sync log
   (channel, SKU, before/after quantity, reason).
4. A low-stock endpoint flags SKUs that need reordering.
5. A restock endpoint mirrors a supplier/warehouse sync event.

## Tech Stack

- **Python 3.11 + FastAPI** — REST API framework
- **SQLAlchemy ORM** — models are MySQL-compatible (swap the connection
  string to `mysql+pymysql://` for production; SQLite is used here for
  zero-setup local runs)
- **Pydantic** — request/response validation
- **Docker** — containerized for deployment

## Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/products` | Register a product/SKU with starting inventory |
| GET | `/products` | List all products and current stock |
| GET | `/products/low-stock` | List SKUs at/below reorder threshold |
| POST | `/webhooks/{channel}/orders` | Simulated marketplace webhook — ingests an order, deducts inventory, logs the sync |
| GET | `/orders` | List orders, optionally filtered by channel |
| GET | `/sync-logs` | Full audit trail of every inventory change |
| POST | `/inventory/{sku}/restock` | Manual restock (supplier/warehouse sync) |
| GET | `/analytics/summary` | Aggregated JSON — orders by channel, inventory, low-stock, recent sync activity |
| GET | `/dashboard` | Live JS analytics dashboard (charts + tables over `/analytics/summary`) |

`channel` supports: `shopify`, `amazon`, `flipkart`, `website`.

## Analytics Dashboard

A lightweight vanilla-JS + Chart.js dashboard is served at `/dashboard`,
built on top of the `/analytics/summary` endpoint. It shows revenue
and order count per channel, current inventory levels (colour-flagged
at low stock), a live low-stock alert table, and a recent sync-activity
feed — the kind of at-a-glance operational view an implementation
team would use to sanity-check a client's integration.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# API docs: http://127.0.0.1:8000/docs
```

## Run with Docker

```bash
docker build -t ecom-sync-api .
docker run -p 8000:8000 ecom-sync-api
```

## Example: simulate an incoming Shopify order

```bash
curl -X POST http://127.0.0.1:8000/webhooks/shopify/orders \
  -H "Content-Type: application/json" \
  -d '{
        "external_order_id": "SHOP-1001",
        "customer_name": "Anita Rao",
        "items": [{"sku": "TSHIRT-BLK-M", "quantity": 45, "unit_price": 499}]
      }'
```

This deducts inventory for `TSHIRT-BLK-M`, creates the order, and
writes a sync log entry — the same pattern used to keep stock accurate
across every channel a seller lists on.
