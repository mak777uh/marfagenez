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

Price, not behaviour, sets what a minimal consumer can do. We derive a boundary from the rules of a
single cell - a consumer survives a step exactly when `income - maintenance >= damage * repair` -
preregister it, and test it out of sample: it holds to the step across four world sizes, and its two
branches are predicted and confirmed.

Three methodological results follow. Seeds are not replication: twelve seeds give a standard
deviation of zero where thirty-six environments give about nine steps. A two-tailed effect must be
reported as a profile, not a mean: one contrast has a mean of -1665 and two humps of +4 and -10001.
And the measure of the medium is inseparable from the instrument that reads it.

We then report six programmes that did not deliver, each with its reason: memory where standing
still is rewarded; structure in a field without a price; ownership that cannot become care;
selection over a fixed repertoire; perception, where a look that pays for itself loses; and a space
of shapes. In that last one a solvency interval is real but bounded by fitness rather than by
solvency, and a predicted extinction threshold holds at 24 of 24 runs below it and 0 of 24 above.

Nothing here is claimed emergent. Where a boundary was found, it is reported as a boundary.

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

Every experiment is preregistered (Nosek et al. 2018) with four outcomes (`passed`, `failed`, `void`, `not
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
exceeds any field variation we tried, within the ranges we varied; it is a strong
statement about this model, not a ranking of mechanisms in general.

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

| spacing (cells between islands) | memory share | 90% bootstrap over environments (Efron and Tibshirani 1993) |
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

The mechanism is the one the literature predicts (Riotte-Lambert et al. 2017): a sighted organism steps toward one
neighbour, so having eaten out an island it walks into the poor sea; a memory-holder
returns to the island when it has recovered. In a patchy medium it pays to return rather
than to search - and the model **cannot** test the alternative, because an organism
compares exactly one neighbour and therefore cannot search at all.

![Share of runs surviving against the fixed cost per form, for three starting forms with the
stock at capacity (left) and at half capacity (right). Dashed lines are the thresholds predicted before
the runs; they land between the last surviving price and the first lethal one in every case. At half
stock every curve falls together, because every income is halved at the same time.](figures/threshold.svg)

*Figure 3.* The threshold of §4.7. The prediction is not the shape of the curves - which is a step by
construction - but the position of each step, from the arithmetic of the starting form.

### 4.7 A predicted extinction threshold on a shared medium

The law of §4.1 is per cell. The shape world of §9.6 tests whether it still predicts when the
medium is shared and the consumer has a shape.

Income is throttled by a shared stock, `f = stock/stock_max`, so a form of `n` cells with `p`
boundary edges survives while

    f * sigma * p  >=  f0 + mu * n + kappa * n^2 / p

with `f0` a fixed cost per form. The left side is maximised, as a function of size, at a surplus of
`14.679`; a medium can therefore support any form at all only while `f >= f0 / 14.679`. With the stock
starting at capacity, the first step of consumption leaves `f = 0.760`, so a fixed cost of 12 demands
`0.817` and cannot be paid, while 11 demands `0.749` and can.

**The prediction was declared before the runs**: 24 replicates per price. It held - 24 of 24 worlds
alive at a fixed cost of 11, and 0 of 24 at 12. The same arithmetic then predicted the threshold for
other starting forms: a single cell should fall by a fixed cost of 7, a two-by-two by 11.8, a
three-by-three by 14.3. Measured: below 8, below 11, and at 12 respectively.

The dependence is worth stating plainly, because it is not the medium's alone: **the medium pays as
much as the most profitable form the world can reach**, and which forms are reachable depends on the
starting configuration. At half the starting stock the threshold does not halve evenly - it falls to
between 2 and 4 for every start, because the income of every form is halved at the same time as its
first step.

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

The same contrast, reported as a mean, gives `−1665` steps. Reported as a profile, it is two
humps: a median win of **+4** and a median loss of **−10 001**. The mean is negative because a loss is
enormous, not because losses are frequent. A two-humped quantity reported as a mean is
an artefact of the summary, and for publication we report two fractions with Wilson
intervals (Wilson 1927) and the median size of each tail.

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

A comparison with Conway's Life (Gardner 1970) is in the repository and is not a result: Life shows
structural novelty from fixed rules without any player, which our model cannot produce
because it has no space of configurations, and our model has a price which Life does
not, so self-maintenance cannot even be asked there. The two are complements.

### 6.4 Care cannot be posed, and neither can searching

Ownership of cells was implemented and measured: a form holds a cell by standing on it,
another takes it only by overwriting, a claim decays without presence, and a stranger
eats a fraction of what the holder eats until it overwrites. In an economy at the
boundary this changes who survives: with a stranger's share of 0.50 the
holder survives and
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
  but care is behaviour and behaviour in this model is written by us, not selected (§6.4).

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

## 9. The negative programme

A paper that reports only what worked leaves the reader unable to tell a narrow result
from a shallow one. This section is the rest of the work: four programmes that were
carried out, measured, and did not give what they were meant to give. Each ends with the
reason, because the reasons are the useful part.

### 9.1 Memory in a world that rewards standing still

Across 216 declared environments, a policy that remembers one cell and returns to it
gains a median of **+4 steps** in 13% of environments, loses a median of **−10 001** in
17%, and is indistinguishable from a memoryless controller in the other 70%. The loss in
the losing tail is the horizon: the organism dies.

The reason is not that memory is bad. It is that in these worlds **movement is not worth
anything**: the medium regrows on its own, so a form that stands on a rich cell does as
well as any searcher, and a memory that saves search saves nothing. When the movement cost
was made explicit, nothing changed, because nobody moved.

What would be needed is a medium where a visit **builds** something that lasts and where
absence loses it. That is a different world, and it is what the next two programmes tried
to build.

### 9.2 Structure in a field without a price, and price without structure

A Gray-Scott field (Gray and Scott 1984) with no agent at all does grow a structure: a localised spot appears at
`(F, k) = 0.045…0.050, 0.065`, reproducible, and it is the first object in this project
that nobody wrote. Given a price, it dies almost immediately - at a consumption of 0.05
against a regrowth of 0.2 - because it pays where it lives, out of the resource that keeps
it open.

A reservoir in the same cells does not help: the price edge does not move at all, because
a store that sits where the structure eats is still a payment in place. What the organism
has and the field lacks is a store it can **carry**.

Two further results closed the programme. The recovery time of the Barkley medium (Barkley 1991) is
`T = eps·a/b`, which is 750 time units at the parameters used, against runs of 120 - so
what looked like a travelling front was sixteen percent of the way to rest, i.e. the decay
of the initial condition. And excitability itself needs a large `eps`, which forces a long
`T`: at small `eps` the excitation dies before it can propagate. **One quantity controls
both**, so no parameter choice gives a structure that both propagates and can be observed
against rest.

The measured complement stands: `Life` has structure without price, this field has price
without structure, and neither gives a form that maintains itself by moving.

### 9.3 Ownership that cannot become care

Ownership was implemented and works. A form holds a cell by standing on it, another takes
it only by overwriting, a claim decays without presence, and a stranger eats a fraction of
what the holder eats until it overwrites. At the maintenance boundary this changes who survives.
With a stranger's share of 0.50 the holder survives while the walker falls from 165 to 49 steps. At
0.25 both die, because the walker overwrites the holder's cell and the holder then eats as a
stranger on its own former place. At 0.00 the holder
dies in 22 steps and the walker holds every cell.

So losing a place is mortal rather than metaphorical. But the claim that ownership creates
care could not be tested. The proposed comparison, a returning form against a wandering one,
failed its own control: with ownership switched off, where the two should not differ, the returning
form lived twenty-four times longer. Memory in this model keeps a form near rich cells, so
returning is confounded with being well fed.

The confound cannot be removed without a policy that reads claims, and writing one means
writing the behaviour. **Care is behaviour; behaviour here is written by us; a rule of
access is not behaviour.**

### 9.4 Selection that has nothing to choose between

With births, deaths and a mutation rate on the policy, selection is real: a population of
walkers at the maintenance boundary ends with a mixed repertoire and half the population
dead, while in a comfortable economy it ends with twelve walkers and no deaths at any
mutation rate. A comfortably fed world selects nothing.

Designing a medium for selection to act on took three attempts. The first was a grave: a
poor level of 0.8 against an upkeep of 1.79 is below the survival line, so three of four
worlds died out entirely - a niche is a place where things are worse, not a place where
they are impossible. The second was too comfortable: with every cell survivable and a
population cap equal to the number of cells, nobody died and the composition did not move
at all. **A margin keeps everyone alive; crowding is what makes anyone die.** The third
worked weakly, and the finding is in §4.6: selection sees the **spacing** of rich patches
and not their patchiness, and cannot see searching at all, because an organism compares
exactly one neighbour.

![Sighted minus memory share against the price of one look, with 90% bootstrap intervals
over eight environments per price. The difference crosses zero between 0.02 and 0.03, and the
intervals separate from zero only at 0.04 and above. The note under the axis gives the
crossings at five surpluses, which show no form.](figures/price.svg)

*Figure 4.* The threshold of §9.5. Positive means looking pays; the dashed band is where the
difference changes sign. The point of the figure is what it does not show: the crossing exists
in this economy, and across surpluses it moves without a pattern.

### 9.5 Perception is necessary and does not pay

If a medium is to reward searching rather than returning, it must offer a signal. On a line
with a rich island every eight cells, a one-neighbour rule is **silent in 71% of the sea**:
both neighbours are equal, so "toward the island" and "away from it" are indistinguishable,
and the rule wanders. This is arithmetic on the field levels, not a simulation
(`checks/perception_signal.py`).

Widening the look to a window of radius three gives a signal in every sea cell, and the
window is added so that radius one runs the original rule byte for byte. With free looks the
window does not beat memory by a significant margin. With priced looks it does - until the
price crosses a threshold: at a read cost of 0.05 the memory-holding share is 0.151 against
0.021 for sighting, with non-overlapping intervals, and at 0.15 sighting is extinct.

The threshold is between 0.02 and 0.03 per look, near 37% of the surplus at that economy.
But it is **not a law**: at a surplus of 1.4 the same fraction falls to 0.01-0.06, so a richer
world tolerates *less* expensive information rather than more, and across five surpluses the
crossing jumps (`0.023, none, 0.003, 0.024, 0.055`) with no visible form.

What is established: a threshold exists, it is not proportional to the surplus, and its order
is hundredths per look. What is a limit of the instrument: the location of the crossing is
unstable at eight environments per point, and a form would need thirty or more plus a smoothed
estimate. That work is not done, and it is not claimed.

### 9.6 Structures: a threshold, and why the interval hid

The last programme gave this model a space of configurations for the first time: a form is a
connected set of cells, its income is proportional to its boundary, its upkeep to its cells plus a
cost for depth and a fixed cost per form. That is enough for shape to matter, and enough to compute
a solvency interval in closed form: a square of side `s` survives while
`4*sigma*s >= f0 + mu*s^2 + kappa*s^3/4`, which gives **two** roots, a minimum and a maximum size.

Three results came out of it, and two of them are corrections of our own reading.

**The mutation process has no stable size.** With one cell added or removed per event, a form has
far more legal additions than legal removals, so size ratchets upwards. The neutral rate is
`p_grow = 0.27`; below 0.18 the form erodes to a single cell, above 0.28 it explodes, and one
hundredth in the rate multiplies the mean size by 3.5. Measured with no economy at all, twenty-four
replicates per rate.

**Viability is not fitness.** The solvency interval says who can live; selection follows the number
of offspring, which is proportional to the **absolute** margin, and absolute margin grows with size.
So the interval never bounded the outcome: bigger forms were simply richer and bred faster. This is
why four earlier attempts failed to see the interval at all.

**The interval is visible in the median, not in the mean.** Over twenty-four runs at a fixed cost of
ten, the median side is 5.00, inside the computed interval 1.571...5.420; the mean over the same runs
is 11 to 17, pulled up by a few large forms. The lesson is the one §5.2 already stated for a memory
contrast: a heavy-tailed quantity must not be reported as a mean.

The programme also produced the predicted threshold reported in §4.7, and the limit of that
mechanism: at half the starting stock the threshold does not halve but falls to between 2 and 4,
because the starting form has to survive its first step for any of the steady-state arithmetic to
apply.

Nothing in this programme shows structure emerging. What it shows is a threshold, the mechanism of
that threshold, and the boundary of the mechanism.

### 9.7 What the six programmes have in common

In every one, the effect that appeared was **smaller and narrower** than the effect that
was sought, and the reason we found in each case was the same: this architecture has a
price and no
space, a repertoire and no variation of it, a neighbour and no region. The law in §4 holds
precisely because it does not depend on any of those: it is arithmetic of a single cell.

## References

Barkley, D. (1991). A model for fast computer simulation of waves in excitable media.
*Physica D* 49(1-2), 61-70.

Efron, B. and Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman and
Hall, New York.

Gardner, M. (1970). Mathematical games: the fantastic combinations of John Conway's new
solitaire game "life". *Scientific American* 223(4), 120-123.

Gray, P. and Scott, S. K. (1984). Autocatalytic reactions in the isothermal, continuous
stirred tank reactor: oscillations and instabilities in the system A + 2B -> 3B; B -> C.
*Chemical Engineering Science* 39(6), 1087-1097.

Nosek, B. A., Ebersole, C. R., DeHaven, A. C. and Mellor, D. T. (2018). The
preregistration revolution. *Proceedings of the National Academy of Sciences* 115(11),
2600-2606.

Riotte-Lambert, L., Benhamou, S., Bonenfant, C. and Chamaille-Jammes, S. (2017). Spatial
memory shapes density dependence in population dynamics. *Proceedings of the Royal Society
B* 284(1867), 20171411.

Wilson, E. B. (1927). Probable inference, the law of succession, and statistical
inference. *Journal of the American Statistical Association* 22(158), 209-212.

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
