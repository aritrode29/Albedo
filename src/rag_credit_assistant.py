#!/usr/bin/env python3
"""
Robust RAG assistant with credit templates, binary evidence classification, and strict citations.

This module wraps the existing LEED RAG indices and provides:
- Credit-specific response templates pulled from the extracted credit catalog
- A lightweight binary evidence classifier that scores whether provided evidence supports a credit
- Strict citation formatting so every returned statement includes an explicit source trail

The assistant is designed for demo/CLI usage but can also be imported by APIs.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from difflib import get_close_matches
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from llm_rag import FAISSIndex, KnowledgeBaseBuilder, KnowledgeChunk
from leed_rag_api import LEEDRAGAPI

logger = logging.getLogger(__name__)


def _clean_text(text: str, limit: int = 360) -> str:
    """Compact whitespace and truncate for display."""
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


@dataclass
class Citation:
    """Structured citation for strict attribution."""

    label: str
    source: str
    pages: List[Any]
    score: float
    snippet: str


class CreditTemplateLibrary:
    """Loads and provides credit-aligned response templates."""

    def __init__(self, credit_paths: Optional[Sequence[str]] = None):
        self.credit_paths = credit_paths or [
            "data/raw/leed_credits.json",
            "outputs/leed_credits.json",
            "outputs/leed_guide_credits.json",
        ]
        self.credits: List[Dict[str, Any]] = []
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        for path in self.credit_paths:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    items = json.load(f)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load credit definitions from %s: %s", path, exc)
                continue
            if isinstance(items, list):
                self.credits.extend(items)
        for credit in self.credits:
            code = (credit.get("credit_code") or "").strip()
            name = (credit.get("credit_name") or "").strip()
            key = code or name
            if key:
                self._index[key.lower()] = credit
        logger.info("Loaded %d credit templates", len(self._index))

    def _match_credit(self, identifier: str) -> Optional[Dict[str, Any]]:
        key = identifier.lower().strip()
        if key in self._index:
            return self._index[key]
        if not self._index:
            return None
        candidates = get_close_matches(key, self._index.keys(), n=1, cutoff=0.6)
        if candidates:
            return self._index[candidates[0]]
        return None

    def build_template(self, identifier: str, fallback_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return a structured template for the requested credit."""
        credit = self._match_credit(identifier) if identifier else None
        meta = credit or (fallback_metadata or {})

        title = f"{meta.get('credit_code', 'LEED Credit')} – {meta.get('credit_name', 'Unspecified')}"
        intent = meta.get("intent") or "Document how the project meets the stated intent of this credit."
        requirements = meta.get("requirements") or []
        documentation = meta.get("documentation") or meta.get("submittals") or []

        return {
            "title": title,
            "intent": intent,
            "requirements": requirements or [
                "List the quantitative and qualitative requirements for this credit.",
            ],
            "documentation": documentation or [
                "Attach narrative description, calculations, and any required forms.",
            ],
            "calculation_notes": meta.get("calculation_notes")
            or "Provide calculations that demonstrate compliance; cite baselines and assumptions.",
            "qa": [
                "Confirm prerequisite alignment.",
                "Highlight uncertainties and assumptions.",
                "Map each evidence item to a citation.",
            ],
        }


class BinaryEvidenceClassifier:
    """Scores whether provided evidence supports the retrieved credit context."""

    def __init__(self, embedder: SentenceTransformer, positive_threshold: float = 0.42, average_threshold: float = 0.32):
        self.embedder = embedder
        self.positive_threshold = positive_threshold
        self.average_threshold = average_threshold

    def classify(self, evidence_text: str, retrieved: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        if not evidence_text or not evidence_text.strip():
            return {
                "decision": "unknown",
                "confidence": 0.0,
                "reason": "No evidence provided.",
            }
        if not retrieved:
            return {
                "decision": "unknown",
                "confidence": 0.0,
                "reason": "No retrieved context to compare against.",
            }

        evidence_embedding = self.embedder.encode([evidence_text], convert_to_tensor=False)[0]
        context_embeddings = self.embedder.encode(
            [r.get("text", "") for r in retrieved],
            convert_to_tensor=False,
        )

        def _norm(vec: np.ndarray) -> np.ndarray:
            denom = np.linalg.norm(vec)
            return vec / denom if denom else vec

        evidence_embedding = _norm(np.asarray(evidence_embedding, dtype="float32"))
        context_embeddings = np.asarray([_norm(np.asarray(v, dtype="float32")) for v in context_embeddings])
        scores = context_embeddings @ evidence_embedding

        top_idx = int(np.argmax(scores))
        top_score = float(scores[top_idx])
        avg_score = float(np.mean(scores))

        supported = top_score >= self.positive_threshold or avg_score >= self.average_threshold
        decision = "supported" if supported else "insufficient"
        rationale = (
            f"Top similarity {top_score:.3f}, average {avg_score:.3f} "
            f"(thresholds: top>={self.positive_threshold}, avg>={self.average_threshold})."
        )

        return {
            "decision": decision,
            "confidence": float(max(top_score, avg_score)),
            "reason": rationale,
            "top_chunk": _clean_text(retrieved[top_idx].get("text", ""), 180),
            "source": retrieved[top_idx].get("metadata", {}),
        }


class RAGInferenceEngine:
    """RAG retrieval with strict citation handling."""

    def __init__(self, index_path: str = "models/leed_knowledge_base"):
        self.index_path = index_path
        self.api = LEEDRAGAPI(index_path=index_path)
        self.embedder: Optional[SentenceTransformer] = None
        self.loaded = self._load()

    def _load(self) -> bool:
        loaded = self.api.load_system()
        if loaded:
            self.embedder = self.api.embedder
            return True

        # Fallback: build a minimal index from the local credit JSON
        fallback_path = "data/raw/leed_credits.json"
        if not os.path.exists(fallback_path):
            logger.error("No RAG indices and no fallback credit file found.")
            return False

        logger.warning("RAG indices missing; building minimal fallback index from %s", fallback_path)
        builder = KnowledgeBaseBuilder()
        chunks = builder.build_from_leed_credits(fallback_path)
        chunks = builder.generate_embeddings(chunks)
        faiss_index = FAISSIndex()
        built = faiss_index.build_index(chunks)
        if not built:
            logger.error("Failed to build fallback FAISS index.")
            return False
        # Persist for downstream use
        os.makedirs("models", exist_ok=True)
        faiss_index.save_index(self.index_path)
        # Reload through the standard path to keep metadata consistent
        loaded = self.api.load_system()
        self.embedder = self.api.embedder
        return loaded

    def retrieve(self, query: str, k: int = 5, sources: Optional[List[str]] = None) -> Tuple[List[Dict[str, Any]], List[Citation]]:
        results = self.api.search(query, k=k, sources=sources)
        citations: List[Citation] = []
        for res in results:
            metadata = res.get("metadata", {}) or {}
            label = metadata.get("credit_code") or metadata.get("credit_name") or metadata.get("category") or "LEED Reference"
            source = metadata.get("source") or metadata.get("_index", "knowledge-base")
            pages = metadata.get("pages") or []
            citations.append(
                Citation(
                    label=str(label),
                    source=str(source),
                    pages=pages if isinstance(pages, list) else [pages],
                    score=float(res.get("score", 0.0)),
                    snippet=_clean_text(res.get("text", "")),
                )
            )
        return results, citations


class RAGCreditAssistant:
    """Orchestrates retrieval, templating, classification, and citation formatting."""

    def __init__(self):
        self.engine = RAGInferenceEngine()
        self.templates = CreditTemplateLibrary()
        self.embedder = self.engine.embedder
        self.classifier = BinaryEvidenceClassifier(self.embedder) if self.embedder else None

    @property
    def ready(self) -> bool:
        return bool(self.engine.loaded and self.embedder)

    def _format_citations(self, citations: Sequence[Citation]) -> str:
        lines = []
        for idx, citation in enumerate(citations, 1):
            pages = f" | pages: {citation.pages}" if citation.pages else ""
            lines.append(
                f"[{idx}] {citation.label} — source: {citation.source}{pages} "
                f"(score {citation.score:.3f}) :: {citation.snippet}"
            )
        return "\n".join(lines) if lines else "No citations available."

    def _format_answer(self, query: str, retrieved: Sequence[Dict[str, Any]], citations: Sequence[Citation]) -> str:
        if not retrieved:
            return "No relevant information found for your query."
        bullets = []
        for idx, res in enumerate(retrieved, 1):
            summary = _clean_text(res.get("text", ""), 220)
            metadata = res.get("metadata", {}) or {}
            credit_label = metadata.get("credit_code") or metadata.get("credit_name") or metadata.get("category")
            prefix = f"{credit_label} — " if credit_label else ""
            bullets.append(f"- {prefix}{summary} [CIT-{idx}]")
        return f"Query: {query}\n" + "\n".join(bullets)

    def analyze(
        self,
        query: str,
        evidence_text: Optional[str] = None,
        sources: Optional[List[str]] = None,
        k: int = 4,
    ) -> Dict[str, Any]:
        retrieved, citations = self.engine.retrieve(query, k=k, sources=sources)

        classification: Optional[Dict[str, Any]] = None
        if evidence_text and self.classifier:
            classification = self.classifier.classify(evidence_text, retrieved)

        template_identifier = ""
        if retrieved:
            md = retrieved[0].get("metadata", {}) or {}
            template_identifier = md.get("credit_code") or md.get("credit_name") or ""
        template = self.templates.build_template(template_identifier or query, retrieved[0].get("metadata") if retrieved else {})

        answer = self._format_answer(query, retrieved, citations)
        citation_block = self._format_citations(citations)

        return {
            "query": query,
            "answer": answer,
            "citations": citation_block,
            "raw_citations": [citation.__dict__ for citation in citations],
            "template": template,
            "evidence_classification": classification,
            "retrieved": retrieved,
        }


def demo_runs() -> None:
    """Run a focused demo showcasing the new capabilities."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    assistant = RAGCreditAssistant()
    if not assistant.ready:
        print("❌ RAG assistant is not ready. Ensure indices exist or run build scripts.")
        return

    scenarios = [
        {
            "query": "EA Credit Optimize Energy Performance requirements",
            "evidence": "Our project model shows 18% cost savings relative to ASHRAE 90.1-2016 with submetering on major end uses.",
        },
        {
            "query": "Water efficiency indoor fixtures prerequisites",
            "evidence": "The design replaces existing fixtures with EPA WaterSense certified faucets and dual-flush toilets.",
        },
    ]

    for scenario in scenarios:
        print("\n" + "=" * 90)
        print(f"🔍 Query: {scenario['query']}")
        result = assistant.analyze(scenario["query"], scenario["evidence"], k=3)
        print("\n📄 Answer with citations:\n")
        print(result["answer"])
        print("\n🔗 Citations:\n")
        print(result["citations"])
        if result.get("evidence_classification"):
            print("\n✅ Evidence classifier:")
            print(json.dumps(result["evidence_classification"], indent=2))
        print("\n🧩 Credit template:")
        print(json.dumps(result["template"], indent=2))


if __name__ == "__main__":
    demo_runs()
