"""AG-7 Citizen Assistance (Phase 15). `CitizenAssistant` depends on a
`Retriever` interface; `KeywordRetriever` (naive keyword overlap over a
7-document synthetic corpus, ported from V1) is the only implementation —
a documented development fallback, not production RAG. `VectorStore` is an
interface only: real embeddings-based retrieval is DEFERRED. The assistant
never fabricates incident-specific system information — if nothing is
retrieved and the LLM is unavailable, it says so explicitly."""

import re
from collections import Counter
from typing import Protocol

from app.agents.citizen_assistance.schemas import ChatRequest, ChatResponse
from app.infrastructure.llm import LLMService

NOT_AVAILABLE_MSG = "Information is not available for this request. For immediate danger, contact local emergency services directly."

# Synthetic "official guidance" corpus — small enough for naive keyword
# retrieval. Not real regulatory text.
CORPUS = [
    {"id": "flood-evacuate", "text": (
        "If water is rising, evacuate immediately to higher ground or the "
        "nearest designated shelter. Do not walk or drive through moving "
        "flood water. Turn off electricity at the mains before leaving if safe to do so."
    )},
    {"id": "shelter-intake", "text": (
        "On arrival at a shelter, register at the intake desk with your name, "
        "household members, and any medical needs. Shelters provide water, basic "
        "meals, and a sleeping area; pets may require a separate holding area."
    )},
    {"id": "medical-triage", "text": (
        "Medical triage prioritizes patients by injury severity, not arrival order. "
        "Life-threatening bleeding, breathing difficulty, or unconsciousness are treated "
        "first. Walking, alert patients with minor injuries should expect to wait."
    )},
    {"id": "cyclone-warning", "text": (
        "During a cyclone warning, secure loose outdoor objects, stock drinking water "
        "and non-perishable food for 72 hours, and stay away from windows. Follow local "
        "authority instructions on evacuation routes if a mandatory order is issued."
    )},
    {"id": "missing-person", "text": (
        "To report a missing person, contact the incident command post or local police "
        "with the person's name, last known location, and a recent photo if available. "
        "Do not wait 24 hours to report a missing person during an active disaster."
    )},
    {"id": "power-outage", "text": (
        "During an extended power outage, keep refrigerator and freezer doors closed, "
        "use flashlights instead of candles to avoid fire risk, and never run a generator "
        "indoors or in an enclosed space due to carbon monoxide danger."
    )},
    {"id": "first-aid-bleeding", "text": (
        "To control severe bleeding, apply firm, direct pressure to the wound with a clean "
        "cloth and keep the injured area elevated above the heart until medical help arrives."
    )},
]

_WORD_RE = re.compile(r"[a-zA-Z]+")


def _tokenize(text: str) -> Counter:
    return Counter(w.lower() for w in _WORD_RE.findall(text))


class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 2) -> list[dict]: ...


class DocumentStore(Protocol):
    def documents(self) -> list[dict]: ...


class VectorStore(Protocol):
    """Interface only — DEFERRED. No embeddings-backed implementation
    exists yet; add one here (and swap it into CitizenAssistant) without
    changing the agent's call site."""

    def similarity_search(self, query: str, k: int) -> list[dict]: ...


class KeywordRetriever:
    """ponytail: naive keyword overlap, not semantic search — fine while
    CORPUS stays small and queries share vocabulary with the docs. Upgrade
    to real embeddings once the corpus outgrows ~20-30 docs or keyword
    matching starts missing paraphrases (e.g. "leave now" vs "evacuate")."""

    def __init__(self, corpus: list[dict] | None = None):
        self._corpus = corpus or CORPUS

    def retrieve(self, query: str, k: int = 2) -> list[dict]:
        query_words = set(_tokenize(query))
        scored = []
        for doc in self._corpus:
            overlap = len(query_words & set(_tokenize(doc["text"])))
            if overlap:
                scored.append((overlap, doc))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [doc for _, doc in scored[:k]]


class CitizenAssistant:
    def __init__(self, retriever: Retriever | None = None, llm: LLMService | None = None):
        self._retriever = retriever or KeywordRetriever()
        self._llm = llm

    def chat(self, request: ChatRequest) -> ChatResponse:
        retrieved = self._retriever.retrieve(request.message, k=2)

        if self._llm is not None:
            context = "\n".join(f"- {d['text']}" for d in retrieved)
            prompt = (
                f"You are an emergency assistance chatbot. Respond in language code '{request.language}'. "
                f"Be calm, concise, and actionable. Use the following official guidance as context "
                f"if relevant:\n{context}\n\nCitizen message: {request.message}"
            )
            llm_result = self._llm.reason(prompt, max_tokens=200)
            if llm_result.status == "SUCCESS":
                return ChatResponse(
                    reply=llm_result.content,
                    language=request.language,
                    reasoning_mode="llm",
                    sources=[d["id"] for d in retrieved],
                )

        if not retrieved:
            return ChatResponse(reply=NOT_AVAILABLE_MSG, language=request.language, reasoning_mode="unavailable", sources=[])

        return ChatResponse(
            reply=retrieved[0]["text"],
            language=request.language,
            reasoning_mode="retrieval_fallback",
            sources=[retrieved[0]["id"]],
        )
