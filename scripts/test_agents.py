"""Exercise every agent node in the graph, plus edge cases HTTP queries can't reach.

Run with: python scripts/test_agents.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import critic_agent, guardrail_agent
from graph_flow import build_graph

graph = build_graph()

SCENARIOS = [
    {
        "name": "visibility_issue (with session -> memory hits)",
        "state": {
            "merchant_id": "M123",
            "language": "en",
            "query": "Why is my product not visible in Japanese search results?",
            "session_id": "S001",
        },
    },
    {
        "name": "campaign_issue (with session)",
        "state": {
            "merchant_id": "M456",
            "language": "en",
            "query": "My campaign was rejected during moderation, why?",
            "session_id": "S002",
        },
    },
    {
        "name": "billing_issue (no session -> memory empty)",
        "state": {
            "merchant_id": "M789",
            "language": "en",
            "query": "My payment for seller fees keeps failing.",
            "session_id": None,
        },
    },
    {
        "name": "general_support (no route keywords -> sql empty)",
        "state": {
            "merchant_id": "M999",
            "language": "en",
            "query": "How do I contact my account manager?",
            "session_id": "S003",
        },
    },
]


def run_full_pipeline():
    print("=" * 70)
    print("FULL PIPELINE RUNS (router -> planner -> memory -> rag -> sql")
    print("                     -> synthesizer -> critic -> guardrail)")
    print("=" * 70)

    for scenario in SCENARIOS:
        result = graph.invoke(scenario["state"])
        evidence_by_type = {}
        for item in result.get("evidence", []):
            evidence_by_type.setdefault(item["source_type"], 0)
            evidence_by_type[item["source_type"]] += 1

        print(f"\n--- {scenario['name']} ---")
        print(f"query:        {scenario['state']['query']}")
        print(f"route:        {result.get('route')}")
        print(f"plan:         {result.get('plan')}")
        print(f"evidence:     {evidence_by_type or '(none)'}")
        print(f"critic issues:{result.get('critic_issues')}")
        print(f"approved:     {result.get('approved')}")
        print(f"status:       {'success' if result.get('approved') else 'needs_review'}")
        print(f"final_answer: {(result.get('final_answer') or '(none, rejected by critic)')[:200]}...")


def run_edge_cases():
    print("\n" + "=" * 70)
    print("EDGE CASES (agent functions tested directly, not via a live query)")
    print("=" * 70)

    # critic_agent should reject when there's no evidence at all
    rejected = critic_agent({"draft_answer": "no evidence here", "evidence": []})
    print(f"\ncritic_agent with empty evidence -> approved={rejected['approved']}, "
          f"issues={rejected['critic_issues']}")
    assert rejected["approved"] is False

    # critic_agent should reject when the required heading is missing
    rejected2 = critic_agent({"draft_answer": "some answer with no steps", "evidence": [{"x": 1}]})
    print(f"critic_agent with missing heading -> approved={rejected2['approved']}, "
          f"issues={rejected2['critic_issues']}")
    assert rejected2["approved"] is False

    # critic_agent should approve when both conditions are satisfied
    approved = critic_agent({"draft_answer": "Recommended next steps: do X", "evidence": [{"x": 1}]})
    print(f"critic_agent with evidence + heading -> approved={approved['approved']}")
    assert approved["approved"] is True

    # guardrail_agent should redact internal-only content
    redacted = guardrail_agent({"draft_answer": "This is internal_only information."})
    print(f"guardrail_agent redaction -> {redacted['final_answer']!r}")
    assert "internal_only" not in redacted["final_answer"]
    assert "[redacted]" in redacted["final_answer"]

    print("\nAll edge-case assertions passed.")


if __name__ == "__main__":
    run_full_pipeline()
    run_edge_cases()
