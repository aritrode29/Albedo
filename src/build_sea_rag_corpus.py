#!/usr/bin/env python3
"""
Build comprehensive RAG corpus from all extracted SEA project data.
Includes text, images, tables, figures, and metadata.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SEARAGBuilder:
    def __init__(self, output_dir: str = "outputs/projects/SEA"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunks = []
        
    def create_text_chunk(self, content: str, metadata: Dict[str, Any], chunk_type: str = "text") -> Dict[str, Any]:
        """Create a RAG chunk from text content."""
        chunk_id = hashlib.md5(content.encode()).hexdigest()[:12]
        
        return {
            "id": f"sea_{chunk_type}_{chunk_id}",
            "text": content,
            "metadata": {
                **metadata,
                "chunk_type": chunk_type,
                "source": "SEA_project",
                "created_at": datetime.now().isoformat(),
                "content_length": len(content)
            }
        }
    
    def process_main_project_files(self):
        """Process main SEA project files."""
        logger.info("Processing main SEA project files...")
        
        # Main project text
        main_text_file = self.output_dir / "full_text_20251016_150514.txt"
        if main_text_file.exists():
            with open(main_text_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            chunk = self.create_text_chunk(
                content,
                {
                    "file_name": "SEA Building Addition",
                    "file_type": "pdf_extraction",
                    "document_type": "project_documentation",
                    "leed_category": "general",
                    "pages": "multiple"
                },
                "project_overview"
            )
            self.chunks.append(chunk)
            logger.info(f"✓ Added main project text chunk ({len(content)} chars)")
        
        # Credits data
        credits_file = self.output_dir / "leed_credits_20251016_150514.json"
        if credits_file.exists():
            with open(credits_file, 'r', encoding='utf-8') as f:
                credits_data = json.load(f)
            
            for credit in credits_data:
                credit_text = f"Credit: {credit.get('name', 'Unknown')}\n"
                credit_text += f"Code: {credit.get('code', 'N/A')}\n"
                credit_text += f"Type: {credit.get('type', 'Credit')}\n"
                credit_text += f"Points: {credit.get('points', 0)}\n"
                credit_text += f"Description: {credit.get('description', 'No description')}\n"
                
                if credit.get('requirements'):
                    credit_text += f"Requirements: {credit['requirements']}\n"
                
                chunk = self.create_text_chunk(
                    credit_text,
                    {
                        "file_name": "SEA Building Addition",
                        "file_type": "structured_credits",
                        "document_type": "leed_credits",
                        "leed_category": credit.get('category', 'general'),
                        "credit_code": credit.get('code'),
                        "credit_name": credit.get('name'),
                        "credit_points": credit.get('points', 0)
                    },
                    "credit_data"
                )
                self.chunks.append(chunk)
            
            logger.info(f"✓ Added {len(credits_data)} credit chunks")
    
    def process_ip_folder(self):
        """Process Integrative Process folder."""
        logger.info("Processing IP (Integrative Process) folder...")
        
        ip_dir = self.output_dir / "IP"
        if not ip_dir.exists():
            logger.warning("IP folder not found")
            return
        
        # Process extracted text
        text_file = ip_dir / "extracted_text.txt"
        if text_file.exists():
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split into sections based on page breaks
            sections = content.split("=== PAGE")
            for i, section in enumerate(sections[1:], 1):  # Skip first empty section
                if section.strip():
                    chunk = self.create_text_chunk(
                        f"Page {i}: {section.strip()}",
                        {
                            "file_name": "Integrative Process Worksheet",
                            "file_type": "pdf_extraction",
                            "document_type": "leed_worksheet",
                            "leed_category": "IP",
                            "page_number": i,
                            "section_type": "integrative_process"
                        },
                        "ip_worksheet"
                    )
                    self.chunks.append(chunk)
            
            logger.info(f"✓ Added {len(sections)-1} IP worksheet chunks")
        
        # Process JSON data
        json_file = ip_dir / "extracted_data.json"
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract structured information
            if 'content' in data:
                chunk = self.create_text_chunk(
                    data['content'],
                    {
                        "file_name": "Integrative Process Worksheet",
                        "file_type": "structured_json",
                        "document_type": "leed_worksheet",
                        "leed_category": "IP",
                        "extraction_method": data.get('extraction_method', 'unknown'),
                        "total_chars": data.get('metadata', {}).get('total_chars', 0),
                        "total_pages": data.get('metadata', {}).get('total_pages', 0)
                    },
                    "ip_structured"
                )
                self.chunks.append(chunk)
                logger.info("✓ Added IP structured data chunk")
    
    def process_we_folder(self):
        """Process Water Efficiency folder."""
        logger.info("Processing WE (Water Efficiency) folder...")
        
        we_dir = self.output_dir / "WE"
        if not we_dir.exists():
            logger.warning("WE folder not found")
            return
        
        # Process UT Austin Water Treatment files
        ut_folder = we_dir / "UT_Austin_Water_Treatment_images"
        if ut_folder.exists():
            self.process_document_folder(ut_folder, "UT Austin Water Treatment Narrative", "WE")
        
        # Process Optimize Process Water Use files
        opt_folder = we_dir / "Optimize_Process_Water_images"
        if opt_folder.exists():
            self.process_document_folder(opt_folder, "Optimize Process Water Use", "WE")
    
    def process_document_folder(self, folder: Path, doc_name: str, leed_category: str):
        """Process a document folder containing text, tables, and images."""
        logger.info(f"Processing {doc_name} folder...")
        
        # Process text files
        for text_file in folder.glob("*_text_*.txt"):
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            chunk = self.create_text_chunk(
                content,
                {
                    "file_name": doc_name,
                    "file_type": "pdf_extraction",
                    "document_type": "leed_documentation",
                    "leed_category": leed_category,
                    "content_type": "full_text"
                },
                "document_text"
            )
            self.chunks.append(chunk)
            logger.info(f"✓ Added {doc_name} text chunk")
        
        # Process table files
        for table_file in folder.glob("*_tables_*.json"):
            with open(table_file, 'r', encoding='utf-8') as f:
                tables_data = json.load(f)
            
            for table in tables_data:
                table_text = f"Table from page {table.get('page', 'unknown')}:\n"
                table_text += f"Rows: {table.get('rows', 0)}, Columns: {table.get('columns', 0)}\n\n"
                
                # Add table data
                if 'data' in table and table['data']:
                    for row_idx, row in enumerate(table['data']):
                        if row:  # Skip empty rows
                            row_text = " | ".join(str(cell) if cell is not None else "" for cell in row)
                            table_text += f"Row {row_idx + 1}: {row_text}\n"
                
                chunk = self.create_text_chunk(
                    table_text,
                    {
                        "file_name": doc_name,
                        "file_type": "structured_tables",
                        "document_type": "leed_documentation",
                        "leed_category": leed_category,
                        "content_type": "table_data",
                        "page_number": table.get('page'),
                        "table_index": table.get('table_index'),
                        "rows": table.get('rows'),
                        "columns": table.get('columns')
                    },
                    "table_data"
                )
                self.chunks.append(chunk)
            
            logger.info(f"✓ Added {len(tables_data)} table chunks from {doc_name}")
        
        # Process comprehensive JSON files
        for comp_file in folder.glob("*_comprehensive_*.json"):
            with open(comp_file, 'r', encoding='utf-8') as f:
                comp_data = json.load(f)
            
            # Extract summary information
            if 'summary' in comp_data:
                summary = comp_data['summary']
                summary_text = f"Document Summary for {doc_name}:\n"
                summary_text += f"Total Pages: {summary.get('total_pages', 0)}\n"
                summary_text += f"Total Images: {summary.get('total_images', 0)}\n"
                summary_text += f"Total Tables: {summary.get('total_tables', 0)}\n"
                summary_text += f"Total Drawings: {summary.get('total_drawings', 0)}\n"
                summary_text += f"Total Annotations: {summary.get('total_annotations', 0)}\n"
                summary_text += f"Total Text Characters: {summary.get('total_text_chars', 0)}\n"
                
                chunk = self.create_text_chunk(
                    summary_text,
                    {
                        "file_name": doc_name,
                        "file_type": "comprehensive_extraction",
                        "document_type": "leed_documentation",
                        "leed_category": leed_category,
                        "content_type": "document_summary",
                        **summary
                    },
                    "document_summary"
                )
                self.chunks.append(chunk)
                logger.info(f"✓ Added {doc_name} comprehensive summary chunk")
            
            # Extract metadata
            if 'metadata' in comp_data:
                metadata = comp_data['metadata']
                metadata_text = f"Document Metadata for {doc_name}:\n"
                metadata_text += f"Title: {metadata.get('title', 'N/A')}\n"
                metadata_text += f"Author: {metadata.get('author', 'N/A')}\n"
                metadata_text += f"Subject: {metadata.get('subject', 'N/A')}\n"
                metadata_text += f"Creator: {metadata.get('creator', 'N/A')}\n"
                metadata_text += f"Producer: {metadata.get('producer', 'N/A')}\n"
                metadata_text += f"Creation Date: {metadata.get('creation_date', 'N/A')}\n"
                metadata_text += f"Modification Date: {metadata.get('modification_date', 'N/A')}\n"
                metadata_text += f"Page Count: {metadata.get('page_count', 0)}\n"
                metadata_text += f"File Size: {metadata.get('file_size', 0)} bytes\n"
                
                chunk = self.create_text_chunk(
                    metadata_text,
                    {
                        "file_name": doc_name,
                        "file_type": "document_metadata",
                        "document_type": "leed_documentation",
                        "leed_category": leed_category,
                        "content_type": "metadata",
                        **metadata
                    },
                    "document_metadata"
                )
                self.chunks.append(chunk)
                logger.info(f"✓ Added {doc_name} metadata chunk")
    
    def build_corpus(self):
        """Build the complete RAG corpus."""
        logger.info("Building comprehensive SEA RAG corpus...")
        
        # Process all data sources
        self.process_main_project_files()
        self.process_ip_folder()
        self.process_we_folder()
        
        logger.info(f"✓ Total chunks created: {len(self.chunks)}")
        return self.chunks
    
    def save_corpus(self):
        """Save the RAG corpus to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as JSONL for RAG system
        jsonl_file = self.output_dir / f"sea_comprehensive_rag_chunks_{timestamp}.jsonl"
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            for chunk in self.chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        
        # Save as JSON for inspection
        json_file = self.output_dir / f"sea_comprehensive_rag_chunks_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)
        
        # Create summary
        summary = {
            "corpus_info": {
                "total_chunks": len(self.chunks),
                "created_at": datetime.now().isoformat(),
                "source": "SEA_project_comprehensive_extraction"
            },
            "chunk_types": {},
            "leed_categories": {},
            "file_types": {}
        }
        
        for chunk in self.chunks:
            chunk_type = chunk['metadata'].get('chunk_type', 'unknown')
            leed_cat = chunk['metadata'].get('leed_category', 'unknown')
            file_type = chunk['metadata'].get('file_type', 'unknown')
            
            summary["chunk_types"][chunk_type] = summary["chunk_types"].get(chunk_type, 0) + 1
            summary["leed_categories"][leed_cat] = summary["leed_categories"].get(leed_cat, 0) + 1
            summary["file_types"][file_type] = summary["file_types"].get(file_type, 0) + 1
        
        summary_file = self.output_dir / f"sea_rag_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ Saved corpus files:")
        logger.info(f"  → JSONL: {jsonl_file}")
        logger.info(f"  → JSON: {json_file}")
        logger.info(f"  → Summary: {summary_file}")
        
        return jsonl_file, json_file, summary_file

def main():
    """Main function to build SEA RAG corpus."""
    builder = SEARAGBuilder()
    
    # Build corpus
    chunks = builder.build_corpus()
    
    if not chunks:
        logger.error("No chunks created!")
        return
    
    # Save corpus
    jsonl_file, json_file, summary_file = builder.save_corpus()
    
    logger.info("🎉 SEA RAG corpus build complete!")
    logger.info(f"📊 Total chunks: {len(chunks)}")
    logger.info(f"📁 Output directory: {builder.output_dir}")

if __name__ == "__main__":
    main()

