//! # A room that grows with the child
//!
//! The previous module found that a wide room is not a wide life: the room has to be
//! filled, and filling takes `(B/σ)²` steps. A child in a room of half-width 30 needs
//! 10 000 steps before it has the range the room allows.
//!
//! This module asks the practical question: **what if the room grows with the child?**
//!
//! ## The three schedules
//!
//! | schedule | rule | what it means |
//! |---|---|---|
//! | **jump** | `B = 30` from the start | the wide room is given at once |
//! | **linear** | `B` grows from 3 to 30 over the run | the room opens gradually |
//! | **matched** | `B = √3 · spread` | the room is exactly the law's room for the child |
//!
//! ## The prediction
//!
//! The matched schedule should keep the child at the law the whole time: the room is
//! always exactly as wide as the child's range requires, so there is nothing to fill.
//!
//! The linear schedule should reach the wide room sooner than the jump, because the
//! child fills each small room before the next opens.
//!
//! ## The catch
//!
//! A matched room **measures the child**. That is principle 3. So the matched schedule
//! is an experiment **outside** the medium — it shows what the ideal would be, not
//! what the medium does.

#![cfg(test)]

use medium_core::boundary::OutsideExperiment;
use medium_core::child::{Child, Medium};
use medium_core::room::{Room, Shape};
use medium_core::HalfWidth;

fn spread_of(pop: &[Child]) -> f64 {
    let n = pop.len();
    let mean: f64 = pop.iter().map(|c| c.position()[0]).sum::<f64>() / n as f64;
    (pop.iter()
        .map(|c| {
            let x = c.position()[0] - mean;
            x * x
        })
        .sum::<f64>()
        / n as f64)
        .sqrt()
}

/// The three schedules.
#[derive(Clone, Copy, PartialEq)]
enum Schedule {
    /// The wide room from the start.
    Jump(f64),
    /// Grows from `b0` to `b1` linearly over `steps`.
    Linear(f64, f64),
    /// `B = sqrt(3) * spread`, clamped.
    Matched,
}

fn run(schedule: Schedule, sigma: f64, n: usize, seed: u64, steps: usize, b0: f64) -> Vec<f64> {
    let room = Room::new(Shape::Box, HalfWidth::new(b0).unwrap(), 1).unwrap();
    let mut medium = Medium::new(room, seed);
    let mut rng = medium_core::Rng::new(seed);
    let mut pop: Vec<Child> = (0..n)
        .map(|_| Child::new(vec![rng.normal() * 0.5], 0.0, sigma).unwrap())
        .collect();

    let experiment = OutsideExperiment::declare();
    let mut history = Vec::new();

    for step in 0..steps {
        let frac = step as f64 / steps as f64;
        let b = match schedule {
            Schedule::Jump(b) => b,
            Schedule::Linear(from, to) => from + (to - from) * frac,
            Schedule::Matched => {
                let s = spread_of(&pop);
                (3.0_f64.sqrt() * s).clamp(0.5, 100.0)
            }
        };
        let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
        medium.set_room(room);

        for c in pop.iter_mut() {
            if schedule == Schedule::Matched {
                // The matched room reads the child, so it is an experiment outside.
                let _ = experiment.step_and_act(&mut medium, c, |p| p.to_vec());
            } else {
                medium.step(c).unwrap();
            }
        }
        history.push(spread_of(&pop));
    }
    history
}

#[test]
fn a_matched_room_is_a_trap() {
    // A correction found by this test.
    //
    // The prediction was that a room matched to the child — `B = sqrt(3) * spread` —
    // would keep the child at the law. It does the opposite: the spread falls.
    //
    // The reason is arithmetic. With `B = sqrt(3) * spread` the law for that room is
    // `B/sqrt(3) = spread`, so the room is always exactly as wide as the child's
    // current range. The spread cannot grow: it is already at the law. And it falls.
    //
    // This is the self-referential wall of `FINDING-feedback.md`, in a new form.
    let sigma = 0.3;
    let steps = 3000;
    let history = run(Schedule::Matched, sigma, 800, 8001, steps, 3.0);

    let early = history[steps / 4];
    let late = history[steps - 1];
    println!("matched: early {:.3}, late {:.3}", early, late);
    assert!(
        late < early,
        "a matched room should narrow the child, not hold it: {} -> {}",
        early,
        late
    );
}

#[test]
fn a_jump_starts_far_below_its_law() {
    // The wide room given at once: the child is far below the law for a long time.
    let sigma = 0.3;
    let steps = 3000;
    let wide = 30.0;
    let law = wide / 3.0_f64.sqrt();
    let history = run(Schedule::Jump(wide), sigma, 800, 8002, steps, 3.0);
    let early = history[steps / 4];
    println!(
        "jump: at {} steps {:.2} of {:.2} law ({:.0}%)",
        steps / 4,
        early,
        law,
        100.0 * early / law
    );
    assert!(
        early / law < 0.5,
        "a jumped room should still be far below its law: {} vs {}",
        early,
        law
    );
}

#[test]
fn a_jump_beats_a_linear_growth() {
    // A correction. The prediction was that a gradual room beats a jump, because the
    // child fills each small room before the next opens.
    //
    // The measurement says the opposite: at the end the jumped child is closer to its
    // law than the gradually grown one (0.829 vs 0.732). The reason is time: the
    // jumped child had the whole run to fill a wide room, while the gradual child only
    // had the last part of the run.
    let sigma = 0.3;
    let steps = 3000;
    let wide = 30.0;

    let jump = run(Schedule::Jump(wide), sigma, 800, 8003, steps, 3.0);
    let linear = run(Schedule::Linear(3.0, wide), sigma, 800, 8003, steps, 3.0);

    let law = wide / 3.0_f64.sqrt();
    let jump_ratio = jump[steps - 1] / law;
    let linear_ratio = linear[steps - 1] / law;

    println!(
        "at the end: jump {:.3} of law, linear {:.3} of law",
        jump_ratio, linear_ratio
    );
    assert!(
        jump_ratio > linear_ratio,
        "a jump should beat a gradual room at equal time: jump {} vs linear {}",
        jump_ratio,
        linear_ratio
    );
}

#[test]
fn the_gradual_room_falls_behind_everywhere() {
    // The complement of the previous test: at every checkpoint the jumped child is at
    // least as close to the wide room's law as the gradual one, because the gradual
    // child spent its early time in a narrow room.
    let sigma = 0.3;
    let steps = 3000;
    let wide = 30.0;

    let jump = run(Schedule::Jump(wide), sigma, 800, 8004, steps, 3.0);
    let linear = run(Schedule::Linear(3.0, wide), sigma, 800, 8004, steps, 3.0);

    let law = wide / 3.0_f64.sqrt();
    let mut behind = 0;
    let mut total = 0;
    for step in (100..steps).step_by(200) {
        total += 1;
        if linear[step] < jump[step] {
            behind += 1;
        }
    }
    println!("linear behind jump in {}/{} checkpoints", behind, total);
    assert!(
        behind * 10 >= total * 9,
        "the gradual room should be behind almost everywhere: {}/{}",
        behind,
        total
    );
    let _ = law;
}
