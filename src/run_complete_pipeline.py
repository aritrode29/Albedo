#!/usr/bin/env python3
"""
Complete Pipeline Runner (FAST VERSION)
Runs extraction -> training -> RAG build efficiently.

Usage:
    python src/run_complete_pipeline.py
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_step(step_name: str, command: list):
    """Run a pipeline step with live output."""
    print(f"\n{'='*50}")
    print(f"STEP: {step_name}")
    print(f"{'='*50}")
    
    try:
        # Run with live output instead of capturing
        result = subprocess.run(command, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Step failed: {e}")
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fast Pipeline Runner')
    parser.add_argument('--data-dir', type=str, default='data', help='Data directory')
    parser.add_argument('--skip-extraction', action='store_true', help='Skip extraction')
    parser.add_argument('--skip-training', action='store_true', help='Skip training data')
    parser.add_argument('--skip-rag', action='store_true', help='Skip RAG building')
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        sys.exit(1)
    
    # Check if extractions already exist
    extracted_dir = Path('outputs/extracted')
    has_extractions = extracted_dir.exists() and any(extracted_dir.rglob("*.json"))
    
    # Step 1: Extract (skip if already done)
    if not args.skip_extraction and not has_extractions:
        run_step("1. Data Extraction", 
                [sys.executable, 'src/robust_extraction_pipeline.py', str(data_dir)])
    elif has_extractions:
        print("\n[SKIP] Extraction - using existing data in outputs/extracted/")
    
    # Step 2: Training data (optional)
    if not args.skip_training:
        run_step("2. Training Data Generation",
                [sys.executable, 'src/robust_training_pipeline.py'])
    
    # Step 3: Build RAG
    if not args.skip_rag:
        run_step("3. RAG Index Building",
                [sys.executable, 'src/robust_rag_builder.py'])
    
    print("\n" + "="*50)
    print("PIPELINE COMPLETE!")
    print("="*50)
    print("\nNext steps:")
    print("  python src/rag_demo.py        # Test RAG")
    print("  python src/leed_rag_api.py    # Start API")


if __name__ == '__main__':
    main()

