# Synthesis: what the three sources say together, and what the bench must be

**Date:** 2026-11-09. **Sources read to the end:** Krishnamurti, *The Awakening of Intelligence* (P1–P295);
A. S. Neill, *Summerhill* (N1–N755); the pond specification, the eliminations register and the habitability
sections of the old line (§10dm–§10du, 58 eliminated mechanisms).

**What this file is.** Not another reading. The three sources were read separately and each produced its own
file. This file puts them **against each other** and asks one question: **what is the optimal bench**, given
everything all three have established — including everything the old line proved does not work.

---

## Part 1. The three sources are one source

They were written in different places, in different decades, about different things: a philosopher talking to
himself, a schoolmaster talking about children, and our own experiments talking about a lattice. **They arrive at
the same four statements.** Not as metaphors — as the same claim.

### 1.1. The record is the cage, and the cage cannot see itself

| source | the statement | where |
|---|---|---|
| **K** | "Thought is the response of memory... it is still the past. So thought is never free." | P13 |
| **K** | "The observer is the observed." | P11 |
| **N** | "The child is Legion: he wants to be normal, correct, like everyone else. He accepts everything he was taught and passes on his complexes." | N96 |
| **old line** | The cell's decision is `resource − pred`; `pred` is the past. Every mechanism we added was a re-weighting of the past. | P13, §10do |

**The same sentence three times.** K says thought cannot be free because it is memory. N says the child becomes
his record and passes it on. Our own data says the cell's decision is a difference between the present and its
own past, and that difference is what cancels the pattern (P11's test on E10).

**And the consequence is the same in all three:** a system made of its record cannot leave its record by
rearranging it. K: "changing the content of consciousness is juggling" (P51). N: "rules only strengthen what
they suppress" (N722, N374). Old line: every parameter we moved was "a piece moved from one corner of the box to
another" (P51), and the result was always a small number and never a change of kind.

### 1.2. The measure is the "me", and the "me" is what we installed

| source | the statement | where |
|---|---|---|
| **K** | "I can deceive myself the moment I have a measure. Comparing myself with somebody is the beginning of illusion." | P102 |
| **N** | "We all have our own standards of value, and we measure others by our own yardstick." | N567 |
| **N** | "The measure is the fear of inspection; the soul of discipline is the fear of inspection." | N181 |
| **old line** | "Favourable share" compared each cell against the top half of cells. | P102 |

**The same act three times.** K says the measure is the self. N says the yardstick is always one's own, and that
being measured is what makes a child afraid. Our bench measured every cell against other cells and called it
objectivity.

**And the consequence is the same:** a comparison is blind to order because it only ranks (P66, P102). N says the
same thing about children: "the strict school's ideal is a quiet, respectful, castrated pupil" (N535) — the
ranking produces the rank-holder, not the person.

### 1.3. Love and indifference, not love and hatred

| source | the statement | where |
|---|---|---|
| **K** | "Where there is an observer separating himself from the thing he observes, there must be conflict." | P11 |
| **N** | "Love and hatred are not opposites. **The opposite of love is indifference.**" | N716 |
| **N** | "Hatred is fed by hatred, and love by love." | N755 |
| **old line** | The cell was indifferent to its own field: it wrote it and was not shaped by it. | P103 |

**This is the sharpest finding of the whole reading, and it is about us.** Our bench was not cruel. It clipped
and bounded and scored, but it did not hate its forms. **It was indifferent.** It watched them, measured them,
and nothing it did changed what they were.

N's sentence is the diagnosis: **indifference is the opposite of love**, and indifference is what a measurement
without a stake produces. K's sentence is the same from the other side: the observer who separates himself from
what he observes creates conflict — and the separation is the act of measuring from outside.

### 1.4. The return path must be closed — and all three say what closes it

| source | the statement | where |
|---|---|---|
| **K** | "The environment has produced this individuality and the individuality has created the environment... the loop is open at the return path." | P103 |
| **N** | "The school created by an idea, not by a person... the medium must be reproducible from its idea." | N92 |
| **N** | "Ownership creates care. Not the reverse." | N149 |
| **old line** | The cells write the field; the field does not write the cells. | P103 |

**All three name the same missing thing:** a two-way loop. K says the loop is open at the return path. N says the
medium must be an idea that another person could build, and that care appears only where there is ownership.
The old line says the field is written but does not write back.

---

## Part 2. What the old line proved does not work

**This is the part that must not be repeated.** Fifty-eight mechanisms were tested and eliminated with numbers.
The register is in [`docs/eliminations.md`](../docs/eliminations.md). The ones that matter for the design:

| what we tried | what happened | why it matters |
|---|---|---|
| **learning the rule** (5 schemes) | `pop_time` 492–540 against 76711 for the fixed rule; class unchanged | learning inside a fixed ontology cannot produce a new kind (§10j) |
| **perception noise** as a trigger | σ up to 2.0, `pop_time` 76711 → 77432 → 76744 | noise does not create structure (§10l) |
| **smooth environment drift** | penalty −14.4 % → −5.5 %, sign and class unchanged | a slowly changing world does not change the cell (§10w) |
| **rich field via regeneration** | free field 0.0067 against 0.0069 at 7.5× inflow | the inflow is absorbed; richness does not arrive (§10am) |
| **inheritance of environment** | legacy 0.844 against foreign 0.846 | the effect was the number of live neighbours, not the place of death (§10ay) |
| **a second morphological scale** | axis period q' = 6–9 in every cell, including at 16× the power | the medium has one scale (§10fh) |
| **memory of a signal** | TE excess +0.0906 at T=0, −0.0080 at T=30, −0.0814 at T=100 | a passive integrator does not create anticipation (§10dt) |
| **a sensor without memory** | 15 structures at κ=0, **2** at κ=0.002, **1** at κ=0.005 | any link to the present signal erases the difference (§10dr) |
| **anticipation** | three arms had **identical hashes**; the manipulation was not connected to the world | the sharpest defect: an experiment that never ran (§10dq-доп-2) |
| **the missing-event design** | positive control did not respond; 0.00 in every arm | the field world has no measurable division event (§10du) |

**The one positive result of the whole habitability line** is §10dn: the pond was uninhabitable by an arithmetic
constant, not by a design flaw. `income = min(own, 4·b·own)` with `b = 0.002` gives at most 0.008 per step,
while existence costs 0.03. The ratio is **0.27**. The break-even point is `b = 0.0075`; the practical threshold
is higher — at `b = 0.010` (ratio 1.33) the population still dies, and only `b = 0.020` (ratio 2.67) survives
**10 of 10 seeds**.

**And the one causal result:** §10ds, the "ghost" control. The cell's state predicts the resource under itself
(+0.0362, 10/10) and **nothing** in empty cells (0.0000, 0/8). Block the cell's consumption and the dependence
**disappears** (0.0000, 0/8). So the cell's model is **a model of its own trace**, and there is no model of the
world. That is P103 measured: the loop runs one way.

---

## Part 3. What the three sources say the bench must be

**Not a list of prohibitions.** The contract we wrote has nine sections of "no", and N says plainly that a list
of prohibitions is ethics, and ethics makes the form bad (N371, N722, N728). The Tao says the same: *the law that
can be expressed in words is not the real law*.

**So: a description.** Here is what a medium in this bench is, in the positive.

### 3.1. It is habitable by arithmetic, not by tuning

**From the old line (§10dn):** the first condition of life is not diversity, not signal, not rules — it is
**economic habitability**. The medium must let a form earn more than it costs to exist, with a margin, and this
must be **checkable before any run**: write `income_max`, `cost_per_step`, the ratio, and the break-even point
into the pre-registration.

**From N:** the same thing in the language of care. "The infant must feed when it wants to feed" (N212). "A child
crying from hunger at four o'clock and not fed is subjected to a stupid, cruel, life-denying discipline" (N213).
**The form must not starve on the medium's clock.**

**The rule:** before any experiment, compute the arithmetic that makes the difference. If the whole field is
above the threshold in both arms (or below in both), the experiment is insensitive **by construction**, whatever
the seed count.

### 3.2. It has a return path that is closed, and the form owns something

**From K (P103):** the environment produced the individuality and the individuality created the environment —
and our loop is open at the return path.

**From N (N149, N501):** the workshop failed when shared and failed when private, and worked when each child who
wanted tools **had his own set**. "Ownership creates care. Not the reverse." And: "every child must have a corner
where he can do whatever he wants."

**The rule:** a form must **own** a part of the field — a region it can lose, and that it maintains. Not a
parameter. A place. And the field it writes must **shape its own terms**, not only its resources.

**This is the largest single gap in our bench.** Our forms own nothing. There is no corner.

> **CORRECTION 2 (2026-11-09, after E2e–E2h).** The gap is **larger than "the world must have a place the form
> owns"**. E2h showed that in a world with **one field**, a return path **cannot be tested at all**: the ghost
> control removes the region's shape from the field the region reads, and in a one-channel world that is the
> same as removing it from the region's rule. **The control cannot separate a return path from a resistance.**
>
> So the requirement is not "add a term". It is: **the medium must have a second channel** — a field the form
> writes and reads that is **not** the field it lives in. N calls it a corner (N501); K calls it the
> environment that produced the individuality (P103); the old line called it the missing sensor (§10dr).
>
> **And the control that works with two channels is specific:** cut the form's **access** to its mark, leave the
> mark in the world, and the field untouched. If the behaviour changes, the loop is closed, and nothing else
> could have produced that change. See [2026-11-09-return-path-results.md](2026-11-09-return-path-results.md).

### 3.3. It has a consequence, not a punishment

**From N (N198, N199, N200):** the boy left the saw in the rain, so he never borrows the saw again. That is not a
punishment, because a punishment always carries a moral judgement. Lane hit back when hit: "it was a necessary
lesson: one cannot endlessly harm others for one's own pleasure." And: "if a boy knocked my hat off with a lump of
clay and I caught him and cuffed him, he would think my reaction perfectly natural; his soul would not be
harmed."

**The rule:** a consequence is **the harm itself**, **immediate**, **equal**, and carries **no judgement**. The
test: does the medium say the form did wrong?

### 3.4. Its authority can take the form's side

**From N (N415, N424):** Homer Lane handed Jebbs the iron poker and said *"Go ahead"*. Jebbs broke the cups. The
next day he asked for better-paid work **to pay for the cups**.

**The rule:** the medium must be able to say *"go ahead"* to something it would rather stop, and then let the
consequence arrive. Authority on the form's side frees the desire; authority against it fixes the desire (N276,
N316, N322).

### 3.5. It has no inspection

**From N (N181):** "the soul of discipline is the fear of inspection."

**From K (P102):** the measure is the "me".

**The rule:** the readout is a camera, not a hand. It may not change the form's life. And it must be
**within-form**: the form against its own situation, never against other forms.

### 3.6. The designer can lose, and must admit it

**From N (N40, N151, N477):** Neill lost 2 to 40 on a vote, and one of his two votes was a misunderstanding. A
girl said: *"The first day I came, I was making a box, and you said I was taking too many nails. From that moment
I knew you were just another headmaster."* He answered: **"You are right. Goodbye."**

**And he admits ten limits** (N480, N503, N528, N556, N566, N622, N623, N675, N700, N747): he could not change
Miroslava; knowledge alone does not help; "where are the medicines?"; the family is stronger than the school; he
is a fanatic; he has a complex about alcohol; his own daughter may need an analyst; the atmosphere exists
nowhere.

**The rule:** a decision the forms make that the designer can lose, and a place where the loss is recorded. And
the designer must state, in every report, **what he could not do**.

---

## Part 4. The optimal bench

**What follows from all of the above.** Not a bigger bench. A **smaller** one, with four things the old one
lacked.

### 4.1. One world, not five

The old line had a pond with 134 configuration fields and five subsystems, and it produced 58 eliminations and
one positive constant. Our new bench has five worlds (field, lenia, particles, neighbour, medium) and produced
four rows of a table.

**Both are the same mistake in different sizes:** many worlds, none of them habitable. The old line's own
diagnosis is exact: *the first condition is not diversity, not signal, not rules — it is habitability by
arithmetic.*

**So: one world.** The one that already works best — `neighbour`, which follows the situation (0.914), holds
(0.136 → 0.176), clusters (1.35) and has a closed return path (1.225). Not because it is the most interesting,
but because it is the only one that is **habitable and two-way** at once.

> **CORRECTION (2026-11-09, after E1–E2d).** The claim "closed return path" is **withdrawn**. E2's control was
> broken and E2c's corrected control was **blind**: the support term is gated by `X*(1-X)`, which is zero
> exactly where the region is, so the region **cannot read its own body**. The loop is open — but for a precise,
> fixable reason: *the return path must be a term that is non-zero where the region is*. See
> [2026-11-09-return-path-results.md](2026-11-09-return-path-results.md).
>
> `neighbour` is still the best world at **following the situation** (0.914). It is **not** a world with a
> closed return path. Those are different things, and the synthesis confused them.

### 4.2. The world must have a place the form owns

**This is the change that matters.** From N149 and N501, and from K's P103: the loop must close on something the
form can lose.

**Concretely:** the field is divided into **owned regions**. A form's region is the part of the field it has
written and not lost. The form earns from its region; the region decays unless maintained; another form can take
it only by writing over it. **The form's terms are shaped by the region it owns** — that is the return path.

**Testable:** turn ownership off and the world must change its **kind**, not its average. If the only difference
is a number, ownership was decoration.

### 4.3. The readout is the form's own situation, and it never ranks

**From K (P102) and N (N181, N567):** the measure must be within-form and must not inspect.

**Concretely:** the primary readout is the **variance decomposition** — how much of a form's behaviour is
explained by its **situation now** against its **own history**. Under a closed return path the situation must
dominate. That is the measurement that discovers the cage (P117), and it is the only one that cannot install a
"me".

**And the secondary readout is N's**: *what the form holds back* — the share of its boundary that cannot move
(N140, N280). Suppression is visible in the body.

### 4.4. The designer states what he cannot do

**From N's ten admissions:** every report must contain a section **"what I could not do"**, and it must be
specific: which form the medium failed, which limit it could not cross, which question it could not answer.

**This is not modesty. It is the only defence against N587:** *"the tragedy is that the parent believes he always
acts for the child's good."*

---

## Part 5. What we will not do, and why

| not doing | why | source |
|---|---|---|
| adding a sixth world | five worlds produced four rows; the problem is habitability, not variety | §10dn |
| adding a record, a gate or a metric | these are the three owners the contract excludes; each was tried | P13, P51 |
| learning the rule | five schemes, `pop_time` 492–540 against 76711 | §10j |
| adding a sensor | κ=0.002 leaves 2 structures, κ=0.005 leaves 1 | §10dr |
| adding memory of a signal | TE excess negative at T=30 and T=100 | §10dt |
| a comparison readout | a comparison is blind to order and installs the "me" | P102 |
| a scheduled feeding | the first totalitarianism begins in the nursery, with feeding by the clock | N211 |
| a punishment | punishment is hatred and closes a vicious circle | N191, N192 |
| an inspection | the soul of discipline is the fear of inspection | N181 |
| a designer on a pedestal | "you are right. Goodbye." | N477 |

---

## Part 6. The first three experiments

**In order, each with its pre-registration arithmetic written before the run.**

> **STATUS (2026-11-09, end of session).** E1 and E2 were run, and **both failed**. E1's arithmetic was wrong
> (it modelled two of three terms). E2's control was broken, then blind, then not specific. **E2h established
> that a return path cannot be tested in a one-channel world at all.** The three experiments below are therefore
> **not** the next step; **E4 (a two-channel world)** is. See
> [2026-11-09-return-path-results.md](2026-11-09-return-path-results.md).
>
> What survived: the **contract checks** were rewritten and now pass 8 of 8, each able to fail — including a §2
> check that measures a difference in **kind** rather than in average, and a §7 check that is shown to be able
> to fail.

### E1. Habitability — **RUN, FAILED**

**Question:** is the `neighbour` world habitable by arithmetic with a margin?

**Result:** the arithmetic predicted dissolution below `support = 0.405`; every arm survived, 5/5, including
`support = 0.0` where the ratio is exactly zero. **The arithmetic modelled two of the rule's three terms.** The
region is held by the cubic reaction, not by the support.

### E2. Ownership — **RUN, VOID**

**Question:** does a place the form owns change the **kind** of what happens?

**Result:** the ghost control fired on the open loop (E2b), was blind after correction (E2c), and was not
specific when it did fire (E2h). **In a one-channel world the return path and a resistance cannot be
separated.** The experiment is void, and the question is not answerable in this world.

### E4. A two-channel world — **THE NEXT STEP**

**The smallest change that makes the return path testable:**

- **channel 1** — the field `X`, as now: the form lives in it, and its neighbours shape its conditions.
- **channel 2** — the mark `M`, written by the form's own presence and **not** consumed by it. `M` decays
  slowly and is read only by the form's own rule.

**The rule:** `X' = X + dt*(D·Lap(X) + reaction(X) + support·(M − X)·X)` — the support reads `M`, the mark,
not `nb`, the neighbours.

**The control:** cut the form's **access** to `M` (set the read to zero) but leave `M` in the world and the
field untouched. **If the behaviour changes, the loop is closed and the control is specific** — nothing else
could have produced the change.

**The arithmetic before the run:** the value of `(M − X)·X` in the interior against the halo, for the form's
own mark. If it is zero in the interior, the mark cannot be read from where the form is, and the world is
wrong again (this is E2d's lesson, and it cost a full session).

**The criterion:** the control must be silent at `support = 0` and fire at `support = 0.8`, **and** the effect
must be monotone in support **in a range where neither arm is near the ceiling** (E2g's lesson).

---

## Part 7. The one sentence

**K says it from the side of the observer:** the observer is the observed, and the measure is the "me".

**N says it from the side of the place:** what you feed is what grows, and the opposite of love is not hatred but
indifference.

**The old line says it from the side of the data:** the cell's state predicts its own trace and nothing else;
block the trace and the prediction disappears.

**All three are one sentence:**

> **A form can only become what its medium gives it back. If the medium gives back nothing, the form becomes
> nothing — and that is not cruelty, it is indifference.**

**Our bench gave back nothing.** It watched, measured, corrected, and was indifferent. The three sources agree
that this is the worst of the available failures, and they agree on what to do instead: **give something back,
and let the form own it.**

---

## Open questions this synthesis leaves

1. **Is the "owned region" a real return path or a parameter in disguise?** The test is E2: does the **kind**
   change? If only the number changes, it is juggling (P51).
2. **Can a form lose its region without that being a punishment?** N's answer is that the loss must be the harm
   itself and carry no judgement (N198). The test: does the form's behaviour change toward the medium, or only
   toward the region?
3. **What is the held edge when the form has no body?** N's measure is physical (N140, N280). Our forms have a
   boundary in the field; whether that boundary is a body is not established.
4. **Does the designer's admission change anything, or is it a ritual?** N's admissions were followed by changes
   in his practice (he stopped using the strap, N179). Ours must be followed by a change in the medium, or the
   admission is decoration.
