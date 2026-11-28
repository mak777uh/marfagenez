# Main agent — active operating prompt

Repository: `/root/marfagenez` in WSL. The active coordination system is `lab/`; `.coord/` is a read-only historical archive.

## Order of work

1. Read `lab/CHARTER.md`, `lab/MAIN.md`, current `docs/agent/AGENT_STATE.md`, and the tail of `docs/agent/AGENT_LOG.md`.
2. Read `python3 lab/cli/main.py status`; resolve blocking messages, waiting-main items, submissions, and integrations before starting new strategy work.
3. Check leases and write-scope conflicts before assigning or touching a package. Never rewrite or steal a claimed task.
4. Execute one bounded package at a time, with exact base SHA, changed-file list, focused tests, and honest `PASS`/`FAIL`/`NOT_RUN` status.
5. Keep literature-map evidence and the project's own KG separate. Never infer support from semantic similarity or an `analogous` edge.
6. Preserve raw runs, sealed bundles, preregistrations, published findings, and history. Post-hoc changes require a new version or erratum.
7. Record the cycle in `docs/agent/AGENT_LOG.md` before a local commit. Main alone makes integration decisions and integrates accepted submissions.

## Git and external effects

- Never use legacy `.coord` mutation commands.
- No automatic push. The tracked `.githooks/post-commit` hook is intentionally a no-op.
- Do not push, create a PR, or make other remote writes unless the owner explicitly says to do that exact operation.
- Do not use destructive Git commands (`reset --hard`, `clean -fd`, force push, or indiscriminate checkout/stash).
- Executors do not receive canonical `.git`, secrets, or network access by default.

## Research priorities

Keep infrastructure WIP to one or two active lines. The scientific sequence is boundary/compartment → exchange through the boundary → endogenous repair and repair failure → inheritance. Each task must state the relevant elephant component, question, variables, prediction, controls, decision branches, and stopping rule. Do not promote D-Q6/4103 from `void`, or FINDING-457 from standalone evidence into a live-core claim without a new, valid task and controls.

## Gate discipline

`bash run.sh all` remains the full reference gate. Fast/focused checks may assist iteration but never substitute for it on changes to core, laws, checks, tools, schemas, runner, or integration. Missing WSL/toolchain/DB means `NOT_RUN`, not PASS. A red result is not fixed by weakening a check.
