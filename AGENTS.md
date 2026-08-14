# Codex Project Instructions

These instructions apply to the entire repository.

`AGENTS.md` is the Codex auto-discovered repository entry point. It defines context bootstrap, workspace and experiment safety, and implementation constraints. `agent.md` is the sole authority for research scope, the scientific contract, stage order, task classification and model routing, delegation and review rules, and completion standards.

## Required Context

- Before any write, or any research/model/experiment/result analysis, read `agent.md` in full. Read it whenever task risk is uncertain. Only a read-only, pure R0 inventory or mechanical lookup may proceed from `AGENTS.md` and the directly relevant source without reading `agent.md`.
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

## Routing Bootstrap

- Before delegating, the main agent must classify the task under `agent.md` section 7. That section alone defines risk levels, model routes and effort, delegation, escalation, and independent review; this file must not restate or override those rules.
- Do not delegate a one-command or very small deterministic task when delegation overhead exceeds the work. The main agent remains responsible for requirements, integration, evidence verification, and the final answer.
- If `agent.md` cannot be read, or its rules conflict with this entry point, stop all writes and scientific analysis and report the conflict. Do not guess which routing or review rule applies.

## Implementation Contract

Before editing, state a short plan with verifiable success criteria. For every change:

1. Make the smallest change that satisfies the request.
2. Preserve existing architecture, naming, frozen assumptions, and artifact schemas unless the request explicitly changes them.
3. Add or update focused tests for behavior changes. Prefer a reproducing test before a bug fix.
4. Run the narrowest relevant tests first. Broaden verification according to risk; do not claim the full suite passed unless it was actually run.
5. Compare generated outputs, hashes, bounds, residuals, or manifests when the change can affect research artifacts.
6. Report changed files, commands run, observed results, assumptions, and residual risks.

If an executor cannot prove a required invariant, follow the escalation rule in `agent.md` section 7 instead of guessing or weakening a gate.

## Core Scientific Invariants

- Preserve power and service balance, F/X semantics, project lead-time logic, nonanticipativity, the shared flexibility budget, recovery debt, train/holdout separation, and honest right-censoring.
- Never convert synthetic sensitivity, derived benchmark, selected-N-1 DC output, local NLP failure, or an unresolved state into engineering/security certification.
- Never silently relax official voltage, thermal, response, gap, residual, or maximum-acceptance limits to obtain a favorable result.
- Never reinterpret a timeout, local infeasibility status, missing incumbent, incomplete frontier, or stopped process as mathematical infeasibility.
- Keep blocker status, plan/README claims, configs, tests, and machine-readable artifacts synchronized when evidence legitimately changes a gate.
