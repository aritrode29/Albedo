# Query Expansion and Reciprocal Rank Fusion (RRF)

## Overview

This document describes the query expansion and RRF fusion system that transforms vague queries into targeted LEED sub-queries and combines results for more stable and relevant retrieval.

## Problem Solved

Vague queries like "energy efficiency requirements" are too broad and can return:
- Random, inconsistent results
- Missing relevant credits
- Low precision due to semantic mismatch

## Solution

### Query Expansion

Transforms vague queries into 3-6 targeted LEED-specific sub-queries:

**Example:**
- Input: `"energy efficiency requirements"`
- Output:
  1. `"EA Minimum Energy Performance requirements LEED v4.1 BD+C"`
  2. `"EA Optimize Energy Performance requirements thresholds"`
  3. `"energy performance prerequisite baseline ASHRAE Appendix G"`
  4. `"dual metric energy performance greenhouse gas emissions"`
  5. `"EA credit requirements LEED v4.1"`
  6. `"energy efficiency requirements LEED v4.1 BD+C"`

### Reciprocal Rank Fusion (RRF)

Combines results from multiple sub-queries using RRF scoring:

**RRF Score Formula:**
```
RRF_Score(result) = Σ(1 / (k + rank_i)) for each query i
```

Where:
- `k = 60` (standard RRF constant)
- `rank_i` = rank of result in query i's results

**Benefits:**
- Results appearing in multiple queries get higher scores
- More stable ranking across different query phrasings
- Better coverage of relevant content

## Implementation

### Module: `src/query_expansion.py`

**Key Functions:**
- `expand_query()`: Main function to expand queries
- `extract_keywords()`: Extracts keywords and categories
- `generate_credit_specific_queries()`: Creates credit-specific queries
- `generate_term_based_queries()`: Creates term-based queries
- `generate_section_specific_queries()`: Creates section-specific queries

**Expansion Strategies:**
1. **Credit Code Detection**: If EA, WE, MR, etc. found → create specific credit queries
2. **Category Detection**: If "energy", "water", etc. → create category-specific queries
3. **Term Expansion**: Expand common terms using predefined mappings
4. **Section Detection**: If "requirements", "thresholds" → create section-specific queries

### Module: `src/reciprocal_rank_fusion.py`

**Key Functions:**
- `reciprocal_rank_fusion()`: Main RRF fusion function
- `fuse_results_with_rrf()`: Convenience function for multiple queries
- `_get_result_key()`: Generates unique keys for deduplication

**Result Key Generation:**
1. Prefer `chunk_id` (most stable)
2. Fall back to `credit_id + section + page_range`
3. Last resort: text hash

### Integration: `src/leed_rag_api.py`

The `search()` method now:
1. Expands query into sub-queries (if enabled)
2. Runs FAISS retrieval for each sub-query
3. Fuses results using RRF
4. Applies deduplication and grouping
5. Returns final ranked results

**Parameters:**
- `use_query_expansion`: Enable/disable expansion (default: True)
- `max_subqueries`: Maximum sub-queries to generate (default: 6)

## Usage Example

### API Request

```json
{
  "query": "energy efficiency requirements",
  "limit": 5,
  "use_query_expansion": true,
  "max_subqueries": 6,
  "use_grouping": true,
  "top_credits": 3
}
```

### Process Flow

1. **Query Expansion:**
   ```
   "energy efficiency requirements"
   ↓
   [
     "EA Minimum Energy Performance requirements LEED v4.1 BD+C",
     "EA Optimize Energy Performance requirements thresholds",
     "energy performance prerequisite baseline ASHRAE Appendix G",
     ...
   ]
   ```

2. **FAISS Retrieval:**
   - Run search for each sub-query
   - Get top-k results per query

3. **RRF Fusion:**
   - Combine all results
   - Calculate RRF scores
   - Re-rank by RRF score

4. **Deduplication & Grouping:**
   - Remove near-duplicates
   - Group by credit
   - Select top credits and sections

### Response Structure

```json
{
  "query": "energy efficiency requirements",
  "results_count": 5,
  "results": [
    {
      "rank": 1,
      "score": 0.045,  // RRF score
      "rrf_score": 0.045,
      "_original_score": 0.89,  // Original FAISS score
      "text": "EA Prerequisite: Minimum Energy Performance\n\nRequirements:...",
      "metadata": {
        "credit_id": "EA-p2",
        "section": "requirements",
        "_query": "EA Minimum Energy Performance requirements LEED v4.1 BD+C"
      }
    },
    ...
  ]
}
```

## Benefits

1. **Better Coverage**: Multiple queries catch different aspects
2. **Stable Results**: RRF reduces randomness in ranking
3. **LEED-Specific**: Queries tailored to LEED terminology
4. **Higher Precision**: Targeted queries match better
5. **Consistent Ranking**: Results appearing in multiple queries ranked higher

## Configuration

### Adjusting Query Expansion

```python
# More sub-queries (broader coverage)
expand_query("energy efficiency", max_subqueries=8)

# Fewer sub-queries (faster, more focused)
expand_query("energy efficiency", max_subqueries=3)
```

### Adjusting RRF Constant

```python
# Higher k = less weight on rank differences (smoother)
reciprocal_rank_fusion(result_lists, k=100)

# Lower k = more weight on rank differences (more selective)
reciprocal_rank_fusion(result_lists, k=30)
```

## Performance

- Query expansion: ~1-5ms (rule-based)
- RRF fusion: ~5-20ms for typical queries
- Overall overhead: ~10-50ms (acceptable for improved results)

## Future Enhancements

- LLM-based query expansion (more sophisticated)
- Learning-based term expansions
- Query-specific RRF constant tuning
- Multi-stage fusion (RRF + score-based re-ranking)
- Query performance analytics

