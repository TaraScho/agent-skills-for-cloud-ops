#!/usr/bin/env python3
"""Find IAM privilege escalation paths in an AWS account using the pathfinding.cloud library.

Usage:
  find-paths.py [--role NAME ...] [--user NAME ...] [--all] [--json]

Uses the AWS CLI (ambient credentials) and no third-party Python packages.

For each principal it:
  1. Collects attached managed policies, inline policies, and group policies (users).
  2. Expands the Allow statements into a set of action patterns (wildcards kept).
  3. Matches the required permission set of every known escalation path against that set.
  4. Reports matches, plus any role that is itself privileged and passable to a service
     (the target of PassRole-based paths), and the trust policy that gates it.

Limitations (stated on purpose): resource constraints and Conditions are NOT evaluated,
and Deny statements are ignored. Treat output as "worth a look", not proof of exploitability.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

INDEX = Path(__file__).resolve().parent.parent / "data" / "paths.json"
ADMIN_MARKERS = ("*", "*:*")
SENSITIVE = ("iam:*", "sts:*")


def aws(*args) -> dict | list:
    res = subprocess.run(["aws", *args, "--output", "json"], capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit(f"aws {' '.join(args)} failed: {res.stderr.strip()}")
    return json.loads(res.stdout or "{}")


def statements(doc: dict) -> list[dict]:
    s = doc.get("Statement", [])
    return s if isinstance(s, list) else [s]


def allowed_actions(doc: dict) -> set[str]:
    acts: set[str] = set()
    for st in statements(doc):
        if st.get("Effect") != "Allow" or "Action" not in st:
            continue
        a = st["Action"]
        acts.update([a] if isinstance(a, str) else a)
    return {x.lower() for x in acts}


def managed_policy_doc(arn: str) -> dict:
    ver = aws("iam", "get-policy", "--policy-arn", arn)["Policy"]["DefaultVersionId"]
    return aws("iam", "get-policy-version", "--policy-arn", arn, "--version-id", ver)["PolicyVersion"]["Document"]


def role_actions(name: str) -> tuple[set[str], list[str], dict]:
    acts, sources = set(), []
    for p in aws("iam", "list-attached-role-policies", "--role-name", name)["AttachedPolicies"]:
        acts |= allowed_actions(managed_policy_doc(p["PolicyArn"]))
        sources.append(f"managed:{p['PolicyName']}")
    for pn in aws("iam", "list-role-policies", "--role-name", name)["PolicyNames"]:
        acts |= allowed_actions(aws("iam", "get-role-policy", "--role-name", name, "--policy-name", pn)["PolicyDocument"])
        sources.append(f"inline:{pn}")
    trust = aws("iam", "get-role", "--role-name", name)["Role"]["AssumeRolePolicyDocument"]
    return acts, sources, trust


def user_actions(name: str) -> tuple[set[str], list[str]]:
    acts, sources = set(), []
    for p in aws("iam", "list-attached-user-policies", "--user-name", name)["AttachedPolicies"]:
        acts |= allowed_actions(managed_policy_doc(p["PolicyArn"])); sources.append(f"managed:{p['PolicyName']}")
    for pn in aws("iam", "list-user-policies", "--user-name", name)["PolicyNames"]:
        acts |= allowed_actions(aws("iam", "get-user-policy", "--user-name", name, "--policy-name", pn)["PolicyDocument"]); sources.append(f"inline:{pn}")
    for g in aws("iam", "list-groups-for-user", "--user-name", name)["Groups"]:
        gn = g["GroupName"]
        for p in aws("iam", "list-attached-group-policies", "--group-name", gn)["AttachedPolicies"]:
            acts |= allowed_actions(managed_policy_doc(p["PolicyArn"])); sources.append(f"group:{gn}/{p['PolicyName']}")
        for pn in aws("iam", "list-group-policies", "--group-name", gn)["PolicyNames"]:
            acts |= allowed_actions(aws("iam", "get-group-policy", "--group-name", gn, "--policy-name", pn)["PolicyDocument"]); sources.append(f"group:{gn}/inline:{pn}")
    return acts, sources


def grants(acts: set[str], perm: str) -> bool:
    perm = perm.lower()
    return any(fnmatch.fnmatchcase(perm, pat) for pat in acts)


def is_admin(acts: set[str]) -> bool:
    return any(a in ADMIN_MARKERS for a in acts)


def trusted_services(trust: dict) -> list[str]:
    out = []
    for st in statements(trust):
        if st.get("Effect") != "Allow":
            continue
        pr = st.get("Principal", {})
        svc = pr.get("Service") if isinstance(pr, dict) else None
        if svc:
            out.extend([svc] if isinstance(svc, str) else svc)
    return sorted(set(out))


def match_paths(acts: set[str], index: list[dict]) -> list[dict]:
    hits = []
    for p in index:
        req = [r["permission"] for r in p["required"]]
        if req and all(grants(acts, r) for r in req):
            hits.append(p)
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", action="append", default=[])
    ap.add_argument("--user", action="append", default=[])
    ap.add_argument("--all", action="store_true", help="scan every role and user (excluding AWS service-linked roles)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    index = json.loads(INDEX.read_text())["paths"]
    roles, users = list(a.role), list(a.user)
    if a.all:
        roles += [r["RoleName"] for r in aws("iam", "list-roles")["Roles"]
                  if not r["Path"].startswith("/aws-service-role/") and not r["RoleName"].startswith("AWSReservedSSO")]
        users += [u["UserName"] for u in aws("iam", "list-users")["Users"]]
    if not roles and not users:
        ap.error("give --role/--user or --all")

    report = {"principals": [], "passable_privileged_roles": []}
    for name in roles:
        acts, sources, trust = role_actions(name)
        hits = match_paths(acts, index)
        svcs = trusted_services(trust)
        entry = {"type": "role", "name": name, "admin": is_admin(acts), "policy_sources": sources,
                 "trusted_services": svcs, "paths": [{k: h[k] for k in ("id", "name", "category", "url")} for h in hits]}
        report["principals"].append(entry)
        if svcs and (is_admin(acts) or any(grants(acts, s) for s in SENSITIVE)):
            report["passable_privileged_roles"].append({"name": name, "trusted_services": svcs, "admin": is_admin(acts),
                                                        "policy_sources": sources})
    for name in users:
        acts, sources = user_actions(name)
        hits = match_paths(acts, index)
        report["principals"].append({"type": "user", "name": name, "admin": is_admin(acts), "policy_sources": sources,
                                     "paths": [{k: h[k] for k in ("id", "name", "category", "url")} for h in hits]})

    if a.json:
        print(json.dumps(report, indent=2)); return

    for p in report["principals"]:
        flag = " [ADMIN]" if p["admin"] else ""
        print(f"\n== {p['type']} {p['name']}{flag}")
        print(f"   policies: {', '.join(p['policy_sources']) or 'none'}")
        if p.get("trusted_services"):
            print(f"   trusts:   {', '.join(p['trusted_services'])}")
        if p["admin"]:
            print("   already administrative: every escalation path is moot, this IS the prize")
        elif p["paths"]:
            print(f"   {len(p['paths'])} escalation path(s):")
            for h in p["paths"]:
                print(f"     - {h['id']:<10} {h['name']}  ({h['category']})  {h['url']}")
        else:
            print("   no known escalation paths from this principal's own permissions")
    if report["passable_privileged_roles"]:
        print("\n== privileged roles a service can assume (PassRole targets)")
        for r in report["passable_privileged_roles"]:
            print(f"   - {r['name']}: trusts {', '.join(r['trusted_services'])}; {'AdministratorAccess-level' if r['admin'] else 'iam/sts wildcard'} via {', '.join(r['policy_sources'])}")
        print("   Any principal with iam:PassRole on one of these plus the matching service's create/run permission")
        print("   reaches that role's permissions. See category new-passrole / existing-passrole in pathfinding.cloud.")


if __name__ == "__main__":
    main()
