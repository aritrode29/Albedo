#!/usr/bin/env python3
"""
Location-Based Analysis Module
Based on the research paper's GIS integration for LEED location and transportation credits.
Handles site selection, transportation access, and environmental context analysis.
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import math

# GIS components
try:
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import Point, Polygon
    GIS_AVAILABLE = True
except ImportError:
    GIS_AVAILABLE = False

@dataclass
class SiteLocation:
    """Site location data structure"""
    latitude: float
    longitude: float
    address: str
    city: str
    state: str
    zip_code: str

@dataclass
class TransitInfo:
    """Public transit information"""
    stop_name: str
    distance_meters: float
    route_type: str  # bus, rail, ferry
    frequency: int  # trips per day
    weekend_service: bool

@dataclass
class WalkabilityData:
    """Walkability analysis data"""
    walk_score: int
    nearby_uses: List[str]
    sidewalk_coverage: float
    crosswalk_density: float

@dataclass
class EnvironmentalContext:
    """Environmental context data"""
    flood_zone: bool
    sensitive_habitat: bool
    prime_farmland: bool
    wetland_proximity: float
    water_body_proximity: float

class LocationAnalyzer:
    """
    Location-based analysis for LEED credits.
    Based on the research paper's GIS and external API integration.
    """
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.api_keys = api_keys or {}
        self.logger = logging.getLogger(__name__)
        
        # API endpoints
        self.walkscore_api = "https://api.walkscore.com/score"
        self.transit_api = "https://transit.land/api/v2"
        self.census_api = "https://api.census.gov/data"
    
    def analyze_site_location(self, site_location: SiteLocation) -> Dict[str, Any]:
        """
        Comprehensive site location analysis for LEED credits.
        Based on the research paper's location evaluation methodology.
        """
        analysis = {
            'site_location': site_location,
            'transit_access': {},
            'walkability': {},
            'environmental_context': {},
            'leed_credits': {}
        }
        
        try:
            # Analyze transit access
            analysis['transit_access'] = self._analyze_transit_access(site_location)
            
            # Analyze walkability
            analysis['walkability'] = self._analyze_walkability(site_location)
            
            # Analyze environmental context
            analysis['environmental_context'] = self._analyze_environmental_context(site_location)
            
            # Evaluate LEED credits
            analysis['leed_credits'] = self._evaluate_leed_credits(analysis)
            
        except Exception as e:
            self.logger.error(f"Error analyzing site location: {e}")
        
        return analysis
    
    def _analyze_transit_access(self, site_location: SiteLocation) -> Dict[str, Any]:
        """Analyze public transit access for LT credits"""
        transit_analysis = {
            'nearby_stops': [],
            'total_trips': 0,
            'weekend_trips': 0,
            'qualifying_routes': 0,
            'lt_credit_points': 0
        }
        
        try:
            # Get nearby transit stops (simulated data for demonstration)
            nearby_stops = self._get_nearby_transit_stops(site_location)
            transit_analysis['nearby_stops'] = nearby_stops
            
            # Calculate total trips
            total_trips = sum(stop.get('frequency', 0) for stop in nearby_stops)
            transit_analysis['total_trips'] = total_trips
            
            # Calculate weekend trips
            weekend_trips = sum(stop.get('frequency', 0) for stop in nearby_stops if stop.get('weekend_service', False))
            transit_analysis['weekend_trips'] = weekend_trips
            
            # Determine LT credit points based on research paper thresholds
            if total_trips >= 360 and weekend_trips >= 216:
                transit_analysis['lt_credit_points'] = 5
            elif total_trips >= 250 and weekend_trips >= 160:
                transit_analysis['lt_credit_points'] = 4
            elif total_trips >= 144 and weekend_trips >= 108:
                transit_analysis['lt_credit_points'] = 3
            elif total_trips >= 100 and weekend_trips >= 70:
                transit_analysis['lt_credit_points'] = 2
            elif total_trips >= 72 and weekend_trips >= 30:
                transit_analysis['lt_credit_points'] = 1
            
        except Exception as e:
            self.logger.error(f"Error analyzing transit access: {e}")
        
        return transit_analysis
    
    def _get_nearby_transit_stops(self, site_location: SiteLocation) -> List[Dict[str, Any]]:
        """Get nearby transit stops (simulated for demonstration)"""
        # This would normally use real transit APIs
        # For demonstration, return simulated data
        return [
            {
                'stop_name': 'Main St Bus Stop',
                'distance_meters': 200,
                'route_type': 'bus',
                'frequency': 120,
                'weekend_service': True
            },
            {
                'stop_name': 'Central Station',
                'distance_meters': 800,
                'route_type': 'rail',
                'frequency': 240,
                'weekend_service': True
            }
        ]
    
    def _analyze_walkability(self, site_location: SiteLocation) -> Dict[str, Any]:
        """Analyze walkability for LT credits"""
        walkability_analysis = {
            'walk_score': 0,
            'nearby_uses': [],
            'diverse_uses_count': 0,
            'lt_credit_points': 0
        }
        
        try:
            # Get walk score (simulated)
            walk_score = self._get_walk_score(site_location)
            walkability_analysis['walk_score'] = walk_score
            
            # Get nearby uses
            nearby_uses = self._get_nearby_uses(site_location)
            walkability_analysis['nearby_uses'] = nearby_uses
            walkability_analysis['diverse_uses_count'] = len(nearby_uses)
            
            # Determine LT credit points based on walk score
            if walk_score >= 90:
                walkability_analysis['lt_credit_points'] = 5
            elif walk_score >= 80:
                walkability_analysis['lt_credit_points'] = 4
            elif walk_score >= 70:
                walkability_analysis['lt_credit_points'] = 3
            elif walk_score >= 60:
                walkability_analysis['lt_credit_points'] = 2
            elif walk_score >= 50:
                walkability_analysis['lt_credit_points'] = 1
            
        except Exception as e:
            self.logger.error(f"Error analyzing walkability: {e}")
        
        return walkability_analysis
    
    def _get_walk_score(self, site_location: SiteLocation) -> int:
        """Get walk score from API (simulated)"""
        # This would normally call the Walk Score API
        # For demonstration, return simulated score
        return 75  # Simulated walk score
    
    def _get_nearby_uses(self, site_location: SiteLocation) -> List[str]:
        """Get nearby uses within walking distance (simulated)"""
        # This would normally use real APIs or GIS data
        return [
            'Restaurant',
            'Retail Store',
            'Bank',
            'Post Office',
            'Library',
            'Park',
            'Coffee Shop',
            'Pharmacy'
        ]
    
    def _analyze_environmental_context(self, site_location: SiteLocation) -> Dict[str, Any]:
        """Analyze environmental context for SS credits"""
        env_analysis = {
            'flood_zone': False,
            'sensitive_habitat': False,
            'prime_farmland': False,
            'wetland_proximity': 0.0,
            'water_body_proximity': 0.0,
            'ss_credit_points': 0
        }
        
        try:
            # Check flood zone (simulated)
            env_analysis['flood_zone'] = self._check_flood_zone(site_location)
            
            # Check sensitive habitat (simulated)
            env_analysis['sensitive_habitat'] = self._check_sensitive_habitat(site_location)
            
            # Check prime farmland (simulated)
            env_analysis['prime_farmland'] = self._check_prime_farmland(site_location)
            
            # Calculate wetland proximity
            env_analysis['wetland_proximity'] = self._calculate_wetland_proximity(site_location)
            
            # Calculate water body proximity
            env_analysis['water_body_proximity'] = self._calculate_water_body_proximity(site_location)
            
            # Determine SS credit points
            if not env_analysis['flood_zone'] and not env_analysis['sensitive_habitat'] and not env_analysis['prime_farmland']:
                env_analysis['ss_credit_points'] = 1
            
        except Exception as e:
            self.logger.error(f"Error analyzing environmental context: {e}")
        
        return env_analysis
    
    def _check_flood_zone(self, site_location: SiteLocation) -> bool:
        """Check if site is in flood zone (simulated)"""
        # This would normally use FEMA flood maps or similar data
        return False  # Simulated result
    
    def _check_sensitive_habitat(self, site_location: SiteLocation) -> bool:
        """Check if site contains sensitive habitat (simulated)"""
        # This would normally use environmental databases
        return False  # Simulated result
    
    def _check_prime_farmland(self, site_location: SiteLocation) -> bool:
        """Check if site is on prime farmland (simulated)"""
        # This would normally use USDA soil data
        return False  # Simulated result
    
    def _calculate_wetland_proximity(self, site_location: SiteLocation) -> float:
        """Calculate distance to nearest wetland (simulated)"""
        # This would normally use GIS data
        return 1000.0  # Simulated distance in meters
    
    def _calculate_water_body_proximity(self, site_location: SiteLocation) -> float:
        """Calculate distance to nearest water body (simulated)"""
        # This would normally use GIS data
        return 500.0  # Simulated distance in meters
    
    def _evaluate_leed_credits(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate LEED credits based on location analysis"""
        leed_credits = {
            'LT_Credit_Access_to_Quality_Transit': {
                'status': 'Not Achieved',
                'points': 0,
                'requirements_met': [],
                'requirements_missing': []
            },
            'LT_Credit_Surrounding_Density_and_Diverse_Uses': {
                'status': 'Not Achieved',
                'points': 0,
                'requirements_met': [],
                'requirements_missing': []
            },
            'SS_Credit_Sensitive_Land_Protection': {
                'status': 'Not Achieved',
                'points': 0,
                'requirements_met': [],
                'requirements_missing': []
            }
        }
        
        try:
            # Evaluate Transit Credit
            transit_points = analysis['transit_access'].get('lt_credit_points', 0)
            if transit_points > 0:
                leed_credits['LT_Credit_Access_to_Quality_Transit']['status'] = f'Achieved ({transit_points} points)'
                leed_credits['LT_Credit_Access_to_Quality_Transit']['points'] = transit_points
                leed_credits['LT_Credit_Access_to_Quality_Transit']['requirements_met'].append(
                    f"Transit service meets minimum thresholds ({analysis['transit_access']['total_trips']} weekday trips, {analysis['transit_access']['weekend_trips']} weekend trips)"
                )
            else:
                leed_credits['LT_Credit_Access_to_Quality_Transit']['requirements_missing'].append(
                    "Insufficient transit service within walking distance"
                )
            
            # Evaluate Walkability Credit
            walkability_points = analysis['walkability'].get('lt_credit_points', 0)
            if walkability_points > 0:
                leed_credits['LT_Credit_Surrounding_Density_and_Diverse_Uses']['status'] = f'Achieved ({walkability_points} points)'
                leed_credits['LT_Credit_Surrounding_Density_and_Diverse_Uses']['points'] = walkability_points
                leed_credits['LT_Credit_Surrounding_Density_and_Diverse_Uses']['requirements_met'].append(
                    f"Walk Score of {analysis['walkability']['walk_score']} meets threshold"
                )
                leed_credits['LT_Credit_Surrounding_Density_and_Diverse_Uses']['requirements_met'].append(
                    f"Found {analysis['walkability']['diverse_uses_count']} diverse uses within walking distance"
                )
            else:
                leed_credits['LT_Credit_Surrounding_Density_and_Diverse_Uses']['requirements_missing'].append(
                    "Walk Score below minimum threshold"
                )
            
            # Evaluate Sensitive Land Protection Credit
            env_points = analysis['environmental_context'].get('ss_credit_points', 0)
            if env_points > 0:
                leed_credits['SS_Credit_Sensitive_Land_Protection']['status'] = f'Achieved ({env_points} point)'
                leed_credits['SS_Credit_Sensitive_Land_Protection']['points'] = env_points
                leed_credits['SS_Credit_Sensitive_Land_Protection']['requirements_met'].append(
                    "Site avoids sensitive lands (flood zones, prime farmland, sensitive habitat)"
                )
            else:
                leed_credits['SS_Credit_Sensitive_Land_Protection']['requirements_missing'].append(
                    "Site may be located on or near sensitive lands"
                )
            
        except Exception as e:
            self.logger.error(f"Error evaluating LEED credits: {e}")
        
        return leed_credits

class CensusDataAnalyzer:
    """
    Census data analysis for LEED location credits.
    Based on the research paper's demographic analysis.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
    
    def analyze_census_tract(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Analyze census tract data for LEED credits"""
        census_data = {
            'tract_id': '',
            'median_income': 0,
            'poverty_rate': 0.0,
            'unemployment_rate': 0.0,
            'population_density': 0,
            'lt_credit_eligible': False
        }
        
        try:
            # Get census tract ID from coordinates
            tract_id = self._get_census_tract_id(latitude, longitude)
            census_data['tract_id'] = tract_id
            
            # Get demographic data (simulated)
            demographic_data = self._get_demographic_data(tract_id)
            census_data.update(demographic_data)
            
            # Check if eligible for LT High Priority Site credit
            census_data['lt_credit_eligible'] = self._check_high_priority_eligibility(census_data)
            
        except Exception as e:
            self.logger.error(f"Error analyzing census data: {e}")
        
        return census_data
    
    def _get_census_tract_id(self, latitude: float, longitude: float) -> str:
        """Get census tract ID from coordinates (simulated)"""
        # This would normally use Census Geocoding API
        return "36061000100"  # Simulated tract ID
    
    def _get_demographic_data(self, tract_id: str) -> Dict[str, Any]:
        """Get demographic data for census tract (simulated)"""
        # This would normally use Census API
        return {
            'median_income': 65000,
            'poverty_rate': 0.15,
            'unemployment_rate': 0.08,
            'population_density': 2500
        }
    
    def _check_high_priority_eligibility(self, census_data: Dict[str, Any]) -> bool:
        """Check if site is eligible for High Priority Site credit"""
        # Based on LEED criteria from research paper
        median_income = census_data.get('median_income', 0)
        poverty_rate = census_data.get('poverty_rate', 0)
        unemployment_rate = census_data.get('unemployment_rate', 0)
        
        # Check if meets any of the criteria
        if median_income <= 65000:  # 80% of AMI threshold
            return True
        if poverty_rate >= 0.20:  # 20% poverty rate threshold
            return True
        if unemployment_rate >= 0.12:  # 150% of regional unemployment
            return True
        
        return False

class LocationReportGenerator:
    """
    Generate location-based LEED credit reports.
    Based on the research paper's report generation methodology.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_location_report(self, analysis: Dict[str, Any]) -> str:
        """Generate comprehensive location analysis report"""
        try:
            report = []
            
            # Site Information
            site = analysis['site_location']
            report.append(f"# Location Analysis Report")
            report.append(f"")
            report.append(f"## Site Information")
            report.append(f"- Address: {site.address}")
            report.append(f"- City: {site.city}, {site.state} {site.zip_code}")
            report.append(f"- Coordinates: {site.latitude}, {site.longitude}")
            report.append(f"")
            
            # Transit Analysis
            transit = analysis['transit_access']
            report.append(f"## Transit Access Analysis")
            report.append(f"- Total weekday trips: {transit['total_trips']}")
            report.append(f"- Weekend trips: {transit['weekend_trips']}")
            report.append(f"- Nearby stops: {len(transit['nearby_stops'])}")
            report.append(f"- LT Credit Points: {transit['lt_credit_points']}")
            report.append(f"")
            
            # Walkability Analysis
            walkability = analysis['walkability']
            report.append(f"## Walkability Analysis")
            report.append(f"- Walk Score: {walkability['walk_score']}")
            report.append(f"- Diverse uses: {walkability['diverse_uses_count']}")
            report.append(f"- LT Credit Points: {walkability['lt_credit_points']}")
            report.append(f"")
            
            # Environmental Context
            env = analysis['environmental_context']
            report.append(f"## Environmental Context")
            report.append(f"- Flood zone: {env['flood_zone']}")
            report.append(f"- Sensitive habitat: {env['sensitive_habitat']}")
            report.append(f"- Prime farmland: {env['prime_farmland']}")
            report.append(f"- SS Credit Points: {env['ss_credit_points']}")
            report.append(f"")
            
            # LEED Credit Summary
            leed_credits = analysis['leed_credits']
            report.append(f"## LEED Credit Summary")
            for credit_name, credit_data in leed_credits.items():
                report.append(f"### {credit_name}")
                report.append(f"- Status: {credit_data['status']}")
                report.append(f"- Points: {credit_data['points']}")
                if credit_data['requirements_met']:
                    report.append(f"- Requirements Met:")
                    for req in credit_data['requirements_met']:
                        report.append(f"  - {req}")
                if credit_data['requirements_missing']:
                    report.append(f"- Requirements Missing:")
                    for req in credit_data['requirements_missing']:
                        report.append(f"  - {req}")
                report.append(f"")
            
            return "\n".join(report)
            
        except Exception as e:
            self.logger.error(f"Error generating location report: {e}")
            return f"Error generating report: {e}"

def main():
    """Main function for testing the location analysis module"""
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    analyzer = LocationAnalyzer()
    report_generator = LocationReportGenerator()
    
    # Example site location
    site_location = SiteLocation(
        latitude=40.7128,
        longitude=-74.0060,
        address="123 Main Street",
        city="New York",
        state="NY",
        zip_code="10001"
    )
    
    # Analyze site location
    analysis = analyzer.analyze_site_location(site_location)
    
    # Generate report
    report = report_generator.generate_location_report(analysis)
    
    print("Location Analysis Module initialized successfully!")
    print("Sample analysis completed.")
    print("\n" + "="*50)
    print(report)

if __name__ == "__main__":
    main() 