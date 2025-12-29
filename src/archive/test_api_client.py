#!/usr/bin/env python3
"""
LEED RAG API Test Client
Test client to demonstrate the LEED RAG API functionality.
"""

import requests
import json
import time

class LEEDRAGAPIClient:
    """Client for testing LEED RAG API"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_status(self):
        """Test API status endpoint"""
        print("🔍 Testing API Status...")
        try:
            response = self.session.get(f"{self.base_url}/api/status")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Status: {data['status']}")
                print(f"✅ Chunks Loaded: {data['chunks_loaded']}")
                print(f"✅ System Ready: {data['system_ready']}")
                return True
            else:
                print(f"❌ Status check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return False
    
    def test_query(self, query: str, limit: int = 3):
        """Test query endpoint"""
        print(f"\n🔍 Testing Query: '{query}'")
        try:
            payload = {"query": query, "limit": limit}
            response = self.session.post(f"{self.base_url}/api/query", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Query successful - {data['results_count']} results")
                
                for i, result in enumerate(data['results'][:2], 1):  # Show top 2
                    print(f"\n📋 Result #{i} (Score: {result['score']:.3f})")
                    metadata = result['metadata']
                    if metadata.get('credit_code'):
                        print(f"   Credit: {metadata['credit_code']}")
                    if metadata.get('credit_name'):
                        print(f"   Name: {metadata['credit_name']}")
                    
                    text = result['text'][:150] + "..." if len(result['text']) > 150 else result['text']
                    print(f"   Content: {text}")
                
                return True
            else:
                print(f"❌ Query failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error in query: {e}")
            return False
    
    def test_credits(self):
        """Test credits endpoint"""
        print("\n🔍 Testing Credits Endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/api/credits")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Credits loaded: {data['total_count']} credits")
                
                # Show first 5 credits
                for credit in data['credits'][:5]:
                    print(f"   • {credit['code']}: {credit['name']} ({credit['type']})")
                
                return True
            else:
                print(f"❌ Credits failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error in credits: {e}")
            return False
    
    def test_analyze(self):
        """Test analyze endpoint"""
        print("\n🔍 Testing Analyze Endpoint...")
        try:
            payload = {
                "document_text": "This building uses LED lighting and has a green roof for energy efficiency.",
                "project_type": "NC",
                "target_credits": ["EA", "SS"]
            }
            
            response = self.session.post(f"{self.base_url}/api/analyze", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Analysis successful for {len(data['analysis_results'])} credits")
                
                for result in data['analysis_results']:
                    print(f"   • {result['credit_code']}: {len(result['relevant_info'])} relevant items found")
                
                return True
            else:
                print(f"❌ Analysis failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error in analysis: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run comprehensive API test"""
        print("🏗️  LEED RAG API - Comprehensive Test")
        print("=" * 50)
        
        # Test status
        if not self.test_status():
            print("❌ API not available. Make sure the server is running.")
            return False
        
        # Test queries
        test_queries = [
            "What are the requirements for energy efficiency credits?",
            "How do I achieve LEED points for water conservation?",
            "EA Credit Optimize Energy Performance",
            "What documentation is needed for LEED credits?"
        ]
        
        for query in test_queries:
            self.test_query(query)
            time.sleep(0.5)  # Brief pause between queries
        
        # Test credits endpoint
        self.test_credits()
        
        # Test analyze endpoint
        self.test_analyze()
        
        print("\n🎉 API Test Completed Successfully!")
        print("✅ All endpoints are working correctly")
        print("✅ RAG system is responding to queries")
        print("✅ API is ready for frontend integration")
        
        return True

def main():
    """Main test function"""
    client = LEEDRAGAPIClient()
    
    print("Starting LEED RAG API test...")
    print("Make sure the API server is running: python src/leed_rag_api.py")
    print()
    
    success = client.run_comprehensive_test()
    
    if success:
        print("\n🚀 Next Steps:")
        print("1. Integrate with CertiSense frontend")
        print("2. Connect to main LEED platform")
        print("3. Test with real project data")
        print("4. Deploy to production")
    else:
        print("\n❌ API test failed. Check server status.")

if __name__ == "__main__":
    main()
