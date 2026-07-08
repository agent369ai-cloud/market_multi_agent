
import logging
from typing import List, Dict, Any, Optional

import cohere
import httpx
import psycopg
from psycopg.rows import dict_row
from pinecone import Pinecone

from config import settings

logger = logging.getLogger(__name__)

_cohere_client = cohere.ClientV2(api_key=settings.COHERE_API_KEY) if settings.COHERE_API_KEY else None
_pinecone_index = (
    Pinecone(api_key=settings.PINECONE_API_KEY).Index(settings.PINECONE_INDEX_NAME)
    if settings.PINECONE_API_KEY
    else None
)

_FALLBACK_DOCS = [
    {
        "source": "azure_ai_search",
        "source_type": "document",
        "confidence": 0.91,
        "content": "Policy states that category mapping is required for product visibility in JP marketplace.",
        "metadata": {"doc_id": "POL-101", "locale": "jp"}
    },
    {
        "source": "azure_ai_search",
        "source_type": "document",
        "confidence": 0.87,
        "content": "Listings may not appear if indexing is delayed after feed submission.",
        "metadata": {"doc_id": "POL-205", "locale": "en"}
    }
]

def search_documents(query: str) -> List[Dict[str, Any]]:
    if not _cohere_client or not _pinecone_index:
        logger.warning("search_documents: Cohere/Pinecone not configured, using fallback docs")
        return _FALLBACK_DOCS

    try:
        embedding = _cohere_client.embed(
            texts=[query],
            model=settings.COHERE_EMBED_MODEL,
            input_type="search_query",
            embedding_types=["float"],
        ).embeddings.float_[0]

        matches = _pinecone_index.query(
            vector=embedding, top_k=3, include_metadata=True
        ).matches

        return [
            {
                "source": "pinecone",
                "source_type": "document",
                "confidence": round(match.score, 4),
                "content": match.metadata["content"],
                "metadata": {
                    "doc_id": match.id,
                    "locale": match.metadata.get("locale"),
                    "category": match.metadata.get("category"),
                },
            }
            for match in matches
        ]
    except Exception:
        logger.exception("search_documents: Cohere/Pinecone call failed for query=%r, using fallback docs", query)
        return _FALLBACK_DOCS

_FALLBACK_SQL = [
    {
        "source": "postgresql",
        "source_type": "sql",
        "confidence": 0.97,
        "content": "Merchant listing status is pending_moderation and category is null.",
        "metadata": {"table": "merchant_listings", "row_id": None}
    }
]

def query_sql(merchant_id: str, route: str = "visibility_issue") -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(settings.DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                if route == "campaign_issue":
                    cur.execute(
                        "SELECT row_id, campaign_id, campaign_status, rejection_reason "
                        "FROM campaign_records WHERE merchant_id = %s "
                        "ORDER BY updated_at DESC",
                        (merchant_id,),
                    )
                    rows = cur.fetchall()
                    return [
                        {
                            "source": "postgresql",
                            "source_type": "sql",
                            "confidence": 0.97,
                            "content": (
                                f"Campaign {row['campaign_id']} for merchant {merchant_id} is "
                                f"{row['campaign_status']}"
                                + (f" (reason: {row['rejection_reason']})" if row["rejection_reason"] else "")
                            ),
                            "metadata": {"table": "campaign_records", "row_id": row["row_id"]},
                        }
                        for row in rows
                    ]
                else:
                    cur.execute(
                        "SELECT row_id, product_id, listing_status, category, locale "
                        "FROM merchant_listings WHERE merchant_id = %s "
                        "ORDER BY updated_at DESC",
                        (merchant_id,),
                    )
                    rows = cur.fetchall()
                    return [
                        {
                            "source": "postgresql",
                            "source_type": "sql",
                            "confidence": 0.97,
                            "content": (
                                f"Merchant {merchant_id} listing {row['product_id']} status is "
                                f"{row['listing_status']} and category is "
                                f"{row['category'] or 'null'} (locale: {row['locale']})"
                            ),
                            "metadata": {"table": "merchant_listings", "row_id": row["row_id"]},
                        }
                        for row in rows
                    ]
    except Exception:
        logger.exception("query_sql: Postgres query failed for merchant_id=%r route=%r, using fallback", merchant_id, route)
        return _FALLBACK_SQL

_FALLBACK_API = [
    {
        "source": "listing_status_api",
        "source_type": "api",
        "confidence": 0.93,
        "content": "Last indexing job status could not be retrieved from the listing API.",
        "metadata": {"timestamp": None}
    }
]

def call_listing_api(merchant_id: str) -> List[Dict[str, Any]]:
    try:
        resp = httpx.get(
            f"{settings.LISTING_API_BASE_URL}/listings/{merchant_id}/indexing-status",
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()

        content = (
            f"Last indexing job for merchant {merchant_id} (product {data['product_id']}) "
            f"{data['last_indexing_job_status']}"
        )
        if data.get("failure_reason"):
            content += f": {data['failure_reason']}"

        return [
            {
                "source": "listing_status_api",
                "source_type": "api",
                "confidence": 0.93,
                "content": content,
                "metadata": {
                    "timestamp": data.get("checked_at"),
                    "status": data.get("last_indexing_job_status"),
                },
            }
        ]
    except Exception:
        logger.exception("call_listing_api: request to listing service failed for merchant_id=%r, using fallback", merchant_id)
        return _FALLBACK_API

def load_memory(session_id: Optional[str]) -> List[Dict[str, Any]]:
    if not session_id:
        return []

    try:
        with psycopg.connect(settings.DATABASE_URL, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT query, final_answer, route, created_at FROM conversation_turns "
                    "WHERE session_id = %s ORDER BY created_at DESC LIMIT 3",
                    (session_id,),
                )
                rows = cur.fetchall()

        return [
            {
                "source": "memory_store",
                "source_type": "memory",
                "confidence": 0.79,
                "content": (
                    f"Merchant previously asked (route: {row['route']}): \"{row['query']}\". "
                    f"Answer given: {(row['final_answer'] or '')[:200]}"
                ),
                "metadata": {"session_id": session_id, "asked_at": row["created_at"].isoformat()},
            }
            for row in rows
        ]
    except Exception:
        logger.exception("load_memory: Postgres query failed for session_id=%r, returning no memory", session_id)
        return []

def save_memory(session_id: Optional[str], merchant_id: str, route: str, query: str, final_answer: str) -> None:
    if not session_id:
        return

    try:
        with psycopg.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO conversation_turns (session_id, merchant_id, route, query, final_answer) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (session_id, merchant_id, route, query, final_answer),
                )
    except Exception:
        logger.exception("save_memory: failed to persist turn for session_id=%r merchant_id=%r", session_id, merchant_id)