# Codex Project Instructions

These instructions apply to the entire repository.

`AGENTS.md` is the Codex auto-discovered repository entry point. It defines context bootstrap, workspace and experiment safety, and implementation constraints. `agent.md` is the sole authority for research scope, the scientific contract, stage order, task classification and model routing, delegation and review rules, and completion standards.

## Required Context

- Read context according to the task: routine lookups and low-risk edits need only the relevant source. For research scope or scientific work, read the applicable sections of `agent.md`; for delegation or uncertain risk, read section 7. Reuse context already read unless it changed.
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
- Do not start a long solver run, formal experiment, external-data download, or paid query unless the user explicitly requests it. Prefer unit tests, tiny synthetic cases, and existing artifacts for routine verification.
- Before every experiment launch, apply the whole-workflow performance review required by `agent.md` section 9, including its evidence-reuse and resource-budget requirements.

## Routing Bootstrap

- Before delegating, the main agent must classify the task under `agent.md` section 7. That section alone defines risk levels, model routes and effort, delegation, escalation, and independent review; this file must not restate or override those rules.
- If a required scientific or review rule is unavailable or materially conflicts with another instruction, report the exact issue and pause only the dependent work.

## Implementation Contract

For substantive changes, briefly state the intended outcome and verification. For every change:

1. Make the smallest change that satisfies the request.
2. Preserve existing architecture, naming, frozen assumptions, and artifact schemas unless the request explicitly changes them.
3. Use meaningful tests for behavior changes. Documentation and low-impact mechanical edits normally need diff or format checks, not new tests that mirror the edit.
4. Run the narrowest relevant checks and required acceptance gates. Expand or repeat only for changed code, failures, or unresolved risk; report only checks actually run.
5. Compare generated outputs, hashes, bounds, residuals, or manifests when the change can affect research artifacts.
6. Report changed files, commands run, observed results, assumptions, and residual risks.

If an executor cannot prove a required invariant, follow the escalation rule in `agent.md` section 7 instead of guessing or weakening a gate.

Complete authorized implementation and safe, scoped local verification without repeated approval requests. Ask only when a material choice or new authority is needed; continue independent work meanwhile. This does not authorize formal runs or expand the requested scope.

## Skills And Search

Use explicitly requested skills and otherwise select skills by the actual workflow, not broad keyword overlap. Read only the relevant supporting references. User instructions take precedence over skill guidelines within higher-priority constraints. If a skill blocks work, identify the exact file and instruction.

Use repository evidence for project facts and external sources for requested searches, current facts, or unresolved source-dependent questions. Stop searching once the needed evidence is established.

## Core Scientific Invariants

- Preserve power and service balance, F/X semantics, project lead-time logic, nonanticipativity, the shared flexibility budget, recovery debt, train/holdout separation, and honest right-censoring.
- Never convert synthetic sensitivity, derived benchmark, selected-N-1 DC output, local NLP failure, or an unresolved state into engineering/security certification.
- Never silently relax official voltage, thermal, response, gap, residual, or maximum-acceptance limits to obtain a favorable result.
- Never reinterpret a timeout, local infeasibility status, missing incumbent, incomplete frontier, or stopped process as mathematical infeasibility.
- Keep blocker status, plan/README claims, configs, tests, and machine-readable artifacts synchronized when evidence legitimately changes a gate.
