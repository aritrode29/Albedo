#!/usr/bin/env python3
"""
Simple text extraction script for PDFs that don't contain LEED credits.
"""

import sys
import json
from pathlib import Path
import pdfplumber
import fitz  # PyMuPDF

def extract_text_simple(pdf_path: str) -> str:
    """Extract all text from PDF using multiple methods."""
    texts = []
    
    # Method 1: pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    texts.append(f"=== PAGE {page_num} ===\n{text}")
    except Exception as e:
        print(f"pdfplumber failed: {e}")
    
    # Method 2: PyMuPDF fallback
    if not texts:
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text and text.strip():
                    texts.append(f"=== PAGE {page_num + 1} ===\n{text}")
            doc.close()
        except Exception as e:
            print(f"PyMuPDF failed: {e}")
    
    return "\n\n".join(texts)

def main():
    if len(sys.argv) != 2:
        print("Usage: python extract_text_only.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = Path("outputs/projects/SEA/IP")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Extracting text from: {pdf_path}")
    
    # Extract text
    text = extract_text_simple(pdf_path)
    
    if not text.strip():
        print("No text extracted!")
        sys.exit(1)
    
    # Save text
    output_file = output_dir / "extracted_text.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)
    
    print(f"Text saved to: {output_file}")
    print(f"Extracted {len(text)} characters")
    
    # Also create a simple JSON structure
    data = {
        "source_file": pdf_path,
        "extraction_method": "text_only",
        "content": text,
        "metadata": {
            "total_chars": len(text),
            "total_pages": text.count("=== PAGE"),
            "extraction_timestamp": "2025-10-16T15:14:00Z"
        }
    }
    
    json_file = output_dir / "extracted_data.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"JSON saved to: {json_file}")

if __name__ == "__main__":
    main()

