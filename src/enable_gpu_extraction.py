#!/usr/bin/env python3
"""
Enable GPU-accelerated extraction for PDFs and images.
Installs EasyOCR if needed and runs extraction with GPU support.
"""

import sys
import subprocess
from pathlib import Path

def check_gpu_availability():
    """Check if GPU is available."""
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            device_name = torch.cuda.get_device_name(0)
            print(f"[OK] GPU detected: {device_name}")
            return True, device_name
        else:
            print("[X] CUDA not available (CPU only)")
            return False, None
    except ImportError:
        print("[X] PyTorch not installed")
        return False, None

def install_easyocr():
    """Install EasyOCR for GPU-accelerated OCR."""
    print("\nInstalling EasyOCR for GPU-accelerated OCR...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "easyocr", "--quiet"])
        print("[OK] EasyOCR installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[X] Failed to install EasyOCR: {e}")
        return False

def main():
    """Main function to enable GPU extraction."""
    print("="*60)
    print("GPU-ACCELERATED EXTRACTION SETUP")
    print("="*60)
    
    # Check GPU availability
    gpu_available, device_name = check_gpu_availability()
    
    if not gpu_available:
        print("\n⚠ Warning: No GPU detected. Extraction will use CPU.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Check if EasyOCR is installed
    try:
        import easyocr
        print("[OK] EasyOCR already installed")
    except ImportError:
        print("[X] EasyOCR not installed")
        if gpu_available:
            install_easyocr()
        else:
            print("[!] Skipping EasyOCR installation (no GPU)")
    
    # Now run extraction with GPU enabled
    print("\n" + "="*60)
    print("RUNNING GPU-ACCELERATED EXTRACTION")
    print("="*60)
    
    from robust_extraction_pipeline import UniversalExtractor
    import argparse
    
    parser = argparse.ArgumentParser(description='GPU-accelerated extraction')
    parser.add_argument('--data-dir', type=str, default='data', help='Data directory')
    parser.add_argument('--output', type=str, default='outputs/extracted', help='Output directory')
    parser.add_argument('--use-ocr', action='store_true', default=True, help='Use OCR for scanned PDFs')
    parser.add_argument('--extract-images', action='store_true', default=False, help='Extract images from PDFs')
    
    args = parser.parse_args()
    
    # Create extractor with GPU support
    extractor = UniversalExtractor(
        output_base=args.output,
        use_gpu=gpu_available,
        use_ocr=args.use_ocr and gpu_available,
        extract_images=args.extract_images
    )
    
    data_path = Path(args.data_dir)
    
    if not data_path.exists():
        print(f"[X] Data directory not found: {data_path}")
        return
    
    print(f"\nExtraction settings:")
    print(f"  GPU enabled: {extractor.use_gpu}")
    print(f"  OCR enabled: {extractor.use_ocr}")
    print(f"  Extract images: {extractor.extract_images}")
    print(f"\nProcessing: {data_path}")
    
    # Process directory
    all_extractions = extractor.process_directory(data_path, recursive=True)
    
    # Print summary
    print(f"\n{'='*60}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Files processed: {extractor.stats['files_processed']}")
    print(f"Files failed: {extractor.stats['files_failed']}")
    print(f"Total pages: {extractor.stats['total_pages']}")
    print(f"Total tables: {extractor.stats['total_tables']}")
    
    if extractor.use_gpu:
        print(f"\n[OK] GPU acceleration was used for processing")

if __name__ == '__main__':
    main()

