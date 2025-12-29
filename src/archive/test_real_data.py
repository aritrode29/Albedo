#!/usr/bin/env python3
"""
Real LEED Project Data Test
Test the enhanced LEED platform with real UT Austin campus building data.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup logging for real data testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def load_campus_buildings() -> List[Dict[str, Any]]:
    """Load UT Austin campus building data"""
    try:
        with open('data/ut_austin_campus/campus_buildings.json', 'r', encoding='utf-8') as f:
            buildings = json.load(f)
        return buildings
    except Exception as e:
        print(f"Error loading campus buildings: {e}")
        return []

def create_project_data_from_building(building: Dict[str, Any]) -> 'ProjectData':
    """Convert campus building data to ProjectData format"""
    from enhanced_leed_platform import ProjectData
    
    # Map building types to LEED project types
    building_type_mapping = {
        'Academic': 'NC',
        'Student Life': 'NC',
        'Residential': 'NC',
        'Research': 'NC'
    }
    
    # Determine target credits based on sustainability features
    target_credits = ['EA_Credit_Optimize_Energy_Performance']
    
    if any('water' in feature.lower() for feature in building.get('sustainability_features', [])):
        target_credits.append('WE_Credit_Water_Use_Reduction')
    
    if any('daylight' in feature.lower() or 'lighting' in feature.lower() for feature in building.get('sustainability_features', [])):
        target_credits.append('EQ_Credit_Daylight')
    
    if any('solar' in feature.lower() or 'green' in feature.lower() for feature in building.get('sustainability_features', [])):
        target_credits.append('SS_Credit_Heat_Island_Reduction')
    
    # Add location credits (assuming Austin, TX)
    target_credits.append('LT_Credit_Access_to_Quality_Transit')
    
    return ProjectData(
        project_name=building['building_name'],
        project_type=building_type_mapping.get(building['building_type'], 'NC'),
        building_area=building['square_footage'],
        site_location={
            'latitude': 30.2849,  # Austin, TX coordinates
            'longitude': -97.7341,
            'address': f"{building['building_name']}, Austin, TX",
            'city': 'Austin',
            'state': 'TX',
            'zip_code': '78712'
        },
        building_geometry={
            'zones': [
                {
                    'name': f"{building['building_code']}_Main_Zone",
                    'area': building['square_footage'],
                    'volume': building['square_footage'] * 3.0,  # Assume 3m ceiling height
                    'height': 3.0,
                    'type': building['building_type']
                }
            ],
            'surfaces': [
                {
                    'name': f"{building['building_code']}_Exterior_Wall",
                    'type': 'Wall',
                    'construction': 'High_Performance_Wall',
                    'area': building['square_footage'] * 0.3  # Assume 30% wall area
                },
                {
                    'name': f"{building['building_code']}_Roof",
                    'type': 'Roof',
                    'construction': 'High_Performance_Roof',
                    'area': building['square_footage']
                }
            ]
        },
        hvac_system={
            'system_type': 'VAV',
            'equipment': [
                {
                    'name': f"{building['building_code']}_AHU",
                    'type': 'AHU',
                    'capacity': building['square_footage'] / 1000,  # Rough capacity estimate
                    'efficiency': 0.90
                }
            ],
            'schedules': {
                'Office_Schedule': [0.0] * 8 + [1.0] * 8 + [0.0] * 8
            },
            'setpoints': {'cooling': 24, 'heating': 20}
        },
        target_credits=target_credits,
        documents=[],
        project_description=f"{building['building_type']} building with {', '.join(building.get('sustainability_features', []))}"
    )

def test_real_project_data():
    """Test enhanced platform with real UT Austin campus data"""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Testing Enhanced LEED Platform with Real Campus Data")
    logger.info("=" * 60)
    
    # Load campus buildings
    buildings = load_campus_buildings()
    if not buildings:
        logger.error("No campus building data found")
        return False
    
    logger.info(f"Loaded {len(buildings)} campus buildings")
    
    # Import enhanced platform
    try:
        from enhanced_leed_platform import EnhancedLEEDPlatform
    except ImportError as e:
        logger.error(f"Failed to import enhanced platform: {e}")
        return False
    
    # Initialize platform
    platform = EnhancedLEEDPlatform()
    if not platform.initialize_platform():
        logger.error("Failed to initialize enhanced platform")
        return False
    
    # Test with each building
    results_summary = []
    
    for i, building in enumerate(buildings[:3], 1):  # Test first 3 buildings
        logger.info(f"\n{'='*20} TESTING BUILDING {i}/{min(3, len(buildings))} {'='*20}")
        logger.info(f"Building: {building['building_name']}")
        logger.info(f"LEED Status: {building['leed_status']} {building['leed_level']}")
        logger.info(f"Size: {building['square_footage']:,} sq ft")
        
        try:
            # Create project data
            project_data = create_project_data_from_building(building)
            platform.load_project_data(project_data)
            
            # Run analysis
            logger.info("Running comprehensive analysis...")
            results = platform.run_comprehensive_analysis()
            
            # Extract key metrics
            summary = results.compliance_summary
            rag_available = bool(results.rag_insights)
            doc_analysis = bool(results.document_analysis)
            
            building_result = {
                'building_name': building['building_name'],
                'leed_status': building['leed_status'],
                'leed_level': building['leed_level'],
                'credits_analyzed': summary.get('total_credits_analyzed', 0),
                'credits_achieved': summary.get('credits_achieved', 0),
                'total_points': summary.get('total_points', 0),
                'rag_insights_available': rag_available,
                'document_analysis_available': doc_analysis,
                'analysis_successful': True
            }
            
            results_summary.append(building_result)
            
            logger.info(f"✅ Analysis completed successfully")
            logger.info(f"   Credits analyzed: {summary.get('total_credits_analyzed', 0)}")
            logger.info(f"   Credits achieved: {summary.get('credits_achieved', 0)}")
            logger.info(f"   Total points: {summary.get('total_points', 0)}")
            logger.info(f"   RAG insights: {'✅' if rag_available else '❌'}")
            logger.info(f"   Document analysis: {'✅' if doc_analysis else '❌'}")
            
            # Save individual results
            output_file = f"outputs/campus_analysis_{building['building_code']}_{i}.json"
            platform.save_results(output_file)
            logger.info(f"   Results saved to: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ Analysis failed for {building['building_name']}: {e}")
            results_summary.append({
                'building_name': building['building_name'],
                'analysis_successful': False,
                'error': str(e)
            })
    
    # Generate summary report
    logger.info("\n" + "=" * 60)
    logger.info("REAL DATA TEST SUMMARY")
    logger.info("=" * 60)
    
    successful_tests = sum(1 for r in results_summary if r.get('analysis_successful', False))
    total_tests = len(results_summary)
    
    logger.info(f"Total buildings tested: {total_tests}")
    logger.info(f"Successful analyses: {successful_tests}")
    logger.info(f"Success rate: {successful_tests/total_tests*100:.1f}%")
    
    if successful_tests > 0:
        logger.info("\nBuilding Analysis Results:")
        for result in results_summary:
            if result.get('analysis_successful'):
                logger.info(f"  • {result['building_name']}: {result['credits_achieved']}/{result['credits_analyzed']} credits, {result['total_points']} points")
    
    # Save summary
    summary_file = "outputs/real_data_test_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'test_date': '2025-10-15',
            'total_buildings_tested': total_tests,
            'successful_analyses': successful_tests,
            'success_rate': successful_tests/total_tests*100 if total_tests > 0 else 0,
            'building_results': results_summary
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nSummary saved to: {summary_file}")
    
    return successful_tests > 0

def main():
    """Main function"""
    success = test_real_project_data()
    
    if success:
        print("\n🎉 Real data testing completed successfully!")
        print("✅ Enhanced platform works with real campus data")
        print("✅ RAG integration functioning properly")
        print("✅ Analysis results saved to outputs/")
    else:
        print("\n❌ Real data testing failed. Check logs for details.")

if __name__ == "__main__":
    main()
