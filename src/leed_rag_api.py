#!/usr/bin/env python3
"""
LEED RAG Web API
Flask-based web API to serve LEED RAG queries and integrate with frontend.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import traceback

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup logging for web API"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

class LEEDRAGAPI:
    """LEED RAG API service"""
    
    def __init__(self, index_path: str = "models/leed_knowledge_base"):
        self.logger = logging.getLogger(__name__)
        self.index_path = index_path
        self.embedder = None
        # Single-index (legacy)
        self.index = None
        self.chunks = []
        self.loaded = False
        # Multi-index store: source -> {index, chunks}
        self.multi: Dict[str, Dict[str, Any]] = {}
        self.available_sources: List[str] = []
        
    def _load_multi_indices(self) -> None:
        """Try to load multi-index set if available."""
        try:
            import faiss
            source_specs = {
                'credits': 'models/index_credits',
                'guide': 'models/index_guide',
                'forms': 'models/index_forms',
                'all': 'models/index_all'
            }
            for source, prefix in source_specs.items():
                faiss_path = f"{prefix}.faiss"
                metadata_path = f"{prefix}.json"
                if os.path.exists(faiss_path) and os.path.exists(metadata_path):
                    idx = faiss.read_index(faiss_path)
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        chunks = json.load(f)
                    self.multi[source] = {'index': idx, 'chunks': chunks}
                    self.available_sources.append(source)
            if self.available_sources:
                self.logger.info(f"Loaded multi-index sources: {', '.join(self.available_sources)}")
        except Exception as e:
            self.logger.warning(f"Multi-index load failed: {e}")
    
    def load_system(self) -> bool:
        """Load the RAG system components"""
        try:
            from sentence_transformers import SentenceTransformer
            import faiss
            
            self.logger.info("Loading LEED RAG system...")
            
            # Load embedding model
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
            
            # Try multi-index first
            self._load_multi_indices()
            if self.available_sources:
                # Fallback single-index not required; mark loaded
                self.loaded = True
                # For legacy endpoints (credits list), prefer 'all' if present, else first source
                if 'all' in self.multi:
                    self.index = self.multi['all']['index']
                    self.chunks = self.multi['all']['chunks']
                else:
                    first = self.available_sources[0]
                    self.index = self.multi[first]['index']
                    self.chunks = self.multi[first]['chunks']
                self.logger.info(f"RAG loaded with multi-index; default view uses: {'all' if 'all' in self.multi else first}")
                return True
            
            # Legacy single-index path
            faiss_path = f"{self.index_path}.faiss"
            metadata_path = f"{self.index_path}.json"
            
            if not os.path.exists(faiss_path) or not os.path.exists(metadata_path):
                self.logger.error("FAISS index or metadata not found")
                return False
            
            self.index = faiss.read_index(faiss_path)
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.chunks = json.load(f)
            
            self.loaded = True
            self.logger.info(f"Loaded RAG system with {len(self.chunks)} LEED chunks (single-index)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading RAG system: {e}")
            return False
    
    def _search_index(self, index, chunks, query: str, k: int) -> List[Dict[str, Any]]:
        import faiss
        # Generate query embedding
        query_embedding = self.embedder.encode([query], convert_to_tensor=False)
        faiss.normalize_L2(query_embedding)
        # Search
        scores, indices = index.search(query_embedding.astype('float32'), k)
        results: List[Dict[str, Any]] = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(chunks):
                chunk = chunks[idx]
                md = chunk.get('metadata', {})
                result = {
                    'rank': i + 1,
                    'score': float(score),
                    'text': chunk.get('text', ''),
                    'metadata': md
                }
                results.append(result)
        return results
    
    def search(self, query: str, k: int = 5, sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search relevant chunks. If sources provided and multi-index is available, merge top-k."""
        try:
            if not self.loaded or not self.embedder:
                return []
            
            # Multi-index path with source filtering
            if self.multi and (sources or self.available_sources):
                use_sources = sources or ['all']
                # Validate sources
                use_sources = [s for s in use_sources if s in self.multi]
                if not use_sources:
                    use_sources = ['all'] if 'all' in self.multi else [self.available_sources[0]]
                merged: List[Dict[str, Any]] = []
                for s in use_sources:
                    res = self._search_index(self.multi[s]['index'], self.multi[s]['chunks'], query, k)
                    # annotate provenance
                    for r in res:
                        r['metadata'] = dict(r.get('metadata', {}))
                        r['metadata']['source'] = r['metadata'].get('source', s)
                        r['metadata']['_index'] = s
                    merged.extend(res)
                # sort by score desc and take top k
                merged.sort(key=lambda x: x.get('score', 0.0), reverse=True)
                # re-rank
                for i, r in enumerate(merged[:k]):
                    r['rank'] = i + 1
                return merged[:k]
            
            # Legacy single-index
            if not self.index or not self.chunks:
                return []
            return self._search_index(self.index, self.chunks, query, k)
        except Exception as e:
            self.logger.error(f"Error searching: {e}")
            return []

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Initialize RAG API
rag_api = LEEDRAGAPI()

@app.route('/')
def home():
    """Home page with API documentation"""
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>LEED RAG API</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .method { color: #007bff; font-weight: bold; }
        .example { background: #e9ecef; padding: 10px; border-radius: 3px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>🏗️ LEED RAG API</h1>
    <p>AI-powered LEED certification assistance API</p>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> /api/status</h3>
        <p>Check API status and system health</p>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">POST</span> /api/query</h3>
        <p>Query the LEED knowledge base</p>
        <div class="example">
            <strong>Request:</strong><br>
            { "query": "What are the requirements for energy efficiency credits?", "limit": 3, "sources": ["credits","guide"] }
        </div>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> /api/credits</h3>
        <p>Get list of available LEED credits</p>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">POST</span> /api/analyze</h3>
        <p>Analyze LEED document or project data</p>
        <div class="example">
            <strong>Request:</strong><br>
            { "document_text": "...", "project_type": "NC", "target_credits": ["EA", "WE"], "sources": ["credits"] }
        </div>
    </div>
    
    <h2>🔗 Integration</h2>
    <p>This API can be integrated with:</p>
    <ul>
        <li>CertiSense demo frontend</li>
        <li>LEED platform main application</li>
        <li>Third-party LEED tools</li>
        <li>Mobile applications</li>
    </ul>
</body>
</html>
    """)

@app.route('/api/status')
def api_status():
    """Check API status"""
    try:
        status = {
            'status': 'healthy' if rag_api.loaded else 'loading',
            'chunks_loaded': len(rag_api.chunks) if rag_api.loaded else 0,
            'system_ready': rag_api.loaded,
            'available_sources': getattr(rag_api, 'available_sources', []),
            'timestamp': json.dumps(None, default=str)
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/query', methods=['POST'])
def api_query():
    """Query the LEED knowledge base"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query parameter required'}), 400
        
        query = data['query']
        limit = data.get('limit', 5)
        sources = data.get('sources')  # optional list
        
        if not query.strip():
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        # Search using RAG system (with optional sources)
        results = rag_api.search(query, k=limit, sources=sources)
        
        response = {
            'query': query,
            'results_count': len(results),
            'results': results,
            'used_sources': sources or (['all'] if 'all' in getattr(rag_api, 'available_sources', []) else getattr(rag_api, 'available_sources', [])),
            'status': 'success'
        }
        
        return jsonify(response)
        
    except Exception as e:
        app.logger.error(f"Error in query API: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/credits')
def api_credits():
    """Get list of available LEED credits"""
    try:
        if not rag_api.loaded:
            return jsonify({'error': 'RAG system not loaded'}), 503
        
        credits = []
        seen_credits = set()
        
        # Prefer combined view from 'all' if present
        chunks_view = rag_api.multi.get('all', {}).get('chunks') if rag_api.multi else rag_api.chunks
        if chunks_view is None:
            chunks_view = rag_api.chunks
        
        for chunk in chunks_view:
            metadata = chunk.get('metadata', {})
            credit_code = metadata.get('credit_code')
            credit_name = metadata.get('credit_name')
            
            if credit_code and credit_name and credit_code not in seen_credits:
                credits.append({
                    'code': credit_code,
                    'name': credit_name,
                    'type': metadata.get('type', 'Unknown'),
                    'points_min': metadata.get('points_min'),
                    'points_max': metadata.get('points_max')
                })
                seen_credits.add(credit_code)
        
        return jsonify({
            'credits': credits,
            'total_count': len(credits),
            'status': 'success'
        })
        
    except Exception as e:
        app.logger.error(f"Error in credits API: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """Analyze LEED document or project data"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        document_text = data.get('document_text', '')
        project_type = data.get('project_type', 'NC')
        target_credits = data.get('target_credits', [])
        sources = data.get('sources')
        
        if not document_text.strip():
            return jsonify({'error': 'Document text required'}), 400
        
        # Analyze document against target credits
        analysis_results = []
        
        for credit_code in target_credits:
            query = f"{credit_code} credit requirements for {project_type} projects"
            results = rag_api.search(query, k=3, sources=sources)
            
            analysis_results.append({
                'credit_code': credit_code,
                'query': query,
                'relevant_info': results,
                'compliance_status': 'needs_review'
            })
        
        response = {
            'project_type': project_type,
            'target_credits': target_credits,
            'analysis_results': analysis_results,
            'used_sources': sources or (['all'] if 'all' in getattr(rag_api, 'available_sources', []) else getattr(rag_api, 'available_sources', [])),
            'status': 'success'
        }
        
        return jsonify(response)
        
    except Exception as e:
        app.logger.error(f"Error in analyze API: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'LEED RAG API',
        'version': '1.1.0',
        'multi_index': getattr(rag_api, 'available_sources', [])
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def main():
    """Main function to run the API server"""
    logger = setup_logging()
    
    logger.info("Starting LEED RAG API server...")
    
    # Load RAG system
    if not rag_api.load_system():
        logger.error("Failed to load RAG system. Make sure you've run the deployment script first.")
        logger.error("Run: python src/deploy_rag_system.py or python src/build_rag_corpus.py")
        return
    
    # Start Flask server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting server on port {port}")
    logger.info(f"API available at: http://localhost:{port}")
    logger.info(f"API documentation: http://localhost:{port}/")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == "__main__":
    main()
