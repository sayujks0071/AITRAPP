#!/usr/bin/env python3
"""
Apply HiveMind patches to configs/kite_day1_live.yaml with safety rails.

Usage:
  DRY RUN (recommended first):
    DRY_RUN=1 python scripts/apply_hivemind_patches.py \
      --config configs/kite_day1_live.yaml \
      --patch reports/hivemind/2025-11-21_hivemind_patches.json

  ACTUAL APPLY:
    python scripts/apply_hivemind_patches.py \
      --config configs/kite_day1_live.yaml \
      --patch reports/hivemind/2025-11-21_hivemind_patches.json
"""

import argparse
import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r") as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)


def load_patches(path: Path) -> Dict[str, Any]:
    with path.open("r") as f:
        return json.load(f)


def get_by_path(root: Dict[str, Any], path: str) -> Tuple[bool, Any]:
    """
    Get value from nested dict using dotted path.
    Returns (found, value).
    """
    parts = path.split(".")
    cur: Any = root
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return False, None
        cur = cur[p]
    return True, cur


def set_by_path(root: Dict[str, Any], path: str, value: Any) -> bool:
    """
    Set value in nested dict using dotted path.
    Returns True on success, False if path not found.
    """
    parts = path.split(".")
    cur: Any = root
    for p in parts[:-1]:
        if not isinstance(cur, dict) or p not in cur:
            return False
        cur = cur[p]
    last = parts[-1]
    if not isinstance(cur, dict) or last not in cur:
        return False
    cur[last] = value
    return True


def within_bounds(proposed: Any, bounds: Dict[str, Any]) -> bool:
    """
    Simple numeric guard. If bounds missing, allow.
    """
    if not isinstance(proposed, (int, float)):
        return True  # non-numeric, skip bound check for now

    lo = bounds.get("min", None)
    hi = bounds.get("max", None)
    if lo is not None and proposed < lo:
        return False
    if hi is not None and proposed > hi:
        return False
    return True


def apply_patches(
    cfg: Dict[str, Any],
    patch_doc: Dict[str, Any],
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Returns a new config dict with patches applied (if not dry_run).
    Prints a human-readable summary.
    """
    patches: List[Dict[str, Any]] = patch_doc.get("patches", [])
    new_cfg = copy.deepcopy(cfg)

    print(f"\n🔧 HiveMind Patches (dry_run={dry_run})")
    print(f"Day: {patch_doc.get('day')}, total patches: {len(patches)}\n")

    applied = 0
    held = 0
    rejected = 0
    skipped = 0

    for p in patches:
        pid = p.get("id", "<no-id>")
        target = p.get("target")
        current_value = p.get("current_value")
        proposed_value = p.get("proposed_value")
        ro = p.get("risk_officer", {}) or {}
        approved = bool(ro.get("approved", False))
        bounds = p.get("bounds", {}) or {}

        if not target:
            print(f"  • {pid}: SKIP (no target)")
            skipped += 1
            continue

        found, actual_current = get_by_path(cfg, target)
        if not found:
            print(f"  • {pid}: SKIP (target not found in config: {target})")
            skipped += 1
            continue

        # Sanity check: HiveMind's current_value vs actual config
        if current_value is not None and current_value != actual_current:
            print(
                f"  • {pid}: WARN (current_value mismatch; config={actual_current}, "
                f"patch={current_value}) → skipping for safety"
            )
            skipped += 1
            continue

        if not approved:
            print(f"  • {pid}: HOLD (not approved by RiskOfficer) {target} -> {proposed_value}")
            held += 1
            continue

        if not within_bounds(proposed_value, bounds):
            print(
                f"  • {pid}: REJECT (out of bounds) {target}: {proposed_value} "
                f"not in [{bounds.get('min')}, {bounds.get('max')}]"
            )
            rejected += 1
            continue

        print(
            f"  • {pid}: APPLY {target}: {actual_current} → {proposed_value} "
            f"(reason: {p.get('reason', '').strip()[:60]}...)"
        )

        if not dry_run:
            ok = set_by_path(new_cfg, target, proposed_value)
            if not ok:
                print(f"    ✖ Failed to set value at path: {target}")
            else:
                applied += 1
        else:
            applied += 1

    print()
    print(f"Summary: {applied} applied, {held} held, {rejected} rejected, {skipped} skipped")
    print()

    return new_cfg


def main():
    ap = argparse.ArgumentParser(
        description="Apply HiveMind patches to config with safety rails"
    )
    ap.add_argument(
        "--config",
        required=True,
        help="Path to base YAML config (e.g., configs/kite_day1_live.yaml)"
    )
    ap.add_argument(
        "--patch",
        required=True,
        help="Path to HiveMind patch JSON file"
    )
    args = ap.parse_args()

    cfg_path = Path(args.config)
    patch_path = Path(args.patch)

    if not cfg_path.exists():
        print(f"❌ Config file not found: {cfg_path}")
        return 1

    if not patch_path.exists():
        print(f"❌ Patch file not found: {patch_path}")
        return 1

    dry_run = os.getenv("DRY_RUN", "0") == "1"

    print("=" * 60)
    print("🔧 HIVEMIND CONFIG PATCHER")
    print("=" * 60)
    print(f"Config: {cfg_path}")
    print(f"Patch: {patch_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'APPLY'}")
    print()

    cfg = load_yaml(cfg_path)
    patch_doc = load_patches(patch_path)

    new_cfg = apply_patches(cfg, patch_doc, dry_run=dry_run)

    if dry_run:
        print("DRY RUN only. No changes written.\n")
        print("To apply changes, run without DRY_RUN=1")
        return 0
    else:
        backup_path = cfg_path.with_suffix(cfg_path.suffix + ".bak")
        save_yaml(backup_path, cfg)
        save_yaml(cfg_path, new_cfg)
        print(f"✅ Changes written to {cfg_path}")
        print(f"📦 Backup saved to {backup_path}\n")
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())




