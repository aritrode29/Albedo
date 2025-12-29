#!/usr/bin/env python3
"""
Enhanced LEED RAG API with Web Search Integration
Adds internet search capability to the existing RAG system.
"""

import os
import sys
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from enhanced_rag_with_web import EnhancedRAGSystem
    from leed_rag_api import LEEDRAGAPI
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all dependencies are installed.")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class EnhancedLEEDRAGAPI:
    def __init__(self):
        self.rag_system = None
        self.enhanced_rag = None
        self.load_system()
    
    def load_system(self):
        """Load the RAG system and enhanced web search."""
        try:
            logger.info("Loading LEED RAG system...")
            self.rag_system = LEEDRAGAPI()
            # Load the RAG system (loads indices and embeddings)
            if not self.rag_system.load_system():
                logger.error("Failed to load RAG system. Make sure indices exist.")
                raise RuntimeError("RAG system failed to load")
            # Pass RAG system directly to avoid HTTP circular calls
            self.enhanced_rag = EnhancedRAGSystem(rag_system=self.rag_system)
            logger.info("✓ Enhanced RAG system loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load RAG system: {e}")
            raise
    
    def search(self, query: str, sources: str = "all", limit: int = 3, 
               use_web_search: bool = True) -> dict:
        """Enhanced search with web integration."""
        try:
            # Use enhanced RAG system for comprehensive results
            enhanced_result = self.enhanced_rag.process_query(query, use_web_search)
            
            # Format response
            response = {
                "query": query,
                "results": enhanced_result['rag_results'],
                "web_results": enhanced_result['web_results'],
                "combined_response": enhanced_result['combined_response'],
                "sources": enhanced_result['sources'],
                "timestamp": datetime.now().isoformat(),
                "total_results": len(enhanced_result['rag_results']) + len(enhanced_result['web_results'])
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "error": str(e),
                "query": query,
                "results": [],
                "web_results": [],
                "combined_response": f"❌ Search failed: {str(e)}",
                "sources": []
            }

# Initialize API
api = EnhancedLEEDRAGAPI()

@app.route('/api/status', methods=['GET'])
def status():
    """API status endpoint."""
    return jsonify({
        "status": "online",
        "service": "Enhanced LEED RAG API with Web Search",
        "version": "2.0",
        "features": ["RAG", "Web Search", "Multi-source"],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/query', methods=['POST'])
def query():
    """Enhanced query endpoint with web search."""
    try:
        data = request.get_json()
        query_text = data.get('query', '').strip()
        sources = data.get('sources', 'all')
        limit = data.get('limit', 3)
        use_web_search = data.get('use_web_search', True)
        
        if not query_text:
            return jsonify({"error": "Query is required"}), 400
        
        logger.info(f"Processing enhanced query: {query_text}")
        
        # Perform enhanced search
        result = api.search(query_text, sources, limit, use_web_search)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Query endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/credits', methods=['GET'])
def credits():
    """Get available LEED credits."""
    try:
        if api.rag_system:
            credits_data = api.rag_system.get_credits()
            return jsonify(credits_data)
        else:
            return jsonify({"error": "RAG system not loaded"}), 500
    except Exception as e:
        logger.error(f"Credits endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analyze uploaded document."""
    try:
        data = request.get_json()
        document_text = data.get('document_text', '')
        project_type = data.get('project_type', 'NC')
        target_credits = data.get('target_credits', [])
        
        if not document_text:
            return jsonify({"error": "Document text is required"}), 400
        
        # Use existing RAG system for analysis
        if api.rag_system:
            analysis_result = api.rag_system.analyze_document(
                document_text, project_type, target_credits
            )
            return jsonify(analysis_result)
        else:
            return jsonify({"error": "RAG system not loaded"}), 500
            
    except Exception as e:
        logger.error(f"Analyze endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/web-search', methods=['POST'])
def web_search():
    """Direct web search endpoint."""
    try:
        data = request.get_json()
        query_text = data.get('query', '').strip()
        num_results = data.get('num_results', 5)
        
        if not query_text:
            return jsonify({"error": "Query is required"}), 400
        
        # Perform web search
        web_results = api.enhanced_rag.web_search.search_web(query_text, num_results)
        formatted_response = api.enhanced_rag.web_search.format_search_results(web_results, query_text)
        
        return jsonify({
            "query": query_text,
            "results": web_results,
            "formatted_response": formatted_response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Web search endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/hybrid-search', methods=['POST'])
def hybrid_search():
    """Hybrid search combining RAG and web results."""
    try:
        data = request.get_json()
        query_text = data.get('query', '').strip()
        rag_limit = data.get('rag_limit', 3)
        web_limit = data.get('web_limit', 3)
        
        if not query_text:
            return jsonify({"error": "Query is required"}), 400
        
        # Get RAG results
        rag_result = api.search(query_text, limit=rag_limit, use_web_search=False)
        
        # Get web results
        web_results = api.enhanced_rag.web_search.search_web(query_text, web_limit)
        
        # Combine results
        combined_response = f"🔍 **Hybrid Search Results for: {query_text}**\n\n"
        
        # Add RAG results
        if rag_result['results']:
            combined_response += "📚 **LEED Knowledge Base:**\n"
            for i, result in enumerate(rag_result['results'], 1):
                metadata = result.get('metadata', {})
                combined_response += f"{i}. {metadata.get('credit_name', 'LEED Info')}\n"
                combined_response += f"   {result.get('text', '')[:150]}...\n\n"
        
        # Add web results
        if web_results:
            combined_response += "🌐 **Web Search Results:**\n"
            for i, result in enumerate(web_results, 1):
                combined_response += f"{i}. {result['title']}\n"
                combined_response += f"   {result['content'][:150]}...\n\n"
        
        return jsonify({
            "query": query_text,
            "rag_results": rag_result['results'],
            "web_results": web_results,
            "combined_response": combined_response,
            "sources": rag_result['sources'] + [f"Web Search: {r.get('source', 'Unknown')}" for r in web_results],
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Hybrid search endpoint error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    """API documentation."""
    return jsonify({
        "service": "Enhanced LEED RAG API with Web Search",
        "version": "2.0",
        "endpoints": {
            "/api/status": "GET - API status",
            "/api/query": "POST - Enhanced query with web search",
            "/api/credits": "GET - Available LEED credits",
            "/api/analyze": "POST - Document analysis",
            "/api/web-search": "POST - Direct web search",
            "/api/hybrid-search": "POST - Combined RAG + web search"
        },
        "features": [
            "RAG-based LEED knowledge retrieval",
            "Web search integration",
            "Multi-source result combination",
            "Document analysis",
            "Credit information lookup"
        ]
    })

def main():
    """Main function to run the enhanced API server."""
    logger.info("Starting Enhanced LEED RAG API with Web Search...")
    logger.info("🌐 Web search integration enabled")
    logger.info("📚 RAG knowledge base loaded")
    logger.info("🔗 API available at: http://localhost:5000")
    logger.info("📖 API documentation: http://localhost:5000/")
    
    port = int(os.environ.get('API_PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == "__main__":
    main()
