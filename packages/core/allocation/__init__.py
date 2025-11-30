"""
Autonomous Capital Allocator (ACA) - Level 9
============================================

Level 9: Dynamic Capital Rebalancing Engine.

Components:
- AllocationVeto: The Gatekeeper (blocks underperforming strategies)
- AutonomousCapitalAllocator: The Central Bank (calculates and enforces allocations)
"""

from packages.core.allocation.allocator import AutonomousCapitalAllocator
from packages.core.allocation.veto import AllocationVeto

__all__ = ["AutonomousCapitalAllocator", "AllocationVeto"]
