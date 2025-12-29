import sys, os
sys.path.insert(0, 'src')

print("Test 1: Import rank_bm25")
try:
    from rank_bm25 import BM25Okapi
    print("OK")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)

print("Test 2: Import BM25Index")
try:
    from bm25_index import BM25Index, BM25_AVAILABLE
    print(f"OK, BM25_AVAILABLE={BM25_AVAILABLE}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Test 3: Build index")
try:
    chunks = [{'text': 'test', 'metadata': {}}]
    bm25 = BM25Index()
    result = bm25.build_index(chunks)
    print(f"OK, result={result}, loaded={bm25.loaded}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Test 4: Save index")
try:
    result = bm25.save_index('models/test_bm25')
    exists = os.path.exists('models/test_bm25.bm25')
    print(f"OK, save_result={result}, file_exists={exists}")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("ALL TESTS PASSED")

