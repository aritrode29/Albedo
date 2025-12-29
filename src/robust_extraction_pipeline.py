#!/usr/bin/env python3
"""
Robust Universal Data Extraction Pipeline (FAST VERSION)
Extracts data from all sources efficiently:
- PDFs (text, tables, metadata - skips slow image/OCR by default)
- Excel/CSV files
- JSON files
- Text files

Outputs:
- Comprehensive XML/JSON for each file
- Normalized chunks ready for RAG
"""

import os
import sys
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import re
import hashlib
import concurrent.futures
from functools import partial

# PDF processing
import pdfplumber
import fitz  # PyMuPDF

# Excel/CSV processing
try:
    import pandas as pd
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

# GPU-accelerated OCR
try:
    import easyocr
    import torch
    GPU_OCR_AVAILABLE = True
    GPU_AVAILABLE = torch.cuda.is_available()
except ImportError:
    GPU_OCR_AVAILABLE = False
    GPU_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Log GPU/OCR status after logger is initialized
if GPU_OCR_AVAILABLE:
    if GPU_AVAILABLE:
        logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
    else:
        logger.info("GPU not available, using CPU for OCR")
else:
    logger.info("EasyOCR not installed. Install with: pip install easyocr")

# Disable slow OCR by default (unless GPU is available)
OCR_AVAILABLE = GPU_OCR_AVAILABLE
IMAGE_PROCESSING_AVAILABLE = GPU_OCR_AVAILABLE


class UniversalExtractor:
    """Extracts all possible data from any file type - FAST mode with GPU acceleration."""
    
    def __init__(self, output_base: str = "outputs/extracted", 
                 extract_images: bool = False, 
                 extract_drawings: bool = False,
                 max_workers: int = 4,
                 use_gpu: bool = True,
                 use_ocr: bool = True):  # Enable OCR by default if GPU available
        self.output_base = Path(output_base)
        self.output_base.mkdir(parents=True, exist_ok=True)
        self.extract_images = extract_images
        self.extract_drawings = extract_drawings
        self.max_workers = max_workers
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.use_ocr = use_ocr and GPU_OCR_AVAILABLE
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'total_pages': 0,
            'total_tables': 0,
            'total_chunks': 0
        }
        
        # Initialize GPU OCR reader if available
        self.ocr_reader = None
        if self.use_ocr and GPU_OCR_AVAILABLE:
            try:
                device = 'cuda' if self.use_gpu else 'cpu'
                logger.info(f"Initializing EasyOCR with device: {device}")
                
                # Fix Windows encoding issue with EasyOCR progress bar
                import os
                import sys
                import io
                from contextlib import redirect_stdout, redirect_stderr
                
                # Suppress EasyOCR progress output to avoid encoding issues
                class NullWriter:
                    def write(self, s):
                        pass
                    def flush(self):
                        pass
                
                # Temporarily redirect stdout/stderr to avoid encoding issues
                try:
                    with redirect_stdout(NullWriter()), redirect_stderr(NullWriter()):
                        import warnings
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            self.ocr_reader = easyocr.Reader(['en'], gpu=self.use_gpu, verbose=False)
                    logger.info("GPU OCR initialized successfully")
                except Exception as init_error:
                    logger.warning(f"Failed to initialize GPU OCR: {init_error}")
                    self.ocr_reader = None
                    self.use_ocr = False
            except Exception as e:
                logger.warning(f"Failed to initialize GPU OCR: {e}")
                self.ocr_reader = None
                self.use_ocr = False
    
    def extract_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract text and tables from PDF - FAST mode (skips images/drawings by default)."""
        logger.info(f"Extracting PDF: {pdf_path.name}")
        result = {
            'source_file': str(pdf_path),
            'file_type': 'pdf',
            'extraction_timestamp': datetime.now().isoformat(),
            'metadata': {},
            'text_content': [],
            'tables': [],
            'bookmarks': []
        }
        
        try:
            # PyMuPDF for fast text extraction
            doc = fitz.open(str(pdf_path))
            result['metadata'] = {
                'title': doc.metadata.get('title', ''),
                'author': doc.metadata.get('author', ''),
                'subject': doc.metadata.get('subject', ''),
                'page_count': len(doc),
                'file_size': pdf_path.stat().st_size
            }
            
            # Extract bookmarks/outline
            try:
                result['bookmarks'] = doc.get_toc()
            except:
                pass
            
            # Extract text from each page (FAST - no formatting details)
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text("text")  # Simple text extraction - FAST
                
                # If page is blank or very little text, try OCR if enabled
                if (not page_text.strip() or len(page_text.strip()) < 50) and self.use_ocr and self.ocr_reader:
                    try:
                        # Convert page to image and run OCR
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                        img_data = pix.tobytes("png")
                        from PIL import Image
                        import io
                        img = Image.open(io.BytesIO(img_data))
                        
                        # Run OCR on the image
                        ocr_results = self.ocr_reader.readtext(img)
                        ocr_text = " ".join([item[1] for item in ocr_results])
                        
                        if ocr_text.strip():
                            page_text = ocr_text
                            result['metadata'].setdefault('ocr_pages', []).append(page_num + 1)
                    except Exception as e:
                        logger.debug(f"OCR failed for page {page_num + 1}: {e}")
                
                if page_text.strip():
                    result['text_content'].append({
                        'page': page_num + 1,
                        'text': page_text.strip(),
                        'total_chars': len(page_text.strip()),
                        'ocr_used': page_num + 1 in result['metadata'].get('ocr_pages', [])
                    })
            
            doc.close()
            
            # pdfplumber for tables (only if file is small enough)
            file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            if file_size_mb < 50:  # Skip table extraction for very large files
                try:
                    with pdfplumber.open(str(pdf_path)) as pdf:
                        for page_num, page in enumerate(pdf.pages, 1):
                            try:
                                page_tables = page.extract_tables()
                                for table_index, table in enumerate(page_tables):
                                    if table and len(table) > 0:
                                        result['tables'].append({
                                            'page': page_num,
                                            'table_index': table_index,
                                            'rows': len(table),
                                            'columns': len(table[0]) if table else 0,
                                            'data': table
                                        })
                            except:
                                continue
                except Exception as e:
                    logger.debug(f"Table extraction skipped: {e}")
            
            self.stats['total_pages'] += result['metadata']['page_count']
            self.stats['total_tables'] += len(result['tables'])
            
        except Exception as e:
            logger.error(f"PDF extraction failed for {pdf_path}: {e}")
            result['error'] = str(e)
            self.stats['files_failed'] += 1
        
        return result
    
    def extract_excel(self, excel_path: Path) -> Dict[str, Any]:
        """Extract from Excel files - FAST mode."""
        logger.info(f"Extracting Excel: {excel_path.name}")
        result = {
            'source_file': str(excel_path),
            'file_type': 'excel',
            'extraction_timestamp': datetime.now().isoformat(),
            'sheets': [],
            'metadata': {}
        }
        
        if not EXCEL_AVAILABLE:
            result['error'] = 'pandas not installed'
            return result
        
        try:
            excel_file = pd.ExcelFile(str(excel_path), engine='openpyxl')
            result['metadata'] = {
                'sheet_names': excel_file.sheet_names,
                'file_size': excel_path.stat().st_size
            }
            
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    # Limit rows for very large sheets
                    if len(df) > 1000:
                        df = df.head(1000)
                    result['sheets'].append({
                        'name': sheet_name,
                        'rows': len(df),
                        'columns': len(df.columns),
                        'column_names': [str(c) for c in df.columns.tolist()],
                        'data': df.fillna('').astype(str).to_dict('records')
                    })
                except Exception as e:
                    logger.debug(f"Sheet {sheet_name} skipped: {e}")
            
        except Exception as e:
            logger.error(f"Excel extraction failed: {e}")
            result['error'] = str(e)
            self.stats['files_failed'] += 1
        
        return result
    
    def extract_json(self, json_path: Path) -> Dict[str, Any]:
        """Extract from JSON files."""
        logger.info(f"Extracting JSON: {json_path.name}")
        result = {
            'source_file': str(json_path),
            'file_type': 'json',
            'extraction_timestamp': datetime.now().isoformat(),
            'data': None,
            'metadata': {'file_size': json_path.stat().st_size}
        }
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                result['data'] = json.load(f)
        except Exception as e:
            logger.error(f"JSON extraction failed: {e}")
            result['error'] = str(e)
            self.stats['files_failed'] += 1
        
        return result
    
    def extract_text_file(self, text_path: Path) -> Dict[str, Any]:
        """Extract from plain text files."""
        logger.info(f"Extracting Text: {text_path.name}")
        result = {
            'source_file': str(text_path),
            'file_type': 'text',
            'extraction_timestamp': datetime.now().isoformat(),
            'content': '',
            'metadata': {'file_size': text_path.stat().st_size}
        }
        
        try:
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(text_path, 'r', encoding=encoding) as f:
                        result['content'] = f.read()
                    break
                except UnicodeDecodeError:
                    continue
        except Exception as e:
            result['error'] = str(e)
            self.stats['files_failed'] += 1
        
        return result
    
    def extract_zip(self, zip_path: Path) -> Dict[str, Any]:
        """Extract contents from ZIP files."""
        import zipfile
        logger.info(f"Extracting ZIP: {zip_path.name}")
        result = {
            'source_file': str(zip_path),
            'file_type': 'zip',
            'extraction_timestamp': datetime.now().isoformat(),
            'files': [],
            'metadata': {'file_size': zip_path.stat().st_size}
        }
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                result['metadata']['file_count'] = len(file_list)
                
                # Extract file list and basic info
                for file_name in file_list:
                    try:
                        file_info = zip_ref.getinfo(file_name)
                        result['files'].append({
                            'name': file_name,
                            'size': file_info.file_size,
                            'compressed_size': file_info.compress_size,
                            'is_directory': file_name.endswith('/')
                        })
                    except:
                        continue
                
                # Try to extract and process key files from ZIP
                extracted_files = []
                for file_name in file_list:
                    if not file_name.endswith('/'):  # Skip directories
                        file_ext = Path(file_name).suffix.lower()
                        if file_ext in ['.pdf', '.xlsx', '.xlsm', '.xls', '.json', '.txt', '.md', '.csv']:
                            try:
                                # Extract to temp location and process
                                import tempfile
                                with tempfile.TemporaryDirectory() as temp_dir:
                                    zip_ref.extract(file_name, temp_dir)
                                    temp_file = Path(temp_dir) / file_name
                                    if temp_file.exists():
                                        # Process the extracted file
                                        extracted = self.extract_file(temp_file)
                                        if extracted:
                                            extracted['zip_source'] = str(zip_path)
                                            extracted['zip_path'] = file_name
                                            extracted_files.append(extracted)
                            except Exception as e:
                                logger.debug(f"Could not extract {file_name} from ZIP: {e}")
                
                result['extracted_contents'] = extracted_files
                
        except Exception as e:
            logger.error(f"ZIP extraction failed: {e}")
            result['error'] = str(e)
            self.stats['files_failed'] += 1
        
        return result
    
    def extract_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Route to appropriate extractor based on file extension."""
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return self.extract_pdf(file_path)
        elif suffix in ['.xlsx', '.xlsm', '.xls']:
            return self.extract_excel(file_path)
        elif suffix == '.json':
            return self.extract_json(file_path)
        elif suffix in ['.txt', '.md', '.csv']:
            return self.extract_text_file(file_path)
        elif suffix == '.zip':
            return self.extract_zip(file_path)
        else:
            return None  # Skip unsupported types silently
    
    def save_extraction(self, data: Dict[str, Any], file_path: Path) -> Tuple[Path, Path]:
        """Save extraction as both XML and JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_stem = file_path.stem[:50]  # Limit filename length
        file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:6]
        
        try:
            output_dir = self.output_base / file_path.parent.relative_to(Path('data'))
        except ValueError:
            output_dir = self.output_base
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON only (faster, XML is optional)
        json_file = output_dir / f"{file_stem}_{file_hash}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        
        # Save XML (simplified)
        xml_file = output_dir / f"{file_stem}_{file_hash}.xml"
        try:
            root = self._dict_to_xml(data, 'extraction')
            xml_str = ET.tostring(root, encoding='unicode')
            with open(xml_file, 'w', encoding='utf-8') as f:
                f.write(xml_str)
        except:
            xml_file = None
        
        logger.info(f"[OK] {file_path.name}")
        return json_file, xml_file
    
    def _dict_to_xml(self, d: Dict[str, Any], root_name: str) -> ET.Element:
        """Convert dictionary to XML Element."""
        root = ET.Element(root_name)
        
        def add_node(parent, key, value):
            if isinstance(value, dict):
                node = ET.SubElement(parent, key)
                for k, v in value.items():
                    add_node(node, k, v)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        node = ET.SubElement(parent, key)
                        for k, v in item.items():
                            add_node(node, k, v)
                    else:
                        node = ET.SubElement(parent, key)
                        node.text = str(item)
            else:
                node = ET.SubElement(parent, key)
                if value is not None:
                    node.text = str(value)
        
        for k, v in d.items():
            add_node(root, k, v)
        
        return root
    
    def process_directory(self, data_dir: Path, recursive: bool = True) -> List[Dict[str, Any]]:
        """Process all files in a directory - with parallel processing."""
        logger.info(f"Processing directory: {data_dir}")
        all_extractions = []
        
        # Only process key file types (skip images for speed)
        patterns = ['**/*.pdf', '**/*.xlsx', '**/*.xlsm', '**/*.json', '**/*.txt', '**/*.md', '**/*.zip']
        
        if not recursive:
            patterns = [p.replace('**/', '') for p in patterns]
        
        files_to_process = []
        for pattern in patterns:
            files_to_process.extend(data_dir.glob(pattern))
        
        # Remove duplicates, skip already-extracted files
        files_to_process = sorted(set(files_to_process))
        files_to_process = [f for f in files_to_process if '_extracted' not in f.name]
        
        logger.info(f"Found {len(files_to_process)} files to process")
        
        # Process files
        for file_path in files_to_process:
            try:
                extraction = self.extract_file(file_path)
                if extraction and not extraction.get('error'):
                    json_file, xml_file = self.save_extraction(extraction, file_path)
                    extraction['saved_json'] = str(json_file) if json_file else None
                    extraction['saved_xml'] = str(xml_file) if xml_file else None
                    all_extractions.append(extraction)
                    self.stats['files_processed'] += 1
            except Exception as e:
                logger.error(f"Failed: {file_path.name}: {e}")
                self.stats['files_failed'] += 1
        
        return all_extractions


def main():
    """Main extraction pipeline - FAST version."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fast Data Extraction Pipeline')
    parser.add_argument('data_path', type=str, nargs='?', default='data', help='Path to data directory')
    parser.add_argument('--output', type=str, default='outputs/extracted', help='Output directory')
    parser.add_argument('--recursive', action='store_true', default=True, help='Process recursively')
    
    args = parser.parse_args()
    
    extractor = UniversalExtractor(output_base=args.output)
    data_path = Path(args.data_path)
    
    if not data_path.exists():
        logger.error(f"Path not found: {data_path}")
        sys.exit(1)
    
    if data_path.is_file():
        extraction = extractor.extract_file(data_path)
        if extraction:
            extractor.save_extraction(extraction, data_path)
            extractor.stats['files_processed'] = 1
    else:
        all_extractions = extractor.process_directory(data_path, recursive=args.recursive)
        
        # Save summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'stats': extractor.stats,
            'files': len(all_extractions)
        }
        
        summary_path = Path(args.output) / "summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n{'='*50}")
        print("EXTRACTION COMPLETE")
        print(f"{'='*50}")
        print(f"Files processed: {extractor.stats['files_processed']}")
        print(f"Files failed: {extractor.stats['files_failed']}")
        print(f"Total pages: {extractor.stats['total_pages']}")
        print(f"Total tables: {extractor.stats['total_tables']}")


if __name__ == '__main__':
    main()

