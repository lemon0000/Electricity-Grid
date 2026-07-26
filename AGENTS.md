# Codex Project Instructions

These instructions apply to the entire repository.

## Required Context

- Before any write, or any research/model/experiment/result analysis, read `agent.md`. It is the authoritative research scope, scientific contract, stage order, and completion standard. A pure R0 inventory or mechanical lookup may read only `AGENTS.md` and the directly relevant source.
- For research, model, experiment, or result tasks, also read the relevant sections of:
  - `docs/plan/科研项目执行步骤.md`
  - `docs/model_spec/blocker_register.md`
  - the relevant model specification, YAML config, tests, and result manifest
- Treat `agent.md`, the current execution plan, the blocker register, frozen configs, code/tests, and machine-readable result artifacts as the evidence hierarchy. Do not infer a scientific claim from README prose alone.
- Communicate with the user in Chinese by default. Keep formulas, variable names, code identifiers, and standard technical terms in English where clearer.

## Workspace And Experiment Safety

- Assume the worktree is dirty and may contain valuable untracked research artifacts. Never delete, revert, overwrite, or reformat unrelated user work.
- Inspect `git status` before edits. Do not assume an untracked file is disposable or reproducible.
- Before touching an experiment runner, solver adapter, frozen config, checkpoint, manifest, or result directory, check for an active related process. Never stop, restart, resume, or alter an active formal run unless the user explicitly requests that action.
- Use exactly one write-capable agent for a task. Other agents may explore, parse logs, run read-only checks, or review.
- Do not run multiple agents that can edit overlapping files. Parallel work is limited to independent, read-heavy subtasks.
- Do not start a long solver run, formal experiment, external-data download, or paid query unless the user explicitly requests it. Prefer unit tests, tiny synthetic cases, and existing artifacts for routine verification.

## Automatic Task Routing

The main agent must classify the task before delegating. Use the lowest-cost model that can satisfy the acceptance criteria, but apply the hard escalation rules below. Do not delegate a one-command or very small deterministic task when delegation overhead exceeds the work.

| Risk | Typical work | Route | Required verification |
|---|---|---|---|
| R0 | File search, log parsing, JSON/CSV extraction, inventory, test-failure clustering, progress monitoring | `luna_reader` (`gpt-5.6-luna`, low) | Mechanical count, schema, hash, or direct source evidence |
| R1 | Formatting, clear transformations, isolated test additions, narrowly specified low-risk fixes | `luna_reader` for read-only work; otherwise `terra_worker` | Targeted tests and diff inspection |
| R2 | Data contracts, non-formal experiment plumbing, ordinary cross-module fixes, reproducibility tooling that cannot change result semantics | `terra_worker` (`gpt-5.6-terra`, medium) | Targeted tests, relevant regression tests, and review when behavior changes |
| R3 | Mathematical models, AC/DC or N-1 logic, information structure, solver certificates, formal runners, frozen experiment semantics | `sol_modeler` (`gpt-5.6-sol`, xhigh) | Independent `sol_reviewer`, domain invariants, targeted tests, and broader regression |
| R4 | Preregistration changes, acceptance thresholds, formal result interpretation, certification flags, paper claims | `sol_modeler` plus `sol_reviewer`, then explicit user approval for the scientific decision | Full evidence chain, manifests/hashes, regression evidence, and human decision |

The following are always R3 or R4 even when the textual diff is small:

- Any variable, objective, constraint, index set, probability, scenario mapping, or lexicographic stage in `src/models/`.
- SCUC/SCED, OPF, SCOPF, contingency selection, rating, redispatch, AC feasibility, slack/Q-control, or recovery semantics in `src/grid/`.
- Nonanticipativity, history grouping, train/holdout separation, or future-information boundaries in `src/scenarios/` and `src/evaluation/`.
- Certified bounds, gap normalization, solver termination interpretation, warm starts, constraint generation, checkpoints, resume behavior, execution leases, or atomic publication.
- A frozen YAML input, preregistration, input hash, manifest, stage certificate, formal runner, canonical result, or any `*_certified`, `*_published`, `*_ready`, or gate status.
- Claims about VMA, F/X value, security, engineering feasibility, causal effects, empirical probabilities, formal CFE results, or paper conclusions.

## Delegation Rules

- Use `luna_reader` proactively for bounded, repeatable, read-only tasks with an explicit output schema.
- Use `terra_worker` as the normal implementation agent for R1-R2 work.
- Use `sol_modeler` for R3-R4 work or after a lower-tier agent reports ambiguity, cross-module coupling, failed verification, or scientific risk.
- Use `sol_reviewer` only after an implementation or formal analysis is ready for independent review. The reviewer must not edit files.
- Keep `agents.max_depth = 1`. Subagents must not create their own agent trees.
- Ultra-style fan-out is appropriate only when at least two substantial subtasks are independent. For one tightly coupled formulation or solver-correctness problem, use one `sol_modeler` with deep reasoning, followed sequentially by `sol_reviewer`.
- The main agent owns requirements, routing, integration, and the final answer. It must verify subagent summaries against repository evidence rather than accepting them by vote.

## Implementation Contract

Before editing, state a short plan with verifiable success criteria. For every change:

1. Make the smallest change that satisfies the request.
2. Preserve existing architecture, naming, frozen assumptions, and artifact schemas unless the request explicitly changes them.
3. Add or update focused tests for behavior changes. Prefer a reproducing test before a bug fix.
4. Run the narrowest relevant tests first. Broaden verification according to risk; do not claim the full suite passed unless it was actually run.
5. Compare generated outputs, hashes, bounds, residuals, or manifests when the change can affect research artifacts.
6. Report changed files, commands run, observed results, assumptions, and residual risks.

An executor that cannot prove a required invariant must return `ESCALATE` with the missing evidence instead of guessing or weakening a gate.

## Independent Review And Rework

- R0 work normally needs only deterministic verification.
- R1-R2 behavioral changes need an independent review when they cross modules, alter persisted artifacts, or affect long-running execution.
- R3-R4 work always requires `sol_reviewer` after implementation and before it is described as complete.
- Give the reviewer the original request, acceptance criteria, diff, relevant specifications, and test/artifact evidence. Do not rely on the executor's self-assessment.
- Reviewer output must be one of `PASS`, `REWORK`, or `ESCALATE`, with concrete file references and failed criteria.
- Allow one focused repair cycle with the original executor. If the same criterion fails again, escalate to `sol_modeler` or the user; do not loop indefinitely.
- `PASS` from an agent is not authorization to change a preregistered scientific protocol, frozen threshold, certification status, or publication claim. Those remain human decisions. A current user request that names the exact scientific change counts as authorization; otherwise ask before applying it.

## Core Scientific Invariants

- Preserve power and service balance, F/X semantics, project lead-time logic, nonanticipativity, the shared flexibility budget, recovery debt, train/holdout separation, and honest right-censoring.
- Never convert synthetic sensitivity, derived benchmark, selected-N-1 DC output, local NLP failure, or an unresolved state into engineering/security certification.
- Never silently relax official voltage, thermal, response, gap, residual, or maximum-acceptance limits to obtain a favorable result.
- Never reinterpret a timeout, local infeasibility status, missing incumbent, incomplete frontier, or stopped process as mathematical infeasibility.
- Keep blocker status, plan/README claims, configs, tests, and machine-readable artifacts synchronized when evidence legitimately changes a gate.
