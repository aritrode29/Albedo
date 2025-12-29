#!/usr/bin/env python3
"""
Enhanced LEED Chunking with Structured Metadata
Implements heading-based chunking with rich metadata for robust RAG retrieval.
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple


# Section mapping for standardized section names
SECTION_MAPPING = {
    'intent': 'intent',
    'requirements': 'requirements',
    'documentation': 'documentation',
    'submittals': 'documentation',
    'points': 'thresholds',
    'applicability': 'definitions',
    'equations': 'calc',
    'calculations': 'calc',
    'related': 'definitions',
    'exemplary': 'definitions',
    'referenced': 'definitions',
    'step_by_step': 'calc',
    'guidance': 'definitions',
}


def generate_credit_id(credit_code: Optional[str], credit_type: Optional[str], 
                       credit_name: Optional[str] = None) -> str:
    """
    Generate stable credit_id like EA-p2, EA-c1, etc.
    
    Args:
        credit_code: Credit code (e.g., "EA", "WE")
        credit_type: "Credit" or "Prerequisite"
        credit_name: Optional credit name to extract number from
    
    Returns:
        credit_id like "EA-p2" or "EA-c1"
    """
    if not credit_code:
        return "UNKNOWN"
    
    # Determine prefix: 'p' for prerequisite, 'c' for credit
    prefix = 'p' if credit_type and 'prerequisite' in credit_type.lower() else 'c'
    
    # Try to extract number from credit name (e.g., "EA Credit 2" -> "2")
    number = None
    if credit_name:
        # Look for patterns like "Credit 2", "Prerequisite 1", "Option 2", etc.
        match = re.search(r'(?:credit|prerequisite|option)\s+(\d+)', credit_name, re.I)
        if match:
            number = match.group(1)
    
    # If no number found, try to extract from credit_code if it has a number
    if not number and credit_code:
        match = re.search(r'(\d+)', credit_code)
        if match:
            number = match.group(1)
    
    # Fallback: use hash of credit_name for uniqueness if no number found
    if not number:
        if credit_name:
            # Use first 4 chars of hash as number
            hash_val = int(hashlib.md5(credit_name.encode()).hexdigest()[:4], 16)
            number = str((hash_val % 100) + 1)  # 1-100 range
        else:
            number = "1"
    
    return f"{credit_code}-{prefix}{number}"


def extract_rating_system(text: Optional[str], rating_system: Optional[str] = None) -> Optional[str]:
    """Extract rating system from text or use provided value."""
    if rating_system:
        return rating_system
    
    if not text:
        return None
    
    # Common patterns: BD+C, ID+C, O+M, ND, etc.
    patterns = [
        r'BD\+C',
        r'ID\+C',
        r'O\+M',
        r'ND',
        r'Core and Shell',
        r'New Construction',
        r'Existing Buildings',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(0)
    
    return None


def extract_project_types(text: Optional[str], applicability: Optional[List[str]] = None) -> List[str]:
    """Extract project types from text or applicability list."""
    project_types = []
    
    # Common project type abbreviations
    type_patterns = {
        'NC': r'\bNC\b|\bNew Construction\b',
        'CS': r'\bCS\b|\bCore and Shell\b',
        'Schools': r'\bSchools?\b',
        'Retail': r'\bRetail\b',
        'Healthcare': r'\bHealthcare\b',
        'Data Centers': r'\bData Centers?\b',
        'Warehouses': r'\bWarehouses?\b',
        'Hospitality': r'\bHospitality\b',
    }
    
    # Check applicability list first
    if applicability:
        for item in applicability:
            for ptype, pattern in type_patterns.items():
                if re.search(pattern, item, re.I):
                    if ptype not in project_types:
                        project_types.append(ptype)
    
    # Check text if provided
    if text:
        for ptype, pattern in type_patterns.items():
            if re.search(pattern, text, re.I):
                if ptype not in project_types:
                    project_types.append(ptype)
    
    return project_types if project_types else ['NC']  # Default to NC


def extract_version_effective_date(version: Optional[str], sources: Optional[Dict] = None) -> Optional[str]:
    """Extract version effective date from version string or sources."""
    if not version:
        return None
    
    # Try to extract date from version string (e.g., "v4.1 (2023-01-01)")
    date_match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', version)
    if date_match:
        return date_match.group(1)
    
    # Check sources metadata
    if sources and isinstance(sources, dict):
        if 'effective_date' in sources:
            return sources['effective_date']
        if 'version_date' in sources:
            return sources['version_date']
    
    return None


def determine_doc_type(credit_type: Optional[str], source_file: Optional[str] = None) -> str:
    """Determine document type from credit type and source file."""
    if credit_type:
        if 'prerequisite' in credit_type.lower():
            return 'prerequisite'
        elif 'credit' in credit_type.lower():
            return 'credit'
    
    if source_file:
        source_lower = source_file.lower()
        if 'form' in source_lower:
            return 'form'
        elif 'guide' in source_lower:
            return 'guide'
        elif 'faq' in source_lower:
            return 'faq'
        elif 'addenda' in source_lower or 'addendum' in source_lower:
            return 'addenda'
    
    return 'credit'  # Default


def get_pages_range(pages: List[int]) -> Tuple[Optional[int], Optional[int]]:
    """Get page_start and page_end from pages list."""
    if not pages:
        return None, None
    
    sorted_pages = sorted(set(pages))
    return sorted_pages[0], sorted_pages[-1]


def generate_stable_chunk_id(credit_id: str, section: str, section_index: int = 0) -> str:
    """Generate stable chunk_id for a chunk."""
    # Format: {credit_id}-{section}-{index}
    # e.g., "EA-p2-requirements-0", "EA-c1-documentation-0"
    return f"{credit_id}-{section}-{section_index}"


def to_enhanced_rag_chunks(credits: List[Any]) -> List[Dict[str, Any]]:
    """
    Create enhanced RAG chunks with heading-based splitting and structured metadata.
    
    Each section (Requirements, Documentation, Intent, etc.) becomes its own chunk.
    This prevents "random informative notes" from dominating search results.
    
    Args:
        credits: List of CreditRecord objects
    
    Returns:
        List of chunk dictionaries with enhanced metadata
    """
    chunks = []
    
    for credit in credits:
        # Extract base metadata
        credit_code = getattr(credit, 'credit_code', None) or credit.get('credit_code') if isinstance(credit, dict) else None
        credit_name = getattr(credit, 'credit_name', None) or credit.get('credit_name') if isinstance(credit, dict) else None
        credit_type = getattr(credit, 'credit_type', None) or credit.get('credit_type') if isinstance(credit, dict) else None
        category = getattr(credit, 'category', None) or credit.get('category') if isinstance(credit, dict) else None
        version = getattr(credit, 'version', 'v4.1') or credit.get('version', 'v4.1') if isinstance(credit, dict) else 'v4.1'
        rating_system = getattr(credit, 'rating_system', None) or credit.get('rating_system') if isinstance(credit, dict) else None
        sources = getattr(credit, 'sources', {}) or credit.get('sources', {}) if isinstance(credit, dict) else {}
        pages = sources.get('pages', []) if isinstance(sources, dict) else []
        
        # Generate credit_id
        credit_id = generate_credit_id(credit_code, credit_type, credit_name)
        
        # Extract additional metadata
        doc_type = determine_doc_type(credit_type)
        # Extract rating system from credit name or use existing
        rating_system = extract_rating_system(credit_name, rating_system)
        
        # Get applicability for project types
        applicability = getattr(credit, 'applicability', []) or credit.get('applicability', []) if isinstance(credit, dict) else []
        project_types = extract_project_types(None, applicability)
        
        # Extract version effective date
        version_effective_date = extract_version_effective_date(version, sources)
        
        # Get page range
        page_start, page_end = get_pages_range(pages)
        
        # Base metadata shared across all chunks for this credit
        base_metadata = {
            'doc_type': doc_type,
            'credit_id': credit_id,
            'credit_code': credit_code,
            'credit_name': credit_name,
            'version': version,
            'version_effective_date': version_effective_date,
            'rating_system': rating_system,
            'project_types': project_types,
            'page_start': page_start,
            'page_end': page_end,
        }
        
        # Section-based chunking: each section becomes its own chunk
        section_chunks = []
        
        # 1. Intent chunk
        intent = getattr(credit, 'intent', None) or credit.get('intent') if isinstance(credit, dict) else None
        if intent and intent.strip():
            section_chunks.append({
                'section': 'intent',
                'text': f"Intent: {intent}",
                'section_index': 0
            })
        
        # 2. Requirements chunk
        requirements = getattr(credit, 'requirements', []) or credit.get('requirements', []) if isinstance(credit, dict) else []
        if requirements:
            req_text = "Requirements:\n- " + "\n- ".join(requirements)
            section_chunks.append({
                'section': 'requirements',
                'text': req_text,
                'section_index': 0
            })
        
        # 3. Options chunks (each option is a separate chunk)
        options = getattr(credit, 'options', []) or credit.get('options', []) if isinstance(credit, dict) else []
        for idx, option in enumerate(options):
            if isinstance(option, dict):
                heading = option.get('heading', f'Option {idx + 1}')
                lines = option.get('lines', [])
            else:
                heading = getattr(option, 'heading', f'Option {idx + 1}')
                lines = getattr(option, 'lines', [])
            
            if lines:
                opt_text = f"{heading}\n- " + "\n- ".join(lines)
                section_chunks.append({
                    'section': 'requirements',  # Options are part of requirements
                    'text': opt_text,
                    'section_index': idx + 1
                })
        
        # 4. Documentation/Submittals chunk
        documentation = getattr(credit, 'documentation', []) or credit.get('documentation', []) if isinstance(credit, dict) else []
        if documentation:
            doc_text = "Documentation:\n- " + "\n- ".join(documentation)
            section_chunks.append({
                'section': 'documentation',
                'text': doc_text,
                'section_index': 0
            })
        
        # 5. Equations/Calculations chunk
        equations = getattr(credit, 'equations', []) or credit.get('equations', []) if isinstance(credit, dict) else []
        calc_methods = getattr(credit, 'calc_methods', []) or credit.get('calc_methods', []) if isinstance(credit, dict) else []
        if equations or calc_methods:
            calc_text = "Calculations:\n"
            if equations:
                calc_text += "\n".join(equations) + "\n"
            if calc_methods:
                calc_text += "\n".join(calc_methods)
            section_chunks.append({
                'section': 'calc',
                'text': calc_text.strip(),
                'section_index': 0
            })
        
        # 6. Applicability/Thresholds chunk
        if applicability:
            app_text = "Applicability:\n- " + "\n- ".join(applicability)
            section_chunks.append({
                'section': 'thresholds',
                'text': app_text,
                'section_index': 0
            })
        
        # 7. Points/Thresholds chunk
        points_min = getattr(credit, 'points_min', None) or credit.get('points_min') if isinstance(credit, dict) else None
        points_max = getattr(credit, 'points_max', None) or credit.get('points_max') if isinstance(credit, dict) else None
        if points_min is not None or points_max is not None:
            points_text = f"Points: {points_min}"
            if points_max and points_max != points_min:
                points_text += f" - {points_max}"
            section_chunks.append({
                'section': 'thresholds',
                'text': points_text,
                'section_index': 1 if applicability else 0
            })
        
        # 8. Related Credits chunk
        related_credits = getattr(credit, 'related_credits', []) or credit.get('related_credits', []) if isinstance(credit, dict) else []
        if related_credits:
            rel_text = "Related Credits:\n- " + "\n- ".join(related_credits)
            section_chunks.append({
                'section': 'definitions',
                'text': rel_text,
                'section_index': 0
            })
        
        # 9. Exemplary Performance chunk
        exemplary = getattr(credit, 'exemplary_performance', []) or credit.get('exemplary_performance', []) if isinstance(credit, dict) else []
        if exemplary:
            ex_text = "Exemplary Performance:\n- " + "\n- ".join(exemplary)
            section_chunks.append({
                'section': 'definitions',
                'text': ex_text,
                'section_index': 1 if related_credits else 0
            })
        
        # 10. Referenced Standards chunk
        referenced = getattr(credit, 'referenced_standards', []) or credit.get('referenced_standards', []) if isinstance(credit, dict) else []
        if referenced:
            ref_text = "Referenced Standards:\n- " + "\n- ".join(referenced)
            section_chunks.append({
                'section': 'definitions',
                'text': ref_text,
                'section_index': len([r for r in [related_credits, exemplary] if r])
            })
        
        # 11. Step-by-Step chunk
        step_by_step = getattr(credit, 'step_by_step', []) or credit.get('step_by_step', []) if isinstance(credit, dict) else []
        if step_by_step:
            step_text = "Step-by-Step:\n- " + "\n- ".join(step_by_step)
            section_chunks.append({
                'section': 'calc',
                'text': step_text,
                'section_index': 1 if (equations or calc_methods) else 0
            })
        
        # 12. Guidance chunk
        guidance = getattr(credit, 'guidance', []) or credit.get('guidance', []) if isinstance(credit, dict) else []
        if guidance:
            guid_text = "Guidance:\n- " + "\n- ".join(guidance)
            section_chunks.append({
                'section': 'definitions',
                'text': guid_text,
                'section_index': len([g for g in [related_credits, exemplary, referenced] if g])
            })
        
        # Create chunks with full metadata
        for section_chunk in section_chunks:
            # Map section to standardized section name
            section = SECTION_MAPPING.get(section_chunk['section'], section_chunk['section'])
            
            # Generate stable chunk_id
            chunk_id = generate_stable_chunk_id(credit_id, section, section_chunk['section_index'])
            
            # Build full text with credit header
            full_text = f"{credit_code} {credit_type}: {credit_name}\n\n{section_chunk['text']}"
            
            # Complete metadata
            chunk_metadata = base_metadata.copy()
            chunk_metadata.update({
                'section': section,
                'chunk_id': chunk_id,
                'category': category,
            })
            
            chunks.append({
                'text': full_text,
                'metadata': chunk_metadata
            })
    
    return chunks

