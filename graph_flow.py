from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

from agents import (
    router_agent,
    planner_agent,
    memory_agent,
    rag_agent,
    sql_agent,
    synthesizer_agent,
    critic_agent,
    guardrail_agent,
    memory_writer_agent,
)

class GraphState(TypedDict, total=False):
    merchant_id: str
    language: str
    query: str
    session_id: str
    route: str
    plan: List[str]
    memory_results: List[Dict[str, Any]]
    doc_results: List[Dict[str, Any]]
    sql_results: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    draft_answer: str
    approved: bool
    critic_issues: List[str]
    final_answer: str

def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("router", router_agent)
    graph.add_node("planner", planner_agent)
    graph.add_node("memory", memory_agent)
    graph.add_node("rag", rag_agent)
    graph.add_node("sql", sql_agent)
    graph.add_node("synthesizer", synthesizer_agent)
    graph.add_node("critic", critic_agent)
    graph.add_node("guardrail", guardrail_agent)
    graph.add_node("memory_writer", memory_writer_agent)

    graph.set_entry_point("router")
    graph.add_edge("router", "planner")
    graph.add_edge("planner", "memory")
    graph.add_edge("memory", "rag")
    graph.add_edge("rag", "sql")
    graph.add_edge("sql", "synthesizer")
    graph.add_edge("synthesizer", "critic")

    def critic_decision(state: GraphState):
        if state.get("approved"):
            return "guardrail"
        return END

    graph.add_conditional_edges("critic", critic_decision, {
        "guardrail": "guardrail",
        END: END
    })

    graph.add_edge("guardrail", "memory_writer")
    graph.add_edge("memory_writer", END)

    return graph.compile()