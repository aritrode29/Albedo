#!/usr/bin/env python3
"""
RAG System Demo Script
Demonstrates the LEED RAG system with templates, binary evidence classifier, and strict citations.
"""

import logging
from typing import Dict, List

from rag_credit_assistant import RAGCreditAssistant


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class RAGDemo:
    """RAG system demonstration with enhanced safety rails."""

    def __init__(self):
        self.assistant = RAGCreditAssistant()

    def run_demo_queries(self) -> None:
        print("\n🏗️  LEED RAG System - Robust Demonstration")
        print("=" * 50)

        if not self.assistant.ready:
            print("❌ Failed to load RAG system. Build the indices before running the demo.")
            print("   Run: python src/build_rag_corpus.py")
            return

        scenarios: List[Dict[str, str]] = [
            {
                "query": "EA Credit Optimize Energy Performance requirements",
                "evidence": "Energy model shows 18% cost savings relative to ASHRAE 90.1-2016 with submetering for HVAC and lighting.",
            },
            {
                "query": "Indoor water use reduction prerequisites",
                "evidence": "Fixtures are EPA WaterSense certified with 30% potable water savings versus baseline.",
            },
            {
                "query": "What documentation is needed for LEED credits?",
                "evidence": "Project team prepared narratives, calculator outputs, and manufacturer cut sheets.",
            },
        ]

        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{'='*20} DEMO SCENARIO {i}/{len(scenarios)} {'='*20}")
            result = self.assistant.analyze(scenario["query"], scenario["evidence"], k=3)

            print("\n📄 Answer with strict citations:")
            print(result["answer"])

            print("\n🔗 Citations:")
            print(result["citations"])

            if result.get("evidence_classification"):
                print("\n✅ Binary evidence classifier:")
                print(result["evidence_classification"])

            print("\n🧩 Credit template:")
            print(result["template"])

            if i < len(scenarios):
                print("\n" + "⏳" * 20 + " Next scenario..." + "⏳" * 20)


def main() -> None:
    setup_logging()
    demo = RAGDemo()
    demo.run_demo_queries()
    print("\n🎉 RAG system demonstration completed!")
    print("✅ Components exercised:")
    print("   • RAG retrieval with top-k strict citations")
    print("   • Credit templates hydrated from the catalog")
    print("   • Binary evidence classifier scoring support vs. insufficiency")


if __name__ == "__main__":
    main()
