#!/usr/bin/env python3
"""
Reciprocal Rank Fusion (RRF)
Combines multiple ranked result lists into a single ranked list.
"""

from typing import List, Dict, Any, Set
from collections import defaultdict


def reciprocal_rank_fusion(
    result_lists: List[List[Dict[str, Any]]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Combine multiple ranked result lists using Reciprocal Rank Fusion.
    
    RRF Score = Σ(1 / (k + rank)) for each result across all lists
    
    Args:
        result_lists: List of ranked result lists (each from a different query)
        k: RRF constant (default: 60, standard value)
    
    Returns:
        Combined and re-ranked results sorted by RRF score (descending)
    """
    if not result_lists:
        return []
    
    if len(result_lists) == 1:
        return result_lists[0]
    
    # Track RRF scores for each unique result
    rrf_scores: Dict[str, float] = defaultdict(float)
    result_map: Dict[str, Dict[str, Any]] = {}
    
    # Process each result list
    for result_list in result_lists:
        for rank, result in enumerate(result_list, start=1):
            # Generate unique key for this result
            result_key = _get_result_key(result)
            
            # Calculate RRF contribution: 1 / (k + rank)
            rrf_contribution = 1.0 / (k + rank)
            rrf_scores[result_key] += rrf_contribution
            
            # Store result (keep first occurrence or highest scoring)
            if result_key not in result_map:
                result_map[result_key] = result.copy()
            else:
                # If we've seen this result before, keep the one with higher score
                existing_score = result_map[result_key].get('score', 0.0)
                new_score = result.get('score', 0.0)
                if new_score > existing_score:
                    result_map[result_key] = result.copy()
    
    # Create combined results with RRF scores
    combined_results = []
    for result_key, rrf_score in rrf_scores.items():
        result = result_map[result_key].copy()
        result['rrf_score'] = rrf_score
        # Keep original score for reference
        result['_original_score'] = result.get('score', 0.0)
        combined_results.append(result)
    
    # Sort by RRF score (descending)
    combined_results.sort(key=lambda x: x['rrf_score'], reverse=True)
    
    # Update ranks based on RRF score
    for i, result in enumerate(combined_results, start=1):
        result['rank'] = i
        # Use RRF score as the primary score
        result['score'] = result['rrf_score']
    
    return combined_results


def _get_result_key(result: Dict[str, Any]) -> str:
    """
    Generate a unique key for a result to identify duplicates.
    
    Uses chunk_id if available, otherwise falls back to text hash or metadata combination.
    """
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
    
    # Last resort: use text hash (first 100 chars)
    text = result.get('text', '')
    if text:
        import hashlib
        text_hash = hashlib.md5(text[:200].encode()).hexdigest()[:16]
        return f"text_hash:{text_hash}"
    
    # Final fallback: use rank and score
    return f"rank:{result.get('rank', 0)}::score:{result.get('score', 0.0)}"


def fuse_results_with_rrf(
    query_results: Dict[str, List[Dict[str, Any]]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Convenience function to fuse results from multiple queries using RRF.
    
    Args:
        query_results: Dictionary mapping query strings to their result lists
        k: RRF constant (default: 60)
    
    Returns:
        Fused and re-ranked results
    """
    result_lists = list(query_results.values())
    return reciprocal_rank_fusion(result_lists, k=k)

