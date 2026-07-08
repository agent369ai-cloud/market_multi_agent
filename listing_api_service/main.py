"""Standalone mock of an external merchant listing-status API.

Runs as its own process on a separate port and is called by the main
app's call_listing_api() over real HTTP, so it demonstrates a genuine
service-to-service integration even though it's backed by the same
local Postgres data as the SQL agent.

Run with: uvicorn listing_api_service.main:app --port 8100
"""
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row

from config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Listing Status API (mock external service)")


@app.get("/")
def health_check():
    return {"message": "Listing Status API is running"}


@app.get("/listings/{merchant_id}/indexing-status")
def indexing_status(merchant_id: str):
    with psycopg.connect(settings.DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT product_id, listing_status, category FROM merchant_listings "
                "WHERE merchant_id = %s ORDER BY updated_at DESC LIMIT 1",
                (merchant_id,),
            )
            row = cur.fetchone()

    if not row:
        logger.warning("indexing_status: no listing found for merchant_id=%r", merchant_id)
        raise HTTPException(status_code=404, detail=f"No listing found for merchant {merchant_id}")

    if row["listing_status"] == "pending_moderation" or not row["category"]:
        status, reason = "failed", "incomplete feed attributes: missing category mapping"
    elif row["listing_status"] == "suspended":
        status, reason = "failed", "listing is suspended"
    else:
        status, reason = "success", None

    return {
        "merchant_id": merchant_id,
        "product_id": row["product_id"],
        "last_indexing_job_status": status,
        "failure_reason": reason,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
