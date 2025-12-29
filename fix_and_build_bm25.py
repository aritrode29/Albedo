#!/usr/bin/env python3
"""Direct script to fix and build BM25 indices"""

import sys
import os
import json
import traceback

# Setup
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

models_dir = 'models'
os.makedirs(models_dir, exist_ok=True)

print("=" * 70)
print("BM25 Index Builder - Direct Fix")
print("=" * 70)

# Step 1: Verify rank-bm25
print("\n[1/4] Checking rank-bm25 installation...")
try:
    from rank_bm25 import BM25Okapi
    print("   ✓ rank-bm25 is installed")
except ImportError as e:
    print(f"   ✗ rank-bm25 NOT installed: {e}")
    print("   Installing rank-bm25...")
    import subprocess
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'rank-bm25'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("   ✓ rank-bm25 installed successfully")
        from rank_bm25 import BM25Okapi
    else:
        print(f"   ✗ Installation failed: {result.stderr}")
        sys.exit(1)

# Step 2: Import BM25Index
print("\n[2/4] Importing BM25Index...")
try:
    from bm25_index import BM25Index
    print("   ✓ BM25Index imported")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 3: Build indices
print("\n[3/4] Building BM25 indices...")
index_specs = [
    ('credits', 'index_credits'),
    ('guide', 'index_guide'),
    ('forms', 'index_forms'),
    ('all', 'index_all')
]

success_count = 0
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
        if not bm25.build_index(chunks):
            print(f"      ✗ Build returned False")
            continue
        
        print(f"      ✓ Index built (loaded={bm25.loaded})")
        
        # Save index
        if not bm25.save_index(bm25_path):
            print(f"      ✗ Save returned False")
            continue
        
        # Verify file
        bm25_file = f"{bm25_path}.bm25"
        if os.path.exists(bm25_file):
            file_size = os.path.getsize(bm25_file)
            print(f"      ✓ Saved: {bm25_file} ({file_size:,} bytes)")
            success_count += 1
        else:
            print(f"      ✗ File not created: {bm25_file}")
            
    except Exception as e:
        print(f"      ✗ Error: {e}")
        traceback.print_exc()

# Step 4: Verify
print(f"\n[4/4] Verification...")
bm25_files = [f for f in os.listdir(models_dir) if f.endswith('.bm25')]
if bm25_files:
    print(f"   ✓ Found {len(bm25_files)} BM25 index files:")
    for f in sorted(bm25_files):
        size = os.path.getsize(os.path.join(models_dir, f))
        print(f"      - {f} ({size:,} bytes)")
else:
    print("   ✗ No BM25 files found")

print("\n" + "=" * 70)
print(f"Completed: {success_count}/{len([s for s in index_specs if os.path.exists(os.path.join(models_dir, f'{s[1]}.json'))])} indices built")
print("=" * 70)

