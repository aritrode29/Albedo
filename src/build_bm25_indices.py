#!/usr/bin/env python3
"""
Build BM25 indices for all RAG sources
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bm25_index import BM25Index

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def build_bm25_indices():
    """Build BM25 indices for all sources"""

    # Define sources and their paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    models_dir = os.path.join(project_root, "models")

    sources = {
        'credits': os.path.join(models_dir, 'index_credits'),
        'guide': os.path.join(models_dir, 'index_guide'),
        'forms': os.path.join(models_dir, 'index_forms'),
        'all': os.path.join(models_dir, 'index_all')
    }

    for source_name, index_path in sources.items():
        logger.info(f"Building BM25 index for {source_name}...")

        # Load chunks from JSON file
        json_file = f"{index_path}.json"
        if not os.path.exists(json_file):
            logger.warning(f"JSON file not found: {json_file}")
            continue

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)

            if not chunks:
                logger.warning(f"No chunks found in {json_file}")
                continue

            # Build BM25 index
            bm25 = BM25Index()
            if bm25.build_index(chunks):
                # Save BM25 index
                if bm25.save_index(index_path):
                    logger.info(f"✓ Successfully built and saved BM25 index for {source_name}")
                else:
                    logger.error(f"✗ Failed to save BM25 index for {source_name}")
            else:
                logger.error(f"✗ Failed to build BM25 index for {source_name}")

        except Exception as e:
            logger.error(f"Error processing {source_name}: {e}")
            import traceback
            logger.debug(traceback.format_exc())

if __name__ == "__main__":
    build_bm25_indices()