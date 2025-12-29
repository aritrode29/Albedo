#!/usr/bin/env python3
"""
Run GPU-accelerated extraction on all files, including ZIP archives.
"""

import sys
from pathlib import Path
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from robust_extraction_pipeline import UniversalExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run GPU-accelerated extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(description='GPU-accelerated extraction')
    parser.add_argument('--data-dir', type=str, default='data', help='Data directory')
    parser.add_argument('--output', type=str, default='outputs/extracted', help='Output directory')
    parser.add_argument('--use-ocr', action='store_true', default=True, help='Use OCR for scanned PDFs')
    parser.add_argument('--no-ocr', action='store_true', default=False, help='Disable OCR')
    parser.add_argument('--extract-images', action='store_true', default=False, help='Extract images from PDFs')
    
    args = parser.parse_args()
    
    # Check GPU availability
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            device_name = torch.cuda.get_device_name(0)
            logger.info(f"[OK] GPU detected: {device_name}")
        else:
            logger.warning("[!] No GPU detected, using CPU")
            gpu_available = False
    except ImportError:
        logger.warning("[!] PyTorch not available, using CPU")
        gpu_available = False
    
    # Check EasyOCR
    try:
        import easyocr
        ocr_available = True
        logger.info("[OK] EasyOCR available")
    except ImportError:
        ocr_available = False
        logger.warning("[!] EasyOCR not installed - OCR disabled")
        args.use_ocr = False
    
    # Create extractor with GPU support
    use_ocr_enabled = args.use_ocr and not args.no_ocr and ocr_available
    extractor = UniversalExtractor(
        output_base=args.output,
        use_gpu=gpu_available,
        use_ocr=use_ocr_enabled,
        extract_images=args.extract_images
    )
    
    data_path = Path(args.data_dir)
    
    if not data_path.exists():
        logger.error(f"Data directory not found: {data_path}")
        sys.exit(1)
    
    logger.info(f"\n{'='*60}")
    logger.info("GPU-ACCELERATED EXTRACTION")
    logger.info(f"{'='*60}")
    logger.info(f"GPU enabled: {extractor.use_gpu}")
    logger.info(f"OCR enabled: {extractor.use_ocr}")
    logger.info(f"Extract images: {extractor.extract_images}")
    logger.info(f"Processing: {data_path}")
    logger.info(f"{'='*60}\n")
    
    # Process directory
    all_extractions = extractor.process_directory(data_path, recursive=True)
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("EXTRACTION COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Files processed: {extractor.stats['files_processed']}")
    logger.info(f"Files failed: {extractor.stats['files_failed']}")
    logger.info(f"Total pages: {extractor.stats['total_pages']}")
    logger.info(f"Total tables: {extractor.stats['total_tables']}")
    
    if extractor.use_gpu:
        logger.info(f"\n[OK] GPU acceleration was used for processing")

if __name__ == '__main__':
    main()

