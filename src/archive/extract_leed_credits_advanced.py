#!/usr/bin/env python3
"""
LEED v4.1 BD+C Advanced Credit Extractor
Enhanced version with improved parsing, validation, and output options

Features:
- Advanced PDF parsing with multiple fallback methods
- Credit validation and quality scoring
- Multiple output formats (JSON, CSV, Excel)
- Credit relationship mapping
- Statistical analysis and reporting
- Configurable parsing parameters
"""

import os, re, json, argparse, itertools
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
import logging
from datetime import datetime

import pdfplumber
import pandas as pd

# Optional OCR fallback
try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# Alternative OCR using PyMuPDF (if pdf2image fails)
try:
    import fitz  # PyMuPDF
    ALTERNATIVE_OCR_AVAILABLE = True
except Exception:
    ALTERNATIVE_OCR_AVAILABLE = False

# For Windows, try to find Poppler in common installation paths
import os
POPPLER_PATHS = [
    r"C:\Program Files\poppler-24.08.0\Library\bin",
    r"C:\Program Files (x86)\poppler-24.08.0\Library\bin",
    os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_*\bin"),
]

# Try to set Poppler path if found
for path in POPPLER_PATHS:
    if os.path.exists(path):
        os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")
        break

# If pdf2image OCR fails, we can still use PyMuPDF for basic text extraction
if not OCR_AVAILABLE and ALTERNATIVE_OCR_AVAILABLE:
    print("Note: Using PyMuPDF as fallback for text extraction")

# -------------------------
# Enhanced Patterns & schema
# -------------------------

CATEGORY_TITLES = [
    "LOCATION AND TRANSPORTATION (LT)",
    "INTEGRATIVE PROCESS (IP)",
    "SUSTAINABLE SITES (SS)",
    "WATER EFFICIENCY (WE)",
    "ENERGY AND ATMOSPHERE (EA)",
    "MATERIALS AND RESOURCES (MR)",
    "INDOOR ENVIRONMENTAL QUALITY (EQ)",
    "INNOVATION (IN)",
    "REGIONAL PRIORITY (RP)",
    "APPENDICES"
]

CATEGORY_PATTERNS = [
    re.compile(r'^LOCATION AND TRANSPORTATION\s*\(LT\)$', re.I),
    re.compile(r'^INTEGRATIVE PROCESS\s*\(IP\)$', re.I),
    re.compile(r'^SUSTAINABLE SITES\s*\(SS\)$', re.I),
    re.compile(r'^WATER EFFICIENCY\s*\(WE\)$', re.I),
    re.compile(r'^ENERGY AND ATMOSPHERE\s*\(EA\)$', re.I),
    re.compile(r'^MATERIALS AND RESOURCES\s*\(MR\)$', re.I),
    re.compile(r'^INDOOR ENVIRONMENTAL QUALITY\s*\(EQ\)$', re.I),
    re.compile(r'^INNOVATION\s*\(IN\)$', re.I),
    re.compile(r'^REGIONAL PRIORITY\s*\(RP\)$', re.I),
    re.compile(r'^APPENDICES$', re.I),
]

# Enhanced credit patterns
CREDIT_PATTERNS = [
    re.compile(r'^(LT|IP|SS|WE|EA|MR|EQ|IN|RP)\s+(Credit|Prerequisite)\s*:?\s*(.+)$', re.I),
    re.compile(r'^(Credit|Prerequisite)\s*:?\s*(.+)$', re.I),
    re.compile(r'^([A-Z]{2})\s*([0-9]+)\s*(Credit|Prerequisite)\s*:?\s*(.+)$', re.I),  # EA1 Credit: etc.
]

POINTS_PATTERN = re.compile(r'^(\d+)(\s*-\s*(\d+))?\s*points?$', re.I)
RATINGSYSTEM_PATTERN = re.compile(r'^(BD\+C.*|ID\+C.*|O\+M.*|ND.*)$', re.I)
BULLET_PATTERN = re.compile(r'^[\-\u2022•]\s*(.*)')
OPTION_HEADER = re.compile(r'^(Option\s*\d+\.|OR|AND)$', re.I)

# Enhanced section patterns
SECTION_PATTERNS = {
    'intent': re.compile(r'^Intent:?$', re.I),
    'requirements': re.compile(r'^Requirements?:?$', re.I),
    'documentation': re.compile(r'^(Documentation|Submittals?):?$', re.I),
    'points': re.compile(r'^Points:?$', re.I),
    'applicability': re.compile(r'^(Applicable Rating System|This credit applies to)', re.I),
    'equations': re.compile(r'^(Equations?|Calculation[s]?)[:]?$', re.I),
    'related': re.compile(r'^(Related Credits|Cross-References)[:]?$', re.I),
    'exemplary': re.compile(r'^(Exemplary Performance)[:]?$', re.I),
    'referenced': re.compile(r'^(Referenced Standards|References)[:]?$', re.I),
    'step_by_step': re.compile(r'^(Step-by-Step|Implementation)[:]?$', re.I),
    'guidance': re.compile(r'^(Guidance|Tips|Best Practices)[:]?$', re.I),
}

CLEAN_LINE = re.compile(r'\s+')

# -------------------------
# Enhanced Data Structures
# -------------------------

@dataclass
class OptionBlock:
    heading: str
    lines: List[str] = field(default_factory=list)
    points: Optional[int] = None

@dataclass
class CreditRecord:
    category: Optional[str] = None
    credit_code: Optional[str] = None
    credit_name: Optional[str] = None
    credit_type: Optional[str] = None
    version: str = "v4.1"
    rating_system: Optional[str] = None
    intent: str = ""
    requirements: List[str] = field(default_factory=list)
    options: List[OptionBlock] = field(default_factory=list)
    documentation: List[str] = field(default_factory=list)
    points_raw: Optional[str] = None
    points_min: Optional[int] = None
    points_max: Optional[int] = None
    applicability: List[str] = field(default_factory=list)
    equations: List[str] = field(default_factory=list)
    calc_methods: List[str] = field(default_factory=list)
    related_credits: List[str] = field(default_factory=list)
    exemplary_performance: List[str] = field(default_factory=list)
    referenced_standards: List[str] = field(default_factory=list)
    step_by_step: List[str] = field(default_factory=list)
    guidance: List[str] = field(default_factory=list)
    tables: List[Any] = field(default_factory=list)
    figures: List[Dict[str, Any]] = field(default_factory=list)
    sources: Dict[str, Any] = field(default_factory=lambda: {"pages": []})
    rating_systems_applicable: List[str] = field(default_factory=list)
    
    # Quality metrics
    completeness_score: float = 0.0
    validation_errors: List[str] = field(default_factory=list)
    extraction_confidence: float = 0.0

@dataclass
class ExtractionStats:
    total_credits: int = 0
    prerequisites: int = 0
    credits: int = 0
    total_points: int = 0
    categories: Dict[str, int] = field(default_factory=dict)
    quality_scores: List[float] = field(default_factory=list)
    extraction_time: float = 0.0
    errors: List[str] = field(default_factory=list)

# -------------------------
# Enhanced Utilities
# -------------------------

def setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup logging configuration"""
    logger = logging.getLogger("leed_extractor")
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def clean(s: str) -> str:
    """Enhanced text cleaning"""
    if not s:
        return ""
    return CLEAN_LINE.sub(' ', s).strip()

def parse_points(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Enhanced points parsing"""
    m = POINTS_PATTERN.match(text)
    if not m:
        return None, None
    lo = int(m.group(1))
    hi = int(m.group(3)) if m.group(3) else lo
    return lo, hi

def ocr_page_image(image: "Image.Image") -> List[str]:
    """Enhanced OCR with better configuration"""
    if not OCR_AVAILABLE:
        return []
    
    # Configure OCR for better accuracy
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789\s\-\(\)\.\,\:\;\!\?'
    txt = pytesseract.image_to_string(image, config=custom_config)
    lines = [clean(x) for x in txt.splitlines()]
    return [x for x in lines if x]

def extract_text_lines(pdf_path: str, logger: logging.Logger) -> List[Tuple[int, List[str]]]:
    """
    Enhanced text extraction with multiple fallback methods
    """
    out: List[Tuple[int, List[str]]] = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            blank_like = set()
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                lines = [clean(x) for x in text.splitlines() if clean(x)]
                if not lines or len(' '.join(lines)) < 15:
                    blank_like.add(i)
                out.append((i, lines))

        # Try OCR if available
        if OCR_AVAILABLE and blank_like:
            try:
                images = convert_from_path(pdf_path, dpi=600)
                for i in blank_like:
                    out[i] = (i, ocr_page_image(images[i]))
                logger.info(f"Applied OCR to {len(blank_like)} pages")
            except Exception as e:
                logger.warning(f"OCR failed: {e}")
                # Fall back to PyMuPDF if available
                if ALTERNATIVE_OCR_AVAILABLE:
                    logger.info("Using PyMuPDF fallback for problematic pages")
                    doc = fitz.open(pdf_path)
                    for i in blank_like:
                        if i < len(doc):
                            page = doc[i]
                            text = page.get_text()
                            lines = [clean(x) for x in text.splitlines() if clean(x)]
                            out[i] = (i, lines)
                    doc.close()
    
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        raise
    
    return out

def extract_all_text(pdf_path: str, logger: logging.Logger) -> str:
    """Extract all visible text from the PDF (best-effort, page order)."""
    texts: List[str] = []
    try:
        # First pass: pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt.strip():
                    texts.append(txt)
        # If entirely empty, try PyMuPDF
        if not any(t.strip() for t in texts) and ALTERNATIVE_OCR_AVAILABLE:
            doc = fitz.open(pdf_path)
            for p in doc:
                txt = p.get_text() or ""
                if txt.strip():
                    texts.append(txt)
            doc.close()
    except Exception as e:
        logger.warning(f"Full-text extraction fallback due to error: {e}")
        if ALTERNATIVE_OCR_AVAILABLE:
            try:
                doc = fitz.open(pdf_path)
                for p in doc:
                    txt = p.get_text() or ""
                    if txt.strip():
                        texts.append(txt)
                doc.close()
            except Exception as e2:
                logger.error(f"PyMuPDF full-text extraction failed: {e2}")
    return "\n\n".join(texts)

def extract_annotations(pdf_path: str, logger: logging.Logger) -> List[Dict[str, Any]]:
    """Extract PDF comments/annotations if present (using PyMuPDF)."""
    annotations: List[Dict[str, Any]] = []
    if not ALTERNATIVE_OCR_AVAILABLE:
        return annotations
    try:
        doc = fitz.open(pdf_path)
        for page_index, page in enumerate(doc):
            try:
                for annot in page.annots() or []:
                    try:
                        info = annot.info or {}
                    except Exception:
                        info = {}
                    annotations.append({
                        "page": page_index + 1,
                        "type": getattr(annot, 'type', str(annot)),
                        "content": info.get('content') or info.get('subject') or "",
                        "author": info.get('title') or info.get('name') or "",
                        "rect": list(annot.rect) if getattr(annot, 'rect', None) else None
                    })
            except Exception:
                # Some pages may not support .annots()
                continue
        doc.close()
    except Exception as e:
        logger.warning(f"Annotation extraction failed: {e}")
    return annotations

def calculate_completeness_score(credit: CreditRecord) -> float:
    """Calculate completeness score for a credit"""
    score = 0.0
    total_fields = 8
    
    if credit.credit_name:
        score += 1
    if credit.credit_code:
        score += 1
    if credit.category:
        score += 1
    if credit.intent:
        score += 1
    if credit.requirements:
        score += 1
    if credit.documentation:
        score += 1
    if credit.points_min is not None:
        score += 1
    if credit.related_credits:
        score += 1
    
    return score / total_fields

def validate_credit(credit: CreditRecord) -> List[str]:
    """Validate credit data and return errors"""
    errors = []
    
    if not credit.credit_name:
        errors.append("Missing credit name")
    
    if not credit.credit_code and credit.category:
        errors.append("Missing credit code")
    
    if credit.points_min and credit.points_max and credit.points_min > credit.points_max:
        errors.append("Invalid points range")
    
    if credit.credit_type not in ['Credit', 'Prerequisite']:
        errors.append("Invalid credit type")
    
    return errors

# -------------------------
# Enhanced Parser
# -------------------------

def parse_pdf(pdf_path: str, logger: logging.Logger) -> Tuple[List[CreditRecord], ExtractionStats]:
    """Enhanced PDF parsing with statistics and validation"""
    start_time = datetime.now()
    
    pages = extract_text_lines(pdf_path, logger)
    credits: List[CreditRecord] = []
    current_category = None
    current: Optional[CreditRecord] = None
    current_section = None
    req_buffer: List[str] = []
    opt_buffer: Optional[OptionBlock] = None
    intent_buffer: List[str] = []
    step_buffer: List[str] = []
    guidance_buffer: List[str] = []

    for page_idx, lines in pages:
        for raw in lines:
            line = raw.strip()

            # Category detection
            for idx, pat in enumerate(CATEGORY_PATTERNS):
                if pat.match(line):
                    current_category = CATEGORY_TITLES[idx]
                    break

            # Credit header detection
            matched_credit = False
            for pat in CREDIT_PATTERNS:
                m = pat.match(line)
                if m:
                    matched_credit = True

                    # Finalize prior record
                    if current:
                        if intent_buffer:
                            current.intent = clean(' '.join(intent_buffer))
                            intent_buffer = []
                        if req_buffer:
                            current.requirements.extend(req_buffer)
                            req_buffer = []
                        if opt_buffer:
                            current.options.append(opt_buffer)
                            opt_buffer = None
                        if step_buffer:
                            current.step_by_step.extend(step_buffer)
                            step_buffer = []
                        if guidance_buffer:
                            current.guidance.extend(guidance_buffer)
                            guidance_buffer = []
                        
                        # Calculate quality metrics
                        current.completeness_score = calculate_completeness_score(current)
                        current.validation_errors = validate_credit(current)
                        credits.append(current)

                    # Create new record
                    if len(m.groups()) == 3:
                        code, ctype, name = m.groups()
                        credit_code = code.upper()
                    else:
                        ctype, name = m.groups()
                        credit_code = (current_category.split('(')[-1].split(')')[0]
                                       if current_category and '(' in current_category else None)

                    current = CreditRecord(
                        category=current_category,
                        credit_code=credit_code,
                        credit_name=clean(name),
                        credit_type="Prerequisite" if re.search(r'Prerequisite', ctype, re.I) else "Credit",
                    )
                    current.sources["pages"].append(page_idx + 1)
                    current_section = None
                    intent_buffer = []
                    req_buffer = []
                    opt_buffer = None
                    step_buffer = []
                    guidance_buffer = []
                    break
            
            if matched_credit:
                continue

            if not current:
                continue

            # Points & rating systems
            if POINTS_PATTERN.match(line):
                current.points_raw = line
                lo, hi = parse_points(line)
                current.points_min, current.points_max = lo, hi
                continue

            if RATINGSYSTEM_PATTERN.match(line):
                current.rating_system = line
                continue

            # Section headers
            switched = False
            for sec_name, sec_pat in SECTION_PATTERNS.items():
                if sec_pat.match(line):
                    # Flush buffers from previous section
                    if current_section == 'requirements' and req_buffer:
                        current.requirements.extend(req_buffer)
                        req_buffer = []
                    if current_section == 'intent' and intent_buffer:
                        current.intent = clean(' '.join(intent_buffer))
                        intent_buffer = []
                    if current_section == 'options' and opt_buffer:
                        current.options.append(opt_buffer)
                        opt_buffer = None
                    if current_section == 'step_by_step' and step_buffer:
                        current.step_by_step.extend(step_buffer)
                        step_buffer = []
                    if current_section == 'guidance' and guidance_buffer:
                        current.guidance.extend(guidance_buffer)
                        guidance_buffer = []
                    
                    current_section = sec_name
                    switched = True
                    break
            
            if switched:
                continue

            # Content processing based on current section
            if current_section == 'applicability':
                mb = BULLET_PATTERN.match(line)
                if mb:
                    current.applicability.append(mb.group(1))
                    continue

            if current_section == 'documentation':
                mb = BULLET_PATTERN.match(line)
                current.documentation.append(mb.group(1) if mb else line)
                continue

            if current_section == 'related':
                current.related_credits.append(line)
                continue

            if current_section == 'exemplary':
                current.exemplary_performance.append(line)
                continue

            if current_section == 'referenced':
                current.referenced_standards.append(line)
                continue

            if current_section == 'equations':
                current.equations.append(line)
                continue

            if current_section == 'intent':
                intent_buffer.append(line)
                continue

            if current_section == 'step_by_step':
                step_buffer.append(line)
                continue

            if current_section == 'guidance':
                guidance_buffer.append(line)
                continue

            if current_section == 'requirements':
                if OPTION_HEADER.match(line):
                    if opt_buffer:
                        current.options.append(opt_buffer)
                    opt_buffer = OptionBlock(heading=line, lines=[])
                else:
                    mb = BULLET_PATTERN.match(line)
                    text = mb.group(1) if mb else line
                    if opt_buffer:
                        opt_buffer.lines.append(text)
                    else:
                        req_buffer.append(text)
                continue

        # Per page end: attach page number for provenance
        if current and current.sources["pages"] and current.sources["pages"][-1] != (page_idx + 1):
            current.sources["pages"].append(page_idx + 1)

    # Finalize last record
    if current:
        if intent_buffer:
            current.intent = clean(' '.join(intent_buffer))
        if req_buffer:
            current.requirements.extend(req_buffer)
        if opt_buffer:
            current.options.append(opt_buffer)
        if step_buffer:
            current.step_by_step.extend(step_buffer)
        if guidance_buffer:
            current.guidance.extend(guidance_buffer)
        
        current.completeness_score = calculate_completeness_score(current)
        current.validation_errors = validate_credit(current)
        credits.append(current)

    # Calculate statistics
    stats = ExtractionStats()
    stats.total_credits = len(credits)
    stats.extraction_time = (datetime.now() - start_time).total_seconds()
    
    for credit in credits:
        if credit.credit_type == 'Prerequisite':
            stats.prerequisites += 1
        else:
            stats.credits += 1
            if credit.points_max:
                stats.total_points += credit.points_max
        
        if credit.category:
            stats.categories[credit.category] = stats.categories.get(credit.category, 0) + 1
        
        stats.quality_scores.append(credit.completeness_score)
        
        if credit.validation_errors:
            stats.errors.extend(credit.validation_errors)

    return credits, stats

# -------------------------
# Enhanced Output Functions
# -------------------------

def to_rag_chunks(credits: List[CreditRecord]) -> List[Dict[str, Any]]:
    """Enhanced RAG-ready chunking with more metadata"""
    chunks = []
    for c in credits:
        meta = {
            "credit_code": c.credit_code,
            "credit_name": c.credit_name,
            "category": c.category,
            "type": c.credit_type,
            "points_min": c.points_min,
            "points_max": c.points_max,
            "version": c.version,
            "pages": c.sources.get("pages", []),
            "completeness_score": c.completeness_score,
            "validation_errors": c.validation_errors,
            "extraction_confidence": c.extraction_confidence
        }
        
        text_blocks = []

        if c.intent:
            text_blocks.append(f"Intent: {c.intent}")
        if c.requirements:
            text_blocks.append("Requirements:\n- " + "\n- ".join(c.requirements))
        for op in c.options:
            text_blocks.append(op.heading + "\n- " + "\n- ".join(op.lines))
        if c.documentation:
            text_blocks.append("Submittals:\n- " + "\n- ".join(c.documentation))
        if c.applicability:
            text_blocks.append("Applicability:\n- " + "\n- ".join(c.applicability))
        if c.equations:
            text_blocks.append("Equations:\n" + "\n".join(c.equations))
        if c.related_credits:
            text_blocks.append("Related Credits:\n- " + "\n- ".join(c.related_credits))
        if c.exemplary_performance:
            text_blocks.append("Exemplary Performance:\n- " + "\n- ".join(c.exemplary_performance))
        if c.referenced_standards:
            text_blocks.append("Referenced Standards:\n- " + "\n- ".join(c.referenced_standards))
        if c.step_by_step:
            text_blocks.append("Step-by-Step:\n- " + "\n- ".join(c.step_by_step))
        if c.guidance:
            text_blocks.append("Guidance:\n- " + "\n- ".join(c.guidance))

        full_text = f"{c.credit_code} {c.credit_type}: {c.credit_name}\n" + "\n\n".join(text_blocks)
        chunks.append({"text": full_text, "metadata": meta})
    
    return chunks

def to_csv(credits: List[CreditRecord], output_path: str):
    """Export credits to CSV format"""
    data = []
    for credit in credits:
        row = {
            'credit_code': credit.credit_code,
            'credit_name': credit.credit_name,
            'category': credit.category,
            'credit_type': credit.credit_type,
            'points_min': credit.points_min,
            'points_max': credit.points_max,
            'intent': credit.intent,
            'requirements_count': len(credit.requirements),
            'documentation_count': len(credit.documentation),
            'completeness_score': credit.completeness_score,
            'validation_errors': '; '.join(credit.validation_errors),
            'pages': ', '.join(map(str, credit.sources.get("pages", [])))
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)

def to_excel(credits: List[CreditRecord], output_path: str):
    """Export credits to Excel format with multiple sheets"""
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Main credits sheet
        data = []
        for credit in credits:
            row = {
                'credit_code': credit.credit_code,
                'credit_name': credit.credit_name,
                'category': credit.category,
                'credit_type': credit.credit_type,
                'points_min': credit.points_min,
                'points_max': credit.points_max,
                'intent': credit.intent,
                'completeness_score': credit.completeness_score
            }
            data.append(row)
        
        df_main = pd.DataFrame(data)
        df_main.to_excel(writer, sheet_name='Credits', index=False)
        
        # Requirements sheet
        req_data = []
        for credit in credits:
            for i, req in enumerate(credit.requirements):
                req_data.append({
                    'credit_code': credit.credit_code,
                    'credit_name': credit.credit_name,
                    'requirement_number': i + 1,
                    'requirement_text': req
                })
        
        if req_data:
            df_req = pd.DataFrame(req_data)
            df_req.to_excel(writer, sheet_name='Requirements', index=False)
        
        # Statistics sheet
        stats_data = {
            'Metric': ['Total Credits', 'Prerequisites', 'Credits', 'Total Points', 'Average Completeness'],
            'Value': [
                len(credits),
                len([c for c in credits if c.credit_type == 'Prerequisite']),
                len([c for c in credits if c.credit_type == 'Credit']),
                sum(c.points_max or 0 for c in credits),
                sum(c.completeness_score for c in credits) / len(credits) if credits else 0
            ]
        }
        df_stats = pd.DataFrame(stats_data)
        df_stats.to_excel(writer, sheet_name='Statistics', index=False)

# -------------------------
# Main Orchestrator
# -------------------------

def run_extraction(pdf_path: str, output_dir: str, logger: logging.Logger) -> None:
    """Enhanced main extraction function with multiple outputs"""
    logger.info(f"Starting extraction from: {pdf_path}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Extract credits
    credits, stats = parse_pdf(pdf_path, logger)
    
    if not credits:
        logger.error("No credits extracted!")
        return
    
    # Generate outputs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON output
    json_path = output_path / f"leed_credits_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in credits], f, ensure_ascii=False, indent=2)
    
    # RAG chunks
    chunks = to_rag_chunks(credits)
    chunks_path = output_path / f"leed_rag_chunks_{timestamp}.jsonl"
    with open(chunks_path, "w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")
    
    # CSV output
    csv_path = output_path / f"leed_credits_{timestamp}.csv"
    to_csv(credits, str(csv_path))
    
    # Excel output
    excel_path = output_path / f"leed_credits_{timestamp}.xlsx"
    to_excel(credits, str(excel_path))

    # Full-text dump
    full_text = extract_all_text(pdf_path, logger)
    full_text_path = output_path / f"full_text_{timestamp}.txt"
    try:
        with open(full_text_path, "w", encoding="utf-8") as f:
            f.write(full_text)
    except Exception as e:
        logger.warning(f"Failed to write full text: {e}")

    # PDF annotations/comments (if any)
    annotations = extract_annotations(pdf_path, logger)
    if annotations:
        annot_path = output_path / f"annotations_{timestamp}.json"
        try:
            with open(annot_path, "w", encoding="utf-8") as f:
                json.dump(annotations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write annotations: {e}")
    
    # Print summary
    logger.info(f"✓ Extracted {stats.total_credits} credits in {stats.extraction_time:.2f}s")
    logger.info(f"✓ Prerequisites: {stats.prerequisites}, Credits: {stats.credits}")
    logger.info(f"✓ Total points: {stats.total_points}")
    logger.info(f"✓ Average completeness: {sum(stats.quality_scores)/len(stats.quality_scores):.2f}")
    logger.info(f"✓ Validation errors: {len(stats.errors)}")
    
    logger.info(f"→ JSON: {json_path}")
    logger.info(f"→ RAG chunks: {chunks_path}")
    logger.info(f"→ CSV: {csv_path}")
    logger.info(f"→ Excel: {excel_path}")
    logger.info(f"→ Full text: {full_text_path}")
    if annotations:
        logger.info(f"→ Annotations: {annot_path}")

def main():
    ap = argparse.ArgumentParser(description="Enhanced LEED v4.1 BD+C Credit Extractor")
    ap.add_argument("--pdf", required=True, help="Path to LEED PDF")
    ap.add_argument("--output_dir", default="outputs", help="Output directory")
    ap.add_argument("--log_level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                   help="Logging level")
    args = ap.parse_args()
    
    logger = setup_logging(args.log_level)
    run_extraction(args.pdf, args.output_dir, logger)

if __name__ == "__main__":
    main()
