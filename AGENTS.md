# Codex Project Instructions

Applies to the entire repository. `AGENTS.md` is the auto-discovered entry point; `agent.md` defines the current thesis scope, scientific invariants, workflow, review rules and completion criteria. Each frozen experiment retains its own bound scientific contract.

## Read only the context needed

- Routine lookups and low-risk edits: read the relevant source. Research work: read applicable `agent.md` sections, the current execution plan and blocker register, then relevant specs, configs, code, tests and result manifests.
- On a new conversation, first read the dated 2026-11-11 mainline section at the top of `agent.md`, then the relevant demo sources in the sibling `../ramp_flex_robust/` directory, including `RESULTS_complete_v1.md`. Verify live Git/process state. The sibling directory is outside this repository's Git publication scope. Reuse unchanged context already read.
- For historical work, read the newest applicable handoff linked in `docs/plan/continuation_handoff_20261022.md` and `paper/drafts/README.md`. Their older mainline statements do not override the dated current mainline in `agent.md`.
- The current thesis scope and completion criteria are defined in the dated 2026-11-11 mainline section of `agent.md`. Its historical §4 three-valued deliverability criterion continues to govern D/E result tables under their original contracts. New demo results remain preliminary feasibility evidence. Do not restate these definitions here.
- `agent.md` section 7 alone defines classification, model routing, delegation, escalation and review. Read it before delegation or uncertain-risk work. Section 8 defines scientific invariants; section 9 defines experiment admission and performance review. Do not duplicate those rules here.
- Communicate in Chinese by default; retain formulas and standard technical identifiers where clearer.

## Preserve workspace and execution state

- Inspect `git status` before edits. Preserve unrelated dirty/untracked work and failed, historical or frozen research artifacts; never assume they are disposable.
- Before touching a runner, solver adapter, frozen config, checkpoint, manifest or result tree, inspect related active processes. Do not stop, restart, resume or alter an active formal run without explicit user authorization.
- Long solver runs, formal experiments, external-data downloads and paid queries require explicit authorization. Before any experiment launch, apply `agent.md` section 9; ordinary tests and static checks follow the implementation contract.
- Updating goals or documentation does not change frozen inputs, results, gates or run authority. If a required rule is unavailable or conflicts materially, identify it and pause only dependent work.

## Implement and verify

- State the intended outcome and relevant checks for substantive work; make the smallest scoped change, preserving architecture, naming, schemas and frozen assumptions.
- Use meaningful tests for behavior changes. Documentation/mechanical edits normally need diff, link or format checks; do not add tests that merely mirror prose.
- Run the narrowest required checks; expand for changes, failures or unresolved risk. Compare hashes, manifests, balances, bounds or residuals when artifacts or results can change. Follow section 7 when an invariant cannot be established.
- Report changed files, checks actually run, observed results and remaining limits. Complete authorized reversible work without repeated approval requests; this does not expand scope or grant experiment authority.

## Sources and publication

- Use repository evidence for project facts and primary external sources for requested searches or unresolved source-dependent claims. Follow named skills; read relevant instructions only and reuse them when unchanged.
- Keep current scope navigation and claims consistent with evidence, preserving frozen records. At authorized completed checkpoints, stage only the reviewed scope, commit/push as requested, and verify the remote hash and final worktree state before reporting synchronization.
