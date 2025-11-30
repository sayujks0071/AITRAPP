"""
Compliance Package

Provides compliance enforcement for SEBI/NSE 2025 requirements:
- Rate limiting (<10 OPS)
- Kill switch checks
- Static IP verification
"""

from packages.core.compliance.guard import ComplianceGuard

# Import helper functions from the compliance.py module file (not this package)
# Use importlib to avoid name clash between package and module
import importlib.util
from pathlib import Path

_compliance_module_file = Path(__file__).parent.parent / "compliance.py"
if _compliance_module_file.exists():
    _spec = importlib.util.spec_from_file_location("compliance_module", str(_compliance_module_file))
    _compliance_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_compliance_module)
    
    # Re-export the helper functions
    check_static_ip = _compliance_module.check_static_ip
    check_oauth_fresh = _compliance_module.check_oauth_fresh
    check_family_only = _compliance_module.check_family_only
    tops_cap_ok = _compliance_module.tops_cap_ok
    algo_id_present = _compliance_module.algo_id_present
else:
    # Fallback if file doesn't exist (shouldn't happen)
    check_static_ip = None
    check_oauth_fresh = None
    check_family_only = None
    tops_cap_ok = None
    algo_id_present = None

__all__ = [
    "ComplianceGuard",
    "check_static_ip",
    "check_oauth_fresh",
    "check_family_only",
    "tops_cap_ok",
    "algo_id_present",
]



