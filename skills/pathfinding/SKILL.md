---
name: pathfinding
description: Find AWS IAM privilege escalation paths in an account using the pathfinding.cloud library (DataDog). Use when asked to check IAM roles, users, or task/execution roles for privilege escalation, over-permissive policies, PassRole abuse, or "can this role become admin". Also use before deploying infrastructure that creates IAM roles, or when reviewing Terraform that attaches managed policies.
metadata:
  version: "0.1.0"
  source: https://github.com/DataDog/pathfinding.cloud
---

# pathfinding: IAM privilege escalation paths

pathfinding.cloud documents ~90 known AWS privilege escalation techniques as structured data:
which permissions are required, what the prerequisites are, and how to fix it. This skill
ships a compiled index of that library (`data/paths.json`) and a finder script that checks
real principals in an account against it.

## Workflow

1. **Refresh the path library first.** Always run this before matching, so newly published
   techniques are included and you are never working from a stale copy:
   ```bash
   python3 <skill-dir>/scripts/refresh-paths.py
   ```
   It pulls `https://pathfinding.cloud/paths.json` and recompiles `data/paths.json` in place
   (standard library only, no checkout needed). It prints any path ids that were added or removed.
   If the network is unavailable it keeps the existing index and continues — note that in the
   report if it happens.

2. **Decide the scope.** Prefer the principals the current work touches: task roles, execution
   roles, CI roles, Lambda roles. Read `terraform/` or the architecture doc to find their names.
   Fall back to `--all` for a whole-account sweep (slow on big accounts; skips service-linked and SSO roles).
3. **Run the finder** (AWS CLI, ambient credentials, read-only IAM calls):
   ```bash
   python3 <skill-dir>/scripts/find-paths.py --role <role-name> [--role ...] [--user ...]
   python3 <skill-dir>/scripts/find-paths.py --all --json > pathfinding-report.json
   ```
4. **Read the output in two halves.**
   - *Per principal*: matched path ids with the technique name and category. A principal marked
     `[ADMIN]` needs no path; it is the destination.
   - *Passable privileged roles*: privileged roles that a service principal can assume. These are
     the targets of every `new-passrole` / `existing-passrole` technique. An admin task role that
     trusts `ecs-tasks.amazonaws.com` means anyone with `iam:PassRole` + `ecs:RegisterTaskDefinition`
     + `ecs:RunTask` in the account is one API call from admin.
5. **Look up detail for any hit** in `data/paths.json` by id, or at `https://pathfinding.cloud/paths/<id>`:
   required permissions with resource constraints, prerequisites, and the upstream `recommendation`.
6. **Report findings** ordered by blast radius: admin principals first, then passable privileged
   roles, then per-principal paths. For each, quote the pathfinding id, say which policy grants it
   (the finder prints `policy_sources`), and give the concrete fix (usually: replace a managed policy
   with a scoped inline one, add resource constraints to PassRole, or split the role).
7. If the infrastructure is Terraform, propose the fix as a diff to the `.tf` files. Do not apply it
   unless asked.

## Reading results honestly

- The finder expands `Allow` action wildcards but does **not** evaluate resource ARNs, `Condition`
  blocks, permission boundaries, SCPs, or `Deny` statements. A hit means "the actions are there",
  not "exploitable right now". Say so in the report.
- Category meanings: `self-escalation` (principal edits its own permissions), `principal-access`
  (take over another principal's credentials), `new-passrole` / `existing-passrole` (run compute as
  a more privileged role). PassRole categories are the ones that matter for ECS, Lambda, Glue, etc.
- `prerequisites.admin` vs `prerequisites.lateral` in a path tells you whether the outcome is full
  admin or just "some other role".

## Refreshing the index

```bash
git clone --depth 1 https://github.com/DataDog/pathfinding.cloud /tmp/pf
pip install pyyaml && python3 <skill-dir>/scripts/build-index.py /tmp/pf
```
