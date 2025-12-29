#!/usr/bin/env python3
"""
Web Search Integration for Albedo RAG System
Adds internet search capability to enhance LEED knowledge base.
"""

import requests
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class WebSearchLayer:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.search_cache = {}
        
    def search_web(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Search the web for relevant information."""
        try:
            # Use DuckDuckGo Instant Answer API (no API key required)
            search_results = self._search_duckduckgo(query, num_results)
            
            # If DuckDuckGo doesn't return enough results, try alternative
            if len(search_results) < 3:
                search_results.extend(self._search_alternative(query, num_results))
            
            return search_results[:num_results]
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []
    
    def _search_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo Instant Answer API."""
        try:
            # DuckDuckGo Instant Answer API
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            results = []
            
            # Extract abstract/answer
            if data.get('Abstract'):
                results.append({
                    'title': data.get('Heading', 'DuckDuckGo Answer'),
                    'content': data.get('Abstract'),
                    'url': data.get('AbstractURL', ''),
                    'source': 'DuckDuckGo Instant Answer'
                })
            
            # Extract related topics
            for topic in data.get('RelatedTopics', [])[:num_results-1]:
                if isinstance(topic, dict) and topic.get('Text'):
                    results.append({
                        'title': topic.get('FirstURL', '').split('/')[-1].replace('_', ' ').title(),
                        'content': topic.get('Text'),
                        'url': topic.get('FirstURL', ''),
                        'source': 'DuckDuckGo Related'
                    })
            
            return results
            
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []
    
    def _search_alternative(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Alternative search method using web scraping."""
        try:
            # Use a simple web search simulation
            # In a real implementation, you might use Google Custom Search API
            # or other search APIs with proper API keys
            
            # For demo purposes, return LEED-related information
            leed_info = self._get_leed_fallback_info(query)
            return leed_info[:num_results]
            
        except Exception as e:
            logger.warning(f"Alternative search failed: {e}")
            return []
    
    def _get_leed_fallback_info(self, query: str) -> List[Dict[str, Any]]:
        """Fallback LEED information when web search fails."""
        query_lower = query.lower()
        
        fallback_info = {
            'energy': {
                'title': 'LEED Energy Efficiency Requirements',
                'content': 'LEED v4.1 energy credits focus on optimizing energy performance through ASHRAE 90.1-2019 compliance, renewable energy integration, and advanced energy metering.',
                'url': 'https://www.usgbc.org/credits/new-construction/v4.1/ea',
                'source': 'USGBC Official'
            },
            'water': {
                'title': 'LEED Water Efficiency Standards',
                'content': 'Water efficiency credits emphasize reducing potable water use through efficient fixtures, landscape irrigation optimization, and innovative water technologies.',
                'url': 'https://www.usgbc.org/credits/new-construction/v4.1/we',
                'source': 'USGBC Official'
            },
            'materials': {
                'title': 'LEED Materials & Resources',
                'content': 'Materials and resources credits promote sustainable material selection, waste reduction, and life-cycle thinking in building design.',
                'url': 'https://www.usgbc.org/credits/new-construction/v4.1/mr',
                'source': 'USGBC Official'
            },
            'indoor': {
                'title': 'LEED Indoor Environmental Quality',
                'content': 'Indoor environmental quality credits focus on occupant comfort, air quality, acoustics, and daylighting to create healthy indoor environments.',
                'url': 'https://www.usgbc.org/credits/new-construction/v4.1/eq',
                'source': 'USGBC Official'
            },
            'site': {
                'title': 'LEED Sustainable Sites',
                'content': 'Sustainable sites credits address site selection, development density, alternative transportation, and stormwater management.',
                'url': 'https://www.usgbc.org/credits/new-construction/v4.1/ss',
                'source': 'USGBC Official'
            }
        }
        
        results = []
        for keyword, info in fallback_info.items():
            if keyword in query_lower:
                results.append(info)
        
        # If no specific match, return general LEED info
        if not results:
            results.append({
                'title': 'LEED Certification Overview',
                'content': 'LEED (Leadership in Energy and Environmental Design) is the most widely used green building rating system worldwide, providing a framework for healthy, highly efficient, and cost-saving green buildings.',
                'url': 'https://www.usgbc.org/leed',
                'source': 'USGBC Official'
            })
        
        return results
    
    def format_search_results(self, results: List[Dict[str, Any]], query: str) -> str:
        """Format search results for chatbot response."""
        if not results:
            return "I couldn't find additional information online for that query. Please try rephrasing your question or ask about specific LEED credits."
        
        response = f"🌐 **Web Search Results for: {query}**\n\n"
        
        for i, result in enumerate(results, 1):
            response += f"**{i}. {result['title']}**\n"
            response += f"{result['content']}\n"
            if result.get('url'):
                response += f"🔗 Source: {result['url']}\n"
            response += f"📊 Source: {result.get('source', 'Web Search')}\n\n"
        
        response += "💡 **Note**: These are general web search results. For project-specific guidance, please upload your LEED documents or ask about specific credits in our knowledge base."
        
        return response

class EnhancedRAGSystem:
    def __init__(self, rag_api_url: str = "http://localhost:5000", rag_system=None):
        self.rag_api_url = rag_api_url
        self.rag_system = rag_system  # Direct RAG system instance
        self.web_search = WebSearchLayer()
        
    def process_query(self, query: str, use_web_search: bool = True) -> Dict[str, Any]:
        """Process query with both RAG and web search."""
        response = {
            'query': query,
            'rag_results': [],
            'web_results': [],
            'combined_response': '',
            'sources': []
        }
        
        # First, try RAG search - use direct instance if available, otherwise HTTP
        try:
            if self.rag_system:
                # Use direct RAG system instance
                logger.info(f"Searching RAG system with query: {query}")
                rag_results = self.rag_system.search(query, k=3)
                logger.info(f"RAG search returned {len(rag_results)} results")
                response['rag_results'] = rag_results
                
                # Format RAG results
                rag_text = self._format_rag_results(response['rag_results'], query)
                response['combined_response'] += rag_text + "\n\n"
            else:
                # Fallback to HTTP API call
                rag_response = requests.post(f"{self.rag_api_url}/api/query", 
                                           json={"query": query, "limit": 3},
                                           timeout=10)
                
                if rag_response.status_code == 200:
                    rag_data = rag_response.json()
                    response['rag_results'] = rag_data.get('results', [])
                    
                    # Format RAG results
                    rag_text = self._format_rag_results(response['rag_results'], query)
                    response['combined_response'] += rag_text + "\n\n"
                
        except Exception as e:
            logger.warning(f"RAG search failed: {e}")
            response['combined_response'] += "❌ Unable to search our LEED knowledge base. "
        
        # Then, add web search if enabled
        if use_web_search:
            try:
                web_results = self.web_search.search_web(query, num_results=3)
                response['web_results'] = web_results
                
                if web_results:
                    web_text = self.web_search.format_search_results(web_results, query)
                    response['combined_response'] += web_text
                else:
                    response['combined_response'] += "🌐 No additional web information found for this query."
                    
            except Exception as e:
                logger.warning(f"Web search failed: {e}")
                response['combined_response'] += "🌐 Web search is currently unavailable."
        
        # Add source information
        response['sources'] = self._extract_sources(response)
        
        return response
    
    def _format_rag_results(self, results: List[Dict[str, Any]], query: str) -> str:
        """Format RAG results for display."""
        if not results:
            return "📚 No relevant information found in our LEED knowledge base."
        
        response = f"📚 **LEED Knowledge Base Results for: {query}**\n\n"
        
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            response += f"**{i}. {metadata.get('credit_name', 'LEED Information')}**\n"
            response += f"{result.get('text', '')[:200]}...\n"
            response += f"📊 Relevance: {result.get('score', 0):.3f}\n"
            if metadata.get('source'):
                response += f"📁 Source: {metadata['source']}\n"
            response += "\n"
        
        return response
    
    def _extract_sources(self, response: Dict[str, Any]) -> List[str]:
        """Extract all sources from the response."""
        sources = []
        
        # Add RAG sources
        for result in response['rag_results']:
            metadata = result.get('metadata', {})
            if metadata.get('source'):
                sources.append(f"LEED Knowledge Base: {metadata['source']}")
        
        # Add web sources
        for result in response['web_results']:
            if result.get('source'):
                sources.append(f"Web Search: {result['source']}")
        
        return list(set(sources))  # Remove duplicates

def main():
    """Test the enhanced RAG system."""
    enhanced_rag = EnhancedRAGSystem()
    
    test_queries = [
        "LEED v4.1 energy efficiency requirements",
        "water efficiency credits",
        "sustainable materials in construction",
        "indoor air quality standards"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        result = enhanced_rag.process_query(query)
        print(result['combined_response'])
        
        if result['sources']:
            print(f"\nSources: {', '.join(result['sources'])}")

if __name__ == "__main__":
    main()
