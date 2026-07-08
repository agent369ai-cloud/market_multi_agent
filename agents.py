import logging
from typing import Dict, Any, List

from openai import OpenAI

from config import settings
from prompts import render as render_prompt
from tools import search_documents, query_sql, call_listing_api, load_memory, save_memory

logger = logging.getLogger(__name__)

groq_client = OpenAI(api_key=settings.GROQ_API_KEY, base_url=settings.GROQ_API_BASE)

def router_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state["query"].lower()

    if "visible" in query or "search" in query or "listing" in query:
        route = "visibility_issue"
    elif "campaign" in query or "rejected" in query:
        route = "campaign_issue"
    elif "payment" in query or "billing" in query:
        route = "billing_issue"
    else:
        route = "general_support"

    logger.info("router_agent: query=%r -> route=%r", state["query"], route)
    return {"route": route}

def planner_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    route = state["route"]

    if route == "visibility_issue":
        plan = [
            "load memory context",
            "search policy documents",
            "check merchant listing in SQL",
            "check indexing API status",
            "synthesize answer"
        ]
    elif route == "campaign_issue":
        plan = [
            "load memory context",
            "search campaign policy docs",
            "check campaign SQL records",
            "check moderation API",
            "synthesize answer"
        ]
    else:
        plan = [
            "load memory context",
            "search support docs",
            "synthesize answer"
        ]

    return {"plan": plan}

def memory_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    items = load_memory(state.get("session_id"))
    return {"memory_results": items}

def rag_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    docs = search_documents(state["query"])
    return {"doc_results": docs}

def sql_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    route = state["route"]
    if route in ["visibility_issue", "campaign_issue"]:
        rows = query_sql(state["merchant_id"], route)
    else:
        rows = []
    return {"sql_results": rows}

def api_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    route = state["route"]
    if route == "visibility_issue":
        api_results = call_listing_api(state["merchant_id"])
    else:
        api_results = []
    return {"api_results": api_results}

def _template_answer(query: str, route: str, evidence: List[Dict[str, Any]]) -> str:
    answer_lines = [
        f"Merchant query: {query}",
        f"Detected route: {route}",
        "Root-cause analysis based on collected evidence:"
    ]

    for item in evidence:
        answer_lines.append(f"- [{item['source_type']}] {item['content']}")

    answer_lines.extend([
        "",
        "Recommended next steps:",
        "1. Update missing category mapping.",
        "2. Re-submit product feed with required attributes.",
        "3. Trigger re-indexing and verify status in merchant dashboard."
    ])

    return "\n".join(answer_lines)

def synthesizer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    evidence = []
    evidence.extend(state.get("memory_results", []))
    evidence.extend(state.get("doc_results", []))
    evidence.extend(state.get("sql_results", []))
    evidence.extend(state.get("api_results", []))

    query = state["query"]
    route = state["route"]
    language = state.get("language", "en")
    response_language = "Japanese" if language == "jp" else "English"
    evidence_block = "\n".join(
        f"- [{item['source_type']}] {item['content']}" for item in evidence
    )

    try:
        completion = groq_client.chat.completions.create(
            model=settings.MODEL_NAME,
            temperature=settings.SYNTHESIZER_TEMPERATURE,
            max_tokens=settings.SYNTHESIZER_MAX_TOKENS,
            messages=[
                {
                    "role": "system",
                    "content": render_prompt("synthesizer_system", response_language=response_language),
                },
                {
                    "role": "user",
                    "content": (
                        f"Merchant query: {query}\n"
                        f"Detected route: {route}\n"
                        f"Evidence:\n{evidence_block or '- none'}"
                    ),
                },
            ],
        )
        draft_answer = completion.choices[0].message.content
    except Exception:
        logger.exception("synthesizer_agent: Groq call failed for query=%r, using template fallback", query)
        draft_answer = _template_answer(query, route, evidence)

    return {
        "evidence": evidence,
        "draft_answer": draft_answer
    }

def critic_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    draft = state.get("draft_answer", "")
    evidence = state.get("evidence", [])

    issues = []
    if len(evidence) == 0:
        issues.append("No evidence collected.")
    if "Recommended next steps" not in draft:
        issues.append("No actionable steps present.")

    approved = len(issues) == 0
    if not approved:
        logger.warning("critic_agent: rejected draft, issues=%s", issues)

    return {
        "approved": approved,
        "critic_issues": issues
    }

def guardrail_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    draft = state.get("draft_answer", "")
    safe_answer = draft.replace("internal_only", "[redacted]")
    return {"final_answer": safe_answer}

def memory_writer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    save_memory(
        session_id=state.get("session_id"),
        merchant_id=state["merchant_id"],
        route=state.get("route", ""),
        query=state["query"],
        final_answer=state.get("final_answer", ""),
    )
    return {}