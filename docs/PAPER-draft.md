# Paper draft: the maintenance boundary of a minimal resource-limited consumer

**Status:** draft for internal review, 2026-11-17, cycle 75. Not submitted.
**Target:** *Ecological Modelling* (fallback: *JASSS* for the methodological half,
*Artificial Life* only if the structure question is ever answered).

**Кратко по-русски:** черновик статьи, собранный из того, что доведено до
предсказанных и подтверждённых результатов (находки 176, 177, 178, 151) и из трёх
методологических выводов (158, 160, 167). Отрицательные линии (память, карта сред)
в основной текст не входят и вынесены в §6 и Appendix B как ограничения, а не как
результаты. Всё, что нельзя утверждать, перечислено в §7.

---

## Abstract

Minimal models of resource-limited consumers usually specify the consumer and leave
the medium implicit. We derive and test the condition under which a single consumer
can maintain itself against a continuous cost in a one-dimensional medium whose
cells deplete and regrow, and we show that the condition is arithmetic rather than
ecological: the consumer persists exactly while its realised surplus covers the
price of repair it must pay each step,
`s_realised = r·available − maintenance ≥ damage_rate · repair_cost`. Two further
terms bound the same condition from above — a damage clock `K·s` and the reserve
`capacity + s` — giving the full edge `max(s/dr, min(K·s, capacity + s))`.

We preregistered all three predictions and tested them out of sample: the per-step
edge across four world sizes (12, 24, 48, 96 cells), the full edge across two of its
branches with different edges for two worlds that differ only in capacity, and the
realised-surplus edge on a depleting lattice, where the effective income is the
regrowth fraction of the cell rather than its level. All three held; the first and
third to the step and to the third decimal respectively.

We also report that the protocol by which co-located consumers share a cell moves
the system's marginal cost of repair by a factor of 15.7 at four consumers, with the
same field and the same organism — more than any field richness we could vary — and
that three methodological decisions, not the model, determined the size of every
effect we measured: the unit of replication is the environment and not the seed; a
bimodal outcome must be reported as a profile and not as a mean; and a measure of
"how much a medium distinguishes" is a property of the instrument as much as of the
medium. We state explicitly what the paper does not claim.

We also report what selection can and cannot see when the repertoire is fixed: over a
declared family of patchy media the share of a memory-bearing policy rises with the
distance between rich patches by a factor of 2.7, peaks near twelve cells, and does not
separate from a uniform poor world - so what selection sees is distance to a known place,
not patchiness. And we state two limits of the architecture rather than hiding them: care
cannot be posed because behaviour is written rather than selected, and searching cannot be
tested because an organism compares exactly one neighbour.

**Keywords:** maintenance boundary; resource-limited consumer; agent-based model;
preregistration; effect size; methodological artefacts.

---

## 1. Introduction

A consumer in a depleting medium faces one arithmetic question before any ecological
one: can it pay the cost of existing? In simulation models this question is usually
answered by running the model and observing survival, which makes the boundary a
property of the parameter grid rather than of the rules. We take the opposite route:
derive the boundary from the rules in closed form, preregister it, and test it on
points the derivation did not use.

The model is deliberately minimal: a one-dimensional medium of cells, a consumer with
two state variables (energy and damage), five hand-written behavioural policies and a
small price list. It has no reproduction by default, no inheritance and no evolution.
It is therefore not a model of the origin of behaviour. It is a model of the
arithmetic that any behaviour must satisfy, and that is the claim we defend.

We also ask a second question that turned out to matter more than expected: which of
the things a modeller varies actually changes the answer? The field's richness, the
consumer's policy, or the rule by which consumers share a cell? The answer is in §4.4
and it is not the one we expected.

## 2. Model

**Medium.** A line or a ring of `N` cells (the core is a line; see §6.1). Each cell
holds a resource level `c` with a ceiling `M` and regrows each step by

```
c' = (c − t) + (M − (c − t))·r
```

where `t` is what was taken and `r` the regrowth fraction. The field is homogeneous,
periodic with `P`-spaced peaks, travelling, or a travelling lattice of peaks.

**Consumer.** Energy `e` and damage `d`. Each step: take `t = min(income, c)`; pay
`maintenance`; damage grows by `dr`; repair costs `dr·rc` and is taken only if the
price fits in the energy; energy is capped at `capacity`; death at `e ≤ 0` or `d ≥ 1`.

**Policies.** `stay`, `random`, `remember` (one cell, no return), `memory` (one cell,
returns), `sighted` (walks to the richer neighbour). Five behaviours, all written by
hand — this is a fixed repertoire, not an evolved one, and no claim about evolution is
made.

**Sharing.** Several consumers on one cell share its take by `Sequential` (in a fixed
order) or `Proportional` (by need).

## 3. Methods of inference

Every experiment is preregistered with four outcomes (`passed`, `failed`, `void`, `not
applicable`), three controls (`fires` — the effect appears where it must; `silent` —
it is absent where it must be; `specific` — it comes from the stated mechanism and not
from an incidental covariate), and a `mde` computed from a **measured** dispersion.
Three decisions were forced by our own errors and are stated as part of the method:

1. **The unit of replication is the environment, not the seed.** On a deterministic
   scene, twelve seeds gave identical lifetimes and `σ = 0`, which makes the `mde`
   formula degenerate and would certify any effect (§5.1).
2. **A bimodal outcome is reported as a profile, not a mean.** The mean of a
   two-humped distribution is an artefact (§5.2).
3. **A measure of the medium is a measure of the instrument.** The number of outcome
   classes among a fixed repertoire is a function of the declared encoding (§5.3).

All numbers below are reproducible from the repository at the commit named in each
figure caption; every recorded result carries the hash of the dynamics that produced
it.

## 4. Results

![The maintenance boundary, tested out of sample: survival across the income boundary at
four world sizes, across the repair-cost edge at two capacities, and across the poor-level
edge at two repair prices. Vertical axis is lifetime to the horizon on a log scale; open
markers survived, filled markers died.](figures/boundary.svg)

*Figure 1.* The three held-out tests of §4.1–4.3 in one view. The dashed lines are the
predicted edges. Generated by `checks/make_figures.py` from the same numbers
`checks/paper_numbers.py` re-measures on every gate run.

### 4.1 The per-step boundary, tested out of sample across four world sizes

```
sustains  ⇔  income − maintenance ≥ damage_rate · repair_cost
```

At `maintenance = 1.7911`, `dr = 0.02`, `rc = 1.5` this is `income ≥ 1.8211`.

Preregistered prediction: survival flips at `1.8211` and the flip is **the same for
every `N`**, because the law is the arithmetic of a single cell.

| income | N = 12 | N = 24 | N = 48 | N = 96 | cause |
|---|---|---|---|---|---|
| 1.70 | 42 | 42 | 42 | 42 | energy |
| 1.78 | 124 | 124 | 124 | 124 | energy |
| **1.8211** | 20000 | 20000 | 20000 | 20000 | alive |
| 1.94 | 20000 | 20000 | 20000 | 20000 | alive |

Not only the boundary but the whole transient agrees to the step across the four
sizes. Size is not a hidden variable for this law.

### 4.2 The full boundary, tested on two of its branches

```
edge = max( s/dr , min( K·s , capacity + s ) )
```

with `K = min{k : fl_sum_k(dr) ≥ 1}` the damage clock. Parameters were chosen so that
two worlds differ only in `capacity` and therefore sit in different branches:
`dr = 0.3` gives `K = 4` and `s = 0.1`, hence `s/dr = 0.3333` and `K·s = 0.4`.

Preregistered: the edge on `rc` is **0.4** at `capacity = 1.0` and **0.3333** at
`capacity = 0.2`.

| rc | capacity 1.0 | capacity 0.2 |
|---|---|---|
| 0.33 | alive | alive |
| 0.35 | alive | **45, damage** |
| 0.40 | alive | 14, damage |
| 0.45 | **33, damage** | 10, damage |

Both edges confirmed, and the two worlds flip in different places — which is what
distinguishes the full boundary from the per-step condition. Death arrives by damage
in that branch, as the mechanism predicts.

### 4.3 The same law on a depleting medium: realised, not nominal surplus

On a peaked lattice a consumer standing on a poor cell takes the cell's level, not the
nominal income. With nominal income 3.0 (a nominal surplus of 1.21, two orders of
magnitude above any edge) it still dies, so the law uses the realised surplus.

The first prediction — a flip at `maintenance + dr·rc` — failed. The reason is the
cell law: the cell is emptied to zero each step and regrows only a fraction `r`, so
the realised income is about `r·poor`. The corrected prediction,

```
poor ≥ (maintenance + dr·rc) / r
```

gives `1.8395` at `rc = 1.5` and `1.8496` at `rc = 2.0`. Measured: 1.838 dies at 3440
steps while 1.8395 lives to the horizon; 1.846 dies at 1459 while 1.8496 lives. Both
edges exactly as predicted and different from each other.

### 4.4 The sharing protocol moves the answer more than the field

With the same field and the same organism, four consumers sharing a cell by
`Proportional` instead of `Sequential` lower the marginal price of repair by a factor
of **15.7**. No field variation we tried comes close. The rule by which consumers
divide a resource is therefore not a detail of the implementation; in this model it
dominates the ecological parameter that a modeller would normally vary first.

### 4.5 The consumer's policy matters far less than the arithmetic

Across 216 environments of a declared family, the richest contrast we could build
between a memory-bearing and a memoryless policy produced a gain of **+4 steps** in
13% of environments and a loss of **−10 001 steps** in 17%, with 70% of environments
indistinguishable. This is reported here as a size, not as a result about memory
(§6.2): it is a bound on how much behaviour can matter once the arithmetic is fixed.

![Memory share against the spacing between rich islands, with 90% bootstrap intervals
over environments, and the two uniform controls as horizontal references. The share rises
by a factor of 2.7 from the densest to the sparsest spacing, peaks near twelve cells, and
the peak does not separate from its neighbours.](figures/selection.svg)

*Figure 2.* What selection sees in §4.6. The dashed lines are the uniform controls: a
uniform rich world supports no memory at all, and a uniform poor world is not
distinguishable from the patchy family as a whole.

### 4.6 Selection over a fixed repertoire sees distance, and only distance

The model has no genome: five hand-written policies are the heritable unit, a child
inherits its parent's with probability `1 - mutation`, and death is the only filter.
That is selection over a fixed repertoire, not open-ended evolution, and it is called
that.

Two questions were asked of it. First, does the economy choose a behaviour at all? At the
maintenance boundary (`income 1.83`), a population of twelve walkers ends with a mixed
repertoire and six survivors; in a comfortable economy (`income 1.95`) it ends with
twelve walkers and no deaths, and nothing changes at any mutation rate - **a comfortably
fed world selects nothing**.

Second, what does the medium have to vary for selection to see it? A declared family of
patchy media - rich islands of 3.0 in a poor sea of 1.65, spacing from 4 to 24 cells,
two richness levels, four seeds each - gives the memory share:

| spacing (cells between islands) | memory share | 90% bootstrap over environments |
|---|---|---|
| 4 | 0.036 | [0.010, 0.068] |
| 8 | 0.052 | [0.026, 0.078] |
| 12 | **0.099** | [0.052, 0.141] |
| 16 | 0.073 | [0.052, 0.099] |
| 20 | 0.052 | [0.010, 0.099] |
| 24 | 0.073 | [0.047, 0.099] |
| uniform poor | 0.073 | [0.021, 0.135] |
| uniform rich | 0.000 | [0.000, 0.000] |

Three things are worth reporting carefully. The share rises from the dense to the
sparse end by a factor of 2.7, and that is the only comparison whose intervals separate.
The trend is **not monotone**: it peaks near twelve cells, and the peak is not
statistically distinguishable from its neighbours. And patchiness as such does not beat a
uniform poor world (`0.064` against `0.073`), so what selection sees is **distance to a
known place**, not patchiness.

The mechanism is the one the literature predicts: a sighted organism steps toward one
neighbour, so having eaten out an island it walks into the poor sea; a memory-holder
returns to the island when it has recovered. In a patchy medium it pays to return rather
than to search - and the model **cannot** test the alternative, because an organism
compares exactly one neighbour and therefore cannot search at all.

## 5. Three methodological results

These are results about the modelling, not the model, and each came from an error of
ours that the controls caught.

### 5.1 σ = 0: seeds are not replication

Twelve seeds on a fixed scene gave identical lifetimes in all twelve combinations of
price and read period. With `σ = 0` the `mde` formula returns a required sample size
of zero and certifies any effect. An `mde` computed from an invented `σ` is not a
conservative choice but a fabricated one. The unit of replication in a deterministic
model is **the environment**: thirty-six environments gave `σ ≈ 8.7` where twelve
seeds gave zero.

### 5.2 A profile, not a mean

The same contrast that reported a mean of `−1665` steps is two humps: a median win of
**+4** and a median loss of **−10 001**. The mean is negative because a loss is
enormous, not because losses are frequent. A two-humped quantity reported as a mean is
an artefact of the summary, and for publication we report two fractions with intervals
and the median size of each tail.

### 5.3 The measure of the medium is a measure of the instrument

Counting distinct outcome classes among a fixed repertoire is documented practice in
testing (equivalent mutants) and it has the same pathology here: it saturates. Five
behaviours gave four classes in 30 of 35 environments. Replacing the class count with
the fraction of differing pairs resolved four distinct values instead of three — and
the declared outcome encoding removed even that: with a 1e-3 threshold on the realised
take, both measures collapse. The measure is not a property of the medium; it is a
property of the pair (medium, instrument), and we never report it without naming the
repertoire and the encoding.

## 6. What this model cannot show

### 6.1 A probe is a second model

Our behavioural experiments run in a probe that reimplements the step while importing
the core's field, organism and world. The core is a line and the probe a ring. Cutting
the access to compare them shows the conclusion transfers qualitatively while the
numbers do not: under the same prices, a memory-bearing policy loses 28% of its
lifetime and the random walker 16% when the ring is replaced by a line, and on the
peaked field where the memory contrast is largest the organisms never reach an edge, so
the two topologies coincide. Moreover a docking comparison is only meaningful before
the first boundary reflection, `T < dist/v_max`, which for our start cell is three
steps. **All behavioural numbers in this paper are ring numbers.**

### 6.2 Memory was not shown to be useless

We built a two-channel medium in which a consumer writes a mark, pays to keep it, and
the place wears with use; the region can be wider than the consumer can see, and the
yield scales with the mean health of the whole region. In that medium a region wider
than the sight costs lifetime monotonically (73, 73, 68, 64 steps for radius 0 to 3)
and paying for a wider keep removes the cost entirely, while every policy that walks
toward what it remembers loses catastrophically: 64 to 15, 64 to 10. The honest
statement is that **in these worlds movement is not viable**, so no policy about
movement — memory included — can pay. What would be needed is a medium where a visit
builds something lasting; that is not this one.

### 6.3 The structure question was not answered

A comparison with Conway's Life is in the repository and is not a result: Life shows
structural novelty from fixed rules without any player, which our model cannot produce
because it has no space of configurations, and our model has a price which Life does
not, so self-maintenance cannot even be asked there. The two are complements.

### 6.4 Care cannot be posed, and neither can searching

Ownership of cells was implemented and measured: a form holds a cell by standing on it,
another takes it only by overwriting, a claim decays without presence, and a stranger
eats a fraction of what the holder eats until it overwrites. In an economy at the
boundary this decides who lives: with a stranger's share of 0.50 the holder survives and
the walker falls from 165 to 49 steps; at 0.25 both die, because the walker overwrites the
holder's cell and the holder then eats as a stranger on its own former place; at 0.00 the
holder dies in 22 steps and the walker holds every cell.

So losing a place is mortal. But the claim that ownership creates care could not be
tested. The proposed comparison - a returning form against a wandering one - failed its
own control: with ownership switched off, where the two should not differ, the returning
form lived twenty-four times longer. Memory in this model keeps a form near rich cells, so
returning is confounded with being well fed.

Removing the confound needs two equally wandering forms that differ only in whether they
return to **their own** cell, and no policy reads claims. Writing one would mean writing
the behaviour, which is the thing this paper is trying to avoid. The honest statement is
therefore a limit of the architecture: care is behaviour, behaviour here is written by us,
and a rule of access is not behaviour.

The same limit applies to searching. An organism compares one neighbour and steps toward
it, so a medium can reward **returning** and cannot reward **searching**; every result in
§4.6 is a statement about return.

## 7. What this paper does not claim

- Not that the boundary is universal: it is derived for this rule set, verified on
  three out-of-sample predictions, and stated with its domain.
- Not that the boundary is ecological. It is arithmetic; the ecology enters through
  the realised take, which is the cell law's business.
- Not that behaviour does not matter. It matters less than the arithmetic in the
  regimes measured, and the regimes are declared.
- Not that any fraction is prevalence. Shares are shares of a declared box, and
  interesting objects in a large configuration space are rare rather than common.
- Not that the probe's numbers are the core's numbers (§6.1).
- Not that anything here is emergent. Every effect reported is named: a rule of access,
  a price, a spacing, a selection pressure. Where a boundary was found it is stated as a
  boundary, not as a result.
- Not that a form can care for a place. Ownership has consequences without any policy,
  but care is behaviour and behaviour in this model is always written by us (§6.4).

## 8. What the author could not do

Following the practice this project adopted from its reading of Neill — that a report
must state what it failed to do, or the admission is decoration:

- I could not keep the memory line from running before the world had a place that can
  be lost. Twenty-two findings went to a question that was degenerate by construction.
- I could not see, before running, six design faults that were visible on paper: a
  moving consumer wears nothing; an unbounded variable makes a loss term negative; a
  rule that optimises a quantity it also changes will oscillate (five times over); a
  symmetry cancels a pull; and a prediction must be derived from every equation the
  measured quantity touches, not from the one that comes to mind first.
- I could not verify the boundary at regrowth rates other than 0.99, in the
  reserve/damage-clock branch on a peaked field, or with reproduction switched on.

## Appendix A. Reproducibility

Every result carries a record with the command, the commit, the dynamics hash, the
`mde` and the controls. The gate is `bash run.sh all`; the agent-state file records
what each cycle changed and what it could not do.

## Appendix B. Negative and withdrawn results

The register of eliminated mechanisms, the reproducibility holes and the list of
claims that were withdrawn are kept in the repository rather than in this paper. Three
withdrawals are relevant to the text above: a claim that a closed return path existed
(it did not; the term was gated where the form stands), a claim that an mde of
`σ = 1000` made an effect void (the σ was invented), and a claim that ring and line
agreed in size (they agree only inside the docking window).
