#!/usr/bin/env python3
"""
BM25 Lexical Search Index
Provides keyword-based retrieval for LEED documents.
"""

import json
import os
import pickle
from typing import List, Dict, Any, Optional
import logging

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError as e:
    BM25_AVAILABLE = False
    # Don't warn here - let callers check BM25_AVAILABLE

logger = logging.getLogger(__name__)


class BM25Index:
    """BM25 lexical search index for LEED chunks."""
    
    def __init__(self):
        self.bm25 = None
        self.chunks = []
        self.tokenized_corpus = []
        self.loaded = False
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25 indexing."""
        if not text:
            return []
        
        # Simple tokenization: lowercase, split on whitespace and punctuation
        import re
        # Remove special characters but keep alphanumeric, hyphens, and spaces
        text = re.sub(r'[^\w\s-]', ' ', text.lower())
        tokens = text.split()
        
        # Filter out very short tokens (less than 2 chars) except for credit codes
        filtered = []
        for token in tokens:
            if len(token) >= 2 or token.upper() in ['EA', 'WE', 'MR', 'EQ', 'SS', 'LT', 'IN', 'RP', 'IP', 'NC', 'CS', 'BD', 'ID', 'OM', 'ND']:
                filtered.append(token)
        
        return filtered
    
    def build_index(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        Build BM25 index from chunks.
        
        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata'
        
        Returns:
            True if successful, False otherwise
        """
        if not BM25_AVAILABLE:
            logger.error("rank-bm25 not available. Cannot build BM25 index.")
            return False
        
        if not chunks:
            logger.warning("No chunks provided for BM25 indexing")
            return False
        
        try:
            self.chunks = chunks
            self.tokenized_corpus = []
            
            # Tokenize all chunk texts
            for chunk in chunks:
                text = chunk.get('text', '')
                # Enhance text with metadata for better keyword matching
                metadata = chunk.get('metadata', {})
                
                # Add credit code, credit name, section to text for better matching
                enhanced_text = text
                if metadata.get('credit_code'):
                    enhanced_text = f"{metadata['credit_code']} {enhanced_text}"
                if metadata.get('credit_name'):
                    enhanced_text = f"{metadata['credit_name']} {enhanced_text}"
                if metadata.get('section'):
                    enhanced_text = f"{metadata['section']} {enhanced_text}"
                if metadata.get('credit_id'):
                    enhanced_text = f"{metadata['credit_id']} {enhanced_text}"
                
                tokens = self._tokenize(enhanced_text)
                self.tokenized_corpus.append(tokens)
            
            # Build BM25 index
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            self.loaded = True
            
            logger.info(f"Built BM25 index with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error building BM25 index: {e}")
            return False
    
    def search(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        Search BM25 index.
        
        Args:
            query: Search query string
            k: Number of results to return
        
        Returns:
            List of result dictionaries with 'text', 'metadata', 'score', 'rank'
        """
        if not self.loaded or not self.bm25:
            logger.warning("BM25 index not loaded")
            return []
        
        if not query or not query.strip():
            return []
        
        try:
            # Tokenize query
            query_tokens = self._tokenize(query)
            
            if not query_tokens:
                return []
            
            # Get BM25 scores
            scores = self.bm25.get_scores(query_tokens)
            
            # Get top-k results
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
            
            # Build results
            results = []
            for rank, idx in enumerate(top_indices, start=1):
                if scores[idx] > 0:  # Only include results with positive scores
                    chunk = self.chunks[idx]
                    result = {
                        'rank': rank,
                        'score': float(scores[idx]),
                        'text': chunk.get('text', ''),
                        'metadata': chunk.get('metadata', {}).copy(),
                        '_retrieval_method': 'bm25'  # Mark as BM25 result
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching BM25 index: {e}")
            return []
    
    def save_index(self, index_path: str) -> bool:
        """Save BM25 index to disk."""
        if not self.loaded or not self.bm25:
            logger.warning("BM25 index not loaded, cannot save")
            return False
        
        if not self.chunks or not self.tokenized_corpus:
            logger.warning("No chunks or tokenized corpus to save")
            return False
        
        try:
            # Save chunks and tokenized corpus (BM25Okapi will be rebuilt on load)
            data = {
                'chunks': self.chunks,
                'tokenized_corpus': self.tokenized_corpus
            }
            
            bm25_file = f"{index_path}.bm25"
            with open(bm25_file, 'wb') as f:
                pickle.dump(data, f)
            
            # Verify file was created
            if os.path.exists(bm25_file):
                file_size = os.path.getsize(bm25_file)
                logger.info(f"Saved BM25 index to {bm25_file} ({file_size:,} bytes)")
                return True
            else:
                logger.error(f"BM25 index file was not created: {bm25_file}")
                return False
            
        except Exception as e:
            logger.error(f"Error saving BM25 index: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def load_index(self, index_path: str) -> bool:
        """Load BM25 index from disk."""
        if not BM25_AVAILABLE:
            logger.error("rank-bm25 not available. Cannot load BM25 index.")
            return False
        
        try:
            bm25_path = f"{index_path}.bm25"
            if not os.path.exists(bm25_path):
                logger.warning(f"BM25 index file not found: {bm25_path}")
                return False
            
            with open(bm25_path, 'rb') as f:
                data = pickle.load(f)
            
            self.chunks = data['chunks']
            self.tokenized_corpus = data['tokenized_corpus']
            
            # Rebuild BM25 index
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            self.loaded = True
            
            logger.info(f"Loaded BM25 index from {bm25_path} with {len(self.chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Error loading BM25 index: {e}")
            return False

