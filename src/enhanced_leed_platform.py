#!/usr/bin/env python3
"""
Enhanced LEED Platform with RAG Integration
Updated main orchestrator that integrates with the deployed RAG API for enhanced report generation.
"""

import os
import sys
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from extract_leed_credits import run_extraction
from energy_modeling import EnergyPlusExtractor, EnergyPlusSimulator, LEEDEnergyAnalyzer
from location_analysis import LocationAnalyzer, LocationReportGenerator

@dataclass
class ProjectData:
    """Enhanced project data structure"""
    project_name: str
    project_type: str  # NC, CS, Schools, etc.
    building_area: float
    site_location: Dict[str, Any]
    building_geometry: Dict[str, Any]
    hvac_system: Dict[str, Any]
    target_credits: List[str]
    documents: List[str] = None  # Paths to uploaded documents
    project_description: str = ""

@dataclass
class AnalysisResults:
    """Enhanced analysis results structure"""
    credit_extraction: Dict[str, Any]
    energy_analysis: Dict[str, Any]
    location_analysis: Dict[str, Any]
    generated_reports: Dict[str, str]
    compliance_summary: Dict[str, Any]
    rag_insights: Dict[str, Any] = None
    document_analysis: Dict[str, Any] = None

class RAGAPIClient:
    """Client for interacting with the deployed RAG API"""
    
    def __init__(self, api_url: str = "http://localhost:5000"):
        self.api_url = api_url
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
    
    def is_available(self) -> bool:
        """Check if RAG API is available"""
        try:
            response = self.session.get(f"{self.api_url}/api/status", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def query_knowledge_base(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query the RAG knowledge base"""
        try:
            payload = {"query": query, "limit": limit}
            response = self.session.post(f"{self.api_url}/api/query", json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            else:
                self.logger.warning(f"RAG API query failed: {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"RAG API query error: {e}")
            return []
    
    def analyze_document(self, document_text: str, project_type: str = "NC", 
                        target_credits: List[str] = None) -> Dict[str, Any]:
        """Analyze document against LEED requirements"""
        try:
            if target_credits is None:
                target_credits = ['EA', 'WE', 'SS', 'EQ', 'MR', 'LT']
            
            payload = {
                "document_text": document_text,
                "project_type": project_type,
                "target_credits": target_credits
            }
            
            response = self.session.post(f"{self.api_url}/api/analyze", json=payload, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Document analysis failed: {response.status_code}")
                return {}
        except Exception as e:
            self.logger.error(f"Document analysis error: {e}")
            return {}
    
    def get_available_credits(self) -> List[Dict[str, Any]]:
        """Get list of available LEED credits"""
        try:
            response = self.session.get(f"{self.api_url}/api/credits", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('credits', [])
            else:
                return []
        except Exception as e:
            self.logger.error(f"Error getting credits: {e}")
            return []

class EnhancedLEEDPlatform:
    """
    Enhanced LEED certification automation platform with RAG integration.
    Integrates with the deployed RAG API for intelligent report generation.
    """
    
    def __init__(self, config_path: Optional[str] = None, rag_api_url: str = "http://localhost:5000"):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # Initialize modules
        self.energy_extractor = EnergyPlusExtractor()
        self.energy_simulator = EnergyPlusSimulator()
        self.energy_analyzer = LEEDEnergyAnalyzer()
        self.location_analyzer = LocationAnalyzer()
        self.location_reporter = LocationReportGenerator()
        
        # Initialize RAG API client
        self.rag_client = RAGAPIClient(rag_api_url)
        
        # Platform state
        self.project_data = None
        self.analysis_results = None
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load platform configuration"""
        default_config = {
            'data_paths': {
                'leed_pdf': 'data/leed_pdfs/BD+C/LEED_v4.1_BD_C_Rating_System_Feb_2025_clean.pdf',
                'credits_json': 'data/raw/leed_credits.json',
                'rag_chunks': 'data/raw/rag_chunks.jsonl',
                'knowledge_base': 'models/leed_knowledge_base',
                'output_dir': 'outputs'
            },
            'analysis_modules': {
                'energy_modeling': True,
                'location_analysis': True,
                'llm_rag': True,
                'document_analysis': True
            },
            'rag_api': {
                'url': 'http://localhost:5000',
                'timeout': 10,
                'retry_attempts': 3
            },
            'api_keys': {}
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                self.logger.error(f"Error loading config: {e}")
        
        return default_config
    
    def initialize_platform(self) -> bool:
        """Initialize the platform and all modules"""
        try:
            self.logger.info("Initializing Enhanced LEED Platform...")
            
            # Create output directories
            os.makedirs(self.config['data_paths']['output_dir'], exist_ok=True)
            os.makedirs('models', exist_ok=True)
            
            # Check RAG API availability
            if self.rag_client.is_available():
                self.logger.info("✅ RAG API is available and connected")
            else:
                self.logger.warning("⚠️ RAG API not available. Some features will be limited.")
            
            self.logger.info("Enhanced Platform initialized successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing platform: {e}")
            return False
    
    def load_project_data(self, project_data: ProjectData) -> bool:
        """Load project data for analysis"""
        try:
            self.project_data = project_data
            self.logger.info(f"Loaded project: {project_data.project_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error loading project data: {e}")
            return False
    
    def run_comprehensive_analysis(self) -> AnalysisResults:
        """
        Run comprehensive LEED analysis with RAG integration.
        Enhanced version that uses the deployed RAG API.
        """
        try:
            self.logger.info("Starting comprehensive LEED analysis with RAG integration...")
            
            results = AnalysisResults(
                credit_extraction={},
                energy_analysis={},
                location_analysis={},
                generated_reports={},
                compliance_summary={},
                rag_insights={},
                document_analysis={}
            )
            
            # Step 1: Credit Extraction (if needed)
            if not os.path.exists(self.config['data_paths']['credits_json']):
                self.logger.info("Extracting LEED credits...")
                run_extraction(
                    self.config['data_paths']['leed_pdf'],
                    self.config['data_paths']['credits_json'],
                    self.config['data_paths']['rag_chunks']
                )
            
            # Step 2: RAG-Enhanced Analysis
            if self.config['analysis_modules']['llm_rag'] and self.rag_client.is_available():
                self.logger.info("Running RAG-enhanced analysis...")
                results.rag_insights = self._run_rag_analysis()
            
            # Step 3: Document Analysis
            if self.config['analysis_modules']['document_analysis'] and self.project_data.documents:
                self.logger.info("Analyzing uploaded documents...")
                results.document_analysis = self._analyze_uploaded_documents()
            
            # Step 4: Energy Analysis
            if self.config['analysis_modules']['energy_modeling']:
                self.logger.info("Running energy analysis...")
                results.energy_analysis = self._run_energy_analysis()
            
            # Step 5: Location Analysis
            if self.config['analysis_modules']['location_analysis']:
                self.logger.info("Running location analysis...")
                results.location_analysis = self._run_location_analysis()
            
            # Step 6: Generate Enhanced Reports
            self.logger.info("Generating enhanced reports with RAG insights...")
            results.generated_reports = self._generate_enhanced_reports(results)
            
            # Step 7: Compliance Summary
            results.compliance_summary = self._generate_compliance_summary(results)
            
            self.analysis_results = results
            self.logger.info("Comprehensive analysis completed!")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive analysis: {e}")
            return AnalysisResults(
                credit_extraction={},
                energy_analysis={},
                location_analysis={},
                generated_reports={},
                compliance_summary={'error': str(e)}
            )
    
    def _run_rag_analysis(self) -> Dict[str, Any]:
        """Run RAG-enhanced analysis for target credits"""
        try:
            rag_insights = {}
            
            for credit_code in self.project_data.target_credits:
                # Query RAG for credit-specific information
                query = f"{credit_code} credit requirements and best practices for {self.project_data.project_type} projects"
                results = self.rag_client.query_knowledge_base(query, limit=3)
                
                if results:
                    rag_insights[credit_code] = {
                        'query': query,
                        'relevant_info': results,
                        'top_recommendations': self._extract_recommendations(results),
                        'compliance_guidance': self._extract_compliance_guidance(results)
                    }
            
            return rag_insights
            
        except Exception as e:
            self.logger.error(f"Error in RAG analysis: {e}")
            return {}
    
    def _analyze_uploaded_documents(self) -> Dict[str, Any]:
        """Analyze uploaded documents using RAG API"""
        try:
            document_analysis = {}
            
            for doc_path in self.project_data.documents:
                if os.path.exists(doc_path):
                    # Read document content
                    with open(doc_path, 'r', encoding='utf-8') as f:
                        doc_content = f.read()
                    
                    # Analyze document
                    analysis = self.rag_client.analyze_document(
                        doc_content,
                        self.project_data.project_type,
                        self.project_data.target_credits
                    )
                    
                    if analysis:
                        document_analysis[doc_path] = analysis
            
            return document_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing documents: {e}")
            return {}
    
    def _extract_recommendations(self, rag_results: List[Dict[str, Any]]) -> List[str]:
        """Extract actionable recommendations from RAG results"""
        recommendations = []
        
        for result in rag_results:
            text = result.get('text', '')
            if 'recommend' in text.lower() or 'should' in text.lower() or 'consider' in text.lower():
                # Extract recommendation sentences
                sentences = text.split('.')
                for sentence in sentences:
                    if any(word in sentence.lower() for word in ['recommend', 'should', 'consider', 'implement']):
                        recommendations.append(sentence.strip())
        
        return recommendations[:3]  # Top 3 recommendations
    
    def _extract_compliance_guidance(self, rag_results: List[Dict[str, Any]]) -> List[str]:
        """Extract compliance guidance from RAG results"""
        guidance = []
        
        for result in rag_results:
            text = result.get('text', '')
            if 'requirement' in text.lower() or 'must' in text.lower() or 'prerequisite' in text.lower():
                # Extract requirement sentences
                sentences = text.split('.')
                for sentence in sentences:
                    if any(word in sentence.lower() for word in ['requirement', 'must', 'prerequisite', 'comply']):
                        guidance.append(sentence.strip())
        
        return guidance[:3]  # Top 3 guidance items
    
    def _run_energy_analysis(self) -> Dict[str, Any]:
        """Run energy analysis (simplified version)"""
        try:
            if not self.project_data:
                return {'error': 'No project data loaded'}
            
            # Simulate energy analysis results
            energy_analysis = {
                'energy_model': 'Simulated Energy Model',
                'simulation_results': {
                    'total_site_energy': 1200000,  # kBtu/year
                    'total_source_energy': 1600000,  # kBtu/year
                    'energy_use_intensity': 16.0  # kBtu/ft²/year
                },
                'leed_analysis': {
                    'energy_use_intensity': 16.0,
                    'compliance_status': 'Achieved',
                    'points_earned': 8,
                    'improvement_potential': '15% reduction possible with envelope upgrades'
                }
            }
            
            return energy_analysis
            
        except Exception as e:
            self.logger.error(f"Error in energy analysis: {e}")
            return {'error': str(e)}
    
    def _run_location_analysis(self) -> Dict[str, Any]:
        """Run location analysis (simplified version)"""
        try:
            if not self.project_data:
                return {'error': 'No project data loaded'}
            
            # Simulate location analysis results
            location_analysis = {
                'site_analysis': {
                    'transit_access': {'lt_credit_points': 3, 'status': 'Achieved'},
                    'walkability': {'lt_credit_points': 2, 'status': 'Achieved'},
                    'environmental_context': {'ss_credit_points': 1, 'status': 'Achieved'}
                },
                'location_report': 'Site analysis completed with good transit access and walkability scores.'
            }
            
            return location_analysis
            
        except Exception as e:
            self.logger.error(f"Error in location analysis: {e}")
            return {'error': str(e)}
    
    def _generate_enhanced_reports(self, results: AnalysisResults) -> Dict[str, str]:
        """Generate enhanced reports using RAG insights"""
        try:
            reports = {}
            
            for credit_code in self.project_data.target_credits:
                report_parts = []
                
                # Credit header
                report_parts.append(f"# {credit_code} Credit Analysis Report")
                report_parts.append(f"**Project:** {self.project_data.project_name}")
                report_parts.append(f"**Project Type:** {self.project_data.project_type}")
                report_parts.append("")
                
                # RAG insights
                if results.rag_insights and credit_code in results.rag_insights:
                    rag_data = results.rag_insights[credit_code]
                    
                    report_parts.append("## RAG-Enhanced Analysis")
                    report_parts.append("")
                    
                    # Top recommendations
                    if rag_data.get('top_recommendations'):
                        report_parts.append("### Recommendations")
                        for rec in rag_data['top_recommendations']:
                            report_parts.append(f"- {rec}")
                        report_parts.append("")
                    
                    # Compliance guidance
                    if rag_data.get('compliance_guidance'):
                        report_parts.append("### Compliance Guidance")
                        for guidance in rag_data['compliance_guidance']:
                            report_parts.append(f"- {guidance}")
                        report_parts.append("")
                    
                    # Relevant information
                    if rag_data.get('relevant_info'):
                        report_parts.append("### Relevant LEED Information")
                        for info in rag_data['relevant_info'][:2]:  # Top 2 results
                            report_parts.append(f"**{info['metadata'].get('credit_name', 'Credit')}** (Score: {info['score']:.3f})")
                            report_parts.append(f"{info['text'][:300]}...")
                            report_parts.append("")
                
                # Energy analysis (if applicable)
                if credit_code.startswith('EA') and results.energy_analysis:
                    report_parts.append("## Energy Analysis")
                    energy_data = results.energy_analysis.get('leed_analysis', {})
                    report_parts.append(f"- Energy Use Intensity: {energy_data.get('energy_use_intensity', 0):.1f} kBtu/ft²/year")
                    report_parts.append(f"- Compliance Status: {energy_data.get('compliance_status', 'Not Analyzed')}")
                    report_parts.append(f"- Points Earned: {energy_data.get('points_earned', 0)}")
                    report_parts.append("")
                
                reports[credit_code] = "\n".join(report_parts)
            
            return reports
            
        except Exception as e:
            self.logger.error(f"Error generating enhanced reports: {e}")
            return {}
    
    def _generate_compliance_summary(self, results: AnalysisResults) -> Dict[str, Any]:
        """Generate comprehensive compliance summary"""
        try:
            summary = {
                'project_name': self.project_data.project_name if self.project_data else 'Unknown',
                'analysis_date': datetime.now().isoformat(),
                'total_credits_analyzed': len(self.project_data.target_credits) if self.project_data else 0,
                'credits_achieved': 0,
                'total_points': 0,
                'credit_details': {},
                'recommendations': [],
                'rag_insights_available': bool(results.rag_insights),
                'document_analysis_available': bool(results.document_analysis)
            }
            
            # Analyze energy credits
            if 'leed_analysis' in results.energy_analysis:
                energy_analysis = results.energy_analysis['leed_analysis']
                summary['credits_achieved'] += 1
                summary['total_points'] += energy_analysis.get('points_earned', 0)
                summary['credit_details']['EA_Credit_Optimize_Energy_Performance'] = {
                    'status': energy_analysis.get('compliance_status', 'Not Achieved'),
                    'points': energy_analysis.get('points_earned', 0),
                    'eui': energy_analysis.get('energy_use_intensity', 0)
                }
            
            # Analyze location credits
            if 'site_analysis' in results.location_analysis:
                location_analysis = results.location_analysis['site_analysis']
                for credit_type, credit_data in location_analysis.items():
                    if isinstance(credit_data, dict) and credit_data.get('lt_credit_points', 0) > 0:
                        summary['credits_achieved'] += 1
                        summary['total_points'] += credit_data.get('lt_credit_points', 0)
                        summary['credit_details'][credit_type] = {
                            'status': credit_data.get('status', 'Not Achieved'),
                            'points': credit_data.get('lt_credit_points', 0)
                        }
            
            # Add RAG-based recommendations
            if results.rag_insights:
                for credit_code, rag_data in results.rag_insights.items():
                    if rag_data.get('top_recommendations'):
                        summary['recommendations'].extend(rag_data['top_recommendations'][:1])  # Top recommendation per credit
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating compliance summary: {e}")
            return {'error': str(e)}
    
    def save_results(self, output_path: Optional[str] = None) -> bool:
        """Save analysis results to file"""
        try:
            if not self.analysis_results:
                return False
            
            if not output_path:
                output_path = os.path.join(
                    self.config['data_paths']['output_dir'],
                    f"enhanced_leed_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
            
            # Convert results to JSON-serializable format
            results_dict = {
                'project_data': asdict(self.project_data) if self.project_data else None,
                'analysis_results': {
                    'energy_analysis': self.analysis_results.energy_analysis,
                    'location_analysis': self.analysis_results.location_analysis,
                    'generated_reports': self.analysis_results.generated_reports,
                    'compliance_summary': self.analysis_results.compliance_summary,
                    'rag_insights': self.analysis_results.rag_insights,
                    'document_analysis': self.analysis_results.document_analysis
                },
                'analysis_date': datetime.now().isoformat(),
                'platform_version': '2.0.0',
                'rag_integration': True
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Enhanced results saved to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            return False

def main():
    """Main function for testing the enhanced LEED platform"""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize enhanced platform
    platform = EnhancedLEEDPlatform()
    
    if not platform.initialize_platform():
        print("Failed to initialize enhanced platform")
        return
    
    # Example project data with documents
    project_data = ProjectData(
        project_name="Green Office Building - Enhanced",
        project_type="NC",
        building_area=75000.0,
        site_location={
            'latitude': 40.7128,
            'longitude': -74.0060,
            'address': '123 Main Street',
            'city': 'New York',
            'state': 'NY',
            'zip_code': '10001'
        },
        building_geometry={
            'zones': [
                {'name': 'Office_Zone_1', 'area': 25000, 'volume': 75000, 'height': 3.0, 'type': 'Office'},
                {'name': 'Office_Zone_2', 'area': 25000, 'volume': 75000, 'height': 3.0, 'type': 'Office'},
                {'name': 'Lobby', 'area': 5000, 'volume': 15000, 'height': 3.0, 'type': 'Lobby'}
            ],
            'surfaces': [
                {'name': 'Exterior_Wall_1', 'type': 'Wall', 'construction': 'High_Performance_Wall', 'area': 5000},
                {'name': 'Roof', 'type': 'Roof', 'construction': 'High_Performance_Roof', 'area': 25000}
            ]
        },
        hvac_system={
            'system_type': 'VAV',
            'equipment': [
                {'name': 'AHU_1', 'type': 'AHU', 'capacity': 100, 'efficiency': 0.90}
            ],
            'schedules': {
                'Office_Schedule': [0.0] * 8 + [1.0] * 8 + [0.0] * 8
            },
            'setpoints': {'cooling': 24, 'heating': 20}
        },
        target_credits=['EA_Credit_Optimize_Energy_Performance', 'LT_Credit_Access_to_Quality_Transit', 'WE_Credit_Water_Use_Reduction'],
        documents=[],  # Add document paths here if available
        project_description="Modern green office building with high-performance systems"
    )
    
    # Load project data
    platform.load_project_data(project_data)
    
    # Run comprehensive analysis
    results = platform.run_comprehensive_analysis()
    
    # Save results
    platform.save_results()
    
    print("Enhanced LEED Platform analysis completed successfully!")
    print(f"RAG insights available: {bool(results.rag_insights)}")
    print(f"Document analysis available: {bool(results.document_analysis)}")
    print(f"Total credits analyzed: {results.compliance_summary.get('total_credits_analyzed', 0)}")

if __name__ == "__main__":
    main()

