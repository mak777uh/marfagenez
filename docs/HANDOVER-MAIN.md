# Main-agent handover — current entry point

This file is an entry point, not a second source of operating rules.

## Read in this order

1. `docs/agent/AGENT_STATE.md` — current state and environment.
2. Tail of `docs/agent/AGENT_LOG.md` — latest completed cycles.
3. `lab/CHARTER.md` — control-plane contract and trust boundaries.
4. `lab/MAIN.md` — main-agent workflow and integration rules.
5. `docs/INDEX.md` and `GOAL.md` — research map and scientific goal.
6. `MARFAGENEZ-UNIFIED-REFACTOR-PLAN-2026-11-28.md` — refactor work packages and acceptance criteria, if present in the working tree.

## Operational invariants

- `/root/marfagenez` in WSL is the canonical working clone; do not use the historical Windows clone.
- `lab/state/control.db` is the only active coordination state. `.coord/` and its standing cards are historical/read-only.
- Check the current task/lease and exact write scope before editing. Never modify a claimed task or another agent's active area.
- Main owns decisions and integration. Validation recommendations do not equal acceptance.
- No hidden push: `post-commit` is a no-op; publish only after the owner's explicit instruction.
- Preserve raw data, sealed task versions, findings, and the historical log. Corrections use errata/new versions.
- If a runner, WSL database, toolchain, or trusted sandbox is unavailable, state `NOT_RUN`/`BLOCKED`; do not infer success.
