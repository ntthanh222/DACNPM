import re
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

class MatchingService:
    """Service to match CVEs with assets and compute risk scores."""

    @staticmethod
    def parse_cpe(cpe_str: str) -> Dict[str, str]:
        """
        Parses a CPE 2.3 or 2.2 string.
        Format: cpe:2.3:a:vendor:product:version:update:edition:language:...
        """
        result = {"part": "", "vendor": "", "product": "", "version": "", "update": ""}
        if not cpe_str:
            return result
        
        parts = cpe_str.split(":")
        if len(parts) >= 6:
            # CPE 2.3
            result["part"] = parts[2]
            result["vendor"] = parts[3]
            result["product"] = parts[4]
            result["version"] = parts[5]
            if len(parts) >= 7:
                result["update"] = parts[6]
        elif len(parts) >= 4:
            # CPE 2.2 style or partial format
            result["vendor"] = parts[2]
            result["product"] = parts[3]
            if len(parts) >= 5:
                result["version"] = parts[4]
        return result

    @classmethod
    def match_cpe(cls, asset_cpe: str, cve_cpe: str) -> tuple[bool, float, str]:
        """
        Compare two CPE strings and return a tuple of (is_match, confidence_score, reason).
        """
        if not asset_cpe or not cve_cpe:
            return False, 0.0, "Missing CPE information"

        asset_parts = cls.parse_cpe(asset_cpe)
        cve_parts = cls.parse_cpe(cve_cpe)

        if not asset_parts["vendor"] or not cve_parts["vendor"]:
            return False, 0.0, "Missing vendor info in CPE"

        # Check vendor and product (allowing case-insensitive and substring/regex variations)
        vendor_match = asset_parts["vendor"].lower() == cve_parts["vendor"].lower()
        product_match = asset_parts["product"].lower() == cve_parts["product"].lower()

        if not vendor_match or not product_match:
            # Try fuzzy check if vendor and product are close or substrings
            if (asset_parts["product"].lower() in cve_parts["product"].lower() or 
                    cve_parts["product"].lower() in asset_parts["product"].lower()) and \
                    asset_parts["vendor"].lower() == cve_parts["vendor"].lower():
                # Weak match
                return True, 0.5, f"Partial product match: {asset_parts['product']} vs {cve_parts['product']}"
            return False, 0.0, "Vendor or Product mismatch"

        # Compare version
        asset_ver = asset_parts["version"]
        cve_ver = cve_parts["version"]

        if cve_ver in ["*", "-", "any"]:
            return True, 1.0, "Product match with wildcard version in CVE"

        if asset_ver == cve_ver:
            return True, 1.0, "Exact match on vendor, product, and version"

        # Simple range match fallback
        try:
            # Try to see if it is a substring or standard match
            if asset_ver in cve_ver or cve_ver in asset_ver:
                return True, 0.8, f"Version partial match: {asset_ver} vs {cve_ver}"
        except Exception:
            pass

        return False, 0.0, "Version mismatch"

    @staticmethod
    def calculate_risk_score(
        cvss_score: float,
        criticality: str,
        internet_exposure: bool = False,
        known_exploited: bool = False,
        patch_available: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate a multi-factor risk score (0-100).
        - CVSS score (60% weight)
        - Asset criticality (20% weight): critical=20, high=15, medium=10, low=5
        - Internet exposure (10% weight): exposed=10, local=0
        - Exploit availability (10% weight): exploited=10, none=0
        - Mitigation: patch unavailable = +5 pts, patch available = 0
        """
        # 1. CVSS Base contribution (max 60)
        cvss_contrib = (cvss_score / 10.0) * 60.0

        # 2. Criticality contribution (max 20)
        crit_map = {"critical": 20, "high": 15, "medium": 10, "low": 5}
        crit_contrib = crit_map.get(criticality.lower(), 10)

        # 3. Internet exposure contribution (max 10)
        exposure_contrib = 10.0 if internet_exposure else 0.0

        # 4. Exploit availability contribution (max 10)
        exploit_contrib = 10.0 if known_exploited else 0.0

        # Calculate raw score
        raw_score = cvss_contrib + crit_contrib + exposure_contrib + exploit_contrib

        # Add modifier for patch availability
        if not patch_available:
            raw_score += 5.0

        # Cap score between 0 and 100
        final_score = min(max(raw_score, 0.0), 100.0)

        # Determine severity level
        if final_score >= 85.0:
            severity = "critical"
        elif final_score >= 70.0:
            severity = "high"
        elif final_score >= 40.0:
            severity = "medium"
        else:
            severity = "low"

        return {
            "score": round(final_score, 1),
            "severity": severity,
            "explanation": (
                f"CVSS contrib: {cvss_contrib:.1f}/60, "
                f"Asset criticality: {crit_contrib:.1f}/20, "
                f"Internet exposure: {exposure_contrib:.1f}/10, "
                f"Exploit info: {exploit_contrib:.1f}/10, "
                f"No patch modifier: {5.0 if not patch_available else 0.0:.1f}"
            )
        }
