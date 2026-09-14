# ecs-rightsizing

> **Example skill — fork and customize.** A worked example from the talk, not a maintained
> product. Adapt it to your environment, naming, and risk tolerance before relying on it.

Right-sizes ECS Fargate tasks from real utilization data and puts monitors on the new limits.
"Right-size and monitor", not "right-size and hope".

This is the skill-orchestrating-skills example: it composes `dd-pup` (the `pup` CLI, to query task
CPU and memory) and `dd-monitors` (to create the alerts) from
[datadog-labs/agent-skills](https://github.com/datadog-labs/agent-skills). Nothing here talks to
an MCP server.

## What it does

1. Reads the service's current task definition with the AWS CLI.
2. Queries Datadog for the task family's CPU and memory over a window (`ecs.fargate.*`, falling
   back to `container.*`).
3. Recommends the smallest valid Fargate CPU/memory pair covering p95 usage plus headroom.
4. Prints a before/after table with the monthly cost delta.
5. Writes two monitor definitions (CPU and memory at 80% of the new limit) for `pup monitors create`.

The agent then proposes the change as a Terraform diff. It never force-deploys the service.

## Install

```bash
npx skills add datadog-labs/agent-skills --skill dd-pup --skill dd-monitors -y
cp -R skills/ecs-rightsizing ~/your-project/.claude/skills/
```

## Use

```bash
python3 .claude/skills/ecs-rightsizing/scripts/recommend.py \
  --cluster my-cluster --service my-service --window 7d
```

Requires the `aws` CLI with `ecs:Describe*`, `pup` authenticated (`pup auth login` or
`DD_API_KEY`/`DD_APP_KEY`), and the Datadog agent running as a sidecar in the task.

Set the `@YOUR-NOTIFICATION-HANDLE` placeholder in `scripts/recommend.py` to your own alert
destination before creating monitors.

## Scope

Fargate only. For the EC2 launch type the container metrics are the same but the sizing target is
the instance fleet, which is a different problem.
