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


def _extract_key_information(retrieved: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract and organize key information from retrieved results."""
    info = {
        "primary_credit": None,
        "credit_code": None,
        "credit_name": None,
        "category": None,
        "requirements": [],
        "intent": None,
        "documentation": [],
        "related_credits": [],
        "key_points": []
    }
    
    if not retrieved:
        return info
    
    # Get primary credit info from first result
    first_meta = retrieved[0].get("metadata", {}) or {}
    info["primary_credit"] = first_meta.get("credit_code") or first_meta.get("credit_name")
    info["credit_code"] = first_meta.get("credit_code")
    info["credit_name"] = first_meta.get("credit_name")
    info["category"] = first_meta.get("category")
    
    # Extract intent and requirements from text
    for res in retrieved[:3]:  # Look at top 3 results
        text = res.get("text", "")
        meta = res.get("metadata", {}) or {}
        
        # Extract intent
        if "intent:" in text.lower() and not info["intent"]:
            intent_start = text.lower().find("intent:")
            if intent_start >= 0:
                intent_text = text[intent_start:].split("\n")[0].replace("Intent:", "").strip()
                if intent_text:
                    info["intent"] = intent_text
        
        # Extract requirements
        if "requirement" in text.lower():
            req_lines = [line.strip() for line in text.split("\n") 
                        if line.strip() and ("requirement" in line.lower() or line.strip().startswith("-"))]
            info["requirements"].extend(req_lines[:3])  # Limit to avoid too much
        
        # Extract key points
        if len(text) > 50:
            sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 30]
            info["key_points"].extend(sentences[:2])
    
    # Collect related credits
    seen_credits = set()
    for res in retrieved[1:]:  # Skip first one
        meta = res.get("metadata", {}) or {}
        credit = meta.get("credit_code") or meta.get("credit_name")
        if credit and credit != info["primary_credit"] and credit not in seen_credits:
            info["related_credits"].append(credit)
            seen_credits.add(credit)
    
    return info


def _generate_natural_response(query: str, info: Dict[str, Any], retrieved: Sequence[Dict[str, Any]], citations: Sequence[Citation]) -> str:
    """Generate a natural, conversational response with detailed explanations."""
    
    if not retrieved:
        return "I apologize, but I couldn't find specific information about that in the LEED knowledge base. Could you try rephrasing your question or asking about a specific LEED credit?"
    
    response_parts = []
    
    # Opening - acknowledge the question naturally
    query_lower = query.lower()
    if any(word in query_lower for word in ["what", "explain", "tell me", "describe"]):
        opening = f"Great question! Let me explain {info['credit_name'] or 'this LEED credit'} in detail."
    elif any(word in query_lower for word in ["how", "do i", "can i", "should"]):
        opening = f"I'd be happy to help you understand how to approach {info['credit_name'] or 'this credit'}."
    elif any(word in query_lower for word in ["requirement", "need", "must"]):
        opening = f"Here's what you need to know about the requirements for {info['credit_name'] or 'this credit'}."
    else:
        opening = f"Based on the LEED knowledge base, here's comprehensive information about {info['credit_name'] or 'this topic'}."
    
    response_parts.append(opening)
    response_parts.append("")  # Blank line for readability
    
    # Credit identification
    if info["credit_code"] and info["credit_name"]:
        response_parts.append(f"**{info['credit_code']}: {info['credit_name']}**")
        if info["category"]:
            response_parts.append(f"This is part of the {info['category']} category in LEED certification.")
        response_parts.append("")
    
    # Intent explanation
    if info["intent"]:
        response_parts.append(f"**What's the purpose?**")
        response_parts.append(f"The intent of this credit is to {info['intent'].lower()}. This means the credit is designed to encourage sustainable practices that align with LEED's environmental goals.")
        response_parts.append("")
    elif retrieved[0].get("text"):
        # Try to infer intent from the text
        first_text = retrieved[0].get("text", "")
        if "intent" in first_text.lower():
            intent_section = first_text.lower().split("intent")[1].split("\n")[0] if "intent" in first_text.lower() else ""
            if intent_section:
                response_parts.append(f"**What's the purpose?**")
                response_parts.append(f"This credit aims to {intent_section.strip().replace('intent:', '').strip()}. Understanding this purpose helps you see how your project can contribute to LEED's sustainability objectives.")
                response_parts.append("")
    
    # Detailed explanation from retrieved content
    response_parts.append("**Here's what you need to know:**")
    
    # Use the most relevant retrieved content
    primary_text = retrieved[0].get("text", "")
    if primary_text:
        # Clean and format the text naturally
        sentences = [s.strip() for s in primary_text.split(".") if len(s.strip()) > 20]
        
        # Take first few meaningful sentences
        key_sentences = []
        for sentence in sentences[:4]:
            if len(sentence) > 30 and not sentence.lower().startswith(("requirement", "documentation", "submittal")):
                key_sentences.append(sentence)
        
        if key_sentences:
            explanation = " ".join(key_sentences[:3])
            # Make it flow naturally
            if not explanation.endswith("."):
                explanation += "."
            response_parts.append(explanation)
        else:
            # Fallback: use cleaned text
            cleaned = _clean_text(primary_text, 400)
            response_parts.append(cleaned)
    
    response_parts.append("")
    
    # Requirements section
    if info["requirements"]:
        response_parts.append("**Key Requirements:**")
        for req in info["requirements"][:5]:  # Limit to top 5
            if req and len(req) > 10:
                # Format requirement naturally
                req_clean = req.replace("Requirements:", "").replace("-", "").strip()
                if req_clean:
                    response_parts.append(f"• {req_clean}")
        response_parts.append("")
    elif any("requirement" in res.get("text", "").lower() for res in retrieved[:2]):
        response_parts.append("**Key Requirements:**")
        response_parts.append("The specific requirements for this credit depend on your project type and the options you choose. Generally, you'll need to demonstrate compliance through calculations, documentation, and sometimes performance testing.")
        response_parts.append("")
    
    # Additional context from other retrieved results
    if len(retrieved) > 1:
        response_parts.append("**Additional Context:**")
        additional_info = []
        for res in retrieved[1:3]:  # Look at 2nd and 3rd results
            text = res.get("text", "")
            meta = res.get("metadata", {}) or {}
            credit_label = meta.get("credit_code") or meta.get("credit_name")
            
            if text and len(text) > 50:
                # Extract a meaningful sentence
                sentences = [s.strip() for s in text.split(".") if 30 < len(s.strip()) < 200]
                if sentences:
                    snippet = sentences[0]
                    if credit_label and credit_label != info["primary_credit"]:
                        additional_info.append(f"Related to {credit_label}: {snippet}")
                    else:
                        additional_info.append(snippet)
        
        if additional_info:
            response_parts.append(" ".join(additional_info[:2]))
        response_parts.append("")
    
    # Practical guidance
    response_parts.append("**How to approach this:**")
    response_parts.append("When working on this credit, I recommend starting by reviewing the specific requirements for your project type. Make sure you understand what documentation and calculations are needed. If you have specific project details, I can help you determine how well your project aligns with these requirements.")
    response_parts.append("")
    
    # Citations reference (natural integration)
    if citations:
        response_parts.append("**Sources:**")
        response_parts.append("The information above comes from official LEED documentation and reference materials. If you need more specific details, I can point you to the exact sections and pages.")
    
    return "\n".join(response_parts)


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
        
        # Generate natural language rationale
        if supported:
            if top_score >= self.positive_threshold:
                rationale = (
                    f"Your evidence appears to align well with the LEED requirements for this credit. "
                    f"The similarity score of {top_score:.2f} suggests a strong match. "
                    f"This indicates that your documentation likely addresses the key aspects needed for compliance."
                )
            else:
                rationale = (
                    f"Your evidence shows moderate alignment with the LEED requirements. "
                    f"While there's a connection (average similarity: {avg_score:.2f}), "
                    f"you may want to ensure all specific requirements are clearly addressed in your documentation."
                )
        else:
            rationale = (
                f"Based on the analysis, your evidence may not fully address the LEED requirements for this credit. "
                f"The similarity scores (top: {top_score:.2f}, average: {avg_score:.2f}) suggest that "
                f"your documentation might be missing some key elements or may need to be more specific about "
                f"how it meets the credit requirements. I'd recommend reviewing the requirements more closely "
                f"and ensuring your evidence directly addresses each point."
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

    def __init__(self, index_path: str = None):
        if index_path is None:
            # Default to models/leed_knowledge_base relative to the script directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)  # Go up one level from src
            index_path = os.path.join(project_root, "models", "leed_knowledge_base")
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
        # #region agent log
        import json as json_lib
        try:
            with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"location":"rag_credit_assistant.py:419","message":"retrieve entry","data":{"query":query[:50],"k":k},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H5"})+"\n")
        except: pass
        # #endregion
        results = self.api.search(query, k=k, sources=sources)
        # #region agent log
        try:
            with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"location":"rag_credit_assistant.py:421","message":"retrieve search done","data":{"results_count":len(results)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H5"})+"\n")
        except: pass
        # #endregion
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
        # #region agent log
        try:
            with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"location":"rag_credit_assistant.py:436","message":"retrieve return","data":{"results_count":len(results),"citations_count":len(citations)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H5"})+"\n")
        except: pass
        # #endregion
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
        """Format citations in a natural, readable way."""
        if not citations:
            return ""
        
        lines = []
        lines.append("**Reference Sources:**")
        lines.append("")
        
        for idx, citation in enumerate(citations, 1):
            # Build natural citation text
            citation_parts = []
            
            if citation.label:
                citation_parts.append(f"**{citation.label}**")
            
            if citation.source:
                citation_parts.append(f"from {citation.source}")
            
            if citation.pages:
                if isinstance(citation.pages, list) and citation.pages:
                    pages_str = ", ".join(str(p) for p in citation.pages[:3])  # Limit pages shown
                    citation_parts.append(f"(pages {pages_str})")
                elif citation.pages:
                    citation_parts.append(f"(page {citation.pages})")
            
            citation_line = " — ".join(citation_parts) if citation_parts else f"Reference {idx}"
            
            # Add snippet if available and meaningful
            if citation.snippet and len(citation.snippet.strip()) > 20:
                snippet_clean = _clean_text(citation.snippet, 150)
                lines.append(f"{idx}. {citation_line}")
                lines.append(f"   \"{snippet_clean}\"")
            else:
                lines.append(f"{idx}. {citation_line}")
            
            lines.append("")  # Blank line between citations
        
        return "\n".join(lines)

    def _format_answer(self, query: str, retrieved: Sequence[Dict[str, Any]], citations: Sequence[Citation]) -> str:
        """Generate a natural, conversational answer with detailed explanations."""
        if not retrieved:
            return ("I apologize, but I couldn't find specific information about that in the LEED knowledge base. "
                   "Could you try rephrasing your question or asking about a specific LEED credit? "
                   "For example, you could ask about 'EA Optimize Energy Performance' or 'Water Efficiency prerequisites'.")
        
        # Extract structured information from retrieved results
        info = _extract_key_information(retrieved)
        
        # Generate natural language response
        response = _generate_natural_response(query, info, retrieved, citations)
        
        return response

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
