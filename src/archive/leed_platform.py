#!/usr/bin/env python3
"""
LEED Certification Automation Platform
Main orchestrator integrating all modules based on the research paper's system architecture.
Combines document processing, energy modeling, location analysis, and LLM-RAG for comprehensive LEED automation.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Import our modules
from extract_leed_credits import run_extraction
from energy_modeling import EnergyPlusExtractor, EnergyPlusSimulator, LEEDEnergyAnalyzer
from llm_rag import LEEDReportGenerator
from location_analysis import LocationAnalyzer, LocationReportGenerator

@dataclass
class ProjectData:
    """Project data structure"""
    project_name: str
    project_type: str  # NC, CS, Schools, etc.
    building_area: float
    site_location: Dict[str, Any]
    building_geometry: Dict[str, Any]
    hvac_system: Dict[str, Any]
    target_credits: List[str]

@dataclass
class AnalysisResults:
    """Analysis results structure"""
    credit_extraction: Dict[str, Any]
    energy_analysis: Dict[str, Any]
    location_analysis: Dict[str, Any]
    generated_reports: Dict[str, str]
    compliance_summary: Dict[str, Any]

class LEEDPlatform:
    """
    Main LEED certification automation platform.
    Based on the research paper's integrated system architecture.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # Initialize modules
        self.energy_extractor = EnergyPlusExtractor()
        self.energy_simulator = EnergyPlusSimulator()
        self.energy_analyzer = LEEDEnergyAnalyzer()
        self.location_analyzer = LocationAnalyzer()
        self.location_reporter = LocationReportGenerator()
        self.report_generator = LEEDReportGenerator()
        
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
                'llm_rag': True
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
            self.logger.info("Initializing LEED Platform...")
            
            # Create output directories
            os.makedirs(self.config['data_paths']['output_dir'], exist_ok=True)
            os.makedirs('models', exist_ok=True)
            
            # Initialize knowledge base if needed
            if not os.path.exists(f"{self.config['data_paths']['knowledge_base']}.faiss"):
                self.logger.info("Initializing knowledge base...")
                success = self.report_generator.initialize_knowledge_base(
                    self.config['data_paths']['credits_json'],
                    self.config['data_paths']['knowledge_base']
                )
                if not success:
                    self.logger.warning("Failed to initialize knowledge base")
            else:
                self.logger.info("Loading existing knowledge base...")
                success = self.report_generator.load_knowledge_base(
                    self.config['data_paths']['knowledge_base']
                )
                if not success:
                    self.logger.warning("Failed to load knowledge base")
            
            self.logger.info("Platform initialized successfully!")
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
        Run comprehensive LEED analysis across all modules.
        Based on the research paper's end-to-end workflow.
        """
        try:
            self.logger.info("Starting comprehensive LEED analysis...")
            
            results = AnalysisResults(
                credit_extraction={},
                energy_analysis={},
                location_analysis={},
                generated_reports={},
                compliance_summary={}
            )
            
            # Step 1: Credit Extraction (if needed)
            if not os.path.exists(self.config['data_paths']['credits_json']):
                self.logger.info("Extracting LEED credits...")
                run_extraction(
                    self.config['data_paths']['leed_pdf'],
                    self.config['data_paths']['credits_json'],
                    self.config['data_paths']['rag_chunks']
                )
            
            # Step 2: Energy Analysis
            if self.config['analysis_modules']['energy_modeling']:
                self.logger.info("Running energy analysis...")
                results.energy_analysis = self._run_energy_analysis()
            
            # Step 3: Location Analysis
            if self.config['analysis_modules']['location_analysis']:
                self.logger.info("Running location analysis...")
                results.location_analysis = self._run_location_analysis()
            
            # Step 4: Generate Reports
            if self.config['analysis_modules']['llm_rag']:
                self.logger.info("Generating LEED reports...")
                results.generated_reports = self._generate_reports()
            
            # Step 5: Compliance Summary
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
    
    def _run_energy_analysis(self) -> Dict[str, Any]:
        """Run energy analysis for LEED credits"""
        try:
            if not self.project_data:
                return {'error': 'No project data loaded'}
            
            # Extract building geometry
            geometry = self.energy_extractor.extract_geometry_from_bim(
                self.project_data.building_geometry
            )
            
            # Extract HVAC system
            hvac = self.energy_extractor.extract_hvac_system(
                self.project_data.hvac_system
            )
            
            # Create energy model
            energy_model = self.energy_extractor.EnergyModel(
                building_geometry=geometry,
                hvac_system=hvac,
                schedules=self.project_data.hvac_system.get('schedules', {}),
                materials=[],
                location=self.project_data.site_location
            )
            
            # Generate IDF file
            idf_path = os.path.join(self.config['data_paths']['output_dir'], 'energy_model.idf')
            success = self.energy_extractor.generate_idf(energy_model, idf_path)
            
            if not success:
                return {'error': 'Failed to generate EnergyPlus model'}
            
            # Run simulation (simulated for demonstration)
            simulation_results = {
                'total_site_energy': 1500000,  # kBtu/year
                'total_source_energy': 2000000,  # kBtu/year
                'monthly_breakdown': {}
            }
            
            # Analyze energy performance
            energy_analysis = self.energy_analyzer.analyze_energy_performance(
                simulation_results,
                self.project_data.building_area
            )
            
            return {
                'energy_model': asdict(energy_model),
                'simulation_results': simulation_results,
                'leed_analysis': energy_analysis,
                'idf_path': idf_path
            }
            
        except Exception as e:
            self.logger.error(f"Error in energy analysis: {e}")
            return {'error': str(e)}
    
    def _run_location_analysis(self) -> Dict[str, Any]:
        """Run location analysis for LEED credits"""
        try:
            if not self.project_data:
                return {'error': 'No project data loaded'}
            
            # Create site location object
            from location_analysis import SiteLocation
            site_location = SiteLocation(
                latitude=self.project_data.site_location['latitude'],
                longitude=self.project_data.site_location['longitude'],
                address=self.project_data.site_location['address'],
                city=self.project_data.site_location['city'],
                state=self.project_data.site_location['state'],
                zip_code=self.project_data.site_location['zip_code']
            )
            
            # Run location analysis
            location_analysis = self.location_analyzer.analyze_site_location(site_location)
            
            # Generate location report
            location_report = self.location_reporter.generate_location_report(location_analysis)
            
            return {
                'site_analysis': location_analysis,
                'location_report': location_report
            }
            
        except Exception as e:
            self.logger.error(f"Error in location analysis: {e}")
            return {'error': str(e)}
    
    def _generate_reports(self) -> Dict[str, str]:
        """Generate LEED credit reports using LLM-RAG"""
        try:
            if not self.project_data:
                return {'error': 'No project data loaded'}
            
            reports = {}
            
            # Generate reports for target credits
            for credit_code in self.project_data.target_credits:
                try:
                    # Create project data for the credit
                    credit_data = {
                        'credit_code': credit_code,
                        'credit_name': f'{credit_code} Credit',
                        'credit_type': 'Credit',
                        'points_min': 1,
                        'points_max': 5,
                        'project_name': self.project_data.project_name,
                        'project_type': self.project_data.project_type
                    }
                    
                    # Generate report
                    query = f"Analyze compliance for {credit_code} based on project data"
                    report = self.report_generator.generate_credit_report(
                        credit_code=credit_code,
                        project_data=credit_data,
                        query=query
                    )
                    
                    reports[credit_code] = report
                    
                except Exception as e:
                    self.logger.error(f"Error generating report for {credit_code}: {e}")
                    reports[credit_code] = f"Error: {e}"
            
            return reports
            
        except Exception as e:
            self.logger.error(f"Error generating reports: {e}")
            return {'error': str(e)}
    
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
                'recommendations': []
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
                leed_credits = location_analysis.get('leed_credits', {})
                
                for credit_name, credit_data in leed_credits.items():
                    if credit_data.get('points', 0) > 0:
                        summary['credits_achieved'] += 1
                        summary['total_points'] += credit_data.get('points', 0)
                        summary['credit_details'][credit_name] = {
                            'status': credit_data.get('status', 'Not Achieved'),
                            'points': credit_data.get('points', 0)
                        }
            
            # Generate recommendations
            if summary['total_points'] < 40:
                summary['recommendations'].append(
                    "Focus on energy efficiency improvements to increase points"
                )
            if summary['credits_achieved'] < len(self.project_data.target_credits):
                summary['recommendations'].append(
                    "Review missing credits and implement required measures"
                )
            
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
                    f"leed_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
            
            # Convert results to JSON-serializable format
            results_dict = {
                'project_data': asdict(self.project_data) if self.project_data else None,
                'analysis_results': {
                    'energy_analysis': self.analysis_results.energy_analysis,
                    'location_analysis': self.analysis_results.location_analysis,
                    'generated_reports': self.analysis_results.generated_reports,
                    'compliance_summary': self.analysis_results.compliance_summary
                },
                'analysis_date': datetime.now().isoformat(),
                'platform_version': '1.0.0'
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Results saved to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            return False
    
    def generate_final_report(self, output_path: Optional[str] = None) -> str:
        """Generate comprehensive final report"""
        try:
            if not output_path:
                output_path = os.path.join(
                    self.config['data_paths']['output_dir'],
                    f"leed_final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                )
            
            report = []
            report.append("# LEED Certification Analysis Report")
            report.append("")
            report.append(f"**Project:** {self.project_data.project_name if self.project_data else 'Unknown'}")
            report.append(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
            
            # Compliance Summary
            if self.analysis_results.compliance_summary:
                summary = self.analysis_results.compliance_summary
                report.append("## Compliance Summary")
                report.append(f"- Total Credits Analyzed: {summary.get('total_credits_analyzed', 0)}")
                report.append(f"- Credits Achieved: {summary.get('credits_achieved', 0)}")
                report.append(f"- Total Points: {summary.get('total_points', 0)}")
                report.append("")
                
                if summary.get('credit_details'):
                    report.append("### Credit Details")
                    for credit_name, credit_data in summary['credit_details'].items():
                        report.append(f"- **{credit_name}**: {credit_data.get('status', 'Not Achieved')} ({credit_data.get('points', 0)} points)")
                    report.append("")
                
                if summary.get('recommendations'):
                    report.append("### Recommendations")
                    for rec in summary['recommendations']:
                        report.append(f"- {rec}")
                    report.append("")
            
            # Energy Analysis
            if self.analysis_results.energy_analysis:
                report.append("## Energy Analysis")
                energy_analysis = self.analysis_results.energy_analysis
                if 'leed_analysis' in energy_analysis:
                    leed_analysis = energy_analysis['leed_analysis']
                    report.append(f"- Energy Use Intensity: {leed_analysis.get('energy_use_intensity', 0):.1f} kBtu/ft²/year")
                    report.append(f"- Compliance Status: {leed_analysis.get('compliance_status', 'Not Achieved')}")
                    report.append(f"- Points Earned: {leed_analysis.get('points_earned', 0)}")
                report.append("")
            
            # Location Analysis
            if self.analysis_results.location_analysis:
                report.append("## Location Analysis")
                location_analysis = self.analysis_results.location_analysis
                if 'location_report' in location_analysis:
                    report.append(location_analysis['location_report'])
                report.append("")
            
            # Generated Reports
            if self.analysis_results.generated_reports:
                report.append("## Detailed Credit Reports")
                for credit_code, credit_report in self.analysis_results.generated_reports.items():
                    report.append(f"### {credit_code}")
                    report.append(credit_report)
                    report.append("")
            
            # Write report
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report))
            
            self.logger.info(f"Final report saved to: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error generating final report: {e}")
            return f"Error: {e}"

def main():
    """Main function for testing the LEED platform"""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize platform
    platform = LEEDPlatform()
    
    if not platform.initialize_platform():
        print("Failed to initialize platform")
        return
    
    # Example project data
    project_data = ProjectData(
        project_name="Green Office Building",
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
        target_credits=['EA_Credit_Optimize_Energy_Performance', 'LT_Credit_Access_to_Quality_Transit']
    )
    
    # Load project data
    platform.load_project_data(project_data)
    
    # Run comprehensive analysis
    results = platform.run_comprehensive_analysis()
    
    # Save results
    platform.save_results()
    
    # Generate final report
    report_path = platform.generate_final_report()
    
    print("LEED Platform analysis completed successfully!")
    print(f"Final report: {report_path}")

if __name__ == "__main__":
    main() 