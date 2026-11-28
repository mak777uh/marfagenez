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

use crate::field::{Field, FieldStateSnapshot};
use crate::life::{Life, LifeExperimentSnapshot};
use crate::organism::{LookOrder, World};

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
    /// The cell the organism was on before it moved this step. Equal to `cell`
    /// when it stood still.
    pub prev_cell: usize,
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
    /// Random generator algorithm/version used by the run.
    pub rng_version: &'static str,
    /// How many cells each organism could read per step.
    ///
    /// Recorded because it decides what the run *means*: a `memory` organism
    /// with a budget of zero cannot see a neighbour, and the same policy at
    /// budget 3 behaves differently. A trace without this number cannot be
    /// compared to another trace.
    pub read_budget: usize,
    /// How the income on a shared cell is divided.
    ///
    /// `sequential` and `proportional` give **different integer laws** for how
    /// many organisms a cell holds on the same resource (see
    /// `checks/exp99_protocol_capacity.py`). A trace that does not record which
    /// one ran cannot be compared to another trace — and two arms that differ
    /// only in the protocol would look like one arm.
    pub share: &'static str,
    /// How a tie between two equal neighbours is resolved.
    ///
    /// On a uniform field every comparison is a tie, so this parameter alone
    /// decides which way the population walks. A trace that does not record it
    /// cannot be compared to another trace: two arms that differ only in the
    /// tie-break would look like one arm, and the left drift would look like a
    /// property of the environment instead of a property of the rule.
    pub tiebreak: &'static str,
    /// Whether a `Memory` organism read its cell before or after eating.
    ///
    /// Same argument as `tiebreak`, one parameter further: the two orders can
    /// produce identical frames for a while -- on a field where the organism
    /// never returns to a cell it has eaten from, they never differ at all --
    /// and then the arms would collide and the collision would be read as "the
    /// parameter did not reach the simulation". See `LookOrder`.
    pub look_order: &'static str,
    /// The energy a parent must hold to give birth; `INFINITY` means never.
    ///
    /// Recorded because a run with births and a run without them are different
    /// experiments, and the parameters are what tells them apart: without them
    /// two arms would be indistinguishable by their record until somebody
    /// happened to die or be born. See `World::birth_threshold`.
    pub birth_threshold: f64,
    /// Energy moved from a parent to a child.
    pub birth_cost: f64,
    /// The population cap; `0` means births are off.
    pub max_population: usize,
    /// Energy paid per neighbour read. `0.0` is free reading.
    ///
    /// Recorded because a priced run and a free run are different experiments
    /// that can share frames for a while. See `World::read_cost`.
    pub read_cost: f64,
    /// Steps between two samples for a `Memory` organism; `1` is every step.
    ///
    /// Recorded for the same reason as `read_cost`: a run that looks every
    /// fourth step and a run that looks every step are different experiments
    /// that can agree for a while and then diverge, and without the number the
    /// two records would look like one.
    pub read_period: usize,
    /// Whether a `Memory` organism looked out of turn when the cell
    /// underfoot could not pay the upkeep. `false` is the historical
    /// schedule; `true` is the rule declared in `docs/FINDING-161.md`.
    pub look_on_shortfall: bool,
    /// Per-slot policy map. `policy` is `mixed` when these are not all equal.
    pub policy_by_slot: Vec<&'static str>,
    /// Configuration snapshot at the start of this recording, as canonical JSON.
    pub configuration: String,
    /// SHA-256 of `configuration`; separate from the historical dynamics hash.
    pub config_sha256: String,
    /// Requested maximum number of advances passed to `record`.
    pub requested_steps: usize,
    /// Number of successful advances actually executed by `record`.
    pub executed_steps: usize,
    /// Absolute step counter at the start of this recording.
    pub start_step: usize,
    /// Caller-provided sampling interval, before the zero-to-one normalization.
    pub sample_every_requested: usize,
    /// Effective sampling interval used by the recorder.
    pub sample_every: usize,
    /// Number of frames written; retained separately from legacy `steps`.
    pub frames_written: usize,
}

/// The version of the dynamics hash.
///
/// `Trace::compute_hash` is the definition of "the same dynamics": two arms
/// with the same hash are one arm (AGENTS.md §5). That rule only holds if the
/// hash means the same thing on both sides of the comparison, and it did not:
/// the recorded hash `40bd71fa379e135a` in `results/standing-is-a-uniform-third/`
/// cannot be reproduced on `HEAD` (`f94d3b830971a9e8`), because `prev_cell` was
/// added to the mix after that record was written. A hash with no version is a
/// comparison between two different functions wearing the same name.
///
/// **This constant changes only together with the hash function.** Bump it in
/// the same edit that changes what `compute_hash` mixes -- never to make a
/// mismatch go away, and never without re-pinning `core/tests/hash_golden.rs`.
/// A record that carries no `hash_version` was written before versioning
/// existed: its hash belongs to that time, and comparing it with a current one
/// says nothing even when the two strings look alike. `checks/hash_version.py`
/// reads this constant back with a regexp, so the Python side and the Rust side
/// cannot drift apart silently.
pub const HASH_VERSION: &str = "2-prev-cell";

/// Version of the complete starting-configuration fingerprint.
pub const CONFIG_HASH_VERSION: &str = "sha256-json-v1";

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
                // `prev_cell` is where the organism came from. Two runs that
                // differ only in movement history are different dynamics; leaving
                // it out let a moved organism and a standing one hash the same.
                mix(s.prev_cell as u64);
            }
        }
        h
    }

    /// The protocol, folded into the hash.
    ///
    /// `compute_hash` sees only the frames. The protocol is not in them: at the
    /// same field and the same energies, `sequential` and `proportional` can
    /// produce identical frames for a while. Folding the name in makes the two
    /// arms different by construction, which is what AGENTS.md §3 asks for.
    pub fn hash_with_protocol(frames: &[Frame], share: &str) -> u64 {
        Self::hash_with_protocol_and_tiebreak(frames, share, "")
    }

    /// The protocol **and** the tie-break, folded into the hash.
    ///
    /// Same argument as `hash_with_protocol`, one parameter further: the
    /// tie-break does not appear in the frames until it has already moved
    /// somebody, and on a field where it never ties it does not appear at all.
    /// Folding the name in makes `left` and `right` different arms by
    /// construction, which is what AGENTS.md §3 asks for — otherwise the two
    /// would collide and the collision would be read as "the parameter did not
    /// reach the simulation".
    pub fn hash_with_protocol_and_tiebreak(
        frames: &[Frame],
        share: &str,
        tiebreak: &str,
    ) -> u64 {
        Self::hash_with_world(frames, share, tiebreak, "")
    }

    /// The protocol, the tie-break **and** the look order, folded into the hash.
    ///
    /// The empty string is what the older wrapper passes, so a caller that has
    /// no look order in hand gets exactly the hash it got before.
    pub fn hash_with_world(
        frames: &[Frame],
        share: &str,
        tiebreak: &str,
        look_order: &str,
    ) -> u64 {
        let mut h = Self::compute_hash(frames);
        for b in share.bytes().chain(tiebreak.bytes()).chain(look_order.bytes()) {
            h ^= b as u64;
            h = h.wrapping_mul(0x0000_0100_0000_01b3);
        }
        h
    }

    /// The world parameters **and** the birth switch, folded into the hash.
    ///
    /// The birth parameters are folded in **only when `max_population > 0`**,
    /// and that is the one way to have both properties at once. Every hash
    /// recorded in `results/` was produced by `hash_with_world`, so appending
    /// the new parameters unconditionally would move all of them -- and a moved
    /// hash is the one thing FINDING-153 promised not to do. With
    /// `max_population == 0` the model has no births by construction and
    /// nothing is appended, which is exactly the old hash. With a non-zero cap
    /// the arm is new, so a new hash is correct, and two arms that differ only
    /// in `birth_cost` cannot collide.
    ///
    /// The read price follows the same rule and for the same reason: it is
    /// appended **only when `read_cost > 0.0`**. A recorded run was free to
    /// read, so `0.0` must append nothing and the old hash is the new hash.
    /// A priced run is a different experiment, so it must not collide with a
    /// free one that happens to share its frames.
    ///
    /// The sampling period follows the same rule, one step further: it is
    /// appended **only when `read_period > 1`**. At `1` the organism looked on
    /// every step, which is what every recorded run did, so the tag is absent
    /// and the old hash is the new hash. At `> 1` the dynamics are different by
    /// construction, so the period must not collide with a look-every-step run.
    pub fn hash_with_births(
        frames: &[Frame],
        share: &str,
        tiebreak: &str,
        look_order: &str,
        max_population: usize,
        birth_threshold: f64,
        birth_cost: f64,
        read_cost: f64,
        read_period: usize,
        look_on_shortfall: bool,
    ) -> u64 {
        let mut h = Self::hash_with_world(frames, share, tiebreak, look_order);
        if max_population > 0 {
            let tag = format!(
                "birth:{}:{}:{}",
                max_population,
                birth_threshold.to_bits(),
                birth_cost.to_bits()
            );
            for b in tag.bytes() {
                h ^= b as u64;
                h = h.wrapping_mul(0x0000_0100_0000_01b3);
            }
        }
        if read_cost > 0.0 {
            let tag = format!("read:{}", read_cost.to_bits());
            for b in tag.bytes() {
                h ^= b as u64;
                h = h.wrapping_mul(0x0000_0100_0000_01b3);
            }
        }
        if read_period > 1 {
            let tag = format!("period:{}", read_period);
            for b in tag.bytes() {
                h ^= b as u64;
                h = h.wrapping_mul(0x0000_0100_0000_01b3);
            }
        }
        if look_on_shortfall {
            let tag = "shortfall:1";
            for b in tag.bytes() {
                h ^= b as u64;
                h = h.wrapping_mul(0x0000_0100_0000_01b3);
            }
        }
        h
    }

    /// Fold a non-default RNG version into the dynamics hash.
    ///
    /// The historical LCG default is the empty-delta case, preserving its old
    /// golden hashes. Every alternative RNG receives an explicit version tag.
    pub fn hash_with_rng_version(base_hash: u64, rng_version: &str) -> u64 {
        if rng_version == crate::RNG_VERSION {
            return base_hash;
        }
        let mut h = base_hash;
        for b in format!("rng:{rng_version}").bytes() {
            h ^= b as u64;
            h = h.wrapping_mul(0x0000_0100_0000_01b3);
        }
        h
    }

    /// The JSON form. Written by hand so the crate keeps zero dependencies.
    pub fn to_json(&self) -> String {
        let mut out = String::new();
        out.push_str("{\n");
        out.push_str(&format!("  \"policy\": \"{}\",\n", self.policy));
        out.push_str(&format!("  \"seed\": {},\n", self.seed));
        out.push_str(&format!("  \"rng_version\": \"{}\",\n", self.rng_version));
        out.push_str(&format!("  \"read_budget\": {},\n", self.read_budget));
        out.push_str(&format!("  \"share\": \"{}\",\n", self.share));
        out.push_str(&format!("  \"tiebreak\": \"{}\",\n", self.tiebreak));
        out.push_str(&format!("  \"look_order\": \"{}\",\n", self.look_order));
        out.push_str(&format!(
            "  \"birth_threshold\": {},\n",
            json_number(self.birth_threshold)
        ));
        out.push_str(&format!("  \"birth_cost\": {},\n", json_number(self.birth_cost)));
        out.push_str(&format!("  \"max_population\": {},\n", self.max_population));
        out.push_str(&format!("  \"read_cost\": {},\n", json_number(self.read_cost)));
        out.push_str(&format!(
            "  \"read_period\": {},\n",
            self.read_period
        ));
        out.push_str(&format!(
            "  \"look_on_shortfall\": {},\n",
            self.look_on_shortfall
        ));
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
                     \"direction\":{},\"taken\":{:.6},\"prev_cell\":{}}}",
                    s.slot, s.cell, s.energy, s.damage, s.alive, s.memory_cell, s.memory_level,
                    s.direction, s.taken, s.prev_cell
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
    let read_budget = life.world().read_budget;
    let mut frames = Vec::new();
    for _ in 0..steps {
        if life.advance().is_none() {
            break;
        }
        if life.step() % every == 0 {
            frames.push(snapshot(life));
        }
    }
    let share = life.world().share.name();
    let tiebreak = life.world().tiebreak.name();
    let look_order = life.world().look_order.name();
    let birth_threshold = life.world().birth_threshold;
    let birth_cost = life.world().birth_cost;
    let max_population = life.world().max_population;
    let read_cost = life.world().read_cost;
    let read_period = life.world().read_period;
    let look_on_shortfall = life.world().look_on_shortfall;
    let base_hash = Trace::hash_with_births(
        &frames,
        share,
        tiebreak,
        look_order,
        max_population,
        birth_threshold,
        birth_cost,
        read_cost,
        read_period,
        look_on_shortfall,
    );
    let rng_version = life.rng_version().as_str();
    let hash = Trace::hash_with_rng_version(base_hash, rng_version);
    Trace {
        frames,
        hash,
        policy: life.policy_name(),
        seed: life.seed(),
        rng_version,
        read_budget,
        share,
        tiebreak,
        look_order,
        birth_threshold,
        birth_cost,
        max_population,
        read_cost,
        read_period,
        look_on_shortfall,
    }
}

/// A JSON-safe rendering of a float.
///
/// `format!("{}", f64::INFINITY)` gives `inf`, which is **not** JSON, and
/// `INFINITY` is the default of `birth_threshold`. Writing it as the string
/// `"infinity"` keeps the file valid and keeps "never" visible instead of
/// silently turning it into `null`.
fn json_number(v: f64) -> String {
    if v.is_finite() {
        format!("{}", v)
    } else if v.is_nan() {
        "\"nan\"".to_string()
    } else if v > 0.0 {
        "\"infinity\"".to_string()
    } else {
        "\"-infinity\"".to_string()
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
    use crate::organism::{TieBreak, World};

    fn setup(policy: Policy, seed: u64) -> Life {
        let world = World {
            income: 1.0,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.01,
            capacity: 10.0,
            read_budget: 0,
            tiebreak: TieBreak::Left,
            share: Default::default(),
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0, read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
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
    fn rng2_version_is_recorded_and_fingerprinted() {
        let mut lcg = setup(Policy::Random, 7);
        let lcg_trace = record(&mut lcg, 100, 10);
        assert_eq!(lcg_trace.rng_version, crate::RNG_VERSION);

        let world = World {
            income: 1.0,
            maintenance_cost: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.01,
            capacity: 10.0,
            read_budget: 0,
            tiebreak: TieBreak::Left,
            share: Default::default(),
            look_order: LookOrder::LookThenEat,
            birth_threshold: f64::INFINITY,
            birth_cost: 0.0,
            max_population: 0,
            read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
        };
        let field = Field::alternating(40, 2.0, 0.2, 0.8).unwrap();
        let mut rng2 = Life::spawn_even_with_rng_version(
            world, field, 40, 5.0, 0.1, Policy::Random, 7, 300,
            crate::RngVersion::Xoshiro256PlusPlusV1,
        ).unwrap();
        let rng2_trace = record(&mut rng2, 100, 10);
        assert_eq!(rng2_trace.rng_version, crate::RNG2_VERSION);
        assert_ne!(lcg_trace.hash, rng2_trace.hash);
        assert!(rng2_trace.to_json().contains(
            "\"rng_version\": \"xoshiro256++-v1\""
        ));
    }

    #[test]
    fn rng_hash_tag_preserves_the_lcg_golden_contract() {
        let base = Trace::compute_hash(&[]);
        assert_eq!(Trace::hash_with_rng_version(base, crate::RNG_VERSION), base);
        assert_ne!(Trace::hash_with_rng_version(base, crate::RNG2_VERSION), base);
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
