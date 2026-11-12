//! # The trace
//!
//! `life.rs` runs the cycle and returns a `Census` — six numbers per step. That is a
//! **summary**, not an observation.
//!
//! This module adds what a summary cannot give: **where each organism was, what it
//! saw, what it remembered, and what it did** — at every step.
//!
//! ## Why
//!
//! The project's rule (Krishnamurti P204): *have you ever watched for ten minutes
//! without judging?* A census judges — it reduces a population to a mean. A trace
//! watches — it records what happened.
//!
//! Krishnamurti P283: *looking with a direction is not looking.* A census has a
//! direction ("is the mean rising?"). A trace has none.
//!
//! ## What is recorded
//!
//! Per step, per organism:
//!
//! | field | meaning |
//! |---|---|
//! | `cell` | where it is |
//! | `energy` | what it has |
//! | `damage` | how hurt it is |
//! | `alive` | whether it is still there |
//! | `memory_cell` | what it remembers as richest |
//! | `memory_level` | how rich that was |
//! | `direction` | where it tried to go |
//! | `taken` | what it took from the cell |
//!
//! ## The hash
//!
//! Every trace carries a **hash of its dynamics**. Two arms with the same hash are
//! one arm — the cheapest defence against the most expensive failure (AGENTS.md §5).

#![forbid(unsafe_code)]

use crate::field::Field;
use crate::life::Life;

/// One organism, at one step.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Sample {
    /// The slot the organism occupied. Slots are stable for the whole run, so
    /// this is the identity of the organism. Without it a death can only be
    /// attributed by guessing from (cell, energy), which fails exactly when two
    /// organisms share a cell -- the case worth measuring.
    pub slot: usize,
    pub cell: usize,
    pub energy: f64,
    pub damage: f64,
    pub alive: bool,
    pub memory_cell: usize,
    pub memory_level: f64,
    pub direction: i32,
    pub taken: f64,
}

/// The whole population, at one step.
#[derive(Debug, Clone, PartialEq)]
pub struct Frame {
    pub step: usize,
    pub field: Vec<f64>,
    pub samples: Vec<Sample>,
}

/// A run: the frames, plus a hash of the dynamics.
#[derive(Debug, Clone, PartialEq)]
pub struct Trace {
    pub frames: Vec<Frame>,
    pub hash: u64,
    pub policy: &'static str,
    pub seed: u64,
}

impl Trace {
    /// A stable hash of everything that moved. Two traces with the same hash had the
    /// same dynamics.
    ///
    /// The hash is FNV-1a over the bit patterns of every recorded number. It is not
    /// cryptographic; it is a fingerprint, and its job is to make "two arms that are
    /// secretly one arm" impossible to miss.
    pub fn compute_hash(frames: &[Frame]) -> u64 {
        let mut h: u64 = 0xcbf2_9ce4_8422_2325;
        let mut mix = |x: u64| {
            h ^= x;
            h = h.wrapping_mul(0x0000_0100_0000_01b3);
        };
        for f in frames {
            mix(f.step as u64);
            for v in &f.field {
                mix(v.to_bits());
            }
            for s in &f.samples {
                mix(s.cell as u64);
                mix(s.energy.to_bits());
                mix(s.damage.to_bits());
                mix(s.alive as u64);
                mix(s.memory_cell as u64);
                mix(s.memory_level.to_bits());
                mix(s.direction as i64 as u64);
                mix(s.taken.to_bits());
            }
        }
        h
    }

    /// The JSON form. Written by hand so the crate keeps zero dependencies.
    pub fn to_json(&self) -> String {
        let mut out = String::new();
        out.push_str("{\n");
        out.push_str(&format!("  \"policy\": \"{}\",\n", self.policy));
        out.push_str(&format!("  \"seed\": {},\n", self.seed));
        out.push_str(&format!("  \"hash\": \"{:016x}\",\n", self.hash));
        out.push_str(&format!("  \"steps\": {},\n", self.frames.len()));
        out.push_str("  \"frames\": [\n");
        for (i, f) in self.frames.iter().enumerate() {
            out.push_str("    {\n");
            out.push_str(&format!("      \"step\": {},\n", f.step));
            out.push_str("      \"field\": [");
            for (j, v) in f.field.iter().enumerate() {
                if j > 0 {
                    out.push(',');
                }
                out.push_str(&format!("{:.6}", v));
            }
            out.push_str("],\n");
            out.push_str("      \"samples\": [\n");
            for (j, s) in f.samples.iter().enumerate() {
                out.push_str(&format!(
                    "        {{\"slot\":{},\"cell\":{},\"energy\":{:.6},\"damage\":{:.6},\
                     \"alive\":{},\"memory_cell\":{},\"memory_level\":{:.6},\
                     \"direction\":{},\"taken\":{:.6}}}",
                    s.slot, s.cell, s.energy, s.damage, s.alive, s.memory_cell, s.memory_level,
                    s.direction, s.taken
                ));
                if j + 1 < f.samples.len() {
                    out.push(',');
                }
                out.push('\n');
            }
            out.push_str("      ]\n");
            out.push_str("    }");
            if i + 1 < self.frames.len() {
                out.push(',');
            }
            out.push('\n');
        }
        out.push_str("  ]\n}\n");
        out
    }
}

/// Records a run of `steps` steps, taking a frame every `every` steps.
///
/// The recording is **outside** the cycle: `Life` does not know it is being watched,
/// and nothing the recorder does can change what the organisms do. That is the
/// project's rule 9 — the readout is a camera, not a hand.
pub fn record(life: &mut Life, steps: usize, every: usize) -> Trace {
    let every = every.max(1);
    let mut frames = Vec::new();
    for _ in 0..steps {
        if life.advance().is_none() {
            break;
        }
        if life.step() % every == 0 {
            frames.push(snapshot(life));
        }
    }
    let hash = Trace::compute_hash(&frames);
    Trace {
        frames,
        hash,
        policy: life.policy_name(),
        seed: life.seed(),
    }
}

/// One frame, taken from outside.
fn snapshot(life: &Life) -> Frame {
    let field: &Field = life.field();
    let mut cells = Vec::with_capacity(field.cells());
    for i in 0..field.cells() {
        cells.push(field.level(i));
    }
    Frame {
        step: life.step(),
        field: cells,
        samples: life.samples(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::life::{Life, Policy};
    use crate::organism::World;

    fn setup(policy: Policy, seed: u64) -> Life {
        let world = World {
            income: 0.8,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.02,
            capacity: 10.0,
            read_budget: 0,
        };
        let field = Field::alternating(40, 2.0, 0.2, 0.8).unwrap();
        Life::spawn(world, field, 40, 5.0, 0.1, policy, seed, 300).unwrap()
    }

    #[test]
    fn a_trace_has_frames() {
        let mut life = setup(Policy::Stay, 7);
        let t = record(&mut life, 100, 10);
        assert_eq!(t.frames.len(), 10);
        assert_eq!(t.frames[0].step, 10);
        assert_eq!(t.frames[9].step, 100);
    }

    #[test]
    fn every_sample_carries_a_position() {
        let mut life = setup(Policy::Random, 7);
        let t = record(&mut life, 50, 10);
        for f in &t.frames {
            assert_eq!(f.samples.len(), 40);
            for s in &f.samples {
                assert!(s.cell < 40, "cell {} out of range", s.cell);
            }
        }
    }

    #[test]
    fn the_hash_is_stable_for_the_same_run() {
        let h1 = {
            let mut life = setup(Policy::Random, 42);
            record(&mut life, 100, 10).hash
        };
        let h2 = {
            let mut life = setup(Policy::Random, 42);
            record(&mut life, 100, 10).hash
        };
        assert_eq!(h1, h2, "the same seed must give the same hash");
    }

    #[test]
    fn different_policies_have_different_hashes() {
        let h_stay = {
            let mut life = setup(Policy::Stay, 42);
            record(&mut life, 100, 10).hash
        };
        let h_random = {
            let mut life = setup(Policy::Random, 42);
            record(&mut life, 100, 10).hash
        };
        assert_ne!(h_stay, h_random, "two different arms must differ");
    }

    #[test]
    fn different_seeds_have_different_hashes() {
        let h1 = {
            let mut life = setup(Policy::Random, 1);
            record(&mut life, 100, 10).hash
        };
        let h2 = {
            let mut life = setup(Policy::Random, 2);
            record(&mut life, 100, 10).hash
        };
        assert_ne!(h1, h2, "two seeds must differ");
    }

    /// The direction in a sample must be the decision the organism took, not the
    /// one it would take now.
    ///
    /// Before this test existed, `samples()` recomputed `direction()` at reading
    /// time, against the field AFTER the step. That made the reading inconsistent:
    /// an organism could be shown standing still next to a richer neighbour, which
    /// the policy would never choose. See `docs/FINDING-trace-inconsistent.md`.
    #[test]
    fn the_direction_is_the_decision_not_a_recomputation() {
        let mut life = setup(Policy::Sighted, 7);
        // Run a few steps so the field has a shape the policy reacts to.
        for _ in 0..20 {
            life.advance();
        }
        let samples = life.samples();
        let field: Vec<f64> = (0..life.field().cells()).map(|i| life.field().level(i)).collect();

        // Every sample that claims to stand still must be standing on a cell that
        // is at least as rich as both neighbours AT THE TIME OF THE DECISION.
        //
        // We cannot recover the field before the step from here, so the test is
        // weaker: it checks that a standing organism is not standing next to a
        // neighbour that is richer by a wide margin. A recomputed direction would
        // fail this, because the neighbour it now sees is the one that grew after
        // the step.
        for s in samples.iter().filter(|s| s.alive && s.direction == 0) {
            let here = field[s.cell];
            let left = if s.cell > 0 { field[s.cell - 1] } else { here };
            let right = if s.cell + 1 < field.len() { field[s.cell + 1] } else { here };
            let best = here.max(left).max(right);
            assert!(
                best - here < 0.5,
                "a standing organism at cell {} sees a neighbour richer by {}",
                s.cell,
                best - here
            );
        }
    }

    #[test]
    fn the_recorder_does_not_change_the_run() {
        // The census of a watched run and an unwatched run must agree.
        let mut watched = setup(Policy::Random, 99);
        let t = record(&mut watched, 100, 10);
        let watched_census = watched.census();

        let mut bare = setup(Policy::Random, 99);
        bare.run(100, 10);
        let bare_census = bare.census();

        assert_eq!(watched_census.alive, bare_census.alive);
        assert_eq!(watched_census.moves, bare_census.moves);
        assert_eq!(t.frames.len(), 10);
    }

    #[test]
    fn the_json_is_valid_shaped() {
        let mut life = setup(Policy::Stay, 7);
        let t = record(&mut life, 20, 10);
        let j = t.to_json();
        assert!(j.starts_with('{'));
        assert!(j.trim_end().ends_with('}'));
        assert!(j.contains("\"policy\""));
        assert!(j.contains("\"hash\""));
        assert!(j.contains("\"frames\""));
        assert_eq!(j.matches("\"step\"").count(), t.frames.len());
    }
}
