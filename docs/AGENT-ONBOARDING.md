# Agent onboarding — current control plane

**Status:** active. **Source of truth:** `lab/CHARTER.md`, `lab/MAIN.md`, `lab/schemas/v1/`.
The old `.coord/` workflow is archived. Do not use its mutation commands.

## First steps

1. Read `lab/CHARTER.md` and `lab/MAIN.md`.
2. Read the role card under `lab/workcells/<department>/ROLE.md` and the exact task version supplied by `main`.
3. Inspect the current queue with:

   ```bash
   python3 lab/cli/main.py --help
   python3 lab/cli/main.py status
   ```

4. Claim only an unclaimed task in the declared department:

   ```bash
   python3 lab/cli/main.py claim --agent <agent-id> --department <experiments|formulas|knowledge>
   ```

   Preserve the returned `lease_id`, `epoch`, task version, and task-version hash. Do not guess missing values.

## Lease and submission

Heartbeat must use the exact returned lease identity:

```bash
python3 lab/cli/main.py heartbeat --lease <lease-id> --epoch <epoch> --agent <agent-id>
```

A voluntary return uses the same fencing fields:

```bash
python3 lab/cli/main.py release --lease <lease-id> --epoch <epoch> --agent <agent-id> --reason "<reason>"
```

Submit only the bundle described by the task contract and use a unique idempotency key:

```bash
python3 lab/cli/main.py submit <submission.json> --idem-key <unique-key>
```

Use `python3 lab/cli/main.py <command> --help` where available. Do not invent endpoints, state transitions, or validator commands. `status` is a queue summary; it is not an inbox listing.

## Hard boundaries

- `lab/state/control.db` is the canonical control state. Do not read/write `.coord/` as live state.
- `tools/coord.py` is read-only diagnostics only; its mutation commands intentionally fail closed.
- Executors do not commit, push, merge, or modify another agent's claimed task.
- Do not edit task versions, schemas, trusted checks, raw data, or sealed result bundles unless the task explicitly grants that scope and `main` approves the integration route.
- Do not run external actions, enable network access, or access secrets unless the owner explicitly authorizes that exact action.
- A scientific failure can be a valid submission. Never rerun until a desired outcome appears.
- `accepted`, `integrated`, and `pushed` are separate states. Push is never automatic; it requires the owner's explicit instruction.

## Where to report blockers

Use the task's documented submission or message channel. If the CLI does not expose a required read/communication operation, report that limitation to `main`; do not fall back to `.coord/` writes.
