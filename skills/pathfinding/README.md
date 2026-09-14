# pathfinding

> **Example skill — fork and customize.** A worked example from the talk, not a maintained
> product. Adapt it to your environment, naming, and risk tolerance before relying on it.

Finds AWS IAM privilege escalation paths in a real account, using
[pathfinding.cloud](https://pathfinding.cloud) as its knowledge base.

## Contents

- `SKILL.md` — the instructions the agent follows.
- `data/paths.json` — a compact index compiled from the pathfinding.cloud YAML (~90 techniques).
- `scripts/find-paths.py` — enumerates IAM principals with the AWS CLI and matches their allowed
  actions against every known path. Standard library only.
- `scripts/refresh-paths.py` — refetches the library from `https://pathfinding.cloud/paths.json`
  and recompiles the index. Standard library only, no checkout needed; SKILL.md runs this on every
  invocation so a run never matches against a stale copy.
- `scripts/build-index.py` — rebuilds the index from a local upstream checkout instead (needs
  `pyyaml`); useful if you want to pin to a specific commit.

## Install

```bash
cp -R skills/pathfinding ~/your-project/.claude/skills/
```

## Use

Ask the agent to check a role, or run the finder directly:

```bash
python3 .claude/skills/pathfinding/scripts/find-paths.py --role my-task-role --role my-ci-role
python3 .claude/skills/pathfinding/scripts/find-paths.py --all
```

Read-only IAM permissions are all it needs (`iam:List*`, `iam:Get*`).

## Refreshing the index

Normal case — no dependencies, no checkout:

```bash
python3 scripts/refresh-paths.py
```

It prints which path ids were added or removed. If the fetch fails it leaves the committed index
in place and exits 0, so a network blip degrades the skill to "slightly stale" rather than breaking
the run.

To build from a pinned local checkout instead:

```bash
git clone --depth 1 https://github.com/DataDog/pathfinding.cloud /tmp/pf
pip install pyyaml && python3 scripts/build-index.py /tmp/pf
```

## Limitations

The matcher looks at `Allow` actions only. Resource constraints, conditions, permission
boundaries, SCPs, and `Deny` statements are not evaluated — **a hit is a lead, not a confirmed
exploit.**

Path data is derived from pathfinding.cloud (Apache-2.0).
