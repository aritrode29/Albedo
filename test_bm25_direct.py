#!/usr/bin/env python3
"""Direct test of BM25 building"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Step 1: Testing rank-bm25 import...")
try:
    from rank_bm25 import BM25Okapi
    print("✓ rank-bm25 imported")
except Exception as e:
    print(f"✗ rank-bm25 import failed: {e}")
    sys.exit(1)

print("\nStep 2: Testing BM25Index import...")
try:
    from bm25_index import BM25Index
    print("✓ BM25Index imported")
except Exception as e:
    print(f"✗ BM25Index import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 3: Testing with sample data...")
try:
    # Create sample chunks
    sample_chunks = [
        {
            'text': 'EA Prerequisite: Minimum Energy Performance. Requirements: Comply with ASHRAE 90.1',
            'metadata': {'credit_id': 'EA-p2', 'credit_code': 'EA', 'section': 'requirements'}
        },
        {
            'text': 'EA Credit: Optimize Energy Performance. Points available based on performance.',
            'metadata': {'credit_id': 'EA-c1', 'credit_code': 'EA', 'section': 'requirements'}
        }
    ]
    
    bm25 = BM25Index()
    if bm25.build_index(sample_chunks):
        print("✓ BM25 index built")
        
        results = bm25.search("EA energy performance", k=2)
        print(f"✓ BM25 search works: {len(results)} results")
        for r in results:
            print(f"  - Score: {r['score']:.2f}, Text: {r['text'][:50]}...")
    else:
        print("✗ BM25 index build failed")
        sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 4: Testing with real data...")
try:
    if os.path.exists('models/index_credits.json'):
        with open('models/index_credits.json', 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"Loaded {len(chunks)} chunks")
        
        bm25 = BM25Index()
        if bm25.build_index(chunks[:100]):  # Test with first 100
            print("✓ BM25 index built with real data")
            if bm25.save_index('models/test_bm25'):
                print("✓ BM25 index saved")
            else:
                print("✗ BM25 index save failed")
        else:
            print("✗ BM25 index build failed")
    else:
        print("⚠ index_credits.json not found, skipping real data test")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n✓ All tests completed!")

