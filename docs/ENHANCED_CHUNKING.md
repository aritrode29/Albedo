# Enhanced LEED Chunking with Structured Metadata

## Overview

This document describes the enhanced chunking system that implements heading-based splitting and structured metadata for robust FAISS-over-LEED-chunks retrieval.

## Key Improvements

### 1. Heading-Based Chunking

Instead of creating loose paragraph chunks, the system now splits content by headings/sections:
- **Requirements** → separate chunk
- **Documentation** → separate chunk  
- **Intent** → separate chunk
- **Calculations** → separate chunk
- **Thresholds** → separate chunk
- **Definitions** → separate chunk

This prevents "random informative notes" from dominating search results by keeping semantically related content together.

### 2. Structured Metadata

Each chunk now carries comprehensive metadata:

#### Required Fields
- `doc_type`: `credit` | `prerequisite` | `form` | `guide` | `faq` | `addenda`
- `credit_id`: Stable identifier like `EA-p2`, `EA-c1`, `WE-c3`
- `credit_name`: Full name of the credit/prerequisite
- `credit_code`: Short code (e.g., `EA`, `WE`, `SS`)
- `section`: `intent` | `requirements` | `calc` | `documentation` | `thresholds` | `definitions`
- `chunk_id`: Stable unique identifier (e.g., `EA-p2-requirements-0`)
- `page_start`, `page_end`: Page range for the chunk

#### Optional Fields
- `version`: LEED version (e.g., `v4.1`)
- `version_effective_date`: When the version became effective
- `rating_system`: `BD+C`, `ID+C`, `O+M`, `ND`, etc.
- `project_types`: List like `['NC', 'CS', 'Schools']`
- `category`: Credit category (e.g., `ENERGY AND ATMOSPHERE (EA)`)
- `points_min`, `points_max`: Point values if applicable

## Implementation

### Core Module: `src/enhanced_chunking.py`

The main function is `to_enhanced_rag_chunks()` which:
1. Takes a list of credit records (CreditRecord objects or dicts)
2. Generates stable `credit_id` values (e.g., `EA-p2`)
3. Splits each credit into section-based chunks
4. Adds comprehensive metadata to each chunk
5. Returns a list of chunk dictionaries

### Integration Points

#### 1. `src/archive/extract_leed_credits_advanced.py`
- Updated `to_rag_chunks()` to use enhanced chunking
- Falls back to basic chunking if enhanced module unavailable

#### 2. `src/build_rag_corpus.py`
- Updated `build_chunks_from_credits_json()` to use enhanced chunking
- Automatically applies to all credit JSON files

#### 3. `src/robust_rag_builder.py`
- Added `chunk_by_headings()` method to `ChunkGenerator`
- Updated `chunk_pdf_pages()` to support heading-based chunking

## Credit ID Generation

The system generates stable credit IDs using this pattern:
- **Prerequisites**: `{code}-p{number}` (e.g., `EA-p2`)
- **Credits**: `{code}-c{number}` (e.g., `EA-c1`)

The number is extracted from:
1. Credit name (e.g., "EA Credit 2" → "2")
2. Credit code if it contains a number
3. Hash-based fallback for uniqueness

## Section Mapping

Sections are standardized to these values:
- `intent`: Intent statements
- `requirements`: Requirements and options
- `documentation`: Documentation/submittals
- `calc`: Calculations, equations, step-by-step
- `thresholds`: Points, applicability criteria
- `definitions`: Related credits, exemplary performance, referenced standards, guidance

## Usage Example

```python
from enhanced_chunking import to_enhanced_rag_chunks

# Load credits (CreditRecord objects or dicts)
credits = load_credits_from_json("leed_credits.json")

# Generate enhanced chunks
chunks = to_enhanced_rag_chunks(credits)

# Each chunk has:
# - text: The section content
# - metadata: All structured fields
for chunk in chunks:
    print(f"Credit: {chunk['metadata']['credit_id']}")
    print(f"Section: {chunk['metadata']['section']}")
    print(f"Pages: {chunk['metadata']['page_start']}-{chunk['metadata']['page_end']}")
```

## Benefits

1. **Better Retrieval**: Section-based chunks ensure queries match the right content type
2. **Stable IDs**: `credit_id` and `chunk_id` enable consistent referencing
3. **Rich Filtering**: Metadata fields allow filtering by rating system, project type, etc.
4. **Page Tracking**: `page_start` and `page_end` enable citation to source pages
5. **Version Control**: `version_effective_date` supports version-aware queries

## Migration

Existing chunking code will automatically use enhanced chunking when available. The system includes fallback mechanisms to ensure compatibility with existing workflows.

