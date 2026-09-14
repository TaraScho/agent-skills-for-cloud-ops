#!/usr/bin/env python3
"""Refresh data/paths.json from the live pathfinding.cloud library.

Usage: refresh-paths.py [--quiet]

Fetches https://pathfinding.cloud/paths.json and compiles it into the compact
index find-paths.py consumes. Standard library only, no checkout required, so
SKILL.md can run this on every invocation and never match against a stale copy.

If the fetch fails the existing index is left untouched and this exits 0 — a
network blip should degrade the skill to "slightly stale", not break the run.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "https://pathfinding.cloud/paths.json"
UPSTREAM = "https://github.com/DataDog/pathfinding.cloud"
INDEX = Path(__file__).resolve().parent.parent / "data" / "paths.json"
TIMEOUT = 20


def compact(d: dict) -> dict:
    perms = d.get("permissions") or {}
    return {
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
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    def say(msg: str) -> None:
        if not a.quiet:
            print(msg)

    try:
        with urllib.request.urlopen(SOURCE, timeout=TIMEOUT) as r:
            upstream = json.load(r)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        have = INDEX.exists()
        say(f"could not refresh from {SOURCE} ({e}); "
            + ("keeping the existing index" if have else "and no index exists"))
        sys.exit(0 if have else 1)

    if not isinstance(upstream, list) or not upstream:
        say(f"unexpected payload at {SOURCE}; keeping the existing index")
        sys.exit(0 if INDEX.exists() else 1)

    try:
        paths = [compact(d) for d in upstream]
    except (KeyError, TypeError) as e:
        say(f"upstream schema changed ({e}); keeping the existing index. "
            f"Rebuild with build-index.py against a checkout of {UPSTREAM}.")
        sys.exit(0 if INDEX.exists() else 1)

    before = None
    if INDEX.exists():
        try:
            before = {p["id"] for p in json.loads(INDEX.read_text())["paths"]}
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    INDEX.parent.mkdir(parents=True, exist_ok=True)
    tmp = INDEX.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({
        "source": UPSTREAM,
        "fetched_from": SOURCE,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "paths": paths,
    }, indent=1))
    tmp.replace(INDEX)

    if before is None:
        say(f"wrote {len(paths)} paths to {INDEX}")
    else:
        added = sorted({p["id"] for p in paths} - before)
        removed = sorted(before - {p["id"] for p in paths})
        say(f"refreshed {len(paths)} paths"
            + (f"; new: {', '.join(added)}" if added else "")
            + (f"; gone: {', '.join(removed)}" if removed else "")
            + ("; no changes" if not added and not removed else ""))


if __name__ == "__main__":
    main()
