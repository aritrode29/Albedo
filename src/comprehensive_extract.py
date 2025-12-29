#!/usr/bin/env python3
"""
Comprehensive PDF extraction script for LEED documents.
Extracts text, images, figures, tables, equations, and all other content.
"""

import sys
import json
import base64
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional
import pdfplumber
import fitz  # PyMuPDF
from PIL import Image
import io

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensivePDFExtractor:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_images(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract all images from PDF."""
        images = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        if pix.n - pix.alpha < 4:  # GRAY or RGB
                            img_data = pix.tobytes("png")
                            img_base64 = base64.b64encode(img_data).decode()
                            
                            images.append({
                                "page": page_num + 1,
                                "image_index": img_index,
                                "xref": xref,
                                "width": pix.width,
                                "height": pix.height,
                                "colorspace": pix.colorspace.name if pix.colorspace else "unknown",
                                "data": img_base64,
                                "format": "png"
                            })
                        pix = None
                    except Exception as e:
                        logger.warning(f"Failed to extract image {img_index} from page {page_num + 1}: {e}")
                        continue
            doc.close()
        except Exception as e:
            logger.error(f"Image extraction failed: {e}")
        return images
    
    def extract_tables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract tables from PDF using pdfplumber."""
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_tables = page.extract_tables()
                    for table_index, table in enumerate(page_tables):
                        if table and len(table) > 0:
                            tables.append({
                                "page": page_num,
                                "table_index": table_index,
                                "rows": len(table),
                                "columns": len(table[0]) if table else 0,
                                "data": table
                            })
        except Exception as e:
            logger.error(f"Table extraction failed: {e}")
        return tables
    
    def extract_text_with_formatting(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract text with formatting information."""
        text_data = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text blocks with formatting
                blocks = page.get_text("dict")
                page_text = ""
                formatted_blocks = []
                
                for block in blocks.get("blocks", []):
                    if "lines" in block:
                        block_text = ""
                        for line in block["lines"]:
                            line_text = ""
                            for span in line["spans"]:
                                span_text = span.get("text", "")
                                line_text += span_text
                                
                                # Store formatting info
                                formatted_blocks.append({
                                    "text": span_text,
                                    "font": span.get("font", ""),
                                    "size": span.get("size", 0),
                                    "flags": span.get("flags", 0),
                                    "color": span.get("color", 0),
                                    "bbox": span.get("bbox", [])
                                })
                            block_text += line_text + "\n"
                        page_text += block_text
                
                text_data.append({
                    "page": page_num + 1,
                    "text": page_text.strip(),
                    "formatted_blocks": formatted_blocks,
                    "total_chars": len(page_text.strip())
                })
            doc.close()
        except Exception as e:
            logger.error(f"Formatted text extraction failed: {e}")
        return text_data
    
    def extract_drawings_and_figures(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract drawings, figures, and vector graphics."""
        drawings = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract drawings (vector graphics)
                drawings_list = page.get_drawings()
                for draw_index, drawing in enumerate(drawings_list):
                        drawings.append({
                            "page": page_num + 1,
                            "drawing_index": draw_index,
                            "type": "vector_graphics",
                            "items": len(drawing.get("items", [])),
                            "rect": list(drawing.get("rect")) if drawing.get("rect") else None,
                            "data": str(drawing)  # Convert to string to avoid serialization issues
                        })
                
                # Extract text blocks that might be figures/captions
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    if "lines" in block:
                        block_text = ""
                        for line in block["lines"]:
                            for span in line["spans"]:
                                block_text += span.get("text", "")
                        
                        # Check if this looks like a figure caption
                        if any(keyword in block_text.lower() for keyword in 
                               ["figure", "fig.", "table", "equation", "formula"]):
                            drawings.append({
                                "page": page_num + 1,
                                "type": "caption_or_label",
                                "text": block_text.strip(),
                                "bbox": list(block.get("bbox", [])) if block.get("bbox") else []
                            })
            doc.close()
        except Exception as e:
            logger.error(f"Drawing extraction failed: {e}")
        return drawings
    
    def extract_annotations(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract PDF annotations and comments."""
        annotations = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                annots = page.annots()
                
                for annot in annots:
                    try:
                        info = annot.info
                        annotations.append({
                            "page": page_num + 1,
                            "type": str(annot.type[1]) if hasattr(annot, 'type') else "unknown",
                            "content": info.get("content", ""),
                            "subject": info.get("subject", ""),
                            "title": info.get("title", ""),
                            "author": info.get("title", ""),
                            "rect": list(annot.rect) if hasattr(annot, 'rect') and annot.rect else None,
                            "flags": annot.flags if hasattr(annot, 'flags') else 0
                        })
                    except Exception as e:
                        logger.warning(f"Failed to extract annotation: {e}")
                        continue
            doc.close()
        except Exception as e:
            logger.error(f"Annotation extraction failed: {e}")
        return annotations
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract PDF metadata."""
        metadata = {}
        try:
            doc = fitz.open(pdf_path)
            metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
                "page_count": len(doc),
                "file_size": Path(pdf_path).stat().st_size
            }
            doc.close()
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
        return metadata
    
    def extract_comprehensive(self, pdf_path: str) -> Dict[str, Any]:
        """Extract all content from PDF."""
        logger.info(f"Extracting comprehensive data from: {pdf_path}")
        
        # Extract all components
        metadata = self.extract_metadata(pdf_path)
        text_data = self.extract_text_with_formatting(pdf_path)
        images = self.extract_images(pdf_path)
        tables = self.extract_tables(pdf_path)
        drawings = self.extract_drawings_and_figures(pdf_path)
        annotations = self.extract_annotations(pdf_path)
        
        # Combine all data
        comprehensive_data = {
            "source_file": pdf_path,
            "extraction_timestamp": datetime.now().isoformat(),
            "metadata": metadata,
            "text_content": text_data,
            "images": images,
            "tables": tables,
            "drawings_figures": drawings,
            "annotations": annotations,
            "summary": {
                "total_pages": metadata.get("page_count", 0),
                "total_images": len(images),
                "total_tables": len(tables),
                "total_drawings": len(drawings),
                "total_annotations": len(annotations),
                "total_text_chars": sum(page.get("total_chars", 0) for page in text_data)
            }
        }
        
        return comprehensive_data
    
    def save_extraction(self, data: Dict[str, Any], pdf_name: str) -> None:
        """Save extracted data to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comprehensive JSON
        json_file = self.output_dir / f"{pdf_name}_comprehensive_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Save plain text
        text_file = self.output_dir / f"{pdf_name}_text_{timestamp}.txt"
        with open(text_file, "w", encoding="utf-8") as f:
            for page_data in data["text_content"]:
                f.write(f"=== PAGE {page_data['page']} ===\n")
                f.write(page_data["text"])
                f.write("\n\n")
        
        # Save images separately
        if data["images"]:
            images_dir = self.output_dir / f"{pdf_name}_images_{timestamp}"
            images_dir.mkdir(exist_ok=True)
            
            for img_data in data["images"]:
                img_file = images_dir / f"page_{img_data['page']}_img_{img_data['image_index']}.png"
                try:
                    img_bytes = base64.b64decode(img_data["data"])
                    with open(img_file, "wb") as f:
                        f.write(img_bytes)
                except Exception as e:
                    logger.warning(f"Failed to save image: {e}")
        
        # Save tables as separate JSON
        if data["tables"]:
            tables_file = self.output_dir / f"{pdf_name}_tables_{timestamp}.json"
            with open(tables_file, "w", encoding="utf-8") as f:
                json.dump(data["tables"], f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ Comprehensive extraction saved:")
        logger.info(f"  → JSON: {json_file}")
        logger.info(f"  → Text: {text_file}")
        if data["images"]:
            logger.info(f"  → Images: {images_dir}")
        if data["tables"]:
            logger.info(f"  → Tables: {tables_file}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python comprehensive_extract.py <pdf_path_or_directory>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    input_path = Path(input_path)
    
    if input_path.is_file():
        # Single file
        pdf_files = [input_path]
        output_dir = input_path.parent / "extracted"
    elif input_path.is_dir():
        # Directory
        pdf_files = list(input_path.glob("*.pdf"))
        output_dir = input_path / "extracted"
    else:
        print(f"Path not found: {input_path}")
        sys.exit(1)
    
    if not pdf_files:
        print("No PDF files found!")
        sys.exit(1)
    
    extractor = ComprehensivePDFExtractor(str(output_dir))
    
    for pdf_file in pdf_files:
        try:
            logger.info(f"Processing: {pdf_file}")
            data = extractor.extract_comprehensive(str(pdf_file))
            pdf_name = pdf_file.stem
            extractor.save_extraction(data, pdf_name)
            
            # Print summary
            summary = data["summary"]
            logger.info(f"✓ Extracted: {summary['total_pages']} pages, "
                       f"{summary['total_images']} images, "
                       f"{summary['total_tables']} tables, "
                       f"{summary['total_drawings']} drawings, "
                       f"{summary['total_annotations']} annotations")
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_file}: {e}")
            continue

if __name__ == "__main__":
    main()
