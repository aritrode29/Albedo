#!/usr/bin/env python3
"""
Hybrid Retrieval: Dense (FAISS) + Lexical (BM25)
Combines semantic and keyword-based retrieval for better results.
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def weighted_fusion(
    dense_results: List[Dict[str, Any]],
    lexical_results: List[Dict[str, Any]],
    dense_weight: float = 0.7,
    lexical_weight: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Combine dense and lexical results using weighted score fusion.
    
    Args:
        dense_results: Results from FAISS (dense retrieval)
        lexical_results: Results from BM25 (lexical retrieval)
        dense_weight: Weight for dense scores (default: 0.7)
        lexical_weight: Weight for lexical scores (default: 0.3)
    
    Returns:
        Combined and re-ranked results
    """
    if not dense_results and not lexical_results:
        return []
    
    if not dense_results:
        return lexical_results
    
    if not lexical_results:
        return dense_results
    
    # Normalize scores to [0, 1] range for both result sets
    dense_scores = [r.get('score', 0.0) for r in dense_results]
    lexical_scores = [r.get('score', 0.0) for r in lexical_results]
    
    # Normalize dense scores (they're already cosine similarity, typically [0, 1])
    max_dense = max(dense_scores) if dense_scores else 1.0
    min_dense = min(dense_scores) if dense_scores else 0.0
    dense_range = max_dense - min_dense if max_dense > min_dense else 1.0
    
    # Normalize lexical scores (BM25 scores can vary widely)
    max_lexical = max(lexical_scores) if lexical_scores else 1.0
    min_lexical = min(lexical_scores) if lexical_scores else 0.0
    lexical_range = max_lexical - min_lexical if max_lexical > min_lexical else 1.0
    
    # Create result map by unique key
    result_map: Dict[str, Dict[str, Any]] = {}
    
    # Process dense results
    for result in dense_results:
        key = _get_result_key(result)
        normalized_score = (result.get('score', 0.0) - min_dense) / dense_range if dense_range > 0 else 0.0
        weighted_score = normalized_score * dense_weight
        
        result_map[key] = {
            **result,
            'dense_score': result.get('score', 0.0),
            'normalized_dense_score': normalized_score,
            'weighted_dense_score': weighted_score,
            'hybrid_score': weighted_score,
            '_retrieval_method': 'dense'
        }
    
    # Process lexical results
    for result in lexical_results:
        key = _get_result_key(result)
        normalized_score = (result.get('score', 0.0) - min_lexical) / lexical_range if lexical_range > 0 else 0.0
        weighted_score = normalized_score * lexical_weight
        
        if key in result_map:
            # Combine: add lexical score to existing dense score
            result_map[key]['lexical_score'] = result.get('score', 0.0)
            result_map[key]['normalized_lexical_score'] = normalized_score
            result_map[key]['weighted_lexical_score'] = weighted_score
            result_map[key]['hybrid_score'] += weighted_score
            result_map[key]['_retrieval_method'] = 'hybrid'
        else:
            # New result from lexical only
            result_map[key] = {
                **result,
                'lexical_score': result.get('score', 0.0),
                'normalized_lexical_score': normalized_score,
                'weighted_lexical_score': weighted_score,
                'hybrid_score': weighted_score,
                '_retrieval_method': 'lexical'
            }
    
    # Convert to list and sort by hybrid score
    combined_results = list(result_map.values())
    combined_results.sort(key=lambda x: x.get('hybrid_score', 0.0), reverse=True)
    
    # Update ranks and use hybrid_score as primary score
    for i, result in enumerate(combined_results, start=1):
        result['rank'] = i
        result['score'] = result.get('hybrid_score', 0.0)
    
    return combined_results


def rrf_fusion_hybrid(
    dense_results: List[Dict[str, Any]],
    lexical_results: List[Dict[str, Any]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Combine dense and lexical results using Reciprocal Rank Fusion.
    
    Args:
        dense_results: Results from FAISS
        lexical_results: Results from BM25
        k: RRF constant (default: 60)
    
    Returns:
        Combined and re-ranked results
    """
    from reciprocal_rank_fusion import reciprocal_rank_fusion
    
    result_lists = [dense_results, lexical_results]
    return reciprocal_rank_fusion(result_lists, k=k)


def hybrid_search(
    query: str,
    dense_search_fn,
    lexical_search_fn,
    k: int = 10,
    fusion_method: str = 'weighted',
    dense_weight: float = 0.7,
    lexical_weight: float = 0.3,
    rrf_k: int = 60
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining dense and lexical retrieval.
    
    Args:
        query: Search query
        dense_search_fn: Function that takes (query, k) and returns dense results
        lexical_search_fn: Function that takes (query, k) and returns lexical results
        k: Number of results to return
        fusion_method: 'weighted' or 'rrf' (default: 'weighted')
        dense_weight: Weight for dense scores (for weighted fusion)
        lexical_weight: Weight for lexical scores (for weighted fusion)
        rrf_k: RRF constant (for RRF fusion)
    
    Returns:
        Combined and re-ranked results
    """
    # Run both searches
    dense_results = dense_search_fn(query, k * 2)  # Get more candidates
    lexical_results = lexical_search_fn(query, k * 2)
    
    # Fuse results
    if fusion_method == 'rrf':
        combined = rrf_fusion_hybrid(dense_results, lexical_results, k=rrf_k)
    else:  # weighted
        combined = weighted_fusion(dense_results, lexical_results, dense_weight, lexical_weight)
    
    # Return top k
    return combined[:k]


def _get_result_key(result: Dict[str, Any]) -> str:
    """Generate a unique key for a result (same as in RRF module)."""
    metadata = result.get('metadata', {})
    
    # Prefer chunk_id if available (most stable)
    chunk_id = metadata.get('chunk_id')
    if chunk_id:
        return f"chunk_id:{chunk_id}"
    
    # Fall back to credit_id + section + page range
    credit_id = metadata.get('credit_id')
    section = metadata.get('section', 'unknown')
    page_start = metadata.get('page_start')
    page_end = metadata.get('page_end')
    
    if credit_id and section and page_start is not None:
        return f"credit:{credit_id}::section:{section}::pages:{page_start}-{page_end}"
    
    # Last resort: use text hash (first 200 chars)
    text = result.get('text', '')
    if text:
        import hashlib
        text_hash = hashlib.md5(text[:200].encode()).hexdigest()[:16]
        return f"text_hash:{text_hash}"
    
    # Final fallback: use rank and score
    return f"rank:{result.get('rank', 0)}::score:{result.get('score', 0.0)}"

