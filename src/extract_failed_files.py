#!/usr/bin/env python3
"""
Extract files that failed in the previous extraction run.
Identifies failed files and attempts to extract them with better error handling.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Any
import sys

# Import the extractor
import sys
sys.path.insert(0, str(Path(__file__).parent))
from robust_extraction_pipeline import UniversalExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def find_all_data_files(data_dir: Path) -> Set[Path]:
    """Find all files in data directory that should be processed."""
    patterns = [
        '**/*.pdf', '**/*.xlsx', '**/*.xlsm', '**/*.xls', 
        '**/*.json', '**/*.txt', '**/*.md', '**/*.csv',
        '**/*.png', '**/*.jpg', '**/*.jpeg', '**/*.gif',
        '**/*.zip', '**/*.doc', '**/*.docx'
    ]
    
    all_files = set()
    for pattern in patterns:
        all_files.update(data_dir.glob(pattern))
    
    # Filter out already extracted files
    all_files = {f for f in all_files if '_extracted' not in f.name}
    return all_files


def find_extracted_files(extracted_dir: Path) -> Set[str]:
    """Find all source files that were successfully extracted."""
    extracted_sources = set()
    
    for json_file in extracted_dir.rglob("*_extracted_*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                source = data.get('source_file', '')
                if source:
                    # Normalize path
                    source_path = Path(source)
                    extracted_sources.add(str(source_path.resolve()))
        except Exception as e:
            logger.debug(f"Could not read {json_file}: {e}")
    
    return extracted_sources


def identify_failed_files(data_dir: Path, extracted_dir: Path) -> List[Path]:
    """Identify files that should have been extracted but weren't."""
    all_files = find_all_data_files(data_dir)
    extracted_sources = find_extracted_files(extracted_dir)
    
    failed_files = []
    for file_path in all_files:
        file_resolved = str(file_path.resolve())
        if file_resolved not in extracted_sources:
            failed_files.append(file_path)
    
    return failed_files


def extract_failed_files(failed_files: List[Path], output_dir: Path, 
                         extractor: UniversalExtractor) -> Dict[str, Any]:
    """Attempt to extract failed files with better error handling."""
    results = {
        'successful': [],
        'failed': [],
        'skipped': []
    }
    
    for file_path in failed_files:
        suffix = file_path.suffix.lower()
        
        # Skip unsupported types
        if suffix not in ['.pdf', '.xlsx', '.xlsm', '.xls', '.json', '.txt', '.md', '.csv']:
            results['skipped'].append({
                'file': str(file_path),
                'reason': f'Unsupported file type: {suffix}'
            })
            continue
        
        try:
            logger.info(f"Attempting to extract: {file_path.name}")
            extraction = extractor.extract_file(file_path)
            
            if extraction:
                if extraction.get('error'):
                    results['failed'].append({
                        'file': str(file_path),
                        'error': extraction['error']
                    })
                else:
                    # Save the extraction
                    json_file, xml_file = extractor.save_extraction(extraction, file_path)
                    results['successful'].append({
                        'file': str(file_path),
                        'output': str(json_file)
                    })
                    extractor.stats['files_processed'] += 1
            else:
                results['failed'].append({
                    'file': str(file_path),
                    'error': 'Extractor returned None'
                })
                
        except Exception as e:
            logger.error(f"Exception extracting {file_path.name}: {e}")
            results['failed'].append({
                'file': str(file_path),
                'error': str(e)
            })
            extractor.stats['files_failed'] += 1
    
    return results


def main():
    """Main function to extract failed files."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract files that failed in previous run')
    parser.add_argument('--data-dir', type=str, default='data', help='Data directory')
    parser.add_argument('--extracted-dir', type=str, default='outputs/extracted', 
                       help='Directory with previous extractions')
    parser.add_argument('--output', type=str, default='outputs/extracted', 
                       help='Output directory')
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    extracted_dir = Path(args.extracted_dir)
    output_dir = Path(args.output)
    
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        sys.exit(1)
    
    logger.info("Identifying failed files...")
    failed_files = identify_failed_files(data_dir, extracted_dir)
    
    logger.info(f"Found {len(failed_files)} files that need extraction")
    
    if not failed_files:
        logger.info("No failed files found!")
        return
    
    # Create extractor
    extractor = UniversalExtractor(output_base=str(output_dir))
    
    # Extract failed files
    logger.info("Extracting failed files...")
    results = extract_failed_files(failed_files, output_dir, extractor)
    
    # Save results summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_failed_files': len(failed_files),
        'successful': len(results['successful']),
        'failed': len(results['failed']),
        'skipped': len(results['skipped']),
        'stats': extractor.stats,
        'details': results
    }
    
    summary_file = output_dir / f"failed_extraction_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n{'='*60}")
    logger.info("FAILED FILES EXTRACTION COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total files found: {len(failed_files)}")
    logger.info(f"Successfully extracted: {len(results['successful'])}")
    logger.info(f"Failed: {len(results['failed'])}")
    logger.info(f"Skipped (unsupported): {len(results['skipped'])}")
    logger.info(f"\nSummary saved to: {summary_file}")
    
    if results['failed']:
        logger.info("\nFailed files:")
        for item in results['failed'][:10]:  # Show first 10
            logger.info(f"  - {Path(item['file']).name}: {item['error']}")
        if len(results['failed']) > 10:
            logger.info(f"  ... and {len(results['failed']) - 10} more")


if __name__ == '__main__':
    main()

