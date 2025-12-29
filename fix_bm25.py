#!/usr/bin/env python3
"""Fix and test BM25 building"""

import sys
import os
import json
import traceback

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

output = []

def log(msg):
    print(msg)
    output.append(msg)

log("=" * 60)
log("BM25 Fix and Test")
log("=" * 60)

# Test 1: Check rank-bm25
log("\n1. Testing rank-bm25 import...")
try:
    from rank_bm25 import BM25Okapi
    log("   ✓ rank-bm25 imported successfully")
except Exception as e:
    log(f"   ✗ rank-bm25 import FAILED: {e}")
    log(f"   Install with: pip install rank-bm25")
    sys.exit(1)

# Test 2: Check BM25Index
log("\n2. Testing BM25Index import...")
try:
    from bm25_index import BM25Index, BM25_AVAILABLE
    log(f"   ✓ BM25Index imported, BM25_AVAILABLE={BM25_AVAILABLE}")
except Exception as e:
    log(f"   ✗ BM25Index import FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 3: Build index with sample data
log("\n3. Testing BM25 index building...")
try:
    sample_chunks = [
        {
            'text': 'EA Prerequisite: Minimum Energy Performance',
            'metadata': {'credit_id': 'EA-p2', 'credit_code': 'EA'}
        }
    ]
    bm25 = BM25Index()
    if bm25.build_index(sample_chunks):
        log("   ✓ BM25 index built successfully")
    else:
        log("   ✗ BM25 index build returned False")
        sys.exit(1)
except Exception as e:
    log(f"   ✗ BM25 index build FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 4: Build with real data
log("\n4. Testing with real chunks...")
try:
    json_path = 'models/index_credits.json'
    if not os.path.exists(json_path):
        log(f"   ⚠ {json_path} not found, skipping")
    else:
        with open(json_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        log(f"   Loaded {len(chunks)} chunks from {json_path}")
        
        bm25 = BM25Index()
        if bm25.build_index(chunks[:10]):  # Test with 10 chunks
            log("   ✓ BM25 index built with real data")
            
            # Test save
            test_path = 'models/test_bm25'
            if bm25.save_index(test_path):
                log(f"   ✓ BM25 index saved to {test_path}.bm25")
                
                # Test load
                bm25_load = BM25Index()
                if bm25_load.load_index(test_path):
                    log(f"   ✓ BM25 index loaded successfully")
                    
                    # Test search
                    results = bm25_load.search("EA energy", k=3)
                    log(f"   ✓ BM25 search works: {len(results)} results")
                else:
                    log("   ✗ BM25 index load failed")
            else:
                log("   ✗ BM25 index save failed")
        else:
            log("   ✗ BM25 index build failed")
except Exception as e:
    log(f"   ✗ Error: {e}")
    traceback.print_exc()

log("\n" + "=" * 60)
log("Test completed!")
log("=" * 60)

# Write output to file
with open('bm25_test_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("\nOutput also written to bm25_test_output.txt")

