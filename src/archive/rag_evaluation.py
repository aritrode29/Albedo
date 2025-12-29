#!/usr/bin/env python3
"""
RAG Retrieval Evaluation Harness
Tests retrieval quality, relevance, and system performance.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RAGEvaluator:
    def __init__(self, api_url: str = "http://localhost:5000"):
        self.api_url = api_url
        self.evaluation_results = []
        
    def test_query(self, query: str, expected_topics: List[str] = None, 
                   sources: str = "all", limit: int = 3) -> Dict[str, Any]:
        """Test a single query and return results."""
        import requests
        
        try:
            start_time = time.time()
            response = requests.post(f"{self.api_url}/api/query", 
                                    json={"query": query, "sources": sources, "limit": limit},
                                    timeout=30)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "query": query,
                    "success": True,
                    "response_time": response_time,
                    "results": data.get("results", []),
                    "total_results": len(data.get("results", [])),
                    "expected_topics": expected_topics or []
                }
            else:
                return {
                    "query": query,
                    "success": False,
                    "response_time": response_time,
                    "error": f"HTTP {response.status_code}",
                    "expected_topics": expected_topics or []
                }
        except Exception as e:
            return {
                "query": query,
                "success": False,
                "response_time": 0,
                "error": str(e),
                "expected_topics": expected_topics or []
            }
    
    def evaluate_relevance(self, result: Dict[str, Any]) -> float:
        """Evaluate relevance of results based on expected topics."""
        if not result["success"] or not result["results"]:
            return 0.0
        
        expected_topics = [topic.lower() for topic in result["expected_topics"]]
        relevance_scores = []
        
        for res in result["results"]:
            text = res.get("text", "").lower()
            metadata = res.get("metadata", {})
            
            # Check text content for expected topics
            topic_matches = sum(1 for topic in expected_topics if topic in text)
            relevance = topic_matches / len(expected_topics) if expected_topics else 0.5
            
            # Boost score for metadata matches
            if metadata.get("credit_code") and any(topic in str(metadata.get("credit_code", "")).lower() 
                                                 for topic in expected_topics):
                relevance += 0.2
            
            if metadata.get("leed_category") and any(topic in str(metadata.get("leed_category", "")).lower() 
                                                   for topic in expected_topics):
                relevance += 0.1
            
            relevance_scores.append(min(relevance, 1.0))
        
        return np.mean(relevance_scores) if relevance_scores else 0.0
    
    def run_evaluation_suite(self) -> Dict[str, Any]:
        """Run comprehensive evaluation suite."""
        logger.info("Starting RAG evaluation suite...")
        
        # Test queries with expected topics
        test_queries = [
            {
                "query": "energy efficiency requirements",
                "expected_topics": ["energy", "efficiency", "ASHRAE", "performance"],
                "sources": "credits"
            },
            {
                "query": "water efficiency LEED credits",
                "expected_topics": ["water", "efficiency", "WE", "fixtures"],
                "sources": "credits"
            },
            {
                "query": "SEA Building Addition project",
                "expected_topics": ["SEA", "building", "addition", "project"],
                "sources": "all"
            },
            {
                "query": "cooling tower water treatment",
                "expected_topics": ["cooling", "tower", "water", "treatment"],
                "sources": "all"
            },
            {
                "query": "integrative process worksheet",
                "expected_topics": ["integrative", "process", "worksheet", "IP"],
                "sources": "all"
            },
            {
                "query": "LEED v4.1 BD+C credits",
                "expected_topics": ["LEED", "v4.1", "BD+C", "credits"],
                "sources": "credits"
            },
            {
                "query": "sustainable materials",
                "expected_topics": ["materials", "sustainable", "MR", "recycled"],
                "sources": "credits"
            },
            {
                "query": "indoor air quality",
                "expected_topics": ["air", "quality", "EQ", "ventilation"],
                "sources": "credits"
            },
            {
                "query": "site selection criteria",
                "expected_topics": ["site", "selection", "SS", "location"],
                "sources": "credits"
            },
            {
                "query": "UT Austin campus buildings",
                "expected_topics": ["UT", "Austin", "campus", "buildings"],
                "sources": "all"
            }
        ]
        
        results = []
        total_relevance = 0
        successful_queries = 0
        total_response_time = 0
        
        for test_case in test_queries:
            logger.info(f"Testing query: {test_case['query']}")
            result = self.test_query(
                test_case["query"], 
                test_case["expected_topics"],
                test_case.get("sources", "all")
            )
            
            # Calculate relevance
            relevance = self.evaluate_relevance(result)
            result["relevance_score"] = relevance
            
            results.append(result)
            
            if result["success"]:
                successful_queries += 1
                total_response_time += result["response_time"]
                total_relevance += relevance
                
                logger.info(f"✓ Success - Relevance: {relevance:.3f}, Time: {result['response_time']:.2f}s")
            else:
                logger.warning(f"✗ Failed - {result.get('error', 'Unknown error')}")
        
        # Calculate metrics
        success_rate = successful_queries / len(test_queries)
        avg_relevance = total_relevance / successful_queries if successful_queries > 0 else 0
        avg_response_time = total_response_time / successful_queries if successful_queries > 0 else 0
        
        evaluation_summary = {
            "timestamp": datetime.now().isoformat(),
            "total_queries": len(test_queries),
            "successful_queries": successful_queries,
            "success_rate": success_rate,
            "average_relevance": avg_relevance,
            "average_response_time": avg_response_time,
            "results": results
        }
        
        logger.info(f"Evaluation complete:")
        logger.info(f"  Success Rate: {success_rate:.1%}")
        logger.info(f"  Average Relevance: {avg_relevance:.3f}")
        logger.info(f"  Average Response Time: {avg_response_time:.2f}s")
        
        return evaluation_summary
    
    def test_api_endpoints(self) -> Dict[str, Any]:
        """Test all API endpoints."""
        import requests
        
        logger.info("Testing API endpoints...")
        endpoint_results = {}
        
        # Test status endpoint
        try:
            response = requests.get(f"{self.api_url}/api/status", timeout=10)
            endpoint_results["status"] = {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            endpoint_results["status"] = {"success": False, "error": str(e)}
        
        # Test credits endpoint
        try:
            response = requests.get(f"{self.api_url}/api/credits", timeout=10)
            endpoint_results["credits"] = {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "count": len(response.json().get("credits", [])) if response.status_code == 200 else 0
            }
        except Exception as e:
            endpoint_results["credits"] = {"success": False, "error": str(e)}
        
        # Test query endpoint
        try:
            response = requests.post(f"{self.api_url}/api/query", 
                                   json={"query": "test", "limit": 1}, timeout=10)
            endpoint_results["query"] = {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "has_results": len(response.json().get("results", [])) > 0 if response.status_code == 200 else False
            }
        except Exception as e:
            endpoint_results["query"] = {"success": False, "error": str(e)}
        
        return endpoint_results
    
    def generate_report(self, evaluation_results: Dict[str, Any], 
                       endpoint_results: Dict[str, Any]) -> str:
        """Generate comprehensive evaluation report."""
        report = f"""
# RAG System Evaluation Report
Generated: {evaluation_results['timestamp']}

## Executive Summary
- **Total Queries Tested**: {evaluation_results['total_queries']}
- **Success Rate**: {evaluation_results['success_rate']:.1%}
- **Average Relevance Score**: {evaluation_results['average_relevance']:.3f}
- **Average Response Time**: {evaluation_results['average_response_time']:.2f}s

## API Endpoint Status
"""
        
        for endpoint, result in endpoint_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            report += f"- **{endpoint.upper()}**: {status}\n"
            if not result["success"]:
                report += f"  - Error: {result.get('error', 'Unknown')}\n"
        
        report += f"""
## Query Performance Details

### High-Performing Queries (Relevance > 0.7)
"""
        
        high_performing = [r for r in evaluation_results['results'] 
                          if r.get('relevance_score', 0) > 0.7 and r['success']]
        
        for result in high_performing:
            report += f"- **{result['query']}**: {result['relevance_score']:.3f} relevance, {result['response_time']:.2f}s\n"
        
        report += f"""
### Failed Queries
"""
        
        failed_queries = [r for r in evaluation_results['results'] if not r['success']]
        
        for result in failed_queries:
            report += f"- **{result['query']}**: {result.get('error', 'Unknown error')}\n"
        
        report += f"""
## Recommendations

### Performance Improvements
1. **Response Time**: Average {evaluation_results['average_response_time']:.2f}s - {'Good' if evaluation_results['average_response_time'] < 2.0 else 'Consider optimization'}
2. **Relevance**: Average {evaluation_results['average_relevance']:.3f} - {'Good' if evaluation_results['average_relevance'] > 0.6 else 'Consider improving chunk quality'}
3. **Success Rate**: {evaluation_results['success_rate']:.1%} - {'Good' if evaluation_results['success_rate'] > 0.8 else 'Investigate API issues'}

### System Health
- API endpoints: {sum(1 for r in endpoint_results.values() if r['success'])}/{len(endpoint_results)} working
- Query processing: {'Stable' if evaluation_results['success_rate'] > 0.8 else 'Needs attention'}

## Detailed Results
"""
        
        for i, result in enumerate(evaluation_results['results'], 1):
            report += f"""
### Query {i}: {result['query']}
- **Status**: {'✅ Success' if result['success'] else '❌ Failed'}
- **Relevance**: {result.get('relevance_score', 0):.3f}
- **Response Time**: {result.get('response_time', 0):.2f}s
- **Results Count**: {result.get('total_results', 0)}
- **Expected Topics**: {', '.join(result.get('expected_topics', []))}
"""
            
            if result['success'] and result.get('results'):
                report += f"- **Top Result**: {result['results'][0].get('text', '')[:100]}...\n"
        
        return report

def main():
    """Main evaluation function."""
    evaluator = RAGEvaluator()
    
    # Test API endpoints first
    logger.info("Testing API endpoints...")
    endpoint_results = evaluator.test_api_endpoints()
    
    # Run evaluation suite
    logger.info("Running evaluation suite...")
    evaluation_results = evaluator.run_evaluation_suite()
    
    # Generate report
    report = evaluator.generate_report(evaluation_results, endpoint_results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save evaluation results
    results_file = f"outputs/rag_evaluation_results_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "evaluation": evaluation_results,
            "endpoints": endpoint_results
        }, f, ensure_ascii=False, indent=2)
    
    # Save report
    report_file = f"outputs/rag_evaluation_report_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"✓ Evaluation complete!")
    logger.info(f"  → Results: {results_file}")
    logger.info(f"  → Report: {report_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("RAG EVALUATION SUMMARY")
    print("="*60)
    print(f"Success Rate: {evaluation_results['success_rate']:.1%}")
    print(f"Average Relevance: {evaluation_results['average_relevance']:.3f}")
    print(f"Average Response Time: {evaluation_results['average_response_time']:.2f}s")
    print(f"API Endpoints Working: {sum(1 for r in endpoint_results.values() if r['success'])}/{len(endpoint_results)}")
    print("="*60)

if __name__ == "__main__":
    main()




