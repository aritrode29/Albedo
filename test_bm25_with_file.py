import sys, os
sys.path.insert(0, 'src')

with open('test_output.txt', 'w') as f:
    f.write("Starting BM25 test...\n")
    f.flush()
    
    try:
        f.write("Importing rank_bm25...\n")
        f.flush()
        from rank_bm25 import BM25Okapi
        f.write("OK: rank_bm25 imported\n")
        f.flush()
    except Exception as e:
        f.write(f"FAILED: {e}\n")
        f.flush()
        sys.exit(1)
    
    try:
        f.write("Importing BM25Index...\n")
        f.flush()
        from bm25_index import BM25Index, BM25_AVAILABLE
        f.write(f"OK: BM25Index imported, BM25_AVAILABLE={BM25_AVAILABLE}\n")
        f.flush()
    except Exception as e:
        f.write(f"FAILED: {e}\n")
        f.flush()
        import traceback
        f.write(traceback.format_exc())
        f.flush()
        sys.exit(1)
    
    if not BM25_AVAILABLE:
        f.write("ERROR: BM25_AVAILABLE is False!\n")
        f.flush()
        sys.exit(1)
    
    try:
        f.write("Building index...\n")
        f.flush()
        chunks = [{'text': 'EA energy performance', 'metadata': {'credit_id': 'EA-p2'}}]
        bm25 = BM25Index()
        result = bm25.build_index(chunks)
        f.write(f"Build result: {result}, loaded: {bm25.loaded}\n")
        f.flush()
        
        if result:
            f.write("Saving index...\n")
            f.flush()
            save_result = bm25.save_index('models/test_bm25')
            f.write(f"Save result: {save_result}\n")
            f.flush()
            
            exists = os.path.exists('models/test_bm25.bm25')
            f.write(f"File exists: {exists}\n")
            f.flush()
            
            if exists:
                size = os.path.getsize('models/test_bm25.bm25')
                f.write(f"File size: {size} bytes\n")
                f.flush()
    except Exception as e:
        f.write(f"ERROR: {e}\n")
        f.flush()
        import traceback
        f.write(traceback.format_exc())
        f.flush()
    
    f.write("Test completed!\n")
    f.flush()

print("Output written to test_output.txt")

