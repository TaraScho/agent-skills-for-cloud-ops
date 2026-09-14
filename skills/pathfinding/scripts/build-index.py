#!/usr/bin/env python3
"""Compile the pathfinding.cloud YAML library into a compact JSON index.

Usage: build-index.py <path-to-pathfinding.cloud-checkout> [out.json]

The index keeps only what the finder needs: id, name, category, services,
required permissions (with resource constraints), prerequisites,
recommendation, and the canonical URL. Everything else stays upstream.
"""
import json
import sys
from pathlib import Path

import yaml

src = Path(sys.argv[1]) / "data" / "paths"
out = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "paths.json")

paths = []
for f in sorted(src.glob("*/*.yaml")):
    d = yaml.safe_load(f.read_text())
    perms = d.get("permissions") or {}
    paths.append({
        "id": d["id"],
        "name": d["name"],
        "category": d.get("category", ""),
        "services": d.get("services", []),
        "required": [
            {"permission": p["permission"], "constraint": p.get("resourceConstraints", "")}
            for p in perms.get("required", [])
        ],
        "prerequisites": d.get("prerequisites") or {},
        "recommendation": (d.get("recommendation") or "").strip(),
        "parent": (d.get("parent") or {}).get("id"),
        "url": f"https://pathfinding.cloud/paths/{d['id']}",
    })

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"source": "https://github.com/DataDog/pathfinding.cloud", "paths": paths}, indent=1))
print(f"wrote {len(paths)} paths to {out}")
