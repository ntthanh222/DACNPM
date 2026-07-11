"""
Knowledge Base Client (Phase 3.2: Semantic Graph Search)

Provides knowledge base functionality for complex security queries
using semantic relationships between devices, OS versions, and CVEs.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SecurityKnowledgeGraph:
    """
    Knowledge base for security context queries using semantic graph search.

    This allows answering complex questions like:
    - "Router XYZ running OS v1.2 có bị CVE-2024-1234 ảnh hưởng không?"
    - "Which devices are affected by this CVE?"
    - "What vulnerabilities affect my infrastructure?"

    For now, this is a simplified implementation using database queries.
    Future versions can integrate with graph databases like Neo4j or Weaviate.
    """

    def __init__(self):
        """Initialize the security knowledge graph"""
        self._init_mock_data()
        logger.info("✅ Security Knowledge Graph initialized")

    def _init_mock_data(self):
        """Initialize mock knowledge base data for demonstration"""
        self.device_vulnerabilities = {
            'router': {
                'Cisco': {
                    'IOS 15.1': ['CVE-2024-1234', 'CVE-2024-5678'],
                    'IOS 15.2': ['CVE-2024-1234'],
                    'IOS 16.0': []
                },
                'Juniper': {
                    'Junos 21.1': ['CVE-2024-9999'],
                    'Junos 21.2': []
                }
            },
            'firewall': {
                'Palo Alto': {
                    'PAN-OS 10.1': ['CVE-2024-1111'],
                    'PAN-OS 10.2': []
                },
                'Fortinet': {
                    'FortiOS 7.2': ['CVE-2024-2222']
                }
            },
            'server': {
                'Windows': {
                    'Server 2019': ['CVE-2024-3333'],
                    'Server 2022': ['CVE-2024-4444']
                },
                'Linux': {
                    'Ubuntu 20.04': ['CVE-2024-5555'],
                    'Ubuntu 22.04': ['CVE-2024-6666']
                }
            }
        }

        self.cve_details = {
            'CVE-2024-1234': {
                'severity': 'high',
                'cvss': '8.5',
                'description': 'Cisco IOS Unauthorized Access Vulnerability',
                'patched_versions': ['IOS 15.2(3)E', 'IOS 16.0(1)']
            },
            'CVE-2024-5678': {
                'severity': 'critical',
                'cvss': '9.8',
                'description': 'Cisco IOS Remote Code Execution',
                'patched_versions': ['IOS 16.0(2)']
            },
            'CVE-2024-9999': {
                'severity': 'medium',
                'cvss': '6.5',
                'description': 'Juniper Junos Denial of Service',
                'patched_versions': ['Junos 21.2R1']
            },
            'CVE-2024-1111': {
                'severity': 'high',
                'cvss': '8.2',
                'description': 'Palo Alto PAN-OS Authentication Bypass',
                'patched_versions': ['PAN-OS 10.1.8', 'PAN-OS 10.2.2']
            },
            'CVE-2024-2222': {
                'severity': 'critical',
                'cvss': '9.5',
                'description': 'Fortinet FortiOS RCE Vulnerability',
                'patched_versions': ['FortiOS 7.2.5']
            }
        }

    def query_device_vulnerabilities(
        self,
        device_type: str,
        vendor: Optional[str] = None,
        os_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query vulnerabilities affecting a specific device.

        Args:
            device_type: Type of device (router, firewall, server, etc.)
            vendor: Optional vendor name
            os_version: Optional OS version

        Returns:
            List of vulnerabilities affecting the device
        """
        device_type = device_type.lower()
        results = []

        # Check if device type exists
        if device_type not in self.device_vulnerabilities:
            logger.warning(f"Unknown device type: {device_type}")
            return []

        vendors = self.device_vulnerabilities[device_type]

        # If no vendor specified, return all vulnerabilities for device type
        if not vendor:
            for vendor_name, os_versions in vendors.items():
                for os_ver, cves in os_versions.items():
                    for cve_id in cves:
                        results.append({
                            'cve_id': cve_id,
                            'device_type': device_type,
                            'vendor': vendor_name,
                            'os_version': os_ver,
                            'details': self.cve_details.get(cve_id, {})
                        })
        else:
            # Query specific vendor
            if vendor not in vendors:
                logger.warning(f"Unknown vendor {vendor} for device type {device_type}")
                return []

            os_versions = vendors[vendor]

            # If no OS version specified, return all vulnerabilities for vendor
            if not os_version:
                for os_ver, cves in os_versions.items():
                    for cve_id in cves:
                        results.append({
                            'cve_id': cve_id,
                            'device_type': device_type,
                            'vendor': vendor,
                            'os_version': os_ver,
                            'details': self.cve_details.get(cve_id, {})
                        })
            else:
                # Query specific OS version
                if os_version not in os_versions:
                    logger.warning(f"Unknown OS version {os_version} for {vendor} {device_type}")
                    return []

                cves = os_versions[os_version]
                for cve_id in cves:
                    results.append({
                        'cve_id': cve_id,
                        'device_type': device_type,
                        'vendor': vendor,
                        'os_version': os_version,
                        'details': self.cve_details.get(cve_id, {})
                    })

        return results

    def query_cve_device_impact(self, cve_id: str) -> List[Dict[str, Any]]:
        """
        Query which devices are affected by a specific CVE.

        Args:
            cve_id: CVE ID to query

        Returns:
            List of affected devices
        """
        results = []
        cve_id = cve_id.upper()

        # Search through all device types
        for device_type, vendors in self.device_vulnerabilities.items():
            for vendor, os_versions in vendors.items():
                for os_ver, cves in os_versions.items():
                    if cve_id in cves:
                        results.append({
                            'device_type': device_type,
                            'vendor': vendor,
                            'os_version': os_ver,
                            'cve_id': cve_id,
                            'details': self.cve_details.get(cve_id, {})
                        })

        return results

    def query_patch_availability(
        self,
        cve_id: str,
        device_type: Optional[str] = None,
        vendor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query patch availability for a CVE.

        Args:
            cve_id: CVE ID
            device_type: Optional device type filter
            vendor: Optional vendor filter

        Returns:
            Patch availability information
        """
        cve_id = cve_id.upper()
        cve_data = self.cve_details.get(cve_id)

        if not cve_data:
            return {
                'cve_id': cve_id,
                'found': False,
                'message': 'CVE not found in knowledge base'
            }

        affected_devices = self.query_cve_device_impact(cve_id)

        # Apply filters
        if device_type:
            affected_devices = [d for d in affected_devices if d['device_type'] == device_type.lower()]

        if vendor:
            affected_devices = [d for d in affected_devices if d['vendor'] == vendor]

        patched_versions = cve_data.get('patched_versions', [])

        return {
            'cve_id': cve_id,
            'found': True,
            'severity': cve_data.get('severity'),
            'cvss': cve_data.get('cvss'),
            'description': cve_data.get('description'),
            'affected_devices': affected_devices,
            'patched_versions': patched_versions,
            'patch_available': len(patched_versions) > 0
        }

    def query_infrastructure_vulnerabilities(
        self,
        infrastructure: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query all vulnerabilities affecting an infrastructure.

        Args:
            infrastructure: Dict describing infrastructure with devices, vendors, versions

        Returns:
            Vulnerabilities grouped by device
        """
        results = {}

        for device in infrastructure.get('devices', []):
            device_type = device.get('type')
            vendor = device.get('vendor')
            os_version = device.get('os_version')
            device_name = device.get('name', f"{vendor} {device_type}")

            vulns = self.query_device_vulnerabilities(device_type, vendor, os_version)

            results[device_name] = vulns

        return results

    def search_related_vulnerabilities(
        self,
        cve_id: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for related vulnerabilities (same device type, similar severity).

        Args:
            cve_id: Reference CVE ID
            max_results: Maximum number of results

        Returns:
            List of related vulnerabilities
        """
        cve_id = cve_id.upper()
        related = []

        # Get affected devices for this CVE
        affected_devices = self.query_cve_device_impact(cve_id)

        if not affected_devices:
            return []

        # Get reference CVE details
        ref_cve = self.cve_details.get(cve_id, {})
        ref_severity = ref_cve.get('severity', 'unknown')

        # Find devices affected by this CVE
        for device in affected_devices:
            device_type = device['device_type']
            vendor = device['vendor']

            # Find other vulnerabilities for same device/vendor
            vulns = self.query_device_vulnerabilities(device_type, vendor)

            for vuln in vulns:
                if vuln['cve_id'] != cve_id:
                    vuln_details = vuln.get('details', {})

                    # Check if similar severity
                    if vuln_details.get('severity') == ref_severity:
                        related.append({
                            'cve_id': vuln['cve_id'],
                            'similarity_reason': f"Same severity ({ref_severity})",
                            'device_type': device_type,
                            'vendor': vendor,
                            'details': vuln_details
                        })

                    if len(related) >= max_results:
                        break

            if len(related) >= max_results:
                break

        return related[:max_results]


def get_knowledge_base_singleton():
    """
    Get or create the singleton SecurityKnowledgeGraph instance.

    Returns:
        SecurityKnowledgeGraph instance
    """
    global _knowledge_base_instance

    if _knowledge_base_instance is None:
        _knowledge_base_instance = SecurityKnowledgeGraph()

    return _knowledge_base_instance


# Global singleton instance
_knowledge_base_instance = None
