import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import MerchantRequest, MerchantResponse, EvidenceItem
from graph_flow import build_graph
from config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)
compiled_graph = build_graph()

@app.get("/")
def health_check():
    return {"message": f"{settings.APP_NAME} is running"}

@app.post("/ask", response_model=MerchantResponse)
def ask_support(request: MerchantRequest):
    logger.info(
        "ask_support: received request merchant_id=%r session_id=%r language=%r",
        request.merchant_id, request.session_id, request.language,
    )

    initial_state = {
        "merchant_id": request.merchant_id,
        "language": request.language,
        "query": request.query,
        "session_id": request.session_id or ""
    }

    result = compiled_graph.invoke(initial_state)

    evidence_items = [
        EvidenceItem(**item) for item in result.get("evidence", [])
    ]
    status = "success" if result.get("approved", False) else "needs_review"

    logger.info(
        "ask_support: merchant_id=%r route=%r evidence_count=%d status=%r",
        request.merchant_id, result.get("route"), len(evidence_items), status,
    )

    return MerchantResponse(
        merchant_id=request.merchant_id,
        query=request.query,
        route=result.get("route", "unknown"),
        plan=result.get("plan", []),
        evidence=evidence_items,
        final_answer=result.get("final_answer", result.get("draft_answer", "")),
        status=status
    )