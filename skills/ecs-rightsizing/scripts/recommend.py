#!/usr/bin/env python3
"""Recommend an ECS Fargate task size from observed utilization in Datadog.

Usage:
  recommend.py --cluster <name> --service <name> [--window 1d] [--headroom 0.3] [--out DIR]

Needs: aws CLI (ambient creds) and pup (Datadog CLI, authenticated). No Python deps.

What it does:
  1. Reads the service's current task definition (cpu units, memory MiB, task family).
  2. Queries Datadog for the task family's CPU and memory over the window, using the
     Fargate agent metrics (ecs.fargate.cpu.percent, ecs.fargate.mem.usage) and falling
     back to the generic container metrics (container.cpu.usage, container.memory.usage).
  3. Computes p95 and max of the summed per-task usage, adds headroom, and snaps to the
     nearest valid Fargate CPU/memory combination.
  4. Prints a before/after table with the monthly cost delta (us-east-1 Linux/x86 on-demand),
     and writes two monitor definitions (CPU % and memory % of the NEW limits) to --out
     for `pup monitors create --file`.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

VCPU_HOUR = 0.04048   # us-east-1 Fargate Linux/x86
GB_HOUR = 0.004445
HOURS = 730
# Valid Fargate cpu units -> the memory values ECS actually accepts for that tier.
# 256 is the one tier that is not a uniform range: only 512, 1024 and 2048 are valid, so a
# computed 1536 would be rejected at RegisterTaskDefinition. Every other tier is a range.
FARGATE = [
    (256, [512, 1024, 2048]),
    (512, list(range(1024, 4096 + 1, 1024))),
    (1024, list(range(2048, 8192 + 1, 1024))),
    (2048, list(range(4096, 16384 + 1, 1024))),
    (4096, list(range(8192, 30720 + 1, 1024))),
    (8192, list(range(16384, 61440 + 1, 4096))),
    (16384, list(range(32768, 122880 + 1, 8192))),
]


def sh(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"{' '.join(cmd[:3])} failed: {r.stderr.strip()[:400]}")
    return r.stdout


def aws(*a):
    return json.loads(sh(["aws", *a, "--output", "json"]))


def dd_query(q: str, window: str) -> list[list[float]]:
    """Return merged pointlist [[ts, value], ...] summed across series."""
    raw = json.loads(sh(["pup", "metrics", "query", "--query", q, "--from", window, "--no-agent"]))
    data = raw.get("data", raw)
    series = data.get("series", [])
    merged: dict[float, float] = {}
    for s in series:
        for ts, v in s.get("pointlist", []):
            if v is not None:
                merged[ts] = merged.get(ts, 0.0) + v
    return sorted([[t, v] for t, v in merged.items()])


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, math.ceil(p * len(s)) - 1)]


def snap(cpu_units: float, mem_mib: float) -> tuple[int, int]:
    """Smallest valid Fargate (cpu, memory) pair that covers both requirements.

    If the memory needed exceeds what a CPU tier allows, step up to the next tier rather
    than capping memory below what was asked for.
    """
    for cpu, mems in FARGATE:
        if cpu_units > cpu:
            continue
        for mem in mems:
            if mem >= mem_mib:
                return cpu, mem
    return FARGATE[-1][0], FARGATE[-1][1][-1]


def cost(cpu_units: int, mem_mib: int, tasks: int = 1) -> float:
    return tasks * HOURS * (cpu_units / 1024 * VCPU_HOUR + mem_mib / 1024 * GB_HOUR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cluster", required=True)
    ap.add_argument("--service", required=True)
    ap.add_argument("--window", default="1d")
    ap.add_argument("--headroom", type=float, default=0.30)
    ap.add_argument("--out", default="rightsizing")
    a = ap.parse_args()

    svc = aws("ecs", "describe-services", "--cluster", a.cluster, "--services", a.service)["services"][0]
    td = aws("ecs", "describe-task-definition", "--task-definition", svc["taskDefinition"])["taskDefinition"]
    family, cpu_now, mem_now, desired = td["family"], int(td["cpu"]), int(td["memory"]), int(svc["desiredCount"])
    scope = f"task_family:{family}"

    # CPU: ecs.fargate.cpu.percent is percent of ONE vCPU per container; sum containers per task.
    cpu_pts = dd_query(f"sum:ecs.fargate.cpu.percent{{{scope}}} by {{task_arn}}", a.window)
    mem_pts = dd_query(f"sum:ecs.fargate.mem.usage{{{scope}}} by {{task_arn}}", a.window)
    source = "ecs.fargate.*"
    if not cpu_pts or not mem_pts:
        # generic container metrics: cpu in nanocores, memory in bytes
        cpu_pts = [[t, v / 1e7] for t, v in dd_query(f"sum:container.cpu.usage{{{scope}}} by {{task_arn}}", a.window)]
        mem_pts = dd_query(f"sum:container.memory.usage{{{scope}}} by {{task_arn}}", a.window)
        source = "container.*"
    if not cpu_pts or not mem_pts:
        sys.exit(f"no utilization data for {scope} in the last {a.window}. Is the Datadog agent sidecar running?")

    # Normalize per task (the 'by task_arn' sum above merges tasks; divide by task count for a per-task view).
    n_tasks = max(1, desired)
    cpu_vals = [v / n_tasks for _, v in cpu_pts]           # percent of one vCPU
    mem_vals = [v / n_tasks / 1024 / 1024 for _, v in mem_pts]  # MiB

    cpu_p95, cpu_max = pct(cpu_vals, 0.95), max(cpu_vals)
    mem_p95, mem_max = pct(mem_vals, 0.95), max(mem_vals)
    cpu_units_needed = cpu_p95 / 100 * 1024 * (1 + a.headroom)
    mem_needed = mem_p95 * (1 + a.headroom)
    cpu_rec, mem_rec = snap(max(cpu_units_needed, 256), max(mem_needed, 512))

    before, after = cost(cpu_now, mem_now, desired), cost(cpu_rec, mem_rec, desired)
    print(f"service {a.service} (cluster {a.cluster}), task family {family}, {desired} task(s), window {a.window}, source {source}")
    print(f"samples: {len(cpu_vals)}")
    print()
    print(f"{'':<14}{'current':>12}{'p95 used':>12}{'max used':>12}{'recommended':>14}")
    print(f"{'CPU (units)':<14}{cpu_now:>12}{cpu_p95/100*1024:>12.0f}{cpu_max/100*1024:>12.0f}{cpu_rec:>14}")
    print(f"{'Memory (MiB)':<14}{mem_now:>12}{mem_p95:>12.0f}{mem_max:>12.0f}{mem_rec:>14}")
    print()
    print(f"CPU utilization at p95: {cpu_p95/ (cpu_now/1024*100) *100:.1f}% of task limit; memory: {mem_p95/mem_now*100:.1f}% of task limit")
    print(f"monthly compute: ${before:,.2f} now -> ${after:,.2f} recommended (saves ${before-after:,.2f}/mo, {100*(before-after)/before:.0f}%)")
    print(f"headroom applied: {int(a.headroom*100)}% over p95")

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    tags = ["managed-by:ecs-rightsizing-skill", f"ecs_service:{a.service}", f"ecs_cluster:{a.cluster}"]
    monitors = {
        "cpu": {
            "name": f"[{a.service}] task CPU above 80% of limit",
            "type": "metric alert",
            "query": f"avg(last_15m):sum:ecs.fargate.cpu.percent{{{scope}}} by {{task_arn}} / {cpu_rec/1024*100:.0f} * 100 > 80",
            "message": f"Task CPU is above 80% of the {cpu_rec} unit limit for 15m. Right-sized on {a.window} of data by ecs-rightsizing-skill; bump the task definition if this fires repeatedly. @YOUR-NOTIFICATION-HANDLE",
            "options": {"thresholds": {"critical": 80, "warning": 65}, "notify_no_data": False, "require_full_window": False},
            "tags": tags,
        },
        "memory": {
            "name": f"[{a.service}] task memory above 80% of limit",
            "type": "metric alert",
            "query": f"avg(last_15m):sum:ecs.fargate.mem.usage{{{scope}}} by {{task_arn}} / {mem_rec*1024*1024} * 100 > 80",
            "message": f"Task memory is above 80% of the {mem_rec} MiB limit for 15m. Right-sized on {a.window} of data by ecs-rightsizing-skill. @YOUR-NOTIFICATION-HANDLE",
            "options": {"thresholds": {"critical": 80, "warning": 65}, "notify_no_data": False, "require_full_window": False},
            "tags": tags,
        },
    }
    for k, m in monitors.items():
        (out / f"monitor-{k}.json").write_text(json.dumps(m, indent=2))
    (out / "recommendation.json").write_text(json.dumps({
        "family": family, "current": {"cpu": cpu_now, "memory": mem_now},
        "observed": {"cpu_p95_units": round(cpu_p95/100*1024), "cpu_max_units": round(cpu_max/100*1024),
                     "mem_p95_mib": round(mem_p95), "mem_max_mib": round(mem_max), "samples": len(cpu_vals), "window": a.window},
        "recommended": {"cpu": cpu_rec, "memory": mem_rec},
        "monthly_cost": {"before": round(before, 2), "after": round(after, 2)},
    }, indent=2))
    print(f"\nwrote {out}/recommendation.json, {out}/monitor-cpu.json, {out}/monitor-memory.json")


if __name__ == "__main__":
    main()
