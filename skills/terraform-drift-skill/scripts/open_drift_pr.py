#!/usr/bin/env python3
"""Push the current branch and open a PR with a fixed-format drift-fix body.

Input is a JSON file (see --results) shaped like:

{
  "title": "Fix Terraform drift in envs/prod",
  "base": "main",                     // optional, defaults to the repo's default branch
  "results": [
    {
      "directory": "envs/prod/network",
      "status": "FIXED",
      "drift": "security group sg-123 had an extra ingress rule not in code",
      "change": "added the missing aws_security_group_rule block"
    },
    {
      "directory": "envs/prod/dns",
      "status": "SKIPPED",
      "reason": "backend was locked by another operation"
    },
    {
      "directory": "envs/prod/db",
      "status": "NEEDS_MANUAL_REVIEW",
      "reason": "drift involves a state-only fix (import); flagging instead of running terraform import"
    }
  ]
}

The PR body layout is fixed by this script, not by the model, so it never
drifts between runs.
"""

import argparse
import json
import subprocess
import sys
import tempfile

STATUSES = ("FIXED", "SKIPPED", "NEEDS_MANUAL_REVIEW")


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def load_results(path):
    with open(path) as f:
        data = json.load(f)

    if "title" not in data or not data["title"].strip():
        fail("results file must have a non-empty 'title'")
    if "results" not in data or not isinstance(data["results"], list) or not data["results"]:
        fail("results file must have a non-empty 'results' array")

    for entry in data["results"]:
        status = entry.get("status")
        directory = entry.get("directory")
        if not directory:
            fail(f"entry missing 'directory': {entry}")
        if status not in STATUSES:
            fail(f"entry for '{directory}' has invalid status {status!r}; must be one of {STATUSES}")
        if status == "FIXED" and (not entry.get("drift") or not entry.get("change")):
            fail(f"FIXED entry for '{directory}' must include 'drift' and 'change'")
        if status in ("SKIPPED", "NEEDS_MANUAL_REVIEW") and not entry.get("reason"):
            fail(f"{status} entry for '{directory}' must include 'reason'")

    return data


def build_body(data):
    results = data["results"]
    fixed = [r for r in results if r["status"] == "FIXED"]
    skipped = [r for r in results if r["status"] == "SKIPPED"]
    manual = [r for r in results if r["status"] == "NEEDS_MANUAL_REVIEW"]

    if not fixed:
        fail("no FIXED entries in results — don't open a PR with nothing fixed")

    lines = []
    lines.append("## Summary")
    lines.append("")
    lines.append("| Directory | Status |")
    lines.append("|---|---|")
    for r in results:
        lines.append(f"| `{r['directory']}` | {r['status']} |")
    lines.append("")

    lines.append("## Fixed")
    lines.append("")
    for r in fixed:
        lines.append(f"### `{r['directory']}`")
        lines.append(f"- **Drift**: {r['drift']}")
        lines.append(f"- **Change**: {r['change']}")
        lines.append("- Verified with `terraform plan` — no changes.")
        lines.append("")

    if skipped:
        lines.append("## Skipped")
        lines.append("")
        for r in skipped:
            lines.append(f"### `{r['directory']}`")
            lines.append(f"- **Reason**: {r['reason']}")
            lines.append("")

    if manual:
        lines.append("## Needs manual review")
        lines.append("")
        for r in manual:
            lines.append(f"### `{r['directory']}`")
            lines.append(f"- **Reason**: {r['reason']}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def run(cmd):
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, help="path to the JSON results file")
    parser.add_argument("--base", help="PR base branch (defaults to the repo's default branch)")
    parser.add_argument("--dry-run", action="store_true", help="print the PR body and exit without pushing or opening a PR")
    args = parser.parse_args()

    data = load_results(args.results)
    body = build_body(data)

    if args.dry_run:
        print(body)
        return

    run(["git", "push", "-u", "origin", "HEAD"])

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(body)
        body_path = f.name

    pr_cmd = ["gh", "pr", "create", "--title", data["title"], "--body-file", body_path]
    base = args.base or data.get("base")
    if base:
        pr_cmd += ["--base", base]

    run(pr_cmd)


if __name__ == "__main__":
    main()
