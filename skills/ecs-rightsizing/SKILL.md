---
name: ecs-rightsizing
description: Right-size ECS Fargate tasks from real utilization and put monitors on the new limits. Use when asked whether an ECS service is overprovisioned, to cut Fargate cost, to pick a task CPU/memory size, or to "right-size and monitor" a container workload. Reads utilization from Datadog through the pup CLI (dd-pup skill) and creates alerts with the dd-monitors conventions.
metadata:
  version: "0.1.0"
  requires: aws CLI, pup (datadog-labs/agent-skills dd-pup), Datadog agent sidecar on the task
---

# ecs-rightsizing: size the task from data, then watch it

Overprovisioned Fargate tasks are the most common quiet cost in container workloads. This skill
composes two others: `dd-pup` to pull the task's real CPU and memory usage from Datadog, and
`dd-monitors` to alert on the new, tighter limits so a bad guess gets caught instead of paged.

## Workflow

1. **Identify the service.** Cluster and service name from `terraform/`, the architecture doc,
   or `aws ecs list-services --cluster <c>`. Confirm the Datadog agent sidecar is in the task
   definition; without it there is no per-task utilization data (see "No data" below).
2. **Check the observation window.** Utilization from less than a day is a smell test, not a
   sizing basis. State the window in the report. `--window 7d` is the sensible default for a
   production change; `1d` is acceptable for a first pass on a new service.
3. **Run the recommender:**
   ```bash
   python3 <skill-dir>/scripts/recommend.py --cluster <cluster> --service <service> --window 1d --out rightsizing/
   ```
   It prints current vs. p95 vs. max vs. recommended CPU and memory, the monthly cost delta,
   and writes `rightsizing/recommendation.json` plus two monitor definitions.
4. **Sanity-check the recommendation** before proposing it:
   - Memory headroom: if `max` is within 10% of the recommended limit, go one step up. OOM kills
     are worse than a few dollars.
   - CPU: a bursty service (short spikes to max) may want the p99 rather than p95; look at the
     max column.
   - Never recommend below 256 CPU / 512 MiB, and keep the combination valid for Fargate
     (the script snaps to valid pairs).
5. **Propose the change as code.** Edit the task definition's `cpu` and `memory` in
   `terraform/` (or the task definition JSON) and show the diff. Do not apply or force a new
   deployment unless the user asks.
6. **Create the monitors** so the tighter limits are watched:
   ```bash
   pup monitors create --file rightsizing/monitor-cpu.json
   pup monitors create --file rightsizing/monitor-memory.json
   ```
   Both alert at 80% of the *new* limit over 15 minutes, warn at 65%, and are tagged
   `managed-by:ecs-rightsizing-skill` so they can be found and cleaned up. Edit the `@` notification
   handle in the JSON if the user has a preferred channel.
7. **Report**: one table (current / observed p95 / observed max / recommended), the monthly
   saving, the window used, the monitor IDs created, and the one caveat that matters most
   (usually the window length).

## No data

If the script reports no utilization data:
- `pup metrics list --filter ecs.fargate --from 1d` to see whether the agent is reporting at all.
- Check the sidecar has `ECS_FARGATE=true`, a valid `DD_API_KEY`, and the task role allows
  `ecs:ListClusters`, `ecs:ListContainerInstances`, `ecs:DescribeContainerInstances`.
- If metrics arrive under `container.*` instead of `ecs.fargate.*`, the script already falls back.

## Scope

Fargate only. For EC2 launch type the container metrics are the same but the sizing target is
the instance fleet, which is a different problem.
