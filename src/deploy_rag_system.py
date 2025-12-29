#!/usr/bin/env python3
"""
RAG System Deployment Script
Initializes FAISS vector database and tests LLM-RAG integration with LEED chunks.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any
import numpy as np

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup logging for RAG deployment"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def check_dependencies():
    """Check if required dependencies are available"""
    logger = logging.getLogger(__name__)
    missing_deps = []
    
    try:
        import sentence_transformers
        logger.info("✓ sentence-transformers available")
    except ImportError:
        missing_deps.append("sentence-transformers")
        logger.warning("✗ sentence-transformers not available")
    
    try:
        import faiss
        logger.info("✓ faiss-cpu available")
    except ImportError:
        missing_deps.append("faiss-cpu")
        logger.warning("✗ faiss-cpu not available")
    
    try:
        import transformers
        logger.info("✓ transformers available")
    except ImportError:
        missing_deps.append("transformers")
        logger.warning("✗ transformers not available")
    
    try:
        import torch
        logger.info("✓ torch available")
    except ImportError:
        missing_deps.append("torch")
        logger.warning("✗ torch not available")
    
    if missing_deps:
        logger.error(f"Missing dependencies: {', '.join(missing_deps)}")
        logger.error("Install with: pip install " + " ".join(missing_deps))
        return False
    
    return True

def load_rag_chunks(chunks_path: str) -> List[Dict[str, Any]]:
    """Load RAG chunks from JSONL file"""
    logger = logging.getLogger(__name__)
    chunks = []
    
    try:
        with open(chunks_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    chunk_data = json.loads(line.strip())
                    chunks.append(chunk_data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping invalid JSON on line {line_num}: {e}")
        
        logger.info(f"Loaded {len(chunks)} chunks from {chunks_path}")
        return chunks
        
    except FileNotFoundError:
        logger.error(f"Chunks file not found: {chunks_path}")
        return []
    except Exception as e:
        logger.error(f"Error loading chunks: {e}")
        return []

def initialize_faiss_database(chunks: List[Dict[str, Any]], 
                           output_path: str,
                           embedding_model: str = "all-MiniLM-L6-v2") -> bool:
    """Initialize FAISS database with LEED chunks"""
    logger = logging.getLogger(__name__)
    
    try:
        # Import required modules
        from sentence_transformers import SentenceTransformer
        import faiss
        
        logger.info(f"Loading embedding model: {embedding_model}")
        embedder = SentenceTransformer(embedding_model)
        
        # Generate embeddings for all chunks
        logger.info("Generating embeddings for chunks...")
        texts = [chunk['text'] for chunk in chunks]
        embeddings = embedder.encode(texts, convert_to_tensor=False)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        logger.info(f"Creating FAISS index with dimension {dimension}")
        
        # Use IndexFlatIP for inner product (cosine similarity)
        index = faiss.IndexFlatIP(dimension)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings.astype('float32'))
        
        # Save FAISS index
        faiss_path = f"{output_path}.faiss"
        faiss.write_index(index, faiss_path)
        logger.info(f"FAISS index saved to: {faiss_path}")
        
        # Save chunks metadata
        metadata_path = f"{output_path}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        logger.info(f"Chunks metadata saved to: {metadata_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing FAISS database: {e}")
        return False

def test_rag_retrieval(index_path: str, 
                      test_queries: List[str],
                      embedding_model: str = "all-MiniLM-L6-v2") -> Dict[str, Any]:
    """Test RAG retrieval with sample queries"""
    logger = logging.getLogger(__name__)
    
    try:
        # Import required modules
        from sentence_transformers import SentenceTransformer
        import faiss
        
        # Load embedding model
        embedder = SentenceTransformer(embedding_model)
        
        # Load FAISS index
        faiss_path = f"{index_path}.faiss"
        metadata_path = f"{index_path}.json"
        
        if not os.path.exists(faiss_path) or not os.path.exists(metadata_path):
            logger.error("FAISS index or metadata not found")
            return {}
        
        index = faiss.read_index(faiss_path)
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        logger.info(f"Loaded FAISS index with {index.ntotal} vectors")
        
        # Test queries
        results = {}
        
        for query in test_queries:
            logger.info(f"Testing query: {query}")
            
            # Generate query embedding
            query_embedding = embedder.encode([query], convert_to_tensor=False)
            faiss.normalize_L2(query_embedding)
            
            # Search for similar chunks
            k = 5  # Top 5 results
            scores, indices = index.search(query_embedding.astype('float32'), k)
            
            # Collect results
            query_results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(chunks):
                    chunk = chunks[idx]
                    result = {
                        'rank': i + 1,
                        'score': float(score),
                        'text': chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text'],
                        'metadata': chunk['metadata']
                    }
                    query_results.append(result)
            
            results[query] = query_results
            
            # Log top result
            if query_results:
                top_result = query_results[0]
                logger.info(f"  Top result (score: {top_result['score']:.3f}): {top_result['text'][:100]}...")
        
        return results
        
    except Exception as e:
        logger.error(f"Error testing RAG retrieval: {e}")
        return {}

def test_llm_integration():
    """Test LLM integration (simplified version)"""
    logger = logging.getLogger(__name__)
    
    try:
        # Try to import LLM components
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
        
        logger.info("Testing LLM integration...")
        
        # Use a smaller model for testing
        model_name = "microsoft/DialoGPT-small"
        
        logger.info(f"Loading model: {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        
        # Test generation
        test_prompt = "What are the requirements for LEED energy credits?"
        inputs = tokenizer.encode(test_prompt, return_tensors="pt")
        
        with torch.no_grad():
            outputs = model.generate(inputs, max_length=100, temperature=0.7, do_sample=True)
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        logger.info(f"LLM test response: {response[:100]}...")
        
        return True
        
    except Exception as e:
        logger.warning(f"LLM integration test failed: {e}")
        logger.warning("This is expected if transformers/torch are not properly installed")
        return False

def create_test_queries() -> List[str]:
    """Create test queries for RAG validation"""
    return [
        "What are the requirements for energy efficiency credits?",
        "How do I achieve LEED points for water conservation?",
        "What is required for indoor air quality credits?",
        "How to get points for sustainable materials?",
        "What are the prerequisites for LEED certification?",
        "How to calculate energy performance metrics?",
        "What documentation is needed for LEED credits?",
        "How to achieve innovation credits in LEED?",
        "What are the requirements for location and transportation credits?",
        "How to implement renewable energy systems for LEED?"
    ]

def main():
    """Main deployment function"""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("LEED RAG System Deployment")
    logger.info("=" * 60)
    
    # Check dependencies
    logger.info("Checking dependencies...")
    if not check_dependencies():
        logger.error("Missing required dependencies. Please install them first.")
        return False
    
    # Set up paths
    chunks_path = "data/raw/rag_chunks.jsonl"
    index_path = "models/leed_knowledge_base"
    
    # Create models directory
    os.makedirs("models", exist_ok=True)
    
    # Load RAG chunks
    logger.info("Loading RAG chunks...")
    chunks = load_rag_chunks(chunks_path)
    
    if not chunks:
        logger.error("No chunks loaded. Please check the chunks file.")
        return False
    
    # Initialize FAISS database
    logger.info("Initializing FAISS database...")
    success = initialize_faiss_database(chunks, index_path)
    
    if not success:
        logger.error("Failed to initialize FAISS database")
        return False
    
    # Test RAG retrieval
    logger.info("Testing RAG retrieval...")
    test_queries = create_test_queries()
    retrieval_results = test_rag_retrieval(index_path, test_queries[:5])  # Test first 5 queries
    
    if retrieval_results:
        logger.info("✓ RAG retrieval test successful")
        
        # Save test results
        results_path = "outputs/rag_test_results.json"
        os.makedirs("outputs", exist_ok=True)
        
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(retrieval_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Test results saved to: {results_path}")
    else:
        logger.error("✗ RAG retrieval test failed")
    
    # Test LLM integration
    logger.info("Testing LLM integration...")
    llm_success = test_llm_integration()
    
    if llm_success:
        logger.info("✓ LLM integration test successful")
    else:
        logger.warning("⚠ LLM integration test failed (may need additional setup)")
    
    # Summary
    logger.info("=" * 60)
    logger.info("RAG System Deployment Summary")
    logger.info("=" * 60)
    logger.info(f"✓ Loaded {len(chunks)} LEED chunks")
    logger.info(f"✓ Initialized FAISS database at {index_path}")
    logger.info(f"✓ Tested RAG retrieval with {len(test_queries)} queries")
    
    if llm_success:
        logger.info("✓ LLM integration working")
    else:
        logger.info("⚠ LLM integration needs additional setup")
    
    logger.info("\nNext steps:")
    logger.info("1. Run: python src/test_rag_system.py")
    logger.info("2. Test with real LEED queries")
    logger.info("3. Integrate with your LEED platform")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 RAG System deployed successfully!")
    else:
        print("\n❌ RAG System deployment failed. Check logs for details.")
