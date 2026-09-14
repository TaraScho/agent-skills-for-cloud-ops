# terraform-drift-skill

> **Example skill — fork and customize.** A worked example from the talk, not a maintained
> product. Adapt it to your environment, naming, and risk tolerance before relying on it.

Finds Terraform drift and fixes it by editing your code to match reality, then opens a PR.
It never runs `terraform apply` on your behalf.

## What it does

1. Scans the path(s) you give it for initialized Terraform root directories.
2. Runs `terraform plan -refresh-only` in each to detect drift — provider-agnostic, so it works
   the same on AWS, GCP, or Azure.
3. Traces drifted values back through variables and modules and edits `.tf`/`.tfvars` to match
   what is actually deployed.
4. Verifies each fix with a plain `terraform plan` showing no changes.
5. Commits, pushes a branch, and opens a PR via `scripts/open_drift_pr.py`.

Drift needing `terraform import`, `terraform state rm`, or a destructive replace is flagged for
manual review rather than attempted. See `agents/drift-remediation.md` for the exact rules.

Work always happens on a `drift-fix-*` branch off the default branch unless you say otherwise.

## Not all drift should be adopted

Drift that makes the live infrastructure *weaker* than the code is a bug to fix, not a fact to
codify. A security group widened to `0.0.0.0/0`, encryption or logging switched off, public
access enabled, an IAM wildcard added, deletion protection removed: the subagent reports these
as `UNSAFE_DRIFT` and refuses to edit the code. They appear in the PR as "apply the code to
correct this". This is the one place where the skill's job is to argue with reality rather than
match it.

## Install

```bash
cp -R skills/terraform-drift-skill ~/your-project/.claude/skills/
cp skills/terraform-drift-skill/agents/drift-remediation.md ~/your-project/.claude/agents/
```

The subagent must end up in `.claude/agents/` — it is kept inside this directory only so the
skill stays a self-contained unit you can copy in one go.

## Use

This skill is **user-invoked only** — it sets `disable-model-invocation: true` and ships no
`description`, so nothing is loaded into the agent's context until you run it by name:

```
/terraform-drift-skill path/to/your/terraform
```

Omit the path to scan the current directory.

## Design notes

- **Never applies.** Every fix is a code change proposed via PR. This is a hard rule in the
  subagent instructions, not a default that can be silently overridden.
- **Skill + subagent split.** The skill orchestrates (find targets, branch, summarize, PR); the
  `drift-remediation` subagent does per-directory plan/diff/fix work in its own context, and runs
  on Sonnet — the per-directory work is mechanical enough not to need a larger model.
- **Fixed PR format.** `open_drift_pr.py` builds the PR body so the format does not drift
  between runs.
- **No frontmatter cost.** Drift detection is something you run on a cadence — daily, weekly, or
  from CI — not something the agent should spend tokens deciding whether to invoke. With
  `disable-model-invocation: true` and no `description`, this skill costs zero context until
  called. The trade-off is that the agent will never reach for it on its own, even when a drift
  question would warrant it.
