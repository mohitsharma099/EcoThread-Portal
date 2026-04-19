"""
EcoThread Analytical Engine (v2.0) - Advanced Textile Science Core

This module contains the deep mathematical and chemical logic used for global 
sustainability metrics and toxicological chemical auditing in the textile industry.

Textile Science Context:
- Water impacts include blue (consumption), green (evaporation), and grey (pollution dilution).
- Carbon footprints cover agricultural inputs, spinning (ring vs open end), weaving, dyeing, and finishing.
- Chemical compliance relies on strict ppm (parts per million) limits under ZDHC (Zero Discharge)
  and REACH (EU Regulation) frameworks.
"""

from .database_seed import get_fiber_data, get_chemical_limit, get_chemical_data
import math
import logging
from typing import Dict, Any, List

# Setup logging for backend troubleshooting
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FootprintCalculator:
    """
    Advanced calculator for environmental metrics across complex textile supply chains.
    Accounts for mechanical vs chemical processing, blend ratios, and regional energy grids.
    """

    @staticmethod
    def _apply_regional_carbon_intensity(base_carbon: float, region: str) -> float:
        """
        Adjusts carbon footprint based on the energy grid carbon intensity of the manufacturing region.
        """
        intensity_factors = {
            "Global Average": 1.0,
            "China": 1.25,        # Higher reliance on coal for industrial grid
            "India": 1.18,
            "Bangladesh": 1.15,
            "Vietnam": 1.10,
            "US": 0.85,           # Mixed grid
            "EU": 0.65,           # Higher renewable penetration
            "Italy": 0.60,
            "Brazil": 0.45,       # Hydro-heavy grid
            "Turkey": 0.95,
            "Pakistan": 1.12,
            "Egypt": 1.05,
            "Indonesia": 1.14
        }
        
        factor = intensity_factors.get(region, 1.0)
        return base_carbon * factor

    @staticmethod
    def _calculate_grey_water_dilution(toxicity_score: float, volume_kg: float) -> float:
        """
        Calculates theoretical grey water required to dilute chemical effluent back to 
        safe ambient water quality standards.
        """
        # Base factor: 50 liters of grey water per kg of fabric per toxicity unit
        return volume_kg * toxicity_score * 50.0

    @staticmethod
    def calculate_total_impact(fiber_name: str, volume_kg: float, wet_processing_type: str = "Standard", region: str = "Global Average") -> Dict[str, Any]:
        """
        Comprehensive calculation of environmental impacts.
        
        Args:
            fiber_name (str): Full name of the fiber variant.
            volume_kg (float): Total mass of production.
            wet_processing_type (str): "Standard", "Low-Water Zero Discharge", "Heavy Dyeing"
            region (str): Manufacturing region.
            
        Returns:
            dict: Detailed metrics including blue/green/grey water, carbon breakdowns, and scores.
        """
        logger.info(f"Initiating footprint calculation for {volume_kg}kg of {fiber_name} in {region}.")
        
        try:
            if volume_kg <= 0:
                raise ValueError("Volume must be strictly positive.")
                
            fiber_data = get_fiber_data(fiber_name)
            if not fiber_data:
                raise KeyError(f"Fiber '{fiber_name}' is unregistered in the EcoThread DB.")
            
            # --- WATER CALCULATIONS ---
            # Extract base metrics
            base_water = fiber_data['water_footprint_l_per_kg']
            is_natural = fiber_data['biodegradable']
            
            # Textile Science: Natural fibers have high blue/green water (irrigation/rain).
            # Synthetics have lower blue water but higher grey water due to chemical intensity.
            if is_natural:
                blue_water_ratio = 0.6
                green_water_ratio = 0.35
                grey_water_ratio = 0.05
            else:
                blue_water_ratio = 0.2
                green_water_ratio = 0.0
                grey_water_ratio = 0.8
                
            # Adjust based on wet processing
            processing_multiplier = 1.0
            if wet_processing_type == "Low-Water Zero Discharge":
                processing_multiplier = 0.6
            elif wet_processing_type == "Heavy Dyeing":
                processing_multiplier = 1.4
                
            total_blue = (base_water * blue_water_ratio) * volume_kg * processing_multiplier
            total_green = (base_water * green_water_ratio) * volume_kg
            total_grey_base = (base_water * grey_water_ratio) * volume_kg * processing_multiplier
            
            # Add dynamic grey water based on microplastic risk
            mp_risk = fiber_data['microplastic_shedding_risk']
            mp_grey_add = FootprintCalculator._calculate_grey_water_dilution(
                toxicity_score=2.5 if mp_risk == "High" else 0.5,
                volume_kg=volume_kg
            )
            total_grey = total_grey_base + mp_grey_add
            total_water = total_blue + total_green + total_grey

            # --- CARBON CALCULATIONS ---
            base_carbon = fiber_data['carbon_footprint_kgCO2e_per_kg']
            regional_carbon = FootprintCalculator._apply_regional_carbon_intensity(base_carbon, region)
            
            # Additional processing carbon
            if wet_processing_type == "Heavy Dyeing":
                regional_carbon *= 1.25 # More thermal energy for dye vats
                
            total_carbon = regional_carbon * volume_kg
            
            # Scope breakdowns
            scope1_carbon = total_carbon * 0.15 # Direct fuel use in factory
            scope2_carbon = total_carbon * 0.55 # Purchased electricity
            scope3_carbon = total_carbon * 0.30 # Raw materials / Agriculture
            
            # --- ENERGY CALCULATIONS ---
            base_energy = fiber_data['energy_kwh_per_kg']
            total_energy = base_energy * volume_kg * (1.1 if wet_processing_type == "Heavy Dyeing" else 1.0)
            
            # --- SCORING HEURISTICS ---
            # Global median benchmarks per kg fabric: ~15kg CO2, ~1000L Water.
            normalized_water = (total_water / volume_kg) / 1000.0
            normalized_carbon = (total_carbon / volume_kg) / 15.0
            
            # Eco-Score out of 100 (100 = Perfect Sustainability, 0 = Catastrophic)
            # Higher normalized values mean worse score.
            penalty = (normalized_water * 30) + (normalized_carbon * 40)
            
            # Bonus for recycled content
            bonus = (fiber_data['recycled_content_pct'] / 100.0) * 15
            
            raw_score = 100 - penalty + bonus
            final_eco_score = max(0.0, min(100.0, raw_score))
            
            return {
                "status": "success",
                "fiber": fiber_name,
                "region": region,
                "process": wet_processing_type,
                "volume_kg": volume_kg,
                "water_metrics": {
                    "total_liters": round(total_water, 2),
                    "blue_water_L": round(total_blue, 2),
                    "green_water_L": round(total_green, 2),
                    "grey_water_L": round(total_grey, 2)
                },
                "carbon_metrics": {
                    "total_kgCO2e": round(total_carbon, 2),
                    "scope_1": round(scope1_carbon, 2),
                    "scope_2": round(scope2_carbon, 2),
                    "scope_3": round(scope3_carbon, 2),
                    "intensity": round(total_carbon / volume_kg, 2)
                },
                "energy_kwh": round(total_energy, 2),
                "materials": {
                    "recycled_pct": fiber_data['recycled_content_pct'],
                    "biodegradable": fiber_data['biodegradable'],
                    "microplastic_risk": mp_risk
                },
                "eco_score_100": round(final_eco_score, 1),
                "is_sustainable": final_eco_score >= 60.0 # Arbitrary threshold for 'good'
            }
            
        except Exception as e:
            logger.error(f"Computation failed in footprint calculator: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"Calculation logic fault: {str(e)}"}


class ChemicalAuditor:
    """
    Advanced audit engine for toxicological lab results.
    Evaluates against multiple stringent international standards (REACH, ZDHC, CPSIA).
    """
    
    @staticmethod
    def _determine_compliance_rating(detected_ppm: float, zdhc_limit: float, reach_limit: float) -> str:
        """Determines the strictness tier passed."""
        if detected_ppm == 0:
            return "UNDETECTED (Optimal)"
        if detected_ppm <= zdhc_limit:
            return "ZDHC MRSL Level 3 Compliant"
        if detected_ppm <= reach_limit:
            return "REACH Compliant (Warning: High for ZDHC)"
        return "NON-COMPLIANT"

    @staticmethod
    def _evaluate_cocktail_effect(lab_results: Dict[str, float]) -> Dict[str, Any]:
        """
        Textile Science: The "Cocktail Effect" refers to compounding toxicity of multiple 
        sub-threshold chemical groups interacting in effluent.
        """
        hazardous_groups_present = set()
        total_endocrine_disruptors = 0
        
        for chem, ppm in lab_results.items():
            if ppm > 0:
                chem_meta = get_chemical_data(chem)
                if chem_meta:
                    hazardous_groups_present.add(chem_meta.get("group", "Unknown"))
                    if chem_meta.get("hazard_class") == "Endocrine Disruptor":
                        total_endocrine_disruptors += 1
                        
        risk = "Low"
        if len(hazardous_groups_present) > 4:
            risk = "Medium - High Variety of Toxins"
        if total_endocrine_disruptors >= 2:
            risk = "High - Multiple Endocrine Disruptors Detected"
            
        return {
            "cocktail_risk_level": risk,
            "unique_chemical_groups": list(hazardous_groups_present)
        }

    @staticmethod
    def audit_batch(lab_results: Dict[str, float], target_standard: str = "ZDHC") -> Dict[str, Any]:
        """
        Executes a deep audit matrix on submitted lab concentrations.
        
        Args:
            lab_results (dict): e.g., {'Lead': 2.5, 'PFAS': 0.0}
            target_standard (str): 'ZDHC', 'REACH', or 'CPSIA'
            
        Returns:
            dict: Comprehensive safety audit.
        """
        logger.info(f"Initiating deep chemical audit against {target_standard} standard.")
        
        audit_report = {
            "overall_status": "Eco-Certified",
            "target_standard": target_standard,
            "total_tested": 0,
            "critical_failures": 0,
            "warnings": 0,
            "details": [],
            "cocktail_analysis": {}
        }
        
        try:
            if not isinstance(lab_results, dict):
                raise TypeError("Lab results must be a dictionary.")
                
            for chem_name, detected_ppm in lab_results.items():
                if detected_ppm < 0:
                    raise ValueError(f"Negative ppm provided for {chem_name}. Lab results must be positive.")
                    
                audit_report["total_tested"] += 1
                
                # Fetch full chemical metadata
                meta = get_chemical_data(chem_name)
                
                if not meta:
                    logger.warning(f"Chemical {chem_name} not found in DB.")
                    audit_report["details"].append({
                        "chemical": chem_name,
                        "detected_ppm": detected_ppm,
                        "status": "UNREGULATED",
                        "notes": "Not present in master compliance database."
                    })
                    audit_report["warnings"] += 1
                    continue
                
                # Extract limits
                zdhc_lim = meta.get("zdhc_mrsl_v3_limit_ppm", 0)
                reach_lim = meta.get("reach_limit_ppm", 0)
                
                # Choose evaluation limit based on target standard
                eval_limit = zdhc_lim if target_standard == "ZDHC" else reach_lim
                if target_standard == "CPSIA":
                    eval_limit = meta.get("cpsia_limit_ppm", reach_lim)
                    
                rating = ChemicalAuditor._determine_compliance_rating(detected_ppm, zdhc_lim, reach_lim)
                
                is_failed = False
                # If it's explicitly banned (is_banned = True in DB) and detected > 0
                if meta.get("is_banned") and detected_ppm > 0:
                    is_failed = True
                    rating = "CRITICAL FAILURE: Banned Substance Detected"
                    
                # If above the selected target limit
                if detected_ppm > eval_limit:
                    is_failed = True
                    
                audit_report["details"].append({
                    "chemical": chem_name,
                    "group": meta.get("group"),
                    "hazard_class": meta.get("hazard_class"),
                    "detected_ppm": detected_ppm,
                    "limit_ppm": eval_limit,
                    "status": "FAILED" if is_failed else "PASSED",
                    "rating_tier": rating
                })
                
                if is_failed:
                    audit_report["critical_failures"] += 1
                    audit_report["overall_status"] = "High Risk"
            
            # Post-processing: Cocktail Effect evaluation
            audit_report["cocktail_analysis"] = ChemicalAuditor._evaluate_cocktail_effect(lab_results)
            if "High" in audit_report["cocktail_analysis"]["cocktail_risk_level"]:
                audit_report["overall_status"] = "High Risk"
                
            return audit_report
            
        except Exception as e:
            logger.error(f"Audit engine failed: {str(e)}", exc_info=True)
            return {"overall_status": "Error", "message": f"Audit execution failed: {str(e)}"}
