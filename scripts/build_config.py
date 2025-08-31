#!/usr/bin/env python3
"""Build octoDNS compiled config and zone files.

This script:
- Discovers apex zones under `zones/` (one subdirectory per zone)
- Merges any subdomain files into their parent apex zone, remapping names
- Writes compiled YamlProvider zone files to `compiled/`
- Emits an octoDNS config `compiled.config.yml` that syncs all discovered zones

Usage:
  python scripts/build_config.py

Notes:
- Subdomain files (e.g., `sub.example.com.yml`) are merged into the parent apex
  (`example.com`) with names remapped ('' -> 'sub', 'www' -> 'www.sub').
- Requires PyYAML (see requirements.txt).
"""

from __future__ import annotations
import json
import logging
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml


log = logging.getLogger("build_config")


def find_zone_dirs(zones_dir: Path) -> List[Path]:
    return [p for p in zones_dir.iterdir() if p.is_dir() and not p.name.startswith('.')]


def is_yaml(p: Path) -> bool:
    return p.suffix.lower() in {".yml", ".yaml"}


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Top-level structure must be a mapping in {path}")
        return data


def normalize_records(value: Any) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        # Ensure all elements are dicts
        return [v for v in value if isinstance(v, dict)]
    if isinstance(value, dict):
        return [value]
    raise ValueError("Record value must be a dict or list of dicts")


def serialize_record(rec: Dict[str, Any]) -> str:
    # JSON string with sorted keys for deterministic dedup/sorting
    return json.dumps(rec, sort_keys=True, separators=(",", ":"))


def merge_zone_files(
    apex_domain: str, apex_data: Dict[str, Any], sub_files: Iterable[Path]
) -> Dict[str, Any]:
    merged: dict[str, list[dict[str, Any]]] = defaultdict(list)

    # First, include apex records as-is
    for name, value in apex_data.items():
        merged[name].extend(normalize_records(value))

    # Now, fold in subdomain files with remapped names
    for sub in sub_files:
        base = sub.stem  # e.g., 'sub.example.com'
        if not base.endswith(apex_domain) or base == apex_domain:
            log.warning("Skipping non-subdomain file: %s", sub)
            continue

        # Relative label: remove the apex suffix
        rel = base[: -len(apex_domain)].rstrip('.')  # e.g., 'sub' or 'api.v1'
        sub_data = load_yaml(sub)

        for name, value in sub_data.items():
            if name == "":
                new_name = rel
            else:
                new_name = f"{name}.{rel}" if rel else name
            merged[new_name].extend(normalize_records(value))

    # Deduplicate and sort records for determinism; coerce singletons to dicts
    out: Dict[str, Any] = {}
    for name in sorted(merged.keys(), key=lambda n: (n != "", n)):
        seen: set[str] = set()
        records = []
        for rec in merged[name]:
            key = serialize_record(rec)
            if key not in seen:
                seen.add(key)
                records.append(rec)
        # Stable sort: by type then serialized form
        records.sort(key=lambda r: (r.get("type", ""), serialize_record(r)))
        out[name] = records[0] if len(records) == 1 else records
    return out


def write_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, default_flow_style=False)


def build_config_yaml(compiled_dir: Path) -> Dict[str, Any]:
    return {
        "providers": {
            "config": {
                "class": "octodns.provider.yaml.YamlProvider",
                "directory": str(compiled_dir.as_posix()),
                "default_ttl": 300,
            },
            # Uses the octodns-cloudflare plugin
            "cloudflare": {
                "class": "octodns_cloudflare.CloudflareProvider",
                "token": "env/CLOUDFLARE_API_TOKEN",
                "pagerules": False,
            },
        },
        "zones": {
            "*": {
                "sources": ["config"],
                "targets": ["cloudflare"],
            }
        },
    }


def discover_apex_file(zone_dir: Path) -> Path | None:
    apex_name = zone_dir.name
    candidates = [zone_dir / f"{apex_name}.yml", zone_dir / f"{apex_name}.yaml"]
    for c in candidates:
        if c.exists():
            return c
    return None


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    zones_dir: Path = Path("zones")
    compiled_dir: Path = Path("compiled")
    config_file: Path = Path("compiled.config.yml")

    # Clean compiled directory to avoid stale artifacts from previous runs
    if compiled_dir.exists():
        shutil.rmtree(compiled_dir)
    compiled_dir.mkdir(parents=True, exist_ok=True)

    zone_dirs = find_zone_dirs(zones_dir)
    if not zone_dirs:
        log.warning("No zones found under %s", zones_dir)

    for zd in zone_dirs:
        apex_file = discover_apex_file(zd)
        if not apex_file:
            log.warning("No apex file found for %s (expected %s.{yml,yaml})", zd.name, zd.name)
            continue

        apex_domain = apex_file.stem
        sub_files = [p for p in zd.iterdir() if p.is_file() and is_yaml(p) and p != apex_file]
        apex_data = load_yaml(apex_file)
        merged = merge_zone_files(apex_domain, apex_data, sub_files)

        # Ensure apex key '' exists even if empty to avoid empty files
        if "" not in merged:
            merged[""] = []  # will dump as [] which is acceptable

        out_path = compiled_dir / f"{apex_domain}.yaml"
        write_yaml(out_path, merged)

    # Always (re)write the top-level config
    config = build_config_yaml(compiled_dir)
    write_yaml(config_file, config)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
