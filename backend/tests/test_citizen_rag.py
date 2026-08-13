"""Unit tests for AG-7 (Citizen Assistance) minimal RAG retrieval (tracker 3.2).

Runs on the llm.available() == False path so it's deterministic and doesn't
need a live LLM call (no GROQ_API_KEY in the test environment).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from agents import citizen
from app import llm

assert not llm.available(), "expected llm unavailable in test env (no GROQ_API_KEY)"


def test_fallback_reply_includes_retrieved_doc_text_for_flood_query():
    result = citizen.chat("how do I evacuate during a flood", language="en")
    docs = citizen._retrieve("how do I evacuate during a flood", k=1)
    assert docs, "expected at least one retrieved doc"
    assert docs[0]["text"] in result["reply"]


def test_retrieve_ranks_flood_doc_above_unrelated_docs():
    docs = citizen._retrieve("flood evacuate water rising", k=1)
    assert "flood" in docs[0]["text"].lower()


def test_language_passthrough_unchanged():
    result = citizen.chat("hello", language="ta")
    assert result["language"] == "ta"
    assert result["llm_used"] is False
