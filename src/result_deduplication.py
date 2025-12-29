#!/usr/bin/env python3
"""
Result Deduplication and Grouping
Removes near-duplicates and groups results by credit with section prioritization.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


# Section priority order (higher priority = more important)
SECTION_PRIORITY = {
    'requirements': 10,
    'intent': 9,
    'documentation': 8,
    'calc': 7,
    'thresholds': 6,
    'definitions': 5,
    'unknown': 1,
}


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot_product / (norm1 * norm2))


def get_chunk_key(chunk: Dict[str, Any]) -> Optional[str]:
    """Generate a key for deduplication based on credit_id, section, and page range."""
    metadata = chunk.get('metadata', {})
    credit_id = metadata.get('credit_id')
    section = metadata.get('section', 'unknown')
    page_start = metadata.get('page_start')
    page_end = metadata.get('page_end')
    doc_id = metadata.get('doc') or metadata.get('source_file')
    
    # Key 1: credit_id + section (for same credit/section dedup)
    if credit_id and section:
        key1 = f"{credit_id}::{section}"
    else:
        key1 = None
    
    # Key 2: doc_id + page range (for same doc/page dedup)
    if doc_id and page_start is not None and page_end is not None:
        key2 = f"{doc_id}::{page_start}-{page_end}"
    else:
        key2 = None
    
    return key1, key2


def remove_near_duplicates(
    results: List[Dict[str, Any]], 
    embedder: Optional[Any] = None,
    similarity_threshold: float = 0.97
) -> List[Dict[str, Any]]:
    """
    Remove near-duplicate results.
    
    Criteria:
    1. Same credit_id + same section + cosine similarity > threshold
    2. Same doc_id + same page range
    
    Args:
        results: List of result dictionaries with 'text' and 'metadata'
        embedder: SentenceTransformer model for computing embeddings (optional)
        similarity_threshold: Cosine similarity threshold (default 0.97)
    
    Returns:
        Deduplicated list of results
    """
    if not results or len(results) < 2:
        return results
    
    # Generate embeddings for all texts if embedder available
    embeddings = None
    if embedder is not None:
        texts = [r['text'] for r in results]
        try:
            embeddings = embedder.encode(texts, convert_to_tensor=False, show_progress_bar=False)
        except Exception:
            # If embedding fails, fall back to key-based dedup only
            embeddings = None
    
    # Track seen items by different criteria
    seen_by_credit_section: Dict[str, int] = {}  # key -> index of kept item
    seen_by_doc_page: Dict[str, int] = {}  # key -> index of kept item
    kept_indices = set()
    
    for i, result in enumerate(results):
        key1, key2 = get_chunk_key(result)
        
        # Check credit_id + section deduplication
        if key1:
            if key1 in seen_by_credit_section:
                # Check similarity if embeddings available
                if embeddings is not None:
                    kept_idx = seen_by_credit_section[key1]
                    similarity = cosine_similarity(embeddings[i], embeddings[kept_idx])
                    if similarity >= similarity_threshold:
                        # Skip this duplicate
                        continue
                else:
                    # Without embeddings, skip if same key
                    continue
            else:
                seen_by_credit_section[key1] = i
        
        # Check doc_id + page range deduplication
        if key2:
            if key2 in seen_by_doc_page:
                # Always skip if same doc/page (exact duplicate)
                continue
            else:
                seen_by_doc_page[key2] = i
        
        kept_indices.add(i)
    
    # Return only kept results, preserving order
    return [results[i] for i in sorted(kept_indices)]


def group_by_credit(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group results by credit_id.
    
    Returns:
        Dictionary mapping credit_id to list of results
    """
    grouped = defaultdict(list)
    
    for result in results:
        metadata = result.get('metadata', {})
        credit_id = metadata.get('credit_id')
        
        if credit_id:
            grouped[credit_id].append(result)
        else:
            # Group items without credit_id under 'unknown'
            grouped['unknown'].append(result)
    
    return dict(grouped)


def get_section_priority(section: Optional[str]) -> int:
    """Get priority score for a section (higher = more important)."""
    if not section:
        return 0
    return SECTION_PRIORITY.get(section.lower(), 1)


def rank_credits_by_relevance(grouped_results: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """
    Rank credits by their relevance (highest scoring chunk).
    
    Returns:
        List of credit_ids sorted by relevance
    """
    credit_scores = []
    
    for credit_id, chunks in grouped_results.items():
        if not chunks:
            continue
        
        # Use the highest score from any chunk in this credit
        max_score = max(chunk.get('score', 0.0) for chunk in chunks)
        
        # Also consider number of relevant chunks
        chunk_count = len(chunks)
        
        # Combined score: max score + bonus for multiple chunks
        combined_score = max_score + (0.01 * min(chunk_count, 5))  # Cap bonus at 5 chunks
        
        credit_scores.append((credit_id, combined_score))
    
    # Sort by score descending
    credit_scores.sort(key=lambda x: x[1], reverse=True)
    
    return [credit_id for credit_id, _ in credit_scores]


def select_top_chunks_per_credit(
    chunks: List[Dict[str, Any]],
    max_chunks_per_credit: int = 3
) -> List[Dict[str, Any]]:
    """
    Select top chunks for a credit, prioritizing by section.
    
    Args:
        chunks: List of chunks for a single credit
        max_chunks_per_credit: Maximum chunks to return per credit
    
    Returns:
        Selected chunks sorted by section priority and score
    """
    if not chunks:
        return []
    
    # Sort by section priority (descending), then by score (descending)
    sorted_chunks = sorted(
        chunks,
        key=lambda c: (
            get_section_priority(c.get('metadata', {}).get('section')),
            c.get('score', 0.0)
        ),
        reverse=True
    )
    
    # Group by section to ensure diversity
    section_groups = defaultdict(list)
    for chunk in sorted_chunks:
        section = chunk.get('metadata', {}).get('section', 'unknown')
        section_groups[section].append(chunk)
    
    # Select top chunk from each section (by priority), then fill remaining slots
    selected = []
    sections_by_priority = sorted(
        section_groups.keys(),
        key=get_section_priority,
        reverse=True
    )
    
    # First pass: take top chunk from each high-priority section
    for section in sections_by_priority:
        if len(selected) >= max_chunks_per_credit:
            break
        if section_groups[section]:
            selected.append(section_groups[section][0])
    
    # Second pass: fill remaining slots with highest-scoring chunks
    remaining_chunks = [
        chunk for section_chunks in section_groups.values()
        for chunk in section_chunks
        if chunk not in selected
    ]
    remaining_chunks.sort(key=lambda c: c.get('score', 0.0), reverse=True)
    
    selected.extend(remaining_chunks[:max_chunks_per_credit - len(selected)])
    
    return selected


def deduplicate_and_group(
    results: List[Dict[str, Any]],
    embedder: Any,
    top_credits: int = 3,
    max_chunks_per_credit: int = 3,
    similarity_threshold: float = 0.97
) -> List[Dict[str, Any]]:
    """
    Main function: deduplicate results and group by credit.
    
    Process:
    1. Remove near-duplicates
    2. Group by credit_id
    3. Rank credits by relevance
    4. Select top credits
    5. For each credit, select top chunks by section priority
    
    Args:
        results: List of search results
        embedder: SentenceTransformer model
        top_credits: Number of top credits to return (2-4)
        max_chunks_per_credit: Maximum chunks per credit
        similarity_threshold: Cosine similarity threshold for dedup
    
    Returns:
        Deduplicated and grouped results
    """
    if not results:
        return []
    
    # Step 1: Remove near-duplicates
    deduplicated = remove_near_duplicates(results, embedder, similarity_threshold)
    
    # Step 2: Group by credit
    grouped = group_by_credit(deduplicated)
    
    # Step 3: Rank credits by relevance
    ranked_credits = rank_credits_by_relevance(grouped)
    
    # Step 4: Select top credits
    top_credit_ids = ranked_credits[:top_credits]
    
    # Step 5: Select top chunks for each credit
    final_results = []
    for credit_id in top_credit_ids:
        credit_chunks = grouped[credit_id]
        selected_chunks = select_top_chunks_per_credit(credit_chunks, max_chunks_per_credit)
        final_results.extend(selected_chunks)
    
    # Re-rank final results by score
    final_results.sort(key=lambda x: x.get('score', 0.0), reverse=True)
    
    # Update ranks
    for i, result in enumerate(final_results):
        result['rank'] = i + 1
    
    return final_results

