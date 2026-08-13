"""AG-7 Citizen Assistance — multilingual chat, on-demand (not part of the
ingest pipeline). Uses LLM if available; canned fallback otherwise.
Includes minimal RAG: retrieves relevant official-guidance docs and grounds
the reply in them, whichever path (LLM or fallback) is taken.
"""
from __future__ import annotations
import re
from collections import Counter
from app import llm

FALLBACK_MSG = (
    "Emergency guidance is currently limited (LLM unavailable). "
    "For immediate danger, contact local emergency services directly."
)

# Synthetic "official guidance" corpus — small enough for naive keyword
# retrieval (see _retrieve). Not real regulatory text.
CORPUS = [
    {
        "id": "flood-evacuate",
        "text": (
            "If water is rising, evacuate immediately to higher ground or the "
            "nearest designated shelter. Do not walk or drive through moving "
            "flood water. Turn off electricity at the mains before leaving if safe to do so."
        ),
    },
    {
        "id": "shelter-intake",
        "text": (
            "On arrival at a shelter, register at the intake desk with your name, "
            "household members, and any medical needs. Shelters provide water, basic "
            "meals, and a sleeping area; pets may require a separate holding area."
        ),
    },
    {
        "id": "medical-triage",
        "text": (
            "Medical triage prioritizes patients by injury severity, not arrival order. "
            "Life-threatening bleeding, breathing difficulty, or unconsciousness are treated "
            "first. Walking, alert patients with minor injuries should expect to wait."
        ),
    },
    {
        "id": "cyclone-warning",
        "text": (
            "During a cyclone warning, secure loose outdoor objects, stock drinking water "
            "and non-perishable food for 72 hours, and stay away from windows. Follow local "
            "authority instructions on evacuation routes if a mandatory order is issued."
        ),
    },
    {
        "id": "missing-person",
        "text": (
            "To report a missing person, contact the incident command post or local police "
            "with the person's name, last known location, and a recent photo if available. "
            "Do not wait 24 hours to report a missing person during an active disaster."
        ),
    },
    {
        "id": "power-outage",
        "text": (
            "During an extended power outage, keep refrigerator and freezer doors closed, "
            "use flashlights instead of candles to avoid fire risk, and never run a generator "
            "indoors or in an enclosed space due to carbon monoxide danger."
        ),
    },
    {
        "id": "first-aid-bleeding",
        "text": (
            "To control severe bleeding, apply firm, direct pressure to the wound with a clean "
            "cloth and keep the injured area elevated above the heart until medical help arrives."
        ),
    },
]

_WORD_RE = re.compile(r"[a-zA-Z]+")


def _tokenize(text: str) -> Counter:
    return Counter(w.lower() for w in _WORD_RE.findall(text))


# ponytail: naive keyword overlap, not semantic search — fine while CORPUS
# stays small and queries share vocabulary with the docs. Upgrade to real
# embeddings once the corpus outgrows ~20-30 docs or keyword matching starts
# missing paraphrases (e.g. "leave now" not matching "evacuate").
def _retrieve(query: str, k: int = 2) -> list[dict]:
    query_words = set(_tokenize(query))
    scored = []
    for doc in CORPUS:
        overlap = len(query_words & set(_tokenize(doc["text"])))
        if overlap:
            scored.append((overlap, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [doc for _, doc in scored[:k]]


def chat(message: str, language: str = "en") -> dict:
    retrieved = _retrieve(message, k=2)
    if llm.available():
        context = "\n".join(f"- {d['text']}" for d in retrieved)
        prompt = (
            f"You are an emergency assistance chatbot. Respond in language code '{language}'. "
            f"Be calm, concise, and actionable. Use the following official guidance as context "
            f"if relevant:\n{context}\n\nCitizen message: {message}"
        )
        reply = llm.reason(prompt, max_tokens=200)
    else:
        reply = FALLBACK_MSG
        if retrieved:
            reply = f"{reply} {retrieved[0]['text']}"
    return {"reply": reply, "language": language, "llm_used": llm.available()}
