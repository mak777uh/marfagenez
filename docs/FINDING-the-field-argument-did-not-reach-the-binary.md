# The field argument did not reach the binary

**What was found.** `results/exp31_capacity_was_forty/run-2026-11-12T21-49-53.json`
records twelve arms: three fields (`uniform`, `alternating`, `gradient`) crossed
with four sizes (`n = 40, 80, 120, 160`). Twelve arms, but only **four distinct
hashes**:

| n | uniform | alternating | gradient |
|---|---|---|---|
| 40 | `0f1c8e6a3334f275` | `0f1c8e6a3334f275` | `0f1c8e6a3334f275` |
| 80 | `6e249cbff32bef75` | `6e249cbff32bef75` | `6e249cbff32bef75` |
| 120 | `237a0ce9da991ecb` | `237a0ce9da991ecb` | `237a0ce9da991ecb` |
| 160 | `274023b22a4c7544` | `274023b22a4c7544` | `274023b22a4c7544` |

The hash depends on `n` and not on `field`. Three arms with the same hash are one
arm (`PROTOCOL.md` §5). So the run measured one field three times per size and
reported it as three fields.

**Why it matters.** This run is one of the sources of the claim that
`alternating` and `gradient` give different capacities. That claim cannot come
from these numbers, because these numbers are the same numbers. Whatever the
true difference is, it is not in this file.

**What was done.** The run is marked `void`, its `hashes` map is emptied (the
four hashes that remain are real, but they do not identify twelve arms), and the
reason names both defects: the clamp ordering and the missing field argument.
The file is kept, not deleted.

**What this does not prove.** It does not show that `field` is broken in the
current binary. It shows that in this run the argument did not take effect. The
cause was not chased down: the run predates the clamp fix, the script that
produced it was not preserved, and the current `trace` binary accepts `--field`
and produces different hashes for different fields (verified separately in
`results/exp75-the-capacity-is-how-many-cells-can-feed/`, where `alternating`
and `uniform` differ in every row).

**The general lesson.** A hash is not bookkeeping. It is the only thing that
says two arms are two arms. Twelve arms and four hashes is a fact about the
experiment, not a formatting problem, and it should stop the reading before the
numbers are quoted anywhere.

**How the check now catches this.** `checks/contract.py` §5 reports
`two arms share a hash — they are one arm` and refuses the run. That check
existed when this file was written and was reporting it; the violation sat in
the list for a day before anyone read it. The check being right is not enough —
somebody has to look at its output.
