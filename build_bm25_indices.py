#!/usr/bin/env python3
"""Standalone script to build BM25 indices"""

import sys
import os
import json
import logging

# Setup logging to console
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

print("=" * 60)
print("Building BM25 Indices")
print("=" * 60)

# Check rank-bm25
print("\n1. Checking rank-bm25...")
try:
    from rank_bm25 import BM25Okapi
    print("   ✓ rank-bm25 is installed")
except ImportError as e:
    print(f"   ✗ rank-bm25 NOT installed: {e}")
    print("   Run: pip install rank-bm25")
    sys.exit(1)

# Import BM25Index
print("\n2. Importing BM25Index...")
try:
    from bm25_index import BM25Index, BM25_AVAILABLE
    print(f"   ✓ BM25Index imported, BM25_AVAILABLE={BM25_AVAILABLE}")
    if not BM25_AVAILABLE:
        print("   ✗ BM25_AVAILABLE is False!")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Build indices for each source
print("\n3. Building BM25 indices...")
models_dir = 'models'
if not os.path.exists(models_dir):
    print(f"   ✗ {models_dir} directory not found")
    sys.exit(1)

index_specs = [
    ('credits', 'index_credits'),
    ('guide', 'index_guide'),
    ('forms', 'index_forms'),
    ('all', 'index_all')
]

for source_name, index_prefix in index_specs:
    json_path = os.path.join(models_dir, f"{index_prefix}.json")
    bm25_path = os.path.join(models_dir, index_prefix)
    
    if not os.path.exists(json_path):
        print(f"   ⚠ Skipping {source_name}: {json_path} not found")
        continue
    
    print(f"\n   Building {source_name} index...")
    try:
        # Load chunks
        with open(json_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"      Loaded {len(chunks)} chunks")
        
        # Build BM25 index
        bm25 = BM25Index()
        if bm25.build_index(chunks):
            print(f"      ✓ Index built")
            
            # Save index
            if bm25.save_index(bm25_path):
                bm25_file = f"{bm25_path}.bm25"
                if os.path.exists(bm25_file):
                    file_size = os.path.getsize(bm25_file)
                    print(f"      ✓ Saved to {bm25_file} ({file_size:,} bytes)")
                else:
                    print(f"      ✗ File not created: {bm25_file}")
            else:
                print(f"      ✗ Save failed")
        else:
            print(f"      ✗ Build failed")
    except Exception as e:
        print(f"      ✗ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("BM25 index building completed!")
print("=" * 60)

# List created files
print("\nCreated BM25 files:")
bm25_files = [f for f in os.listdir(models_dir) if f.endswith('.bm25')]
if bm25_files:
    for f in bm25_files:
        size = os.path.getsize(os.path.join(models_dir, f))
        print(f"  - {f} ({size:,} bytes)")
else:
    print("  (none)")

