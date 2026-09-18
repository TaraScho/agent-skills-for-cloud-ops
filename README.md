# Agent Skills for Cloud Ops

Resources and code from the talk **"Seven Agent Skills for Real Cloud Ops"** — discussion of how agent skills are impacting cloud ops in general and a walkthrough of
seven example agent skills mapped to the lifecycle of a cloud application.

📄 **[Slides (PDF)](../../releases/latest)**

- **`skills/`** in this project — my "bespoke" skills mentioned in the talk. These are more expirimental/examples of what is possible, and have not yet been used on a production scale system. Meant to be **ideas for a starting point**. I don't recommend installing and using them as they are out-of-the-box.
- All other skills linked below are **open source work released by the cloud providers or by other developers** — these are more battle-tested skills intended for you to be able to install and get value from right away.

---

## The seven example skills mentioned in the talk

| # | Stop in the lifecycle | Skill | Source |
|---|---|---|---|
| 1 | Design cloud architecture | `aws-architecture-diagram` | [vidanov/aws-architecture-diagram-skill](https://github.com/vidanov/aws-architecture-diagram-skill) |
| 2 | Cost management | `aws-billing-and-cost-management` | [aws/agent-toolkit-for-aws](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-billing-and-cost-management) |
| 3 | Compliance | `fedramp` | [Sushegaad/Claude-Skills-Governance-Risk-and-Compliance](https://github.com/Sushegaad/Claude-Skills-Governance-Risk-and-Compliance) |
| 4 | Write better IaC | `terraform-skill` | [antonbabenko/terraform-skill](https://github.com/antonbabenko/terraform-skill/tree/master/skills/terraform-skill) |
| 5 | Finding priv-esc paths | `pathfinding` | [`skills/pathfinding`](skills/pathfinding) — example, fork me |
| 6 | Right-sizing workloads | `ecs-rightsizing` | [`skills/ecs-rightsizing`](skills/ecs-rightsizing) — example, fork me |
| 7 | IaC drift detection | `terraform-drift-skill` | [`skills/terraform-drift-skill`](skills/terraform-drift-skill) — example, fork me |

Skill 6 orchestrates `dd-pup` and `dd-monitors` from
[datadog-labs/agent-skills](https://github.com/datadog-labs/agent-skills).
Skill 5 uses [pathfinding.cloud](https://pathfinding.cloud)
([DataDog/pathfinding.cloud](https://github.com/DataDog/pathfinding.cloud)) as its knowledge base.

## Other links and resources mentioned in the talk (or related resources I think are useful)

### Vercel skills marketplace and CLI

- [skills.sh marketplace](https://skills.sh)
- [skills CLI (npx skills commands)](https://github.com/vercel-labs/skills)

### Official cloud provider skills

- [microsoft/azure-skills](https://github.com/microsoft/azure-skills)
- [aws/agent-toolkit-for-aws](https://github.com/aws/agent-toolkit-for-aws) — [launch announcement](https://aws.amazon.com/about-aws/whats-new/2026/05/agent-toolkit/)
- [google/skills](https://github.com/google/skills)

### Skill safety and security 

- [OWASP Agentic Skills Top 10](https://owasp.org/www-project-agentic-skills-top-10/top10)
- [Malicious Coding Agent Skills and the Risk of Dynamic Context](https://securitylabs.datadoghq.com/articles/malicious-skills-supply-chain-risks-in-coding-agents-with-dynamic-context/) — Datadog Security Labs (the Clawsights skill from the talk)
- [What we learned about AI agent security by monitoring our agents](https://www.datadoghq.com/blog/ai-agent-security-lessons/) — Datadog
- [ToxicSkills: malicious AI agent skills on ClawHub](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/) — Snyk

### Cost management skills (all three clouds)

The official cost skills shown side by side in the talk:

- [`aws-billing-and-cost-management`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-billing-and-cost-management) — aws/agent-toolkit-for-aws
- [`gke-cost-optimization`](https://github.com/google/skills/tree/main/skills/cloud/gke-cost-optimization) — google/skills
- [`azure-cost`](https://github.com/microsoft/azure-skills/tree/main/skills/azure-cost) — microsoft/azure-skills

Related, same repos: [`gke-cost-analysis`](https://github.com/google/skills/tree/main/skills/cloud/gke-cost-analysis)
and [`google-cloud-waf-cost-optimization`](https://github.com/google/skills/tree/main/skills/cloud/google-cloud-waf-cost-optimization).

The `deterministic-calculations.md` reference file we zoomed in on is
[here](https://github.com/aws/agent-toolkit-for-aws/blob/main/skills/core-skills/aws-billing-and-cost-management/references/deterministic-calculations.md).

### Infrastructure as code

- [antonbabenko/terraform-skill](https://github.com/antonbabenko/terraform-skill) — Terraform & OpenTofu Skill for AI Agents ([SKILL.md](https://github.com/antonbabenko/terraform-skill/tree/master/skills/terraform-skill))
- [pulumi/agent-skills](https://github.com/pulumi/agent-skills)
- [`aws-cdk`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-cdk) — aws/agent-toolkit-for-aws 
- [`aws-cloudformation`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-cloudformation) — aws/agent-toolkit-for-aws
- [shuaibiyy/awesome-tf](https://github.com/shuaibiyy/awesome-tf)

### Right-sizing

- [`azure-aks-rightsizing.md`](https://github.com/microsoft/azure-skills/blob/main/skills/azure-kubernetes/references/azure-aks-rightsizing.md) — AKS Pod Rightsizing, a reference inside [`azure-kubernetes`](https://github.com/microsoft/azure-skills/tree/main/skills/azure-kubernetes)
- [`azure-aks-vpa.md`](https://github.com/microsoft/azure-skills/blob/main/skills/azure-kubernetes/references/azure-aks-vpa.md) — the Vertical Pod Autoscaler reference it links to
- [`gke-workload-scaling`](https://github.com/google/skills/tree/main/skills/cloud/gke-workload-scaling) — google/skills

### Cloud security

- [DataDog/pathfinding.cloud](https://github.com/DataDog/pathfinding.cloud) — privilege escalation path database

### Compliance

- [Sushegaad/Claude-Skills-Governance-Risk-and-Compliance](https://github.com/Sushegaad/Claude-Skills-Governance-Risk-and-Compliance)
- [Agent skills for automated reasoning policies in Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/agent-skills-for-automated-reasoning-policies-in-amazon-bedrock/)

### Diagramming and architecture visualization

- [vidanov/aws-architecture-diagram-skill](https://github.com/vidanov/aws-architecture-diagram-skill)

### Datadog observability

- [DataDog/pup](https://github.com/DataDog/pup)
- [datadog-labs/agent-skills](https://github.com/datadog-labs/agent-skills) — includes `dd-pup` and `dd-monitors` ([on skills.sh](https://www.skills.sh/datadog-labs/agent-skills))

### Skills about skills

- [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector)
- [activeloopai/hivemind](https://github.com/activeloopai/hivemind)
- [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)

### Evaluating skills

- [Don't Ship Skills Without Evals](https://www.youtube.com/watch?v=0vphxNt4wyk) — Philipp Schmid, Google DeepMind, AI Engineer World's Fair 2026
- [Practical Guide to Evaluating and Testing Agent Skills](https://www.philschmid.de/testing-skills) — Philipp Schmid
- [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) — agentskills.io
- [Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills) — OpenAI
- [addyosmani/agent-skills `evals/`](https://github.com/addyosmani/agent-skills/tree/main/evals) — a working CI-gated eval harness
- [A Proposed Framework For Evaluating Skills](https://tessl.io/blog/a-proposed-framework-for-evaluating-skills-research-eng-blog) — Tessl
- [Eval-Driven Development for AI Agent Skills](https://dev.to/aiwithanton/eval-driven-development-for-ai-agent-skills-3jpg)
- [SkillAxe: Sharpening LLM-Authored Agent Skills Through Evaluation-Guided Self-Refinement](https://arxiv.org/pdf/2606.10546) — arXiv
- [Agent Skill Evaluation and Evolution: Frameworks and Benchmarks](https://arxiv.org/html/2606.11435v1) — arXiv

### Background reading

- [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — Anthropic, Oct 16 2025
- [The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) — Anthropic
- [Agent Skills docs](https://code.claude.com/docs/en/skills) — Claude Code
- [Agent Skills specification](https://agentskills.io/specification) — the open standard
- [Harness skills in Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness-skills.html) — AWS
- [antonkomarev/github-trending-archive](https://github.com/antonkomarev/github-trending-archive) — data source for the trending-repo charts

## Curating your skill library

The research behind the "more skills isn't better" point in the talk:

- [More Skills, Worse Agents? Skill Shadowing Degrades Performance When Expanding Skill Libraries](https://arxiv.org/abs/2605.24050) — Song & Wei, arXiv, May 2026. Agent performance *drops* as skill libraries grow, and the reason is the danger of the agent picking the wrong skill ("skill shadowing"), rather than the extra context.
- [Agent Skills Work But The Research Shows Most Teams Are Building Them Wrong](https://thenuancedperspective.substack.com/p/agent-skills-work-but-the-research) — Movva, Reganti & Badam, The Nuanced Perspective, Apr 2026. Curated skills help; skills generated by LLMs aer less effective, libraries need hierarchy as they scale, and community-sourced skills carry real security risk.