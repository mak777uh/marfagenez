//! A golden vector for the dynamics hash.
//!
//! `Trace::compute_hash` is the definition of "the same dynamics" (AGENTS.md
//! §5): two arms with the same hash are one arm. That definition is only worth
//! something if the hash cannot change while the records that quote it stay on
//! disk. It did change once -- `prev_cell` was mixed in after
//! `results/standing-is-a-uniform-third/` was written, and the recorded
//! `40bd71fa379e135a` stopped reproducing (`f94d3b830971a9e8` on `HEAD`).
//!
//! So one fixed scenario is pinned to a literal. If any component of the hash
//! moves -- a field, a sample field, the order they are mixed, the birth tag --
//! this test goes red, and the author has to decide whether the change is
//! intentional (bump `HASH_VERSION`, re-pin this constant, update
//! `docs/hash-unversioned.txt`) or a regression.
//!
//! ## What the scenario touches
//!
//! The world is not a convenient one: 120 steps of `Policy::Memory` on an
//! alternating field with births on. The assertions below are there because a
//! golden vector that only exercises half the hash pins nothing about the other
//! half. This scenario produces, over 7176 samples: 3706 alive and 3470 dead,
//! 3470 with non-zero `damage`, 2843 with non-zero `taken`, both directions
//! (`-1`: 2174, `+1`: 1880, `0`: 3122), 3587 samples whose `cell` differs from
//! `prev_cell`, non-zero `memory_cell`/`memory_level`, and a population that
//! grows past the starting 24 (births, so the birth tag is in the hash too).
//!
//! ## What it does not prove
//!
//! It pins **one** scenario, not the function. A change that only affects
//! branches this run never takes would still pass. That gap is closed by the
//! version bump, not by this file: the constant is a witness, not a proof.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{LookOrder, ShareProtocol, TieBreak, World};
use medium_core::trace::{record, Trace};

/// The hash of the scenario below, computed with `HASH_VERSION = "2-prev-cell"`.
///
/// Re-pin this only together with a bump of `HASH_VERSION` in `core/src/trace.rs`.
const GOLDEN_HASH: u64 = 0x445834e79a0843ee;

fn golden_trace() -> Trace {
    let world = World {
        income: 1.0,
        maintenance_cost: 0.6,
        repair_cost: 1.5,
        damage_rate: 0.02,
        capacity: 10.0,
        read_budget: 1,
        share: ShareProtocol::Sequential,
        tiebreak: TieBreak::Left,
        look_order: LookOrder::LookThenEat,
        birth_threshold: 4.0,
        birth_cost: 2.0,
        max_population: 60,
    };
    let field = Field::alternating(12, 2.4, 1.6, 0.8).unwrap();
    let mut life =
        Life::spawn_even(world, field, 24, 5.0, 0.1, Policy::Memory, 7, 300).unwrap();
    record(&mut life, 120, 1)
}

#[test]
fn the_dynamics_hash_is_pinned_to_a_golden_vector() {
    let trace = golden_trace();

    assert_eq!(trace.frames.len(), 120, "the scenario must run all 120 steps");
    assert_eq!(
        trace.hash, GOLDEN_HASH,
        "the dynamics hash moved. If the change is intended, bump HASH_VERSION \
         in core/src/trace.rs, re-pin GOLDEN_HASH, and refresh \
         docs/hash-unversioned.txt; if it is not, this is the regression that \
         FINDING-154 was written about"
    );
}

/// Every component `compute_hash` mixes must actually carry a non-zero value in
/// the golden run. Without this, the constant above would keep passing while
/// silently pinning fewer and fewer fields.
#[test]
fn the_golden_scenario_touches_every_component_of_the_hash() {
    let trace = golden_trace();

    let mut alive = 0usize;
    let mut dead = 0usize;
    let mut damage_nonzero = 0usize;
    let mut taken_nonzero = 0usize;
    let mut dir_neg = 0usize;
    let mut dir_pos = 0usize;
    let mut moved = 0usize;
    let mut memory_learned = 0usize;
    let mut memory_level_nonzero = 0usize;
    let mut field_nonzero = 0usize;
    let mut peak_population = 0usize;

    for frame in &trace.frames {
        if frame.field.iter().any(|v| *v != 0.0) {
            field_nonzero += 1;
        }
        peak_population = peak_population.max(frame.samples.len());
        for s in &frame.samples {
            if s.alive {
                alive += 1;
            } else {
                dead += 1;
            }
            if s.damage != 0.0 {
                damage_nonzero += 1;
            }
            if s.taken != 0.0 {
                taken_nonzero += 1;
            }
            if s.direction < 0 {
                dir_neg += 1;
            } else if s.direction > 0 {
                dir_pos += 1;
            }
            if s.cell != s.prev_cell {
                moved += 1;
            }
            if s.memory_cell != s.cell {
                memory_learned += 1;
            }
            if s.memory_level != 0.0 {
                memory_level_nonzero += 1;
            }
        }
    }

    assert!(field_nonzero == trace.frames.len(), "the field is mixed every frame");
    assert!(alive > 0, "no living sample: `alive` is constant, not pinned");
    assert!(dead > 0, "no dead sample: `alive` is constant, not pinned");
    assert!(damage_nonzero > 0, "damage is always zero and not pinned");
    assert!(taken_nonzero > 0, "taken is always zero and not pinned");
    assert!(dir_neg > 0, "no organism ever walked left");
    assert!(dir_pos > 0, "no organism ever walked right");
    assert!(moved > 0, "prev_cell never differs from cell: movement not pinned");
    assert!(
        memory_learned > 0,
        "no organism ever remembered a cell other than its own"
    );
    assert!(
        memory_level_nonzero > 0,
        "memory levels are always zero and not pinned"
    );
    assert!(
        peak_population > 24,
        "the population never grew past the starting 24, so the birth tag is \
         absent from the hash"
    );
}
