#!/usr/bin/env python3
"""Lightweight mock API for the Albedo demo (no external deps).
Serves minimal /api/status, /api/credits, /api/query, /api/analyze endpoints on port 5000.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import urlparse

SAMPLE_CREDITS = [
    {"code": "EA-Optimize", "name": "Optimize Energy Performance", "type": "Credit", "points_min": 1, "points_max": 20},
    {"code": "WE-Conserve", "name": "Water Efficiency", "type": "Credit", "points_min": 1, "points_max": 10},
    {"code": "SS-Access", "name": "Site Sustainability", "type": "Credit", "points_min": 1, "points_max": 5}
]

# Try to load a more comprehensive credit list if available in the repository outputs
def load_comprehensive_credits():
    import os
    credits_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs', 'leed_credits.json')
    if os.path.exists(credits_path):
        try:
            with open(credits_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            credits = []
            for item in data:
                code = item.get('credit_code') or item.get('credit_name')
                # normalize and shorten overly long names
                name = (item.get('credit_name') or '').strip()
                if name and len(name) > 120:
                    name = name[:116] + '...'
                if code or name:
                    credits.append({
                        'code': code if code else None,
                        'name': name if name else None,
                        'type': item.get('credit_type') or 'Credit',
                        'points_min': item.get('points_min'),
                        'points_max': item.get('points_max')
                    })
            if credits:
                return credits
        except Exception:
            pass
    return SAMPLE_CREDITS

COMPREHENSIVE_CREDITS = load_comprehensive_credits()

class MockHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/status' or path == '/api/health':
            self._set_headers()
            body = {
                'status': 'healthy',
                'system_ready': True,
                'chunks_loaded': len(COMPREHENSIVE_CREDITS),
                'available_sources': ['credits','guide','forms']
            }
            self.wfile.write(json.dumps(body).encode('utf-8'))
            return
        if path == '/api/credits':
            self._set_headers()
            # Serve the richer credit list when available
            body = {
                'credits': COMPREHENSIVE_CREDITS,
                'total_count': len(COMPREHENSIVE_CREDITS),
                'status': 'success'
            }
            self.wfile.write(json.dumps(body).encode('utf-8'))
            return
        # serve index.html and other static files via the static server; return 404 here
        self._set_headers(404)
        self.wfile.write(json.dumps({'error': 'Not found'}).encode('utf-8'))

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get('content-length', 0))
        raw = self.rfile.read(length) if length else b''
        try:
            data = json.loads(raw.decode('utf-8')) if raw else {}
        except Exception:
            data = {}

        if path == '/api/query':
            query = (data.get('query') or '').strip()
            # Simple keyword match against available credit names/codes to simulate relevance
            results = []
            limit = int(data.get('limit', 5) or 5)
            for idx, c in enumerate(COMPREHENSIVE_CREDITS):
                name = (c.get('name') or '')
                code = (c.get('code') or '')
                score = 0.5
                if query:
                    qlow = query.lower()
                    if qlow in (name or '').lower() or qlow in (code or '').lower():
                        score = 0.9
                    elif any(tok in (name or '').lower() for tok in qlow.split()):
                        score = 0.75
                results.append({
                    'rank': idx + 1,
                    'score': float(score),
                    'text': f"Simulated guidance for {name or code}. This is a short extract intended for demo purposes. For production, this would be the retrieved chunk from the RAG index.",
                    'metadata': {'credit_name': name or code, 'credit_code': code, 'source': 'mock'}
                })
                if len(results) >= limit:
                    break
            body = {'query': query, 'results_count': len(results), 'results': results, 'status': 'success'}
            self._set_headers()
            self.wfile.write(json.dumps(body).encode('utf-8'))
            return

        if path == '/api/analyze':
            document_text = data.get('document_text', '')
            target_credits = data.get('target_credits', []) or []
            # If targets not provided, select the top 3 credits as demo
            if not target_credits:
                target_credits = [c.get('code') or c.get('name') for c in COMPREHENSIVE_CREDITS[:3]]
            analysis_results = []
            for c in target_credits:
                # Find matching credit metadata
                match = None
                for cc in COMPREHENSIVE_CREDITS:
                    if c and ((cc.get('code') and cc.get('code') == c) or (cc.get('name') and c.lower() in cc.get('name','').lower())):
                        match = cc
                        break
                credit_name = match.get('name') if match else c
                relevant = [
                    {
                        'rank': 1,
                        'score': 0.88,
                        'text': f"Demo analysis: Found references that relate to {credit_name}. Example: the submission should include documentation of calculation methods and relevant citations.",
                        'metadata': {'credit_name': credit_name, 'credit_code': match.get('code') if match else None, 'source': 'mock'}
                    }
                ]
                analysis_results.append({
                    'credit_code': c,
                    'query': f'Simulated analysis for {c}',
                    'relevant_info': relevant,
                    'compliance_status': 'needs_review'
                })
            body = {'project_type': data.get('project_type', 'NC'), 'target_credits': target_credits, 'analysis_results': analysis_results, 'status': 'success'}
            self._set_headers()
            self.wfile.write(json.dumps(body).encode('utf-8'))
            return

        if path == '/api/assistant':
            query = (data.get('query') or '').strip()
            evidence_text = data.get('evidence_text')
            limit = int(data.get('limit', 4) or 4)
            
            # Generate natural language response based on query
            response_text = self._generate_natural_response(query, evidence_text)
            
            # Generate mock citations
            citations = self._generate_citations(query, limit)
            
            # Mock evidence classification
            evidence_classification = None
            if evidence_text:
                evidence_classification = {
                    'decision': 'supports' if 'leed' in evidence_text.lower() else 'insufficient',
                    'confidence': 0.85
                }
            
            body = {
                'status': 'success',
                'answer': response_text,
                'citations': citations,
                'evidence_classification': evidence_classification
            }
            self._set_headers()
            self.wfile.write(json.dumps(body).encode('utf-8'))
            return

        self._set_headers(404)
        self.wfile.write(json.dumps({'error': 'Not found'}).encode('utf-8'))

    def _generate_natural_response(self, query, evidence_text=None):
        """Generate a natural language response for the query."""
        query_lower = query.lower()
        
        # Handle common LEED questions
        if 'what is leed' in query_lower or 'leed' in query_lower and ('what' in query_lower or 'explain' in query_lower):
            return """LEED (Leadership in Energy and Environmental Design) is a green building certification program developed by the U.S. Green Building Council (USGBC). It's a rating system that evaluates buildings based on their environmental and health performance.

LEED certification provides a framework for healthy, efficient, and cost-saving green buildings. It covers aspects like energy efficiency, water conservation, sustainable materials, indoor air quality, and site sustainability. Buildings can earn different levels of certification (Certified, Silver, Gold, Platinum) based on the number of points they achieve across various credit categories.

The program helps building owners, architects, and developers make informed decisions that benefit the environment, building occupants, and the bottom line."""
        
        elif 'energy' in query_lower and ('efficiency' in query_lower or 'performance' in query_lower):
            return """LEED's energy efficiency requirements focus on reducing energy consumption and greenhouse gas emissions through the Optimize Energy Performance credit category. Key requirements include:

1. **Whole Building Energy Modeling**: Projects must demonstrate energy cost savings compared to a baseline building that meets minimum energy code requirements.

2. **Energy Performance**: Buildings must achieve a percentage improvement in energy performance above the baseline, with points awarded based on the level of improvement (up to 50% or more for maximum points).

3. **Renewable Energy**: On-site renewable energy systems can earn additional points.

4. **Advanced Energy Metering**: Submetering of major energy uses for ongoing performance tracking.

The baseline is typically based on ASHRAE 90.1 standards, and projects can use various strategies like improved insulation, efficient HVAC systems, daylighting, and smart controls to achieve the required savings."""
        
        elif 'water' in query_lower and ('efficiency' in query_lower or 'conservation' in query_lower):
            return """LEED water efficiency requirements help reduce potable water consumption through several strategies:

1. **Water-Efficient Landscaping**: Reduce irrigation needs through native plants, efficient irrigation systems, and rainwater harvesting.

2. **Water-Efficient Fixtures**: Install low-flow fixtures like WaterSense-labeled faucets, showerheads, and toilets that reduce water use by 20-50%.

3. **Alternative Water Sources**: Use non-potable water sources like rainwater, graywater, or municipally supplied reclaimed water for irrigation and other appropriate uses.

4. **Cooling Tower Water Efficiency**: Implement water treatment technologies and system optimization for cooling towers.

Projects can earn up to 11 points in the Water Efficiency credit category, with requirements varying by building type and location."""
        
        elif 'materials' in query_lower and ('sustainable' in query_lower or 'recycled' in query_lower):
            return """LEED's sustainable materials requirements encourage the use of environmentally responsible building materials:

1. **Building Product Disclosure**: Require manufacturers to disclose product ingredients and environmental impacts.

2. **Recycled Content**: Use materials with recycled content, earning points based on the percentage of recycled materials used.

3. **Regional Materials**: Source materials from within 500 miles of the project site to reduce transportation impacts.

4. **Certified Wood**: Use wood certified by sustainable forestry programs like FSC (Forest Stewardship Council).

5. **Construction Waste Management**: Divert construction waste from landfills through recycling and reuse.

These requirements help reduce the environmental impact of material extraction, processing, and transportation while promoting sustainable sourcing practices."""
        
        else:
            # Generic response for other queries
            return f"""Based on LEED certification guidelines, here's what I can tell you about "{query}":

LEED (Leadership in Energy and Environmental Design) is a comprehensive green building rating system that evaluates buildings across multiple environmental categories. While I don't have specific information on that exact topic in my current knowledge base, LEED generally emphasizes sustainable design principles including energy efficiency, water conservation, material selection, indoor environmental quality, and site sustainability.

For specific credit requirements or detailed guidance, I recommend consulting the official LEED rating system documentation or working with a LEED-accredited professional who can provide project-specific advice."""

    def _generate_citations(self, query, limit):
        """Generate mock citations for the response."""
        citations = []
        
        # Find relevant credits based on query
        relevant_credits = []
        query_lower = query.lower()
        
        for credit in COMPREHENSIVE_CREDITS[:limit]:
            name = (credit.get('name') or '').lower()
            code = (credit.get('code') or '').lower()
            
            if any(keyword in query_lower for keyword in ['leed', 'certification', 'building']):
                relevant_credits.append(credit)
            elif 'energy' in query_lower and ('energy' in name or 'ea' in code):
                relevant_credits.append(credit)
            elif 'water' in query_lower and ('water' in name or 'we' in code):
                relevant_credits.append(credit)
            elif 'material' in query_lower and ('material' in name or 'mr' in code):
                relevant_credits.append(credit)
        
        for i, credit in enumerate(relevant_credits[:limit]):
            citations.append({
                'label': f"LEED v4.1 Reference {i+1}",
                'source': f"LEED BD+C Rating System - {credit.get('name', 'Credit')}",
                'pages': [f"Section {credit.get('code', 'N/A')}"],
                'score': 0.8 - (i * 0.1),
                'snippet': f"Requirements for {credit.get('name', 'this credit')} as outlined in the LEED rating system."
            })
        
        return citations

def run(server_class=HTTPServer, handler_class=MockHandler, port=5000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Mock API running on http://localhost:{port}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down mock API')
    finally:
        httpd.server_close()

if __name__ == '__main__':
    run()
