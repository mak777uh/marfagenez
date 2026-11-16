//! The damage clock is the running sum, not `ceil(1/dr)`.
//!
//! Step 3 of `Organism::step_with` is
//!
//! ```text
//! self.damage = (self.damage + world.damage_rate).min(1.0);
//! ```
//!
//! so the number of steps from no damage to death by damage is
//!
//! ```text
//! K(dr) = min { k : fl_sum_k(dr) >= 1.0 }
//! ```
//!
//! with every addition rounded. `FINDING-148` measured `K = 11` at `dr = 0.1`
//! and used it in the boundary of life; `FINDING-150` says when the formula
//! `ceil(1/dr)` is that number and when it is not. These tests pin the model's
//! own clock, so that a rewrite of the accumulation into `damage = dr * k` --
//! which is exactly what `ceil(1/dr)` assumes -- cannot pass.
//!
//! Three points, chosen because they are the three cases the finding
//! distinguishes:
//!
//! * `dr = 0.1` -- the running sum falls `1 ulp` short of `1.0` in ten steps,
//!   so `K = 11 > ceil(1/dr) = 10`. This is the point 148 saw.
//! * `dr = 0.125` -- `ceil(1/dr) = 8` is exact and the running sum is exact,
//!   so the formula is right: `K = 8`. Not `10`: the clock is measured, and the
//!   brief for this test carried `10` by mistake.
//! * `dr = 0.0909090909090909` -- just below `1/11`. The division rounds
//!   `1.0 / dr` up to `11.000000000000002`, `ceil` gives **12**, and the model
//!   dies on step **11**: here `ceil` overestimates, which a formula-shaped
//!   error would show as a test that could only ever be too high.

use medium_core::organism::{Organism, RepairPolicy, World};

/// Steps until death by damage, with repair off and the reserve never empty.
///
/// `RepairPolicy::None` is the point: the clock is a property of step 3 alone,
/// and a repairing organism would reset the damage before it reached `1.0`.
/// The reserve cannot be the cause of death here -- income `1.0` against
/// maintenance `0.6` fills it to `capacity` and keeps it there -- and the two
/// assertions say so instead of assuming it.
fn damage_clock(damage_rate: f64) -> usize {
    let world = World {
        damage_rate,
        ..Default::default()
    };
    let mut organism = Organism::healthy(5.0).expect("a healthy organism");
    let mut steps = 0;
    loop {
        steps += 1;
        assert!(
            steps <= 20_000,
            "the clock did not stop at dr = {damage_rate}"
        );
        if !organism.step_with(&world, world.income, RepairPolicy::None) {
            break;
        }
    }
    assert!(
        organism.damage() >= 1.0,
        "death was not from damage at dr = {damage_rate}"
    );
    assert!(
        organism.energy() > 0.0,
        "death was from starvation, not damage, at dr = {damage_rate}"
    );
    steps
}

/// `dr = 0.1`: the running sum misses `1.0` by one ulp in ten steps.
///
/// `FINDING-148` measured this as `K = 11` against `ceil(1/dr) = 10`. The
/// assertion on `ceil` is not decoration: it keeps the two numbers in the same
/// test, so a reader does not have to take the discrepancy on faith.
#[test]
fn the_damage_clock_is_eleven_steps_at_one_tenth() {
    assert_eq!((1.0_f64 / 0.1).ceil() as usize, 10);
    assert_eq!(damage_clock(0.1), 11);
}

/// `dr = 0.125`: `1/8` is exact in binary, so the formula is right.
///
/// This is the control in the other direction -- the clock is not simply
/// `ceil + 1`. `ceil(1/0.125) = 8` and the model dies on the eighth step.
#[test]
fn the_damage_clock_agrees_with_ceil_at_one_eighth() {
    assert_eq!((1.0_f64 / 0.125).ceil() as usize, 8);
    assert_eq!(damage_clock(0.125), 8);
}

/// Just below `1/11`: `ceil(1.0/dr)` **overestimates** the clock.
///
/// `1.0 / 0.0909090909090909` rounds up to `11.000000000000002`, so `ceil`
/// gives 12. The running sum reaches `1.0` on the eleventh addition: eleven
/// copies of this `dr` round to just over `1.0`, while ten do not. A formula
/// that could only err by one extra step would not produce this case, and a
/// test that only checked `dr = 0.1` would not either.
#[test]
fn ceil_overestimates_just_below_one_eleventh() {
    let damage_rate = 0.0909090909090909_f64;
    assert_eq!((1.0_f64 / damage_rate).ceil() as usize, 12);
    assert_eq!(damage_clock(damage_rate), 11);
}
