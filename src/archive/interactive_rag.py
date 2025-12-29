#!/usr/bin/env python3
"""
Interactive RAG Query Tool
Simple command-line interface to test LEED RAG queries interactively.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup logging"""
    logging.basicConfig(level=logging.WARNING)  # Reduce verbosity
    return logging.getLogger(__name__)

class InteractiveRAG:
    """Interactive RAG query interface"""
    
    def __init__(self, index_path: str = "models/leed_knowledge_base"):
        self.logger = logging.getLogger(__name__)
        self.index_path = index_path
        self.embedder = None
        self.index = None
        self.chunks = []
        
    def load_system(self) -> bool:
        """Load the RAG system components"""
        try:
            from sentence_transformers import SentenceTransformer
            import faiss
            
            print("Loading LEED RAG system...")
            
            # Load embedding model
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
            
            # Load FAISS index
            faiss_path = f"{self.index_path}.faiss"
            metadata_path = f"{self.index_path}.json"
            
            if not os.path.exists(faiss_path) or not os.path.exists(metadata_path):
                print("❌ FAISS index or metadata not found")
                return False
            
            self.index = faiss.read_index(faiss_path)
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.chunks = json.load(f)
            
            print(f"✅ Loaded RAG system with {len(self.chunks)} LEED chunks")
            return True
            
        except Exception as e:
            print(f"❌ Error loading RAG system: {e}")
            return False
    
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant chunks"""
        try:
            import faiss
            
            if not self.embedder or not self.index:
                return []
            
            # Generate query embedding
            query_embedding = self.embedder.encode([query], convert_to_tensor=False)
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = self.index.search(query_embedding.astype('float32'), k)
            
            # Collect results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.chunks):
                    chunk = self.chunks[idx]
                    result = {
                        'rank': i + 1,
                        'score': float(score),
                        'text': chunk['text'],
                        'metadata': chunk['metadata']
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            print(f"❌ Error searching: {e}")
            return []
    
    def display_results(self, query: str, results: List[Dict[str, Any]]):
        """Display search results in a formatted way"""
        print(f"\n🔍 Query: {query}")
        print("=" * 60)
        
        if not results:
            print("❌ No results found")
            return
        
        for result in results:
            print(f"\n📋 Result #{result['rank']} (Score: {result['score']:.3f})")
            
            # Display metadata
            metadata = result['metadata']
            if metadata.get('credit_code'):
                print(f"   Credit Code: {metadata['credit_code']}")
            if metadata.get('credit_name'):
                print(f"   Credit Name: {metadata['credit_name']}")
            if metadata.get('type'):
                print(f"   Type: {metadata['type']}")
            if metadata.get('points_min') and metadata.get('points_max'):
                print(f"   Points: {metadata['points_min']}-{metadata['points_max']}")
            
            # Display text (truncated)
            text = result['text']
            if len(text) > 200:
                text = text[:200] + "..."
            print(f"   Content: {text}")
            print("-" * 40)
    
    def run_interactive(self):
        """Run interactive query session"""
        print("🏗️  LEED RAG System - Interactive Query Tool")
        print("=" * 50)
        print("Ask questions about LEED credits, requirements, and compliance.")
        print("Type 'help' for example queries, 'quit' to exit.")
        print()
        
        # Example queries
        example_queries = [
            "What are the requirements for energy efficiency credits?",
            "How do I achieve LEED points for water conservation?",
            "What is required for indoor air quality credits?",
            "EA Credit Optimize Energy Performance",
            "WE Credit Water Use Reduction",
            "What documentation is needed for LEED credits?",
            "How to calculate renewable energy credits?",
            "What are the prerequisites for LEED certification?"
        ]
        
        while True:
            try:
                query = input("\n💬 Enter your LEED question: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if query.lower() == 'help':
                    print("\n📚 Example queries:")
                    for i, example in enumerate(example_queries, 1):
                        print(f"   {i}. {example}")
                    continue
                
                if not query:
                    continue
                
                # Search and display results
                results = self.search(query, k=3)
                self.display_results(query, results)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

def main():
    """Main function"""
    logger = setup_logging()
    
    # Initialize interactive RAG
    rag = InteractiveRAG()
    
    # Load system
    if not rag.load_system():
        print("❌ Failed to load RAG system. Make sure you've run the deployment script first.")
        return
    
    # Run interactive session
    rag.run_interactive()

if __name__ == "__main__":
    main()
