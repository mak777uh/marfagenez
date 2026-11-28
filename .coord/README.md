# `.coord/` — ARCHIVED / READ ONLY

This directory is retained as historical evidence and for migration/audit purposes. It is not an active
coordination system and must not be used to claim tasks, write messages, update status, or coordinate agents.

The sole active control plane is `lab/`, with canonical state in `lab/state/control.db`.

Read the current contracts:

- `lab/CHARTER.md`
- `lab/MAIN.md`
- `docs/AGENT-ONBOARDING.md`
- `docs/HANDOVER-MAIN.md`

`python3 tools/coord.py` is fail-closed for every mutating command. Its small read-only diagnostic
allow-list is retained only to inspect historical state. Do not delete, rewrite, or migrate legacy data
as part of ordinary work; migration requires a separately scoped and audited task.
