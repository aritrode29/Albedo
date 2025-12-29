#!/usr/bin/env python3
"""
Query Expansion for LEED-Specific Queries
Transforms vague queries into targeted LEED sub-queries.
"""

import re
from typing import List, Dict, Any, Optional
from collections import defaultdict


# LEED credit category mappings
CREDIT_CATEGORIES = {
    'energy': ['EA', 'ENERGY AND ATMOSPHERE'],
    'water': ['WE', 'WATER EFFICIENCY'],
    'materials': ['MR', 'MATERIALS AND RESOURCES'],
    'indoor': ['EQ', 'INDOOR ENVIRONMENTAL QUALITY'],
    'site': ['SS', 'SUSTAINABLE SITES'],
    'location': ['LT', 'LOCATION AND TRANSPORTATION'],
    'innovation': ['IN', 'INNOVATION'],
    'regional': ['RP', 'REGIONAL PRIORITY'],
}

# Common LEED terms and their expansions
TERM_EXPANSIONS = {
    'energy efficiency': [
        'EA Minimum Energy Performance',
        'EA Optimize Energy Performance',
        'energy performance prerequisite baseline ASHRAE',
        'dual metric energy performance greenhouse gas emissions',
    ],
    'energy': [
        'EA credit requirements',
        'energy performance ASHRAE 90.1',
        'energy efficiency optimization',
        'renewable energy credits',
    ],
    'water': [
        'WE water use reduction',
        'WE outdoor water use reduction',
        'WE indoor water use reduction',
        'water efficiency fixtures',
    ],
    'materials': [
        'MR building life-cycle impact reduction',
        'MR building product disclosure',
        'MR construction and demolition waste management',
        'MR environmental product declarations',
    ],
    'requirements': [
        'prerequisite requirements',
        'credit requirements',
        'documentation requirements',
        'compliance requirements',
    ],
    'efficiency': [
        'energy efficiency',
        'water efficiency',
        'resource efficiency',
        'operational efficiency',
    ],
}

# LEED version and rating system terms
RATING_SYSTEMS = ['BD+C', 'ID+C', 'O+M', 'ND', 'Core and Shell', 'New Construction']
VERSIONS = ['v4.1', 'v4', 'LEED v4.1', 'LEED v4']


def extract_keywords(query: str) -> Dict[str, List[str]]:
    """Extract keywords and their categories from query."""
    query_lower = query.lower()
    keywords = {
        'categories': [],
        'terms': [],
        'credit_codes': [],
        'has_requirements': False,
        'has_thresholds': False,
        'has_documentation': False,
    }
    
    # Check for credit categories
    for category, codes in CREDIT_CATEGORIES.items():
        if category in query_lower:
            keywords['categories'].extend(codes)
    
    # Check for credit codes (EA, WE, MR, etc.)
    credit_code_pattern = r'\b([A-Z]{1,2})\b'
    matches = re.findall(credit_code_pattern, query)
    for match in matches:
        if match in ['EA', 'WE', 'MR', 'EQ', 'SS', 'LT', 'IN', 'RP', 'IP']:
            keywords['credit_codes'].append(match)
    
    # Check for common terms
    for term, expansions in TERM_EXPANSIONS.items():
        if term in query_lower:
            keywords['terms'].append(term)
    
    # Check for section types
    if 'requirement' in query_lower or 'prerequisite' in query_lower:
        keywords['has_requirements'] = True
    if 'threshold' in query_lower or 'point' in query_lower or 'score' in query_lower:
        keywords['has_thresholds'] = True
    if 'documentation' in query_lower or 'submittal' in query_lower or 'evidence' in query_lower:
        keywords['has_documentation'] = True
    
    return keywords


def generate_credit_specific_queries(keywords: Dict[str, List[str]], base_query: str) -> List[str]:
    """Generate credit-specific queries based on extracted keywords."""
    queries = []
    
    # If credit codes found, create specific queries
    if keywords['credit_codes']:
        for code in keywords['credit_codes'][:3]:  # Limit to 3 codes
            if keywords['has_requirements']:
                queries.append(f"{code} prerequisite requirements LEED v4.1")
                queries.append(f"{code} credit requirements LEED v4.1")
            else:
                queries.append(f"{code} credit LEED v4.1 BD+C")
                if 'requirement' not in base_query.lower():
                    queries.append(f"{code} requirements thresholds")
    
    # If categories found, create category-specific queries
    elif keywords['categories']:
        for category_code in keywords['categories'][:2]:  # Limit to 2 categories
            if category_code in ['EA', 'ENERGY AND ATMOSPHERE']:
                queries.append("EA Minimum Energy Performance requirements LEED v4.1 BD+C")
                queries.append("EA Optimize Energy Performance requirements thresholds")
                queries.append("energy performance prerequisite baseline ASHRAE Appendix G")
            elif category_code in ['WE', 'WATER EFFICIENCY']:
                queries.append("WE water use reduction requirements LEED v4.1")
                queries.append("WE outdoor water use reduction thresholds")
            elif category_code in ['MR', 'MATERIALS AND RESOURCES']:
                queries.append("MR building product disclosure requirements")
                queries.append("MR construction waste management requirements")
    
    return queries


def generate_term_based_queries(keywords: Dict[str, List[str]], base_query: str) -> List[str]:
    """Generate queries based on extracted terms."""
    queries = []
    
    for term in keywords['terms'][:3]:  # Limit to 3 terms
        if term in TERM_EXPANSIONS:
            expansions = TERM_EXPANSIONS[term]
            # Take first 2 expansions
            for expansion in expansions[:2]:
                # Avoid duplicate "requirements" if expansion already contains it
                if keywords['has_requirements'] and 'requirement' not in expansion.lower():
                    queries.append(f"{expansion} requirements LEED v4.1")
                elif not keywords['has_requirements']:
                    queries.append(f"{expansion} LEED v4.1 BD+C")
    
    return queries


def generate_section_specific_queries(keywords: Dict[str, List[str]], base_query: str) -> List[str]:
    """Generate section-specific queries."""
    queries = []
    
    if keywords['has_requirements']:
        queries.append(f"{base_query} prerequisite requirements")
        queries.append(f"{base_query} credit requirements")
    if keywords['has_thresholds']:
        queries.append(f"{base_query} thresholds points")
    if keywords['has_documentation']:
        queries.append(f"{base_query} documentation submittals")
    
    return queries


def expand_query_rule_based(query: str, max_subqueries: int = 6) -> List[str]:
    """
    Expand a vague query into targeted LEED sub-queries using rule-based approach.
    
    Args:
        query: Original query string
        max_subqueries: Maximum number of sub-queries to generate
    
    Returns:
        List of expanded sub-queries
    """
    query = query.strip()
    if not query:
        return [query]
    
    # Extract keywords
    keywords = extract_keywords(query)
    
    # Generate different types of queries
    all_queries = []
    
    # 1. Credit-specific queries
    credit_queries = generate_credit_specific_queries(keywords, query)
    all_queries.extend(credit_queries)
    
    # 2. Term-based queries
    term_queries = generate_term_based_queries(keywords, query)
    all_queries.extend(term_queries)
    
    # 3. Section-specific queries
    section_queries = generate_section_specific_queries(keywords, query)
    all_queries.extend(section_queries)
    
    # 4. Add original query with LEED context if not already present
    if 'leed' not in query.lower():
        all_queries.append(f"{query} LEED v4.1 BD+C")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_queries = []
    for q in all_queries:
        q_normalized = q.lower().strip()
        if q_normalized not in seen:
            seen.add(q_normalized)
            unique_queries.append(q)
    
    # Limit to max_subqueries
    return unique_queries[:max_subqueries]


def expand_query_llm(query: str, max_subqueries: int = 6, llm_client: Optional[Any] = None) -> List[str]:
    """
    Expand query using LLM (optional, falls back to rule-based).
    
    Args:
        query: Original query string
        max_subqueries: Maximum number of sub-queries
        llm_client: Optional LLM client (OpenAI, etc.)
    
    Returns:
        List of expanded sub-queries
    """
    # If no LLM client, fall back to rule-based
    if llm_client is None:
        return expand_query_rule_based(query, max_subqueries)
    
    # TODO: Implement LLM-based expansion
    # For now, fall back to rule-based
    return expand_query_rule_based(query, max_subqueries)


def expand_query(query: str, max_subqueries: int = 6, use_llm: bool = False, llm_client: Optional[Any] = None) -> List[str]:
    """
    Main function to expand a query.
    
    Args:
        query: Original query string
        max_subqueries: Maximum number of sub-queries (default: 6)
        use_llm: Whether to use LLM expansion (default: False, uses rule-based)
        llm_client: Optional LLM client
    
    Returns:
        List of expanded sub-queries
    """
    if use_llm and llm_client:
        return expand_query_llm(query, max_subqueries, llm_client)
    else:
        return expand_query_rule_based(query, max_subqueries)

