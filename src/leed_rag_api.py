#!/usr/bin/env python3
"""
LEED RAG Web API
Flask-based web API to serve LEED RAG queries and integrate with frontend.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rag_credit_assistant import RAGCreditAssistant
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
    
    def __init__(self, index_path: str = None):
        self.logger = logging.getLogger(__name__)
        if index_path is None:
            # Default to models/leed_knowledge_base relative to the script directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)  # Go up one level from src
            index_path = os.path.join(project_root, "models", "leed_knowledge_base")
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
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)  # Go up one level from src
            source_specs = {
                'credits': os.path.join(project_root, 'models', 'index_credits'),
                'guide': os.path.join(project_root, 'models', 'index_guide'),
                'forms': os.path.join(project_root, 'models', 'index_forms'),
                'all': os.path.join(project_root, 'models', 'index_all')
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
        # #region agent log
        import json as json_lib
        try:
            with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"location":"leed_rag_api.py:76","message":"load_system entry","data":{"index_path":self.index_path},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+"\n")
        except: pass
        # #endregion
        try:
            import faiss
            
            self.logger.info("Loading LEED RAG system...")
            
            # Load embedding model (lazy load later if needed)
            # self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
            
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
                # #region agent log
                try:
                    with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                        f.write(json_lib.dumps({"location":"leed_rag_api.py:100","message":"load_system multi-index success","data":{"available_sources":self.available_sources,"chunks_count":len(self.chunks) if self.chunks else 0},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+"\n")
                except: pass
                # #endregion
                return True
            
            # Legacy single-index path
            faiss_path = f"{self.index_path}.faiss"
            metadata_path = f"{self.index_path}.json"
            
            if not os.path.exists(faiss_path) or not os.path.exists(metadata_path):
                self.logger.error("FAISS index or metadata not found")
                # #region agent log
                try:
                    with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                        f.write(json_lib.dumps({"location":"leed_rag_api.py:108","message":"load_system index files missing","data":{"faiss_exists":os.path.exists(faiss_path),"json_exists":os.path.exists(metadata_path)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+"\n")
                except: pass
                # #endregion
                return False
            
            self.index = faiss.read_index(faiss_path)
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self.chunks = json.load(f)
            
            self.loaded = True
            self.logger.info(f"Loaded RAG system with {len(self.chunks)} LEED chunks (single-index)")
            # #region agent log
            try:
                with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"location":"leed_rag_api.py:116","message":"load_system single-index success","data":{"chunks_count":len(self.chunks)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+"\n")
            except: pass
            # #endregion
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading RAG system: {e}")
            # #region agent log
            try:
                with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"location":"leed_rag_api.py:120","message":"load_system exception","data":{"error":str(e)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+"\n")
            except: pass
            # #endregion
            return False
    
    def _preprocess_query(self, query: str) -> str:
        """Preprocess query to improve semantic understanding."""
        query = query.strip()
        
        # Add LEED context if not present
        if 'leed' not in query.lower():
            query = f"LEED {query}"
        
        return query
    
    def _expand_query(self, query: str) -> str:
        """Expand query with domain-specific synonyms and context for better semantic matching."""
        query_lower = query.lower()
        original_query = query
        
        # Domain-specific query expansion mappings
        expansions = {
            'water': ['water efficiency', 'water use', 'water consumption', 'potable water', 'fixtures', 'irrigation', 'WE'],
            'energy': ['energy efficiency', 'energy performance', 'energy consumption', 'ASHRAE', 'optimize energy', 'EA'],
            'materials': ['materials', 'resources', 'sustainable materials', 'recycled content', 'waste reduction', 'MR'],
            'indoor': ['indoor air quality', 'IAQ', 'ventilation', 'air quality', 'indoor environmental quality', 'EQ'],
            'site': ['sustainable sites', 'site selection', 'location', 'transportation', 'brownfield', 'SS'],
            'efficiency': ['efficiency', 'performance', 'optimization', 'reduction', 'conservation'],
            'requirements': ['requirements', 'prerequisites', 'standards', 'criteria', 'compliance'],
            'credits': ['credits', 'points', 'certification', 'LEED credits', 'credit requirements'],
            'we': ['water efficiency', 'WE credits', 'water use reduction', 'water'],
            'ea': ['energy and atmosphere', 'EA credits', 'energy performance', 'energy'],
            'mr': ['materials and resources', 'MR credits', 'sustainable materials', 'materials'],
            'eq': ['indoor environmental quality', 'EQ credits', 'indoor air quality', 'indoor'],
            'ss': ['sustainable sites', 'SS credits', 'site selection', 'site'],
            'lt': ['location and transportation', 'LT credits', 'transportation'],
        }
        
        # Add expanded terms
        expanded_terms = [original_query]
        for key, synonyms in expansions.items():
            if key in query_lower:
                # Add first 2 most relevant synonyms
                expanded_terms.extend(synonyms[:2])
        
        # Combine original query with expansions (limit to avoid too long queries)
        expanded_query = ' '.join(set(expanded_terms[:4]))  # Use set to remove duplicates
        
        return expanded_query if len(expanded_query) > len(original_query) else original_query
    
    def _search_index(self, index, chunks, query: str, k: int) -> List[Dict[str, Any]]:
        # #region agent log
        import json as json_lib
        try:
            with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"location":"leed_rag_api.py:122","message":"_search_index entry","data":{"query":query[:50],"k":k,"chunks_count":len(chunks) if chunks else 0,"has_embedder":self.embedder is not None,"index_ntotal":index.ntotal if hasattr(index,'ntotal') else 'unknown'},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H4"})+"\n")
        except: pass
        # #endregion
        import faiss
        try:
            # Preprocess and expand query for better semantic matching
            preprocessed_query = self._preprocess_query(query)
            expanded_query = self._expand_query(preprocessed_query)
            
            # Generate query embedding with expanded query
            query_embedding = self.embedder.encode([expanded_query], convert_to_tensor=False)
            # #region agent log
            try:
                with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"location":"leed_rag_api.py:126","message":"_search_index embedding generated","data":{"embedding_shape":list(query_embedding.shape) if hasattr(query_embedding,'shape') else 'unknown'},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H3"})+"\n")
            except: pass
            # #endregion
            faiss.normalize_L2(query_embedding)
            # Search
            scores, indices = index.search(query_embedding.astype('float32'), k)
            # #region agent log
            try:
                with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"location":"leed_rag_api.py:130","message":"_search_index faiss search done","data":{"scores_count":len(scores[0]) if len(scores)>0 else 0,"indices_count":len(indices[0]) if len(indices)>0 else 0,"top_score":float(scores[0][0]) if len(scores)>0 and len(scores[0])>0 else None},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H4"})+"\n")
            except: pass
            # #endregion
            results: List[Dict[str, Any]] = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                # FAISS can return -1 for invalid indices, skip those
                if idx >= 0 and idx < len(chunks):
                    chunk = chunks[idx]
                    md = chunk.get('metadata', {})
                    result = {
                        'rank': i + 1,
                        'score': float(score),
                        'text': chunk.get('text', ''),
                        'metadata': md
                    }
                    results.append(result)
            # #region agent log
            try:
                with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"location":"leed_rag_api.py:143","message":"_search_index return","data":{"results_count":len(results)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H4"})+"\n")
            except: pass
            # #endregion
            return results
        except Exception as e:
            self.logger.error(f"Error in _search_index: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            # #region agent log
            try:
                with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"location":"leed_rag_api.py:148","message":"_search_index exception","data":{"error":str(e)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H3"})+"\n")
            except: pass
            # #endregion
            return []
    
    def search(self, query: str, k: int = 5, sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search relevant chunks. If sources provided and multi-index is available, merge top-k."""
        # #region agent log
        import json as json_lib
        try:
            with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"location":"leed_rag_api.py:150","message":"search entry","data":{"query":query[:50],"k":k,"loaded":self.loaded,"has_multi":bool(self.multi),"available_sources":self.available_sources},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H6"})+"\n")
        except: pass
        # #endregion
        try:
            if not self.loaded:
                self.logger.warning("RAG system not loaded")
                # #region agent log
                try:
                    with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                        f.write(json_lib.dumps({"location":"leed_rag_api.py:154","message":"search not loaded","data":{},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+"\n")
                except: pass
                # #endregion
                return []
            
            # Lazy load embedder
            if self.embedder is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    self.logger.info("Loading embedding model...")
                    self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
                    # #region agent log
                    try:
                        with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                            f.write(json_lib.dumps({"location":"leed_rag_api.py:162","message":"embedder loaded","data":{},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H2"})+"\n")
                    except: pass
                    # #endregion
                except Exception as e:
                    self.logger.error(f"Failed to load embedder: {e}")
                    # #region agent log
                    try:
                        with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                            f.write(json_lib.dumps({"location":"leed_rag_api.py:165","message":"embedder load failed","data":{"error":str(e)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H2"})+"\n")
                    except: pass
                    # #endregion
                    return []
            
            # Multi-index path with source filtering
            if self.multi and (sources or self.available_sources):
                use_sources = sources or ['all']
                # Validate sources
                use_sources = [s for s in use_sources if s in self.multi]
                if not use_sources:
                    use_sources = ['all'] if 'all' in self.multi else [self.available_sources[0]]
                
                self.logger.info(f"Searching sources: {use_sources} for query: {query[:50]}")
                merged: List[Dict[str, Any]] = []
                # Search with higher k to get more candidates, then re-rank
                search_k = min(k * 3, 20)  # Get 3x results for better semantic matching
                for s in use_sources:
                    idx = self.multi[s]['index']
                    chks = self.multi[s]['chunks']
                    self.logger.debug(f"Source {s}: index size={idx.ntotal if hasattr(idx, 'ntotal') else 'unknown'}, chunks={len(chks)}")
                    res = self._search_index(idx, chks, query, search_k)
                    self.logger.debug(f"Source {s} returned {len(res)} results")
                    # annotate provenance
                    for r in res:
                        r['metadata'] = dict(r.get('metadata', {}))
                        r['metadata']['source'] = r['metadata'].get('source', s)
                        r['metadata']['_index'] = s
                    merged.extend(res)
                # Sort by score desc and take top k
                merged.sort(key=lambda x: x.get('score', 0.0), reverse=True)
                # Filter low-quality results (score threshold)
                filtered = [r for r in merged if r.get('score', 0.0) > 0.3]  # Minimum similarity threshold
                if not filtered:
                    filtered = merged[:k]  # Fallback to top k if all scores are low
                # Re-rank and limit to k
                for i, r in enumerate(filtered[:k]):
                    r['rank'] = i + 1
                self.logger.info(f"Search completed: {len(filtered[:k])} results for query: {query[:50]}")
                # #region agent log
                try:
                    with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                        f.write(json_lib.dumps({"location":"leed_rag_api.py:195","message":"search multi-index return","data":{"results_count":len(filtered[:k]),"merged_total":len(merged),"filtered_count":len(filtered)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H6"})+"\n")
                except: pass
                # #endregion
                return filtered[:k]
            
            # Legacy single-index
            if not self.index or not self.chunks:
                self.logger.warning("Legacy index not available")
                # #region agent log
                try:
                    with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                        f.write(json_lib.dumps({"location":"leed_rag_api.py:200","message":"search legacy index missing","data":{"has_index":bool(self.index),"has_chunks":bool(self.chunks)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+"\n")
                except: pass
                # #endregion
                return []
            # Search with higher k for better semantic matching
            search_k = min(k * 3, 20)
            result = self._search_index(self.index, self.chunks, query, search_k)
            # Filter low-quality results
            filtered = [r for r in result if r.get('score', 0.0) > 0.3]
            if not filtered:
                filtered = result[:k]
            # #region agent log
            try:
                with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"location":"leed_rag_api.py:201","message":"search legacy return","data":{"results_count":len(filtered[:k]),"original_count":len(result)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H6"})+"\n")
            except: pass
            # #endregion
            return filtered[:k]
        except Exception as e:
            self.logger.error(f"Error searching: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            # #region agent log
            try:
                with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"location":"leed_rag_api.py:206","message":"search exception","data":{"error":str(e)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H6"})+"\n")
            except: pass
            # #endregion
            return []

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Initialize RAG API
rag_api = LEEDRAGAPI()
# #region agent log
import json as json_lib
try:
    with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
        f.write(json_lib.dumps({"location":"leed_rag_api.py:325","message":"rag_api initialized","data":{"loaded":rag_api.loaded},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+"\n")
except: pass
# #endregion
# Singleton robust assistant (lazy-initialized when /api/assistant is used)
assistant: Optional[Any] = None

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
    # #region agent log
    import json as json_lib
    try:
        with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json_lib.dumps({"location":"leed_rag_api.py:291","message":"api_query entry","data":{"rag_api_loaded":rag_api.loaded},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+"\n")
    except: pass
    # #endregion
    try:
        # Lazy load RAG system if not loaded
        if not rag_api.loaded:
            # #region agent log
            try:
                with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                    f.write(json_lib.dumps({"location":"leed_rag_api.py:295","message":"api_query lazy loading RAG","data":{},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H1"})+"\n")
            except: pass
            # #endregion
            rag_api.load_system()
        
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query parameter required'}), 400
        
        query = data['query']
        limit = data.get('limit', 5)
        # Increase limit for better semantic matching (will filter later)
        search_limit = max(limit, 5)  # Minimum 5 results
        sources = data.get('sources')  # optional list
        
        # #region agent log
        try:
            with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"location":"leed_rag_api.py:300","message":"api_query params","data":{"query":query[:50],"limit":limit,"sources":sources,"rag_loaded_after":rag_api.loaded},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H6"})+"\n")
        except: pass
        # #endregion
        
        if not query.strip():
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        # Search using RAG system (with optional sources)
        # Use higher k for better semantic matching, then filter to limit
        results = rag_api.search(query, k=search_limit, sources=sources)
        
        # #region agent log
        try:
            with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"location":"leed_rag_api.py:307","message":"api_query search done","data":{"results_count":len(results)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H6"})+"\n")
        except: pass
        # #endregion
        
        response = {
            'query': query,
            'results_count': len(results),
            'results': results,
            'used_sources': sources or (['all'] if 'all' in getattr(rag_api, 'available_sources', []) else getattr(rag_api, 'available_sources', [])),
            'status': 'success'
        }
        
        # #region agent log
        try:
            with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"location":"leed_rag_api.py:317","message":"api_query response","data":{"response_results_count":len(response['results'])},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H6"})+"\n")
        except: pass
        # #endregion
        
        return jsonify(response)
        
    except Exception as e:
        app.logger.error(f"Error in query API: {e}")
        # #region agent log
        try:
            with open(r"g:\My Drive\UT_Austin_MSSD\Proposals\GreenFund\03 LEED Tool\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json_lib.dumps({"location":"leed_rag_api.py:321","message":"api_query exception","data":{"error":str(e)},"timestamp":int(__import__("time").time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"H6"})+"\n")
        except: pass
        # #endregion
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


@app.route('/api/assistant', methods=['POST'])
def api_assistant():
    """
    Robust RAG assistant endpoint.

    Combines:
    - Retrieval over the LEED multi-index knowledge base
    - Credit templates hydrated from the credit catalog
    - Binary evidence classifier (optional evidence_text)
    - Strict citations in a ChatGPT-style answer payload
    """
    global assistant
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query parameter required'}), 400

        query: str = data['query']
        evidence_text: Optional[str] = data.get('evidence_text') or data.get('evidence') or None
        sources = data.get('sources')
        k = int(data.get('limit', data.get('k', 4)))

        if not query.strip():
            return jsonify({'error': 'Query cannot be empty'}), 400

        # Ensure RAG system is loaded before initializing assistant
        if not rag_api.loaded:
            rag_api.load_system()
        
        if assistant is None:
            app.logger.info("Initializing RAGCreditAssistant for /api/assistant")
            try:
                from rag_credit_assistant import RAGCreditAssistant
                assistant = RAGCreditAssistant()
            except Exception as e:
                app.logger.error(f"Failed to initialize assistant: {e}")
                return jsonify({
                    'error': f'Failed to initialize assistant: {str(e)}',
                    'status': 'error'
                }), 500

        if not assistant.ready:
            # Try to reload the assistant's engine
            try:
                if hasattr(assistant, 'engine') and hasattr(assistant.engine, 'api'):
                    assistant.engine.api.load_system()
                    if assistant.engine.api.loaded:
                        assistant.engine.loaded = True
                        assistant.embedder = assistant.engine.api.embedder
            except Exception as e:
                app.logger.warning(f"Failed to reload assistant engine: {e}")
            
            if not assistant.ready:
                # Return error but don't use 503 - let frontend fall back to RAG API
                return jsonify({
                    'error': 'RAG assistant not ready. Falling back to basic search.',
                    'status': 'error',
                    'fallback_available': True
                }), 200  # Return 200 so frontend can handle gracefully

        result = assistant.analyze(
            query=query,
            evidence_text=evidence_text,
            sources=sources,
            k=k,
        )

        return jsonify({
            'status': 'success',
            **result,
        })

    except Exception as e:
        app.logger.error(f"Error in assistant API: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e), 'status': 'error'}), 500

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
        logger.warning("Failed to load RAG system. The API will start but queries may not work.")
        logger.warning("To build the models, run: python src/deploy_rag_system.py")
        # Don't exit, start the server anyway
    
    # Start Flask server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting server on port {port}")
    logger.info(f"API available at: http://localhost:{port}")
    logger.info(f"API documentation: http://localhost:{port}/")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == "__main__":
    main()
