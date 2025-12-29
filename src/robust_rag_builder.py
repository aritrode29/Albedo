#!/usr/bin/env python3
"""
Robust RAG Corpus Builder
Builds comprehensive RAG indices from ALL extracted data:
- Processes XML/JSON extractions
- Creates intelligent chunks with metadata
- Builds multi-source FAISS indices
- Generates training/test datasets
- Creates evaluation benchmarks
"""

import os
import sys
import json
import xml.etree.ElementTree as ET
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import hashlib
import re

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ChunkGenerator:
    """Generates intelligent chunks from extracted data."""
    
    def __init__(self, min_chunk_size: int = 100, max_chunk_size: int = 1000, overlap: int = 50):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
        if not text or len(text.strip()) < self.min_chunk_size:
            return []
        
        chunks = []
        words = text.split()
        
        start = 0
        while start < len(words):
            end = min(start + self.max_chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            
            if len(chunk_text.strip()) >= self.min_chunk_size:
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = len(chunks)
                chunk_metadata['chunk_start_word'] = start
                chunk_metadata['chunk_end_word'] = end
                chunk_metadata['chunk_hash'] = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
                
                chunks.append({
                    'text': chunk_text,
                    'metadata': chunk_metadata
                })
            
            start = end - self.overlap
        
        return chunks
    
    def chunk_pdf_pages(self, extraction: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk PDF pages with page-level metadata."""
        chunks = []
        
        for page_data in extraction.get('text_content', []):
            page_text = page_data.get('text', '')
            if not page_text.strip():
                continue
            
            page_metadata = {
                'source_file': extraction.get('source_file', ''),
                'file_type': 'pdf',
                'page': page_data.get('page', 0),
                'total_chars': page_data.get('total_chars', 0),
                'has_images': any(img.get('page') == page_data.get('page') 
                                 for img in extraction.get('images', [])),
                'has_tables': any(tbl.get('page') == page_data.get('page') 
                                 for tbl in extraction.get('tables', [])),
                'has_drawings': any(drw.get('page') == page_data.get('page') 
                                   for drw in extraction.get('drawings', [])),
                'extraction_timestamp': extraction.get('extraction_timestamp', '')
            }
            
            # Add PDF metadata if available
            if 'metadata' in extraction:
                pdf_meta = extraction['metadata']
                page_metadata.update({
                    'pdf_title': pdf_meta.get('title', ''),
                    'pdf_author': pdf_meta.get('author', ''),
                    'total_pages': pdf_meta.get('page_count', 0)
                })
            
            page_chunks = self.chunk_text(page_text, page_metadata)
            chunks.extend(page_chunks)
        
        return chunks
    
    def chunk_excel_sheets(self, extraction: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk Excel sheets with structured data."""
        chunks = []
        
        for sheet in extraction.get('sheets', []):
            sheet_name = sheet.get('name', 'unknown')
            sheet_data = sheet.get('data', [])
            
            # Convert each row to a text chunk
            for row_idx, row in enumerate(sheet_data):
                row_text_parts = []
                for col, val in row.items():
                    if val and str(val).strip():
                        row_text_parts.append(f"{col}: {val}")
                
                if row_text_parts:
                    row_text = " | ".join(row_text_parts)
                    
                    row_metadata = {
                        'source_file': extraction.get('source_file', ''),
                        'file_type': 'excel',
                        'sheet_name': sheet_name,
                        'row_index': row_idx,
                        'column_count': len(row),
                        'extraction_timestamp': extraction.get('extraction_timestamp', '')
                    }
                    
                    row_chunks = self.chunk_text(row_text, row_metadata)
                    chunks.extend(row_chunks)
        
        return chunks
    
    def chunk_json_data(self, extraction: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk JSON data structures."""
        chunks = []
        json_data = extraction.get('data')
        
        if not json_data:
            return chunks
        
        def json_to_text(obj: Any, prefix: str = "") -> str:
            """Recursively convert JSON to readable text."""
            if isinstance(obj, dict):
                parts = []
                for k, v in obj.items():
                    key = f"{prefix}.{k}" if prefix else k
                    parts.append(f"{key}: {json_to_text(v, key)}")
                return " | ".join(parts)
            elif isinstance(obj, list):
                parts = []
                for i, item in enumerate(obj):
                    parts.append(json_to_text(item, f"{prefix}[{i}]"))
                return " | ".join(parts)
            else:
                return str(obj)
        
        json_text = json_to_text(json_data)
        
        json_metadata = {
            'source_file': extraction.get('source_file', ''),
            'file_type': 'json',
            'extraction_timestamp': extraction.get('extraction_timestamp', '')
        }
        
        json_chunks = self.chunk_text(json_text, json_metadata)
        chunks.extend(json_chunks)
        
        return chunks
    
    def chunk_extraction(self, extraction: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Route to appropriate chunking method."""
        file_type = extraction.get('file_type', 'unknown')
        
        if file_type == 'pdf':
            return self.chunk_pdf_pages(extraction)
        elif file_type == 'excel':
            return self.chunk_excel_sheets(extraction)
        elif file_type == 'json':
            return self.chunk_json_data(extraction)
        elif file_type == 'text':
            text_metadata = {
                'source_file': extraction.get('source_file', ''),
                'file_type': 'text',
                'extraction_timestamp': extraction.get('extraction_timestamp', '')
            }
            return self.chunk_text(extraction.get('content', ''), text_metadata)
        else:
            logger.warning(f"Unknown file type for chunking: {file_type}")
            return []


class RobustRAGBuilder:
    """Builds comprehensive RAG corpus from all extracted data."""
    
    def __init__(self, extraction_dir: str = "outputs/extracted", output_dir: str = "models"):
        self.extraction_dir = Path(extraction_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_generator = ChunkGenerator()
        
        self.sources = {
            'credits': [],
            'guide': [],
            'forms': [],
            'calculators': [],
            'projects': [],
            'research': [],
            'all': []
        }
    
    def load_extractions(self) -> List[Dict[str, Any]]:
        """Load all extraction JSON files."""
        extraction_files = list(self.extraction_dir.rglob("*_extracted_*.json"))
        logger.info(f"Found {len(extraction_files)} extraction files")
        
        all_extractions = []
        for ext_file in extraction_files:
            try:
                with open(ext_file, 'r', encoding='utf-8') as f:
                    extraction = json.load(f)
                    extraction['extraction_file'] = str(ext_file)
                    all_extractions.append(extraction)
            except Exception as e:
                logger.warning(f"Failed to load {ext_file}: {e}")
        
        return all_extractions
    
    def categorize_extraction(self, extraction: Dict[str, Any]) -> str:
        """Categorize extraction by source type."""
        source_file = extraction.get('source_file', '').lower()
        
        if 'leed' in source_file and ('guide' in source_file or 'rating' in source_file):
            return 'guide'
        elif 'form' in source_file or 'sample' in source_file:
            return 'forms'
        elif 'calculator' in source_file or 'calc' in source_file:
            return 'calculators'
        elif 'project' in source_file or 'sea' in source_file:
            return 'projects'
        elif 'research' in source_file or 'proposal' in source_file:
            return 'research'
        elif 'credit' in source_file or 'leed' in source_file:
            return 'credits'
        else:
            return 'credits'  # Default
    
    def build_corpus(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build corpus from all extractions."""
        logger.info("Building RAG corpus from extractions...")
        
        extractions = self.load_extractions()
        logger.info(f"Loaded {len(extractions)} extractions")
        
        for extraction in extractions:
            category = self.categorize_extraction(extraction)
            chunks = self.chunk_generator.chunk_extraction(extraction)
            
            logger.info(f"Generated {len(chunks)} chunks from {extraction.get('source_file', 'unknown')} -> {category}")
            
            self.sources[category].extend(chunks)
            self.sources['all'].extend(chunks)
        
        # Log statistics
        logger.info("\n" + "="*60)
        logger.info("CORPUS STATISTICS")
        logger.info("="*60)
        for source, chunks in self.sources.items():
            logger.info(f"{source:15s}: {len(chunks):6d} chunks")
        logger.info("="*60)
        
        return self.sources
    
    def build_faiss_index(self, chunks: List[Dict[str, Any]], embedder: SentenceTransformer, 
                         out_prefix: str) -> Tuple[bool, int, int]:
        """Build FAISS index from chunks."""
        if not chunks:
            return False, 0, 0
        
        logger.info(f"Building FAISS index for {len(chunks)} chunks...")
        
        texts = [c['text'] for c in chunks]
        embeddings = embedder.encode(texts, convert_to_tensor=False, show_progress_bar=True)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        vecs = np.asarray(embeddings, dtype='float32')
        
        index = faiss.IndexFlatIP(vecs.shape[1])
        index.add(vecs)
        
        # Save index and metadata
        faiss.write_index(index, f"{out_prefix}.faiss")
        with open(f"{out_prefix}.json", 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Saved {out_prefix}.faiss ({vecs.shape[0]} vectors, dim={vecs.shape[1]})")
        return True, vecs.shape[0], vecs.shape[1]
    
    def build_all_indices(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """Build all FAISS indices."""
        logger.info(f"Loading embedding model: {embedding_model}")
        embedder = SentenceTransformer(embedding_model)
        
        # Build corpus first
        sources = self.build_corpus()
        
        # Build indices for each source
        index_specs = [
            ('credits', 'models/index_credits'),
            ('guide', 'models/index_guide'),
            ('forms', 'models/index_forms'),
            ('calculators', 'models/index_calculators'),
            ('projects', 'models/index_projects'),
            ('research', 'models/index_research'),
            ('all', 'models/index_all')
        ]
        
        for source_key, out_prefix in index_specs:
            chunks = sources.get(source_key, [])
            if chunks:
                success, nvecs, dim = self.build_faiss_index(chunks, embedder, out_prefix)
                if success:
                    logger.info(f"✓ {source_key} index: {nvecs} vectors")
            else:
                logger.warning(f"No chunks for {source_key}, skipping index")
        
        logger.info("\n🎉 All RAG indices built successfully!")


def main():
    """Main RAG builder."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Robust RAG Corpus Builder')
    parser.add_argument('--extraction-dir', type=str, default='outputs/extracted',
                       help='Directory containing extraction JSON files')
    parser.add_argument('--output-dir', type=str, default='models',
                       help='Output directory for indices')
    parser.add_argument('--embedding-model', type=str, default='all-MiniLM-L6-v2',
                       help='Sentence transformer model name')
    
    args = parser.parse_args()
    
    builder = RobustRAGBuilder(extraction_dir=args.extraction_dir, output_dir=args.output_dir)
    builder.build_all_indices(embedding_model=args.embedding_model)


if __name__ == '__main__':
    main()





