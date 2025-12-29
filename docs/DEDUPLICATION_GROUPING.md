# Result Deduplication and Grouping

## Overview

This document describes the deduplication and grouping system that prevents duplicate results and organizes them by credit with section prioritization.

## Problem Solved

Previously, search results could show the same prerequisite or credit multiple times when:
- Multiple near-identical chunks were retrieved
- Same content appeared in different sources
- Overlapping page ranges contained similar content

## Solution

### A) Near-Duplicate Removal

Two deduplication strategies:

1. **Credit + Section Deduplication**
   - Same `credit_id` + same `section` + cosine similarity > 0.97
   - Removes near-identical chunks from the same credit section

2. **Document + Page Range Deduplication**
   - Same `doc_id` + same `page_start`-`page_end` range
   - Removes exact duplicates from the same document location

### B) Grouping by Credit with Section Prioritization

Instead of returning a flat list of chunks, results are:

1. **Grouped by credit_id**
2. **Credits ranked by relevance** (highest scoring chunk)
3. **Top 2-4 credits selected**
4. **For each credit**: Top chunks selected by section priority

#### Section Priority Order

1. **requirements** (priority 10) - Most important
2. **intent** (priority 9)
3. **documentation** (priority 8)
4. **calc** (priority 7)
5. **thresholds** (priority 6)
6. **definitions** (priority 5)
7. **unknown** (priority 1) - Least important

## Implementation

### Module: `src/result_deduplication.py`

Key functions:

- `remove_near_duplicates()`: Removes duplicates based on similarity and keys
- `group_by_credit()`: Groups results by credit_id
- `rank_credits_by_relevance()`: Ranks credits by their highest chunk score
- `select_top_chunks_per_credit()`: Selects top chunks per credit by section priority
- `deduplicate_and_group()`: Main function that orchestrates the entire process

### Integration: `src/leed_rag_api.py`

The `search()` method now:
1. Retrieves more candidates (k * 3, up to 20)
2. Applies deduplication and grouping
3. Returns organized results

**Parameters:**
- `use_grouping`: Enable/disable grouping (default: True)
- `top_credits`: Number of top credits to return (default: 3, range: 2-4)

## Usage Example

### API Request

```json
{
  "query": "energy efficiency requirements",
  "limit": 5,
  "use_grouping": true,
  "top_credits": 3
}
```

### Response Structure

Results are returned grouped by credit:

```json
{
  "query": "energy efficiency requirements",
  "results_count": 5,
  "results": [
    {
      "rank": 1,
      "score": 0.89,
      "text": "EA Prerequisite: Minimum Energy Performance\n\nRequirements:...",
      "metadata": {
        "credit_id": "EA-p2",
        "credit_name": "Minimum Energy Performance",
        "section": "requirements",
        "page_start": 45,
        "page_end": 47
      }
    },
    {
      "rank": 2,
      "score": 0.87,
      "text": "EA Prerequisite: Minimum Energy Performance\n\nDocumentation:...",
      "metadata": {
        "credit_id": "EA-p2",
        "credit_name": "Minimum Energy Performance",
        "section": "documentation",
        "page_start": 48,
        "page_end": 48
      }
    },
    {
      "rank": 3,
      "score": 0.85,
      "text": "EA Credit: Optimize Energy Performance\n\nRequirements:...",
      "metadata": {
        "credit_id": "EA-c1",
        "credit_name": "Optimize Energy Performance",
        "section": "requirements",
        "page_start": 50,
        "page_end": 52
      }
    }
  ]
}
```

## Benefits

1. **No Duplicates**: Same prerequisite/credit appears only once per section
2. **Better Organization**: Results grouped by credit for easier understanding
3. **Section Prioritization**: Requirements and Intent prioritized over definitions
4. **Diverse Coverage**: Multiple sections per credit (requirements + documentation)
5. **Relevance Ranking**: Top credits by relevance, then sections by priority

## Configuration

### Adjusting Deduplication Sensitivity

```python
# More aggressive deduplication (higher threshold)
deduplicate_and_group(results, embedder, similarity_threshold=0.98)

# Less aggressive (lower threshold)
deduplicate_and_group(results, embedder, similarity_threshold=0.95)
```

### Adjusting Grouping

```python
# Return top 4 credits with 2 chunks each
deduplicate_and_group(results, embedder, top_credits=4, max_chunks_per_credit=2)

# Return top 2 credits with 3 chunks each
deduplicate_and_group(results, embedder, top_credits=2, max_chunks_per_credit=3)
```

## Performance

- Deduplication adds minimal overhead (~10-50ms for typical queries)
- Embedding computation is batched for efficiency
- Falls back gracefully if embeddings unavailable

## Future Enhancements

- Configurable section priorities per query type
- Cross-credit deduplication for related content
- Result diversity scoring
- User preference learning

