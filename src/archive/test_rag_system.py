#!/usr/bin/env python3
"""
RAG System Test Script
Comprehensive testing of the LEED RAG system with various queries and validation.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Tuple
import numpy as np

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup logging for RAG testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

class RAGTester:
    """Comprehensive RAG system tester"""
    
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
            
            # Load embedding model
            self.logger.info("Loading embedding model...")
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
            
            # Load FAISS index
            faiss_path = f"{self.index_path}.faiss"
            metadata_path = f"{self.index_path}.json"
            
            if not os.path.exists(faiss_path) or not os.path.exists(metadata_path):
                self.logger.error("FAISS index or metadata not found")
                return False
            
            self.index = faiss.read_index(faiss_path)
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.chunks = json.load(f)
            
            self.logger.info(f"Loaded RAG system with {len(self.chunks)} chunks")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading RAG system: {e}")
            return False
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
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
            self.logger.error(f"Error searching: {e}")
            return []
    
    def test_basic_queries(self) -> Dict[str, Any]:
        """Test basic LEED queries"""
        self.logger.info("Testing basic LEED queries...")
        
        test_queries = [
            "energy efficiency requirements",
            "water conservation credits",
            "indoor air quality",
            "sustainable materials",
            "renewable energy",
            "transit access",
            "bicycle facilities",
            "parking reduction",
            "heat island reduction",
            "light pollution"
        ]
        
        results = {}
        for query in test_queries:
            search_results = self.search(query, k=3)
            results[query] = search_results
            
            if search_results:
                top_score = search_results[0]['score']
                self.logger.info(f"  {query}: Top score {top_score:.3f}")
            else:
                self.logger.warning(f"  {query}: No results")
        
        return results
    
    def test_credit_specific_queries(self) -> Dict[str, Any]:
        """Test credit-specific queries"""
        self.logger.info("Testing credit-specific queries...")
        
        credit_queries = [
            "EA Credit Optimize Energy Performance",
            "WE Credit Water Use Reduction",
            "EQ Credit Indoor Air Quality Assessment",
            "MR Credit Building Product Disclosure",
            "LT Credit Access to Quality Transit",
            "SS Credit Heat Island Reduction",
            "IN Credit Innovation",
            "RP Credit Regional Priority"
        ]
        
        results = {}
        for query in credit_queries:
            search_results = self.search(query, k=3)
            results[query] = search_results
            
            if search_results:
                top_score = search_results[0]['score']
                self.logger.info(f"  {query}: Top score {top_score:.3f}")
            else:
                self.logger.warning(f"  {query}: No results")
        
        return results
    
    def test_compliance_queries(self) -> Dict[str, Any]:
        """Test compliance and documentation queries"""
        self.logger.info("Testing compliance queries...")
        
        compliance_queries = [
            "What documentation is required for LEED credits?",
            "How to calculate energy performance metrics?",
            "What are the prerequisites for certification?",
            "How to achieve innovation credits?",
            "What is the minimum energy performance requirement?",
            "How to document water use reduction?",
            "What are the requirements for indoor environmental quality?",
            "How to calculate renewable energy credits?"
        ]
        
        results = {}
        for query in compliance_queries:
            search_results = self.search(query, k=3)
            results[query] = search_results
            
            if search_results:
                top_score = search_results[0]['score']
                self.logger.info(f"  {query}: Top score {top_score:.3f}")
            else:
                self.logger.warning(f"  {query}: No results")
        
        return results
    
    def validate_retrieval_quality(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality of retrieval results"""
        self.logger.info("Validating retrieval quality...")
        
        validation = {
            'total_queries': len(results),
            'queries_with_results': 0,
            'average_top_score': 0,
            'score_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'credit_code_coverage': set(),
            'category_coverage': set()
        }
        
        total_score = 0
        
        for query, search_results in results.items():
            if search_results:
                validation['queries_with_results'] += 1
                top_score = search_results[0]['score']
                total_score += top_score
                
                # Score distribution
                if top_score > 0.7:
                    validation['score_distribution']['high'] += 1
                elif top_score > 0.5:
                    validation['score_distribution']['medium'] += 1
                else:
                    validation['score_distribution']['low'] += 1
                
                # Collect metadata
                for result in search_results:
                    metadata = result['metadata']
                    if metadata.get('credit_code'):
                        validation['credit_code_coverage'].add(metadata['credit_code'])
                    if metadata.get('category'):
                        validation['category_coverage'].add(metadata['category'])
        
        if validation['queries_with_results'] > 0:
            validation['average_top_score'] = total_score / validation['queries_with_results']
        
        validation['credit_code_coverage'] = list(validation['credit_code_coverage'])
        validation['category_coverage'] = list(validation['category_coverage'])
        
        return validation
    
    def generate_test_report(self, all_results: Dict[str, Any]) -> str:
        """Generate a comprehensive test report"""
        report = []
        report.append("# LEED RAG System Test Report")
        report.append("")
        report.append(f"**Test Date:** {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))}")
        report.append(f"**Total Chunks:** {len(self.chunks)}")
        report.append("")
        
        # Basic queries results
        if 'basic' in all_results:
            report.append("## Basic Query Results")
            report.append("")
            for query, results in all_results['basic'].items():
                if results:
                    top_score = results[0]['score']
                    report.append(f"- **{query}**: {top_score:.3f}")
                else:
                    report.append(f"- **{query}**: No results")
            report.append("")
        
        # Credit-specific results
        if 'credits' in all_results:
            report.append("## Credit-Specific Query Results")
            report.append("")
            for query, results in all_results['credits'].items():
                if results:
                    top_score = results[0]['score']
                    report.append(f"- **{query}**: {top_score:.3f}")
                else:
                    report.append(f"- **{query}**: No results")
            report.append("")
        
        # Compliance results
        if 'compliance' in all_results:
            report.append("## Compliance Query Results")
            report.append("")
            for query, results in all_results['compliance'].items():
                if results:
                    top_score = results[0]['score']
                    report.append(f"- **{query}**: {top_score:.3f}")
                else:
                    report.append(f"- **{query}**: No results")
            report.append("")
        
        # Validation summary
        validation = self.validate_retrieval_quality({**all_results.get('basic', {}), 
                                                   **all_results.get('credits', {}), 
                                                   **all_results.get('compliance', {})})
        
        report.append("## Validation Summary")
        report.append("")
        report.append(f"- **Total Queries:** {validation['total_queries']}")
        report.append(f"- **Queries with Results:** {validation['queries_with_results']}")
        report.append(f"- **Average Top Score:** {validation['average_top_score']:.3f}")
        report.append("")
        report.append("### Score Distribution")
        report.append(f"- **High (>0.7):** {validation['score_distribution']['high']}")
        report.append(f"- **Medium (0.5-0.7):** {validation['score_distribution']['medium']}")
        report.append(f"- **Low (<0.5):** {validation['score_distribution']['low']}")
        report.append("")
        
        if validation['credit_code_coverage']:
            report.append("### Credit Code Coverage")
            report.append(f"- **Covered Codes:** {', '.join(validation['credit_code_coverage'])}")
            report.append("")
        
        return "\n".join(report)
    
    def run_comprehensive_test(self) -> bool:
        """Run comprehensive RAG system test"""
        self.logger.info("Starting comprehensive RAG system test...")
        
        # Load system
        if not self.load_system():
            return False
        
        # Run tests
        all_results = {}
        
        # Basic queries
        all_results['basic'] = self.test_basic_queries()
        
        # Credit-specific queries
        all_results['credits'] = self.test_credit_specific_queries()
        
        # Compliance queries
        all_results['compliance'] = self.test_compliance_queries()
        
        # Generate report
        report = self.generate_test_report(all_results)
        
        # Save results
        os.makedirs("outputs", exist_ok=True)
        
        # Save detailed results
        results_path = "outputs/rag_comprehensive_test_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        # Save report
        report_path = "outputs/rag_test_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.logger.info(f"Test results saved to: {results_path}")
        self.logger.info(f"Test report saved to: {report_path}")
        
        return True

def main():
    """Main test function"""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("LEED RAG System Comprehensive Test")
    logger.info("=" * 60)
    
    # Initialize tester
    tester = RAGTester()
    
    # Run comprehensive test
    success = tester.run_comprehensive_test()
    
    if success:
        logger.info("✓ Comprehensive test completed successfully")
        logger.info("Check outputs/rag_test_report.md for detailed results")
    else:
        logger.error("✗ Comprehensive test failed")
    
    return success

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 RAG System test completed successfully!")
    else:
        print("\n❌ RAG System test failed. Check logs for details.")
