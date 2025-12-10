"""
Patch Converter - Convert Agent Outputs to Patch Schema
=======================================================

Converts HiveMind agent outputs (CortexAnalyst, SG1StrategyGenerator) into
the standardized patch schema for config updates.
"""

from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime


def convert_sg1_to_patches(
    sg1_output: Dict[str, Any],
    analyst_output: Dict[str, Any],
    day: str = None,
) -> Dict[str, Any]:
    """
    Convert SG1StrategyGenerator output to patch schema.
    
    Args:
        sg1_output: Output from SG1StrategyGenerator.think()
        analyst_output: Output from CortexAnalyst.think() (for context)
        day: Date string (default: today)
    
    Returns:
        Patch document in the standardized format
    """
    if day is None:
        day = datetime.now().strftime("%Y-%m-%d")
    
    proposed_changes = sg1_output.get("proposed_changes", [])
    patches: List[Dict[str, Any]] = []
    
    for idx, change in enumerate(proposed_changes):
        patch_id = f"PATCH-{idx+1:03d}"
        
        patch = {
            "id": patch_id,
            "target": change.get("path", ""),
            "current_value": change.get("old_value"),
            "proposed_value": change.get("new_value"),
            "change_type": "tune",
            "reason": change.get("reason", ""),
            "priority": change.get("priority", "MEDIUM"),
            "bounds": _infer_bounds(change.get("path", ""), change.get("old_value")),
            "risk_officer": {
                "approved": sg1_output.get("changes_safe_to_apply_automatically", False),
                "comment": _generate_risk_comment(change, analyst_output),
            }
        }
        
        patches.append(patch)
    
    return {
        "day": day,
        "version": "v1",
        "source": "hivemind",
        "summary": sg1_output.get("summary", ""),
        "analyst_summary": analyst_output.get("summary", ""),
        "patches": patches,
    }


def _infer_bounds(path: str, current_value: Any) -> Dict[str, Any]:
    """
    Infer safe bounds for a config path based on its type and current value.
    """
    if not isinstance(current_value, (int, float)):
        return {}
    
    # Strategy-specific bounds
    if "target_delta" in path:
        return {"min": 0.10, "max": 0.50}
    elif "adx_threshold" in path:
        return {"min": 15, "max": 40}
    elif "max_portfolio_heat" in path:
        return {"min": 0.10, "max": 0.50}
    elif "max_position_size" in path:
        return {"min": 0.05, "max": 0.30}
    elif "stop_loss" in path or "stop_loss_pct" in path:
        return {"min": 0.01, "max": 0.20}
    elif "take_profit" in path or "take_profit_pct" in path:
        return {"min": 0.10, "max": 1.0}
    
    # Generic numeric bounds (±50% of current value)
    if isinstance(current_value, (int, float)) and current_value > 0:
        return {
            "min": current_value * 0.5,
            "max": current_value * 1.5,
        }
    
    return {}


def _generate_risk_comment(
    change: Dict[str, Any],
    analyst_output: Dict[str, Any]
) -> str:
    """
    Generate a risk officer comment based on the change and analyst insights.
    """
    priority = change.get("priority", "MEDIUM")
    reason = change.get("reason", "")
    
    # Check if analyst flagged any issues
    risk_flags = analyst_output.get("risk_flags", [])
    if risk_flags:
        return f"Analyst flagged risks: {', '.join(risk_flags[:2])}. Review recommended."
    
    if priority == "HIGH":
        return "High priority change. Verify against recent performance data."
    elif priority == "LOW":
        return "Low priority. Safe to auto-apply if within bounds."
    else:
        return "Medium priority. Standard review recommended."


def validate_patch_doc(patch_doc: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate a patch document structure.
    
    Returns:
        (is_valid, error_message)
    """
    if "day" not in patch_doc:
        return False, "Missing 'day' field"
    
    if "patches" not in patch_doc:
        return False, "Missing 'patches' field"
    
    if not isinstance(patch_doc["patches"], list):
        return False, "'patches' must be a list"
    
    for idx, patch in enumerate(patch_doc["patches"]):
        required_fields = ["id", "target", "proposed_value"]
        for field in required_fields:
            if field not in patch:
                return False, f"Patch {idx}: missing required field '{field}'"
    
    return True, ""




