---
name: terraform-drift-skill
disable-model-invocation: true
metadata:
  author: TaraScho
  version: "1.2"
---

Find Terraform drift under the given path(s) and fix it by editing code to match reality — never by applying. Finish by opening a PR with the fixes.

## Steps

1. **Resolve targets**: Take the path(s) the user gave as arguments. If none were given, use the current directory. For each path, find every directory at or below it that is a Terraform root — i.e. contains `.tf` files AND has been initialized (a `.terraform/` directory or a configured backend). Skip any directory that looks like a reusable module only (referenced via `source = ...` elsewhere, never planned directly) — you're looking for root modules, not library code.

   If no initialized Terraform roots are found under the given path(s), tell the user and stop — don't attempt to `terraform init` on their behalf, since that may select workspaces or backends you don't understand.

2. **Branch**: Unless the user said to work on the current branch, create `drift-fix-<short-description>` off the repo's default branch before making any changes. Never commit drift fixes directly to the default branch.

3. **Remediate each root**: For each Terraform root directory found in step 1, use the `drift-remediation` subagent, passing it that directory. Do this one directory at a time (not all in parallel) so Terraform state locks in the same backend aren't contended.

4. **Format**: Run `terraform fmt -recursive` on the target path(s) to normalize any files you touched.

5. **Summarize and commit**:
   - If nothing was fixed (all directories reported `NO_DRIFT`), tell the user and stop — do not create an empty commit or PR.
   - Otherwise, commit the changes with a message describing the drift fixed (group logically if there are multiple unrelated fixes — separate commits per unrelated resource/module is fine).
   - Write a JSON results file summarizing every directory's outcome (see the schema in `scripts/open_drift_pr.py`'s docstring: `directory`, `status` of `FIXED`/`SKIPPED`/`NEEDS_MANUAL_REVIEW`, plus `drift`/`change` for fixed ones or `reason` for skipped/flagged ones).
   - Run `scripts/open_drift_pr.py --results <file>` to push the branch and open the PR. The script builds the PR body itself (summary table + per-directory detail, with every FIXED entry noted as verified via `terraform plan`) so its format is fixed and doesn't drift between runs — don't write the PR body by hand.

## Hard rules

- This skill never runs `terraform apply`. Every fix is a code change proposed via PR for a human to review and apply themselves.
- Never touch Terraform state directly (`import`, `state rm`, etc.) — flag those cases as `NEEDS_MANUAL_REVIEW` instead of attempting them.
- Never delete a resource from code just because it's missing from real infrastructure — that may have been intentional. Flag it.
- If a directory's Terraform backend is locked or credentials are missing, skip that directory and note it in the final report rather than failing the whole run.
- Never adopt drift that weakens security or reliability (a wider CIDR or `0.0.0.0/0`, encryption/versioning/logging turned off, public access enabled, wildcard IAM, deletion protection off). The subagent reports these as `UNSAFE_DRIFT`; surface them in the PR as "apply the code to correct this", not as a code change.
- This skill runs only when invoked for drift work. A refresh-only plan hits real provider APIs and takes time; never run one speculatively during unrelated tasks.
