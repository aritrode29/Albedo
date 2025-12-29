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

        self._set_headers(404)
        self.wfile.write(json.dumps({'error': 'Not found'}).encode('utf-8'))

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
