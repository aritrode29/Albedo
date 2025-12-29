#!/usr/bin/env python3
"""
Robust AI Training & Testing Pipeline
Creates training/test datasets from extracted data.
"""

import os
import sys
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import random

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TrainingDataGenerator:
    """Generates training datasets from extracted LEED data."""
    
    def __init__(self, extraction_dir: str = "outputs/extracted", output_dir: str = "outputs/training"):
        self.extraction_dir = Path(extraction_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_qa_pairs(self, extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate question-answer pairs from credit extractions."""
        qa_pairs = []
        
        for extraction in extractions:
            if extraction.get('file_type') != 'pdf':
                continue
            
            # Extract credit information
            text_content = extraction.get('text_content', [])
            metadata = extraction.get('metadata', {})
            
            # Look for credit patterns
            for page_data in text_content:
                page_text = page_data.get('text', '')
                page_num = page_data.get('page', 0)
                
                # Pattern: "EA Credit X: [Name]"
                credit_pattern = r'([A-Z]{1,2})\s+(Credit|Prerequisite)\s+([^:]+):\s*(.+)'
                matches = re.finditer(credit_pattern, page_text, re.IGNORECASE)
                
                for match in matches:
                    credit_code = match.group(1)
                    credit_type = match.group(2)
                    credit_name = match.group(3).strip()
                    credit_desc = match.group(4).strip()[:500]  # Limit description
                    
                    # Generate questions
                    questions = [
                        f"What is {credit_code} {credit_type}: {credit_name}?",
                        f"What are the requirements for {credit_code} {credit_type}: {credit_name}?",
                        f"How do I achieve {credit_code} {credit_type}: {credit_name}?",
                        f"Tell me about {credit_code} {credit_type}: {credit_name}",
                        f"{credit_code} {credit_type}: {credit_name} requirements"
                    ]
                    
                    # Create answer with citation
                    answer = f"{credit_code} {credit_type}: {credit_name}\n\n{credit_desc}"
                    citation = {
                        'source_file': extraction.get('source_file', ''),
                        'page': page_num,
                        'credit_code': credit_code,
                        'credit_type': credit_type,
                        'credit_name': credit_name
                    }
                    
                    for question in questions:
                        qa_pairs.append({
                            'question': question,
                            'answer': answer,
                            'citation': citation,
                            'source': 'leed_credits',
                            'difficulty': 'medium'
                        })
        
        logger.info(f"Generated {len(qa_pairs)} QA pairs")
        return qa_pairs
    
    def generate_evidence_classification_data(self, extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate evidence classification training data."""
        evidence_data = []
        
        for extraction in extractions:
            if extraction.get('file_type') != 'pdf':
                continue
            
            text_content = extraction.get('text_content', [])
            
            for page_data in text_content:
                page_text = page_data.get('text', '')
                
                # Extract requirements/evidence patterns
                # Look for bullet points, numbered lists, etc.
                lines = page_text.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line or len(line) < 20:
                        continue
                    
                    # Check if it looks like a requirement
                    if any(keyword in line.lower() for keyword in 
                           ['must', 'shall', 'require', 'provide', 'demonstrate', 'achieve']):
                        
                        # Create positive example
                        evidence_data.append({
                            'evidence_text': line,
                            'credit_context': page_text[:500],
                            'label': 'supported',
                            'confidence': 0.8,
                            'source': extraction.get('source_file', '')
                        })
        
        logger.info(f"Generated {len(evidence_data)} evidence classification examples")
        return evidence_data
    
    def generate_citation_data(self, extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate citation generation training data."""
        citation_data = []
        
        for extraction in extractions:
            if extraction.get('file_type') != 'pdf':
                continue
            
            text_content = extraction.get('text_content', [])
            metadata = extraction.get('metadata', {})
            
            for page_data in text_content:
                page_text = page_data.get('text', '')
                page_num = page_data.get('page', 0)
                
                # Extract statements that need citations
                sentences = re.split(r'[.!?]\s+', page_text)
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) < 30 or len(sentence) > 300:
                        continue
                    
                    # Create citation example
                    citation = {
                        'source_file': extraction.get('source_file', ''),
                        'page': page_num,
                        'title': metadata.get('title', ''),
                        'author': metadata.get('author', '')
                    }
                    
                    citation_data.append({
                        'statement': sentence,
                        'citation': citation,
                        'citation_format': f"[{citation['source_file']}, p.{page_num}]"
                    })
        
        logger.info(f"Generated {len(citation_data)} citation examples")
        return citation_data
    
    def create_test_benchmark(self, qa_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create evaluation benchmark from QA pairs."""
        # Split into train/test
        random.shuffle(qa_pairs)
        split_idx = int(len(qa_pairs) * 0.8)
        
        train_set = qa_pairs[:split_idx]
        test_set = qa_pairs[split_idx:]
        
        benchmark = {
            'name': 'LEED_RAG_Benchmark',
            'version': '1.0',
            'created': datetime.now().isoformat(),
            'train_size': len(train_set),
            'test_size': len(test_set),
            'train_questions': [qa['question'] for qa in train_set],
            'test_questions': [qa['question'] for qa in test_set],
            'test_answers': {i: qa['answer'] for i, qa in enumerate(test_set)},
            'test_citations': {i: qa['citation'] for i, qa in enumerate(test_set)}
        }
        
        return benchmark, train_set, test_set
    
    def save_training_data(self, qa_pairs: List[Dict[str, Any]], 
                          evidence_data: List[Dict[str, Any]],
                          citation_data: List[Dict[str, Any]],
                          benchmark: Dict[str, Any],
                          train_set: List[Dict[str, Any]],
                          test_set: List[Dict[str, Any]]):
        """Save all training datasets."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save QA pairs
        qa_file = self.output_dir / f"qa_pairs_{timestamp}.jsonl"
        with open(qa_file, 'w', encoding='utf-8') as f:
            for qa in qa_pairs:
                f.write(json.dumps(qa, ensure_ascii=False) + '\n')
        logger.info(f"✓ Saved QA pairs: {qa_file}")
        
        # Save evidence classification
        evidence_file = self.output_dir / f"evidence_classification_{timestamp}.jsonl"
        with open(evidence_file, 'w', encoding='utf-8') as f:
            for ev in evidence_data:
                f.write(json.dumps(ev, ensure_ascii=False) + '\n')
        logger.info(f"✓ Saved evidence data: {evidence_file}")
        
        # Save citation data
        citation_file = self.output_dir / f"citation_data_{timestamp}.jsonl"
        with open(citation_file, 'w', encoding='utf-8') as f:
            for cit in citation_data:
                f.write(json.dumps(cit, ensure_ascii=False) + '\n')
        logger.info(f"✓ Saved citation data: {citation_file}")
        
        # Save benchmark
        benchmark_file = self.output_dir / f"benchmark_{timestamp}.json"
        with open(benchmark_file, 'w', encoding='utf-8') as f:
            json.dump(benchmark, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ Saved benchmark: {benchmark_file}")
        
        # Save train/test splits
        train_file = self.output_dir / f"train_set_{timestamp}.jsonl"
        with open(train_file, 'w', encoding='utf-8') as f:
            for qa in train_set:
                f.write(json.dumps(qa, ensure_ascii=False) + '\n')
        
        test_file = self.output_dir / f"test_set_{timestamp}.jsonl"
        with open(test_file, 'w', encoding='utf-8') as f:
            for qa in test_set:
                f.write(json.dumps(qa, ensure_ascii=False) + '\n')
        
        logger.info(f"✓ Saved train/test sets: {train_file}, {test_file}")


def main():
    """Main training data generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Robust AI Training & Testing Pipeline')
    parser.add_argument('--extraction-dir', type=str, default='outputs/extracted',
                       help='Directory containing extraction JSON files')
    parser.add_argument('--output-dir', type=str, default='outputs/training',
                       help='Output directory for training data')
    
    args = parser.parse_args()
    
    generator = TrainingDataGenerator(extraction_dir=args.extraction_dir, output_dir=args.output_dir)
    
    # Load extractions
    extraction_files = list(Path(args.extraction_dir).rglob("*_extracted_*.json"))
    logger.info(f"Loading {len(extraction_files)} extraction files...")
    
    extractions = []
    for ext_file in extraction_files:
        try:
            with open(ext_file, 'r', encoding='utf-8') as f:
                extractions.append(json.load(f))
        except Exception as e:
            logger.warning(f"Failed to load {ext_file}: {e}")
    
    logger.info(f"Loaded {len(extractions)} extractions")
    
    # Generate training data
    logger.info("Generating QA pairs...")
    qa_pairs = generator.generate_qa_pairs(extractions)
    
    logger.info("Generating evidence classification data...")
    evidence_data = generator.generate_evidence_classification_data(extractions)
    
    logger.info("Generating citation data...")
    citation_data = generator.generate_citation_data(extractions)
    
    logger.info("Creating test benchmark...")
    benchmark, train_set, test_set = generator.create_test_benchmark(qa_pairs)
    
    # Save everything
    generator.save_training_data(qa_pairs, evidence_data, citation_data, benchmark, train_set, test_set)
    
    logger.info("\n🎉 Training data generation complete!")
    logger.info(f"  QA pairs: {len(qa_pairs)}")
    logger.info(f"  Evidence examples: {len(evidence_data)}")
    logger.info(f"  Citation examples: {len(citation_data)}")
    logger.info(f"  Train set: {len(train_set)}")
    logger.info(f"  Test set: {len(test_set)}")


if __name__ == '__main__':
    main()

