M = 2.0, r = 0.8, t = 0.6, need = 0.6

Measured settled level L*(k):
  k=1 -> 1.85
  k=2 -> 1.70
  k=3 -> 1.60
  k=4 -> 1.60

Step 1 of each run starts from level M = 2.0.
k=1: 2.0 - 0.6 = 1.4, regrow -> 1.4 + 0.6*0.8 = 1.88
k=2: 2.0 - 1.2 = 0.8, regrow -> 0.8 + 1.2*0.8 = 1.76
k=3: 2.0 - 1.8 = 0.2, regrow -> 0.2 + 1.8*0.8 = 1.64

So the order is: all takes, then one regrow.  (order A)

Fixed point of that map for k organisms taking t each:
  L' = (L - k*t) + (M - (L - k*t))*r
  L* = M - k*t*(1-r)/r
  k=1: 2 - 0.6*0.2/0.8 = 2 - 0.15 = 1.85   OK
  k=2: 2 - 1.2*0.2/0.8 = 2 - 0.30 = 1.70   OK
  k=3: 2 - 1.8*0.2/0.8 = 2 - 0.45 = 1.55   measured 1.60  MISMATCH

Why k=3 stops at 1.60: the cell runs out.
  At L = 1.60 the first two take 0.6 each -> 0.4 left.
  The third can only take 0.4, not 0.6.  It is rationed.
  Then regrow: 0.0 + 2.0*0.8 = 1.60.  Stable.
  At L = 1.60 the sum of takes is 1.60 = L, so the cell empties every step.

So the settled level is the fixed point of
  L' = (L - min(k*t, L)) + (M - (L - min(k*t, L)))*r

If k*t <= L:  L* = M - k*t*(1-r)/r        (rationed-free branch)
If k*t >  L:  L' = M*r  (cell empties), and M*r = 1.6.
              The branch is used when k*t > M*r, i.e. k > M*r/t = 1.6/0.6 = 2.667.

Check: k=1,2 -> first branch: 1.85, 1.70.  k=3,4 -> second branch: 1.60.

    L*(k) = M - k*t*(1-r)/r   if k*t <= M*r
          = M*r               if k*t >  M*r

Verified: EXP-94, 21 arms, 0 mismatches.

CAPACITY.  One cell holds kFull = floor(M*r/t) organisms that each get
the full t, plus one more that gets the remainder

    rem = M*r - kFull*t.

That last one survives only if its ration covers its maintenance:

    per_cell = kFull + [rem > maintenance_cost]
    capacity = cells * per_cell

Verified: EXP-97, 10 arms, 0 mismatches (M in 2..4, r in 0.5..0.9,
t in 0.2..1.0, mc in 0.1..0.5).

TWO WORLDS WHERE THE LAW DOES NOT HOLD, and why:

1. maintenance_cost = 0.  `Organism::step` does `energy += taken;
   energy -= maintenance_cost`.  An organism that eats nothing and
   costs nothing keeps its energy forever.  Nothing starves, so there
   is no capacity at all: n = 240 on 40 cells leaves 240 alive.
   EXP-96 A.  A world with zero maintenance has no carrying capacity.

2. maintenance_cost >= income.  Every organism loses energy every step
   and dies, including the ones that eat.  EXP-97 measured alive = 0
   at M=2, r=0.8, t=0.2, mc=0.5.  This is the `is_viable` condition
   (`income > maintenance_cost`) and it must be checked before any
   capacity is quoted.

So the capacity formula is conditional on
    maintenance_cost < income        (else everyone dies)
    maintenance_cost > 0             (else nobody dies)
and it is the same formula the earlier "C = 80" was an instance of:
cells=40, M=2, r=0.8, t=0.6, mc=0.6 -> kFull=2, rem=0.4, 0.4 < 0.6 ->
per_cell=2 -> C=80.  The old C=80 was right for its world and wrong as
a law.

The old formula M - t/r was wrong because it assumed one organism per
cell.  The old C = cells*M*r/income was wrong because it ignored the
rationed organism and the maintenance threshold.
