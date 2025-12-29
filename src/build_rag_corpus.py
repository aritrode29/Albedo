#!/usr/bin/env python3
"""
Build Unified RAG Corpus + Multi-Index FAISS
Aggregates extracted sources (credits, guide, forms/calculators), normalizes metadata,
creates per-source indices and a combined index.
"""

import os
import sys
import json
import glob
import logging
from typing import List, Dict, Any, Optional, Tuple

# Third-party
try:
	import numpy as np
	from sentence_transformers import SentenceTransformer
	import faiss
except Exception as e:
	print("Missing dependencies. Install with: pip install sentence-transformers faiss-cpu numpy")
	raise

# Local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
	from llm_rag import KnowledgeBaseBuilder
except Exception:
	KnowledgeBaseBuilder = None

logger = logging.getLogger(__name__)

# -------------------------
# Helpers
# -------------------------

def setup_logging() -> None:
	logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def read_lines_jsonl(path: str) -> List[Dict[str, Any]]:
	items: List[Dict[str, Any]] = []
	with open(path, 'r', encoding='utf-8') as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			try:
				items.append(json.loads(line))
			except json.JSONDecodeError:
				logger.warning(f"Skipping invalid JSONL line in {path}")
	return items


def normalize_chunk(text: str, metadata: Dict[str, Any], source: str, doc_label: Optional[str] = None) -> Dict[str, Any]:
	md = dict(metadata or {})
	md.setdefault('source', source)
	if doc_label:
		md.setdefault('doc', doc_label)
	# Normalize common fields
	md['type'] = md.get('type') or md.get('credit_type') or md.get('CreditType')
	md['credit_code'] = md.get('credit_code') or md.get('CreditCode') or md.get('category')
	md['credit_name'] = md.get('credit_name') or md.get('CreditName')
	md['points_min'] = md.get('points_min')
	md['points_max'] = md.get('points_max')
	md['version'] = md.get('version', 'v4.1')
	if isinstance(md.get('pages'), list) is False and md.get('pages') is not None:
		md['pages'] = [md['pages']]
	return { 'text': text, 'metadata': md }


def build_chunks_from_credits_json(path: str) -> List[Dict[str, Any]]:
	"""Use KnowledgeBaseBuilder formatting if available; otherwise basic fallback."""
	chunks: List[Dict[str, Any]] = []
	try:
		with open(path, 'r', encoding='utf-8') as f:
			credits = json.load(f)
	except Exception as e:
		logger.warning(f"Failed to read credits JSON {path}: {e}")
		return chunks
	
	if KnowledgeBaseBuilder is not None:
		builder = KnowledgeBaseBuilder()
		# Recreate text formatting from credits
		for credit in credits:
			try:
				text = builder._format_credit_text(credit)  # type: ignore[attr-defined]
			except Exception:
				# Fallback simple formatting
				header = f"{credit.get('credit_code','Unknown')} {credit.get('credit_type','Credit')}: {credit.get('credit_name','Unknown')}"
				req = credit.get('requirements', []) or []
				text = header + "\n" + "\n".join([f"- {r}" for r in req])
			metadata = {
				'credit_code': credit.get('credit_code'),
				'credit_name': credit.get('credit_name'),
				'category': credit.get('category'),
				'credit_type': credit.get('credit_type'),
				'points_min': credit.get('points_min'),
				'points_max': credit.get('points_max'),
				'version': credit.get('version', 'v4.1'),
				'pages': (credit.get('sources') or {}).get('pages', [])
			}
			chunks.append(normalize_chunk(text, metadata, source='credits', doc_label=os.path.basename(path)))
	return chunks


def build_chunks_from_jsonl(path: str, source: str) -> List[Dict[str, Any]]:
	items = read_lines_jsonl(path)
	chunks: List[Dict[str, Any]] = []
	for it in items:
		text = it.get('text') or ''
		metadata = it.get('metadata') or {}
		chunks.append(normalize_chunk(text, metadata, source=source, doc_label=os.path.basename(path)))
	return chunks


def build_corpus() -> Dict[str, List[Dict[str, Any]]]:
	"""Aggregate available sources into per-source chunk lists."""
	sources: Dict[str, List[Dict[str, Any]]] = {
		'credits': [],
		'guide': [],
		'forms': [],
		'all': []
	}

	# Candidate files
	candidate_credits_json = [
		"data/raw/leed_credits.json",
		"outputs/leed_credits.json",
		"outputs/leed_guide_credits.json",
		"outputs/leed_checklist_credits.json"
	]
	candidate_credits_chunks = [
		"data/raw/rag_chunks.jsonl",
		"outputs/leed_rag_chunks.jsonl",
		"outputs/leed_rag_chunks_improved.jsonl",
		"outputs/leed_guide_rag_chunks.jsonl",
		"outputs/leed_checklist_rag_chunks.jsonl"
	]
	candidate_guide_chunks = [
		"outputs/leed_guide_rag_chunks.jsonl"
	]
	candidate_forms_chunks = [
		"outputs/sample_forms_chunks.jsonl",
		"outputs/sample_forms.jsonl"
	]

	# Credit mapping and miscellaneous json/jsonl under outputs/credit_mapping/**
	for path in glob.glob("outputs/credit_mapping/**/*", recursive=True):
		if path.lower().endswith('.jsonl') and os.path.isfile(path):
			logger.info(f"Adding credit mapping chunks from {path}")
			sources['credits'].extend(build_chunks_from_jsonl(path, source='credits'))
		elif path.lower().endswith('.json') and os.path.isfile(path):
			logger.info(f"Adding credit mapping credits from {path}")
			sources['credits'].extend(build_chunks_from_credits_json(path))
	# Collect credits
	for path in candidate_credits_json:
		if os.path.exists(path):
			logger.info(f"Adding credits from {path}")
			sources['credits'].extend(build_chunks_from_credits_json(path))
	for path in candidate_credits_chunks:
		if os.path.exists(path):
			logger.info(f"Adding credit chunks from {path}")
			sources['credits'].extend(build_chunks_from_jsonl(path, source='credits'))

	# Advanced extraction outputs
	for path in glob.glob("outputs/advanced_extraction/*_rag_chunks_*.jsonl"):
		logger.info(f"Adding advanced extraction chunks from {path}")
		sources['credits'].extend(build_chunks_from_jsonl(path, source='credits'))
	
	# SEA project comprehensive data
	for path in glob.glob("outputs/projects/SEA/sea_comprehensive_rag_chunks_*.jsonl"):
		logger.info(f"Adding SEA project chunks from {path}")
		sources['credits'].extend(build_chunks_from_jsonl(path, source='credits'))

	# Guide
	for path in candidate_guide_chunks:
		if os.path.exists(path):
			logger.info(f"Adding guide chunks from {path}")
			sources['guide'].extend(build_chunks_from_jsonl(path, source='guide'))

	# Forms / calculators (treat both as 'forms' source for retrieval routing)
	for path in candidate_forms_chunks:
		if os.path.exists(path):
			logger.info(f"Adding forms chunks from {path}")
			sources['forms'].extend(build_chunks_from_jsonl(path, source='forms'))
	# Calculator training data *.jsonl
	for path in glob.glob("outputs/calculator_training_data*.jsonl"):
		logger.info(f"Adding calculator training data from {path}")
		sources['forms'].extend(build_chunks_from_jsonl(path, source='forms'))

	# Calculator metadata (convert entries to chunks)
	calc_meta = "outputs/calculator_metadata.json"
	if os.path.exists(calc_meta):
		try:
			with open(calc_meta, 'r', encoding='utf-8') as f:
				data = json.load(f)
			if isinstance(data, list):
				for item in data:
					text = json.dumps(item, ensure_ascii=False)
					meta = {'source': 'calculators', 'credit_code': item.get('credit_code'), 'credit_name': item.get('credit_name')}
					sources['forms'].append({'text': text, 'metadata': meta})
			else:
				# if dict, store as single chunk
				text = json.dumps(data, ensure_ascii=False)
				meta = {'source': 'calculators'}
				sources['forms'].append({'text': text, 'metadata': meta})
		except Exception as e:
			logger.warning(f"Skipping calculator_metadata.json due to error: {e}")

	# Merge all
	sources['all'] = sources['credits'] + sources['guide'] + sources['forms']
	logger.info(
		f"Corpus sizes -> credits: {len(sources['credits'])}, guide: {len(sources['guide'])}, forms: {len(sources['forms'])}, all: {len(sources['all'])}"
	)
	return sources


def build_faiss_index(chunks: List[Dict[str, Any]], embedder: SentenceTransformer, out_prefix: str) -> Tuple[bool, int, int]:
	if not chunks:
		return False, 0, 0
	texts = [c['text'] for c in chunks]
	embeddings = embedder.encode(texts, convert_to_tensor=False)
	# Normalize for cosine similarity
	faiss.normalize_L2(embeddings)
	vecs = np.asarray(embeddings, dtype='float32')
	index = faiss.IndexFlatIP(vecs.shape[1])
	index.add(vecs)
	# Save index and metadata
	faiss.write_index(index, f"{out_prefix}.faiss")
	with open(f"{out_prefix}.json", 'w', encoding='utf-8') as f:
		json.dump(chunks, f, indent=2, ensure_ascii=False)
	return True, vecs.shape[0], vecs.shape[1]


def main():
	setup_logging()
	logger.info("Building unified RAG corpus + multi-index FAISS...")
	os.makedirs('models', exist_ok=True)

	# 1) Build corpus
	sources = build_corpus()

	# 2) Embeddings
	embedding_model = os.environ.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
	logger.info(f"Loading embedding model: {embedding_model}")
	embedder = SentenceTransformer(embedding_model)

	# 3) Build per-source indices
	index_specs = [
		('credits', 'models/index_credits'),
		('guide', 'models/index_guide'),
		('forms', 'models/index_forms'),
		('all', 'models/index_all')
	]
	for source_key, out_prefix in index_specs:
		logger.info(f"Building index for {source_key} -> {out_prefix}")
		success, nvecs, dim = build_faiss_index(sources[source_key], embedder, out_prefix)
		if success:
			logger.info(f"✓ Saved {out_prefix}.faiss ({nvecs} vectors, dim={dim}) and {out_prefix}.json")
		else:
			logger.warning(f"No data for {source_key}; index not created")

	logger.info("Unified corpus + multi-index build complete.")
	print("\n🎉 Unified corpus + multi-index build complete!")
	for source_key, out_prefix in index_specs:
		exists = os.path.exists(f"{out_prefix}.faiss")
		print(f"  - {source_key}: {'✅' if exists else '⚠️ missing'} -> {out_prefix}.faiss")

if __name__ == '__main__':
	main()
