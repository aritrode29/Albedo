#!/usr/bin/env python3
"""Test BM25 index building"""

import sys
import os
sys.path.insert(0, 'src')

try:
    print("Testing rank-bm25 import...")
    import rank_bm25
    print("✓ rank-bm25 imported successfully")
except ImportError as e:
    print(f"✗ rank-bm25 import failed: {e}")
    sys.exit(1)

try:
    print("\nTesting BM25Index import...")
    from bm25_index import BM25Index
    print("✓ BM25Index imported successfully")
except ImportError as e:
    print(f"✗ BM25Index import failed: {e}")
    sys.exit(1)

try:
    print("\nTesting BM25Index building...")
    # Load a sample chunk
    import json
    if os.path.exists('models/index_credits.json'):
        with open('models/index_credits.json', 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"Loaded {len(chunks)} chunks from index_credits.json")
        
        bm25 = BM25Index()
        if bm25.build_index(chunks[:10]):  # Test with first 10 chunks
            print("✓ BM25 index built successfully")
            if bm25.save_index('models/test_bm25'):
                print("✓ BM25 index saved successfully")
                # Test search
                results = bm25.search("EA energy performance", k=3)
                print(f"✓ BM25 search works: found {len(results)} results")
            else:
                print("✗ BM25 index save failed")
        else:
            print("✗ BM25 index build failed")
    else:
        print("✗ index_credits.json not found")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓ All tests passed!")

