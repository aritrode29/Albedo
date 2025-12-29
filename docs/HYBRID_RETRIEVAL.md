# Hybrid Retrieval: Dense (FAISS) + Lexical (BM25)

## Overview

This document describes the hybrid retrieval system that combines dense semantic search (FAISS) with lexical keyword search (BM25) for improved retrieval quality, especially for LEED-specific content like credit IDs, acronyms, tables, and thresholds.

## Problem Solved

FAISS alone can:
- Miss obvious keyword matches (e.g., "EA-p2", "ASHRAE 90.1")
- Return semantically "close" but irrelevant chunks
- Struggle with exact matches for credit codes, acronyms, and technical terms

BM25 alone can:
- Miss semantic relationships (e.g., "energy efficiency" vs "optimize energy performance")
- Over-rely on exact keyword matches
- Miss context and meaning

**Solution:** Combine both approaches for the best of both worlds.

## Implementation

### Module: `src/bm25_index.py`

**BM25Index Class:**
- Builds BM25 lexical search index from chunks
- Enhances text with metadata (credit codes, names, sections) for better keyword matching
- Tokenizes text with special handling for LEED credit codes
- Saves/loads indices to disk

**Key Features:**
- Tokenization preserves credit codes (EA, WE, MR, etc.)
- Metadata enhancement: adds credit_code, credit_name, section to searchable text
- Efficient indexing and retrieval

### Module: `src/hybrid_retrieval.py`

**Fusion Methods:**

1. **Weighted Fusion** (default):
   ```python
   hybrid_score = (normalized_dense_score * dense_weight) + 
                  (normalized_lexical_score * lexical_weight)
   ```
   - Default weights: dense=0.7, lexical=0.3
   - Normalizes scores to [0, 1] range before weighting
   - Combines results from both methods

2. **RRF Fusion**:
   - Uses Reciprocal Rank Fusion to combine ranked lists
   - Results appearing in both lists get higher scores
   - More stable ranking

### Integration: `src/leed_rag_api.py`

The `search()` method now:
1. Runs FAISS (dense) search
2. Runs BM25 (lexical) search (if available)
3. Fuses results using weighted or RRF fusion
4. Continues with query expansion, deduplication, and grouping

**Parameters:**
- `use_hybrid`: Enable/disable hybrid retrieval (default: True)
- `fusion_method`: 'weighted' or 'rrf' (default: 'weighted')
- `dense_weight`: Weight for dense scores (default: 0.7)
- `lexical_weight`: Weight for lexical scores (default: 0.3)

### Index Building: `src/build_rag_corpus.py`

BM25 indices are automatically built alongside FAISS indices:
- Builds BM25 index for each source (credits, guide, forms, all)
- Saves as `.bm25` files alongside `.faiss` and `.json` files
- Loads automatically when available

## Usage Example

### API Request

```json
{
  "query": "EA Minimum Energy Performance ASHRAE 90.1",
  "limit": 5,
  "use_hybrid": true,
  "fusion_method": "weighted",
  "dense_weight": 0.7,
  "lexical_weight": 0.3,
  "use_query_expansion": true,
  "use_grouping": true
}
```

### Process Flow

1. **Dense Search (FAISS):**
   - Semantic similarity search
   - Finds "EA Optimize Energy Performance" (semantically similar)
   - Score: 0.85

2. **Lexical Search (BM25):**
   - Keyword matching search
   - Finds exact "EA Minimum Energy Performance" (keyword match)
   - Score: 12.5 (BM25 score)

3. **Fusion:**
   - Normalize scores: dense=0.85, lexical=0.95 (normalized)
   - Weighted: (0.85 * 0.7) + (0.95 * 0.3) = 0.88
   - Re-rank by hybrid score

4. **Result:**
   - Exact match ("EA Minimum Energy Performance") ranked higher
   - Semantic matches still included
   - Best of both worlds

### Response Structure

```json
{
  "query": "EA Minimum Energy Performance ASHRAE 90.1",
  "results": [
    {
      "rank": 1,
      "score": 0.88,  // Hybrid score
      "hybrid_score": 0.88,
      "dense_score": 0.85,
      "lexical_score": 12.5,
      "normalized_dense_score": 0.85,
      "normalized_lexical_score": 0.95,
      "weighted_dense_score": 0.595,
      "weighted_lexical_score": 0.285,
      "_retrieval_method": "hybrid",
      "text": "EA Prerequisite: Minimum Energy Performance...",
      "metadata": {
        "credit_id": "EA-p2",
        "section": "requirements"
      }
    }
  ]
}
```

## Benefits

1. **Better Keyword Matching**: BM25 catches exact matches for credit IDs, acronyms, standards
2. **Semantic Understanding**: FAISS captures meaning and context
3. **Comprehensive Coverage**: Both exact and semantic matches included
4. **Configurable Balance**: Adjust weights based on query type
5. **Quality Jump**: Biggest improvement for LEED text (credit IDs, acronyms, thresholds)

## Configuration

### Adjusting Fusion Weights

```python
# More weight on keywords (good for exact matches)
use_hybrid=True, fusion_method='weighted',
dense_weight=0.5, lexical_weight=0.5

# More weight on semantics (good for conceptual queries)
use_hybrid=True, fusion_method='weighted',
dense_weight=0.8, lexical_weight=0.2

# Use RRF instead
use_hybrid=True, fusion_method='rrf'
```

### When to Use Each Method

**Weighted Fusion:**
- Good for general queries
- Allows fine-tuning of balance
- Default choice

**RRF Fusion:**
- Good when you want stable ranking
- Less sensitive to score differences
- Works well with query expansion

## Performance

- BM25 indexing: ~100-500ms per 1000 chunks
- BM25 search: ~1-5ms per query
- Fusion overhead: ~1-2ms
- Overall: Minimal impact, significant quality improvement

## Dependencies

Install rank-bm25:
```bash
pip install rank-bm25
```

The system gracefully falls back to dense-only if BM25 is unavailable.

## Future Enhancements

- Adaptive weight tuning based on query characteristics
- Per-source weight configuration
- Learning-based weight optimization
- Multi-stage fusion (dense → lexical → re-rank)
- Query type detection (keyword-heavy vs semantic)

