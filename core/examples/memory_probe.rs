//! Read-only probe for `checks/exp_memory_question.py` (FINDING-155).
//!
//! ## The question
//!
//! Two external reviews agreed on one pre-check: in a fully observed environment
//! memory cannot evolve at any non-zero price, so the first thing to show is that
//! a **memoryless** agent is materially worse than the best agent. If the
//! memoryless agent already gets ~90 % of the best, the memory line is closed.
//!
//! The optimum is not attainable (the state is a vector of continuous levels), so
//! the probe measures an **upper bound**: `oracle` walks to the globally richest
//! cell every step. It knows more than any memory can know (a memory knows only
//! what it has seen), so it bounds every agent that stores anything from above.
//!
//! ## The world
//!
//! One organism on a **ring** of `cells` cells, every cell with the same ceiling
//! `M` and the same regrowth `r`, so the only thing that differs between cells is
//! how long ago the organism grazed them. This is the minimal world in which the
//! period `P` of the formula is literally the length of the organism's cycle:
//!
//! ```text
//! c' = (c - t) + (M - (c - t)) * r        the cell law, core/src/field.rs
//! t_max(P) = M * (1 - (1 - r)^P)          the most a cell gives back in P steps
//! P_need   = ceil( ln(M/(M-m)) / (-ln(1-r)) ),  m = maintenance + dr*rc
//! ```
//!
//! An organism that eats every step and returns to a cell every `P` steps can
//! take `t_max(P)` from it, so it lives iff `t_max(P) >= m`. `income = m` on the
//! experiment grid, so the take is exactly the need and the only question is
//! whether the cell had that much.
//!
//! The ring is the probe's, not the library's: `Field` supports any index and
//! `Life` never wraps, so the movement rule here wraps and the difference is
//! recorded rather than hidden. Without a ring no 1-D walk can have a return
//! period above 2 without passing the same cell twice per excursion, and
//! `P_need` in `{3, 5}` would be unreachable by construction.
//!
//! ## The arms
//!
//! | arm | what it does | what it is for |
//! |---|---|---|
//! | `oracle` | reads the whole field, walks toward the globally richest cell | upper bound |
//! | `sighted` | local window (own cell + both neighbours), walks to the strictly richer, tie -> stay | best memoryless |
//! | `intact` | one `Memory` slot updated by the `Life::Memory` rule, same window | the asset under test |
//! | `sham` | the same level is stored, the address is redrawn from the visited cells | the association, not the volume |
//! | `erased` | memory is always empty: it wanders | what is left with no state |
//! | `stay` | never moves | lower base |
//! | `random` | -1 / 0 / +1 with equal probability | lower base |
//!
//! ## What is held equal on purpose (`specific` control)
//!
//! `intact` and `sham` are the **same struct** (`Remembering`), so the state size
//! is identical by construction; they share `move_cost`, `read_budget`,
//! `memory_life` and the local window, and they run on the same seed, so the
//! random stream is the same. The only difference is one line: `sham` replaces
//! the address that the level is attached to. `--sham-mode` selects the address
//! pool: `visited` (uniform over the cells the organism has stood on, the review's
//! `sham-address`) or `neighbour` (uniform over the two neighbours, which keeps
//! the address distance at 1 instead of biasing it backwards).
//!
//! ## What the probe does not do
//!
//! It does not touch `core/src`. It links the library, drives `Remembering`
//! itself and prints one JSON object. Nothing here is a claim about `Life`: the
//! `Life::Memory` update rule is re-stated here so the probe can intervene
//! between the update and the decision, and that re-statement is what
//! `checks/exp_memory_question.py` compares `intact` against.
//!
//! ```bash
//! cargo build --release --example memory_probe
//! ./target/release/examples/memory_probe --arm sighted --steps 100 \
//!     --cells 24 --m 2.0 --regrow 0.8 --income 1.9 --maintenance 1.87 \
//!     --repair-cost 1.5 --damage-rate 0.02 --energy 5.0
//! ```

use medium_core::field::Field;
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, RepairPolicy, TieBreak, World};
use medium_core::Rng;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Arm {
    Oracle,
    Sighted,
    Intact,
    Sham,
    Erased,
    Stay,
    Random,
}

impl Arm {
    fn name(self) -> &'static str {
        match self {
            Self::Oracle => "oracle",
            Self::Sighted => "sighted",
            Self::Intact => "intact",
            Self::Sham => "sham",
            Self::Erased => "erased",
            Self::Stay => "stay",
            Self::Random => "random",
        }
    }

    /// Arms that read the local window and therefore pay the same reads.
    fn looks(self) -> bool {
        matches!(self, Self::Sighted | Self::Intact | Self::Sham)
    }
}

/// The field the probe runs on. `Uniform` is FINDING-155's world, where the
/// richest cell is always adjacent; `Peaks` is FINDING-156's, where it may be
/// outside the visible window.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum FieldKind {
    Uniform,
    Peaks,
}

impl FieldKind {
    fn name(self) -> &'static str {
        match self {
            Self::Uniform => "uniform",
            Self::Peaks => "peaks",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ShamMode {
    Visited,
    Neighbour,
}

struct Args {
    arm: Arm,
    sham_mode: ShamMode,
    cells: usize,
    m: f64,
    regrow: f64,
    income: f64,
    maintenance: f64,
    repair_cost: f64,
    damage_rate: f64,
    move_cost: f64,
    energy: f64,
    capacity: f64,
    read_budget: usize,
    /// Energy paid for one **neighbour** read. The own cell is free.
    read_cost: f64,
    /// Steps between two samples for the remembering arms (`intact`, `sham`).
    /// `1` is every step and reproduces the arms recorded before the period
    /// existed; `sighted` is never gated, because it has no memory to act on.
    read_period: usize,
    /// Whether a remembering arm may look out of turn when the cell
    /// underfoot cannot pay the upkeep. The rule declared in
    /// `docs/FINDING-161.md`; off reproduces every earlier run.
    look_on_shortfall: bool,
    field: FieldKind,
    /// One rich cell every `period` cells, for `FieldKind::Peaks`.
    period: usize,
    /// The poor ceiling of a peaked field.
    poor: f64,
    memory_life: usize,
    steps: usize,
    seed: u64,
    start_cell: usize,
    threshold: Option<f64>,
    tiebreak: TieBreak,
}

impl Default for Args {
    fn default() -> Self {
        Self {
            arm: Arm::Sighted,
            sham_mode: ShamMode::Visited,
            cells: 24,
            m: 2.0,
            regrow: 0.8,
            income: 1.0,
            maintenance: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.02,
            move_cost: 0.0,
            energy: 5.0,
            capacity: 10.0,
            read_budget: 3,
            read_cost: 0.0,
            read_period: 1,
            look_on_shortfall: false,
            field: FieldKind::Uniform,
            period: 6,
            poor: 0.2,
            memory_life: 1_000_000,
            steps: 2000,
            seed: 1,
            start_cell: 0,
            threshold: None,
            tiebreak: TieBreak::Left,
        }
    }
}

/// Parses the value that follows `--flag`, refusing to fall back to a default.
/// Same rule as `src/bin/trace.rs`: a flag that was given and cannot be parsed
/// is an error, not a silent default.
fn number<T: std::str::FromStr>(args: &[String], i: usize, flag: &str) -> T {
    match args.get(i) {
        None => {
            eprintln!("refusing to run: {} needs a value", flag);
            std::process::exit(2);
        }
        Some(raw) => match raw.parse::<T>() {
            Ok(v) => v,
            Err(_) => {
                eprintln!("refusing to run: {} {:?} is not a number", flag, raw);
                std::process::exit(2);
            }
        },
    }
}

/// `--start-cell` outside the field is refused, not wrapped: a silently moved
/// start is a different run under the same name.
fn cell_in_field(cell: i64, cells: usize) -> usize {
    if cell < 0 || cell as usize >= cells {
        eprintln!("refusing to run: start cell {} is outside the field", cell);
        std::process::exit(2);
    }
    cell as usize
}

/// The neighbour `k` steps away on a ring, in either direction.
fn ring(cell: usize, delta: i64, cells: usize) -> usize {
    let n = cells as i64;
    (((cell as i64 + delta) % n) + n) as usize % cells
}

/// `P_need` from the review's formula, or `None` where it is undefined
/// (`m >= M` has no finite period, `m <= 0` needs no period).
fn p_need(m_field: f64, regrow: f64, need: f64) -> Option<usize> {
    if need <= 0.0 || need >= m_field || regrow <= 0.0 || regrow >= 1.0 {
        return None;
    }
    let raw = (m_field / (m_field - need)).ln() / -(1.0 - regrow).ln();
    Some(raw.ceil() as usize)
}

fn main() {
    let argv: Vec<String> = std::env::args().collect();
    let mut a = Args::default();
    let mut i = 1;
    while i < argv.len() {
        match argv[i].as_str() {
            "--arm" => {
                i += 1;
                a.arm = match argv.get(i).map(|s| s.as_str()) {
                    Some("oracle") => Arm::Oracle,
                    Some("sighted") => Arm::Sighted,
                    Some("intact") => Arm::Intact,
                    Some("sham") => Arm::Sham,
                    Some("erased") => Arm::Erased,
                    Some("stay") => Arm::Stay,
                    Some("random") => Arm::Random,
                    other => {
                        eprintln!("unknown arm: {:?}", other);
                        std::process::exit(2);
                    }
                };
            }
            "--sham-mode" => {
                i += 1;
                a.sham_mode = match argv.get(i).map(|s| s.as_str()) {
                    Some("visited") => ShamMode::Visited,
                    Some("neighbour") | Some("neighbor") => ShamMode::Neighbour,
                    other => {
                        eprintln!("unknown sham mode: {:?}", other);
                        std::process::exit(2);
                    }
                };
            }
            "--tiebreak" => {
                i += 1;
                a.tiebreak = match argv.get(i).map(|s| s.as_str()) {
                    Some("left") => TieBreak::Left,
                    Some("right") => TieBreak::Right,
                    Some("random") => TieBreak::Random,
                    other => {
                        eprintln!("unknown tiebreak: {:?}", other);
                        std::process::exit(2);
                    }
                };
            }
            "--cells" => {
                i += 1;
                a.cells = number(&argv, i, "--cells");
            }
            "--m" => {
                i += 1;
                a.m = number(&argv, i, "--m");
            }
            "--regrow" => {
                i += 1;
                a.regrow = number(&argv, i, "--regrow");
            }
            "--income" => {
                i += 1;
                a.income = number(&argv, i, "--income");
            }
            "--maintenance" => {
                i += 1;
                a.maintenance = number(&argv, i, "--maintenance");
            }
            "--repair-cost" => {
                i += 1;
                a.repair_cost = number(&argv, i, "--repair-cost");
            }
            "--damage-rate" => {
                i += 1;
                a.damage_rate = number(&argv, i, "--damage-rate");
            }
            "--move-cost" => {
                i += 1;
                a.move_cost = number(&argv, i, "--move-cost");
            }
            "--energy" => {
                i += 1;
                a.energy = number(&argv, i, "--energy");
            }
            "--capacity" => {
                i += 1;
                a.capacity = number(&argv, i, "--capacity");
            }
            "--read-budget" => {
                i += 1;
                a.read_budget = number(&argv, i, "--read-budget");
            }
            "--read-cost" => {
                i += 1;
                a.read_cost = number(&argv, i, "--read-cost");
            }
            "--read-period" => {
                i += 1;
                a.read_period = number(&argv, i, "--read-period");
            }
            "--look-on-shortfall" => {
                a.look_on_shortfall = true;
            }
            "--field" => {
                i += 1;
                a.field = match argv.get(i).map(|s| s.as_str()) {
                    Some("uniform") => FieldKind::Uniform,
                    Some("peaks") => FieldKind::Peaks,
                    other => {
                        eprintln!("unknown field: {:?}", other);
                        std::process::exit(2);
                    }
                };
            }
            "--period" => {
                i += 1;
                a.period = number(&argv, i, "--period");
            }
            "--poor" => {
                i += 1;
                a.poor = number(&argv, i, "--poor");
            }
            "--memory-life" => {
                i += 1;
                a.memory_life = number(&argv, i, "--memory-life");
            }
            "--steps" => {
                i += 1;
                a.steps = number(&argv, i, "--steps");
            }
            "--seed" => {
                i += 1;
                a.seed = number(&argv, i, "--seed");
            }
            "--start-cell" => {
                i += 1;
                a.start_cell = number(&argv, i, "--start-cell");
            }
            "--threshold" => {
                i += 1;
                a.threshold = Some(number(&argv, i, "--threshold"));
            }
            "--help" | "-h" => {
                println!("usage: memory_probe --arm A [--cells N] [--m M] [--regrow R]");
                println!("       [--income I] [--maintenance T] [--repair-cost RC]");
                println!("       [--damage-rate DR] [--move-cost MC] [--energy E0]");
                println!("       [--capacity CAP] [--read-budget B] [--read-cost X]");
                println!("       [--read-period N]  remembering arms look every N steps");
        println!("       [--look-on-shortfall]  remembering arms look out of turn when the cell is too poor");
                println!("       [--field uniform|peaks] [--period P] [--poor V]");
                println!("       [--memory-life L]");
                println!("       [--steps S] [--seed Z] [--start-cell K] [--threshold X]");
                println!("       [--sham-mode visited|neighbour] [--tiebreak left|right|random]");
                return;
            }
            other => {
                eprintln!("unknown argument: {}", other);
                std::process::exit(2);
            }
        }
        i += 1;
    }

    let cells = a.cells;
    let start = cell_in_field(a.start_cell as i64, cells);
    let world = World {
        income: a.income,
        maintenance_cost: a.maintenance,
        repair_cost: a.repair_cost,
        damage_rate: a.damage_rate,
        capacity: a.capacity,
        read_budget: a.read_budget,
        read_cost: a.read_cost,
        read_period: a.read_period,
        look_on_shortfall: a.look_on_shortfall,
        tiebreak: a.tiebreak,
        ..World::default()
    };
    if world.validate().is_err() {
        eprintln!("refusing to run: the world does not validate");
        std::process::exit(2);
    }
    // `rich` is the field's ceiling `m`, the same `M` as FINDING-155, so the
    // two experiments share a `P_need`; `poor` is a per-cell ceiling far below
    // it. With `period >= 4` the next rich cell is outside the local window.
    let field = match a.field {
        FieldKind::Uniform => Field::new(cells, a.m, a.regrow),
        FieldKind::Peaks => Field::peaks(cells, a.m, a.poor, a.regrow, a.period),
    };
    let field = match field {
        Some(f) => f,
        None => {
            eprintln!("refusing to run: cannot build the field");
            std::process::exit(2);
        }
    };
    let organism = match Organism::healthy(a.energy) {
        Some(o) => o,
        None => {
            eprintln!("refusing to run: cannot build the organism");
            std::process::exit(2);
        }
    };
    let mut r = match Remembering::new(
        organism,
        start,
        field.level(start),
        a.move_cost,
        a.memory_life,
    ) {
        Some(r) => r,
        None => {
            eprintln!("refusing to run: cannot build the organism");
            std::process::exit(2);
        }
    };
    // One stream per run, seeded by the caller, so two arms with the same seed
    // face the same coin: `Remembering::new` seeds from the starting cell, which
    // would make the comparison depend on the start.
    r.rng = Rng::new(a.seed ^ 0x9E37_79B9_7F4A_7C15);

    // The cells the organism has stood on: the address pool of `sham`.
    let mut visited = vec![false; cells];
    visited[start] = true;
    let mut visited_list: Vec<usize> = vec![start];

    let mut field = field;
    let need = a.maintenance + a.damage_rate * a.repair_cost;
    let threshold = a.threshold.unwrap_or(need);

    // FNV-1a over everything that moved, per step: the same mixing the library
    // uses in `Trace::compute_hash`, applied to the whole run rather than to
    // sampled frames.
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    let mut mix = |h: &mut u64, x: u64| {
        *h ^= x;
        *h = h.wrapping_mul(0x0000_0100_0000_01b3);
    };

    let mut lifetime = a.steps;
    let mut cause = "alive";
    let mut energy_acc = 0.0f64;
    let mut energy_end = a.energy;
    let mut damage_end = 0.0f64;
    let mut taken_sum = 0.0f64;
    let mut rich_steps = 0usize;
    let mut alive_steps = 0usize;
    let mut moves = 0u64;
    let mut shortfall_looks = 0u64;
    let mut field_mean = 0.0f64;
    let mut field_min = a.m;
    let mut field_max = a.m;

    for step in 0..a.steps {
        // --- 1. Reads. The budget is a cap, not a price: the whole probe has one
        //        price list (`move_cost`) and every arm pays it. The own cell
        //        costs one read, exactly as in `Life::advance_with`, so a budget
        //        of 3 is the local window (own + two neighbours).
        //
        //        A remembering arm looks only every `read_period`-th step; on
        //        the other steps it reads nothing, pays nothing and acts on the
        //        memory. `sighted` is never gated: it has no memory to fall back
        //        on, so a skipped look would be blindness, not economy.
        // The exit rule declared in `docs/FINDING-161.md`: a remembering arm
        // looks out of turn when the cell underfoot cannot pay the upkeep.
        // The own cell is `field.level` here -- free, outside the budget --
        // so this only moves a look earlier. `sighted` is untouched: it has
        // no memory to fall back on, and a skipped look would blind it.
        let due = match a.arm {
            Arm::Intact | Arm::Sham => step % a.read_period.max(1) == 0,
            _ => true,
        };
        let needy = matches!(a.arm, Arm::Intact | Arm::Sham)
            && a.look_on_shortfall
            && field.level(r.cell) < need;
        let sample = due || needy;
        if needy && !due {
            shortfall_looks += 1;
        }
        let mut reads = a.read_budget;
        let here = if a.arm.looks() && reads > 0 && sample {
            reads -= 1;
            field.level(r.cell)
        } else {
            0.0
        };
        // A neighbour costs one look from the budget AND `read_cost` energy.
        // The own cell is free in energy (the organism already eats there) but
        // still costs one look -- the probe's budget rule, unchanged since
        // FINDING-155, so a budget of 3 is the local window.
        //
        // A look that cannot be paid for is **not taken**: the organism goes
        // short-sighted instead of into debt, which is the rule
        // `Life::advance_with` states. At `read_cost == 0.0` `spend` subtracts
        // zero and cannot fail, so nothing moves.
        let left_level = if a.arm.looks() && reads > 0 && sample && r.organism.spend(a.read_cost) {
            reads -= 1;
            field.level(ring(r.cell, -1, cells))
        } else {
            f64::NEG_INFINITY
        };
        let right_level = if a.arm.looks() && reads > 0 && sample && r.organism.spend(a.read_cost) {
            field.level(ring(r.cell, 1, cells))
        } else {
            f64::NEG_INFINITY
        };

        // --- 2. Decide.
        let dir: i32 = match a.arm {
            Arm::Stay => 0,
            Arm::Random => {
                let u = r.rng.uniform();
                if u < 1.0 / 3.0 {
                    -1
                } else if u < 2.0 / 3.0 {
                    0
                } else {
                    1
                }
            }
            Arm::Erased => {
                // Nothing is stored, so the only thing left is exploration: the
                // state a `decay`d memory leaves behind.
                if r.rng.uniform() < 0.5 {
                    -1
                } else {
                    1
                }
            }
            Arm::Oracle => {
                // Omniscience is bought, not assumed: looking at the whole
                // field costs one `read_cost` per cell it examines (the own
                // cell is free). If that is unaffordable the organism does not
                // get a partial oracle -- it knows only the cell it stands on
                // and stays, which is what "cannot afford to look" means. At
                // `read_cost == 0.0` the charge is zero and this branch is the
                // arm FINDING-155 recorded, bit for bit.
                let scan = a.read_cost * (cells.saturating_sub(1)) as f64;
                if !r.organism.spend(scan) {
                    0
                } else {
                // The whole field: more than any memory can know.
                let here_now = field.level(r.cell);
                let mut best = here_now;
                for c in 0..cells {
                    let v = field.level(c);
                    if v > best {
                        best = v;
                    }
                }
                if best <= here_now {
                    0
                } else {
                    // The nearest cell that holds the maximum; a tie in distance
                    // is the world's tie-break, not a hidden rule.
                    let mut left_d = usize::MAX;
                    let mut right_d = usize::MAX;
                    for d in 1..=cells / 2 {
                        if left_d == usize::MAX
                            && field.level(ring(r.cell, -(d as i64), cells)) == best
                        {
                            left_d = d;
                        }
                        if right_d == usize::MAX
                            && field.level(ring(r.cell, d as i64, cells)) == best
                        {
                            right_d = d;
                        }
                        if left_d != usize::MAX && right_d != usize::MAX {
                            break;
                        }
                        if left_d != usize::MAX || right_d != usize::MAX {
                            break;
                        }
                    }
                    if left_d < right_d {
                        -1
                    } else if right_d < left_d {
                        1
                    } else {
                        world.tiebreak.pick(&mut r.rng) as i32
                    }
                }
                }
            }
            Arm::Sighted => {
                let best = here.max(left_level).max(right_level);
                if best > here {
                    if left_level > right_level {
                        -1
                    } else if right_level > left_level {
                        1
                    } else {
                        world.tiebreak.pick(&mut r.rng) as i32
                    }
                } else {
                    0
                }
            }
            Arm::Intact | Arm::Sham => {
                // The `Life::Memory` rule, re-stated step for step so the probe
                // can intervene between the update and the decision. `intact`
                // stops here; `sham` replaces the address below.
                if sample {
                    if r.memory.best_cell == r.cell {
                        r.memory.best_level = here;
                        r.memory.age = 0;
                    } else {
                        r.memory.observe(r.cell, here);
                    }
                    r.memory.decay(r.memory_life);
                    if r.memory.best_cell != r.cell && r.memory.best_level <= here {
                        r.memory.best_cell = r.cell;
                        r.memory.best_level = here;
                        r.memory.age = 0;
                    }
                    let best = here.max(left_level).max(right_level);
                    let step_dir = if left_level > right_level {
                        -1
                    } else if right_level > left_level {
                        1
                    } else {
                        world.tiebreak.pick(&mut r.rng) as i32
                    };
                    let target = ring(r.cell, step_dir as i64, cells);
                    let take = best > here || (best == here && best > r.memory.best_level);
                    if take && best > r.memory.best_level {
                        r.memory.best_cell = target;
                        r.memory.best_level = best;
                        r.memory.age = 0;
                    }
                    if a.arm == Arm::Sham && !r.memory.is_empty() {
                        // The intervention: the level, the age and the number of
                        // records stay exactly where they are. Only the address is
                        // redrawn, so the association "this level belongs to that
                        // place" is destroyed while the volume of memory is not.
                        let pool: &[usize] = match a.sham_mode {
                            ShamMode::Visited => &visited_list,
                            ShamMode::Neighbour => {
                                // The two neighbours are the addresses `intact` uses
                                // in the overwhelming majority of steps; drawing from
                                // them keeps the address distance at 1 and removes
                                // only the association.
                                &[]
                            }
                        };
                        let cell = if pool.is_empty() {
                            let u = r.rng.uniform();
                            if u < 0.5 {
                                ring(r.cell, -1, cells)
                            } else {
                                ring(r.cell, 1, cells)
                            }
                        } else {
                            let k = (r.rng.uniform() * pool.len() as f64) as usize;
                            pool[k.min(pool.len() - 1)]
                        };
                        r.memory.best_cell = cell;
                    }
                }
                if r.memory.best_level <= 0.0 {
                    if r.rng.uniform() < 0.5 {
                        -1
                    } else {
                        1
                    }
                } else {
                    r.direction()
                }
            }
        };

        // --- 3. Move. A blocked step at the edge cannot happen on a ring; the
        //        cost is paid only when the move happens, as in `Field::Walker`.
        if dir != 0 && r.organism.spend(a.move_cost) {
            r.cell = ring(r.cell, dir as i64, cells);
            moves += 1;
            if !visited[r.cell] {
                visited[r.cell] = true;
                visited_list.push(r.cell);
            }
        }

        // --- 4. Eat and live. The order is `Remembering::step`'s and `Life`'s:
        //        move, take, live, regrow.
        let at = field.level(r.cell);
        let taken = field.take(r.cell, a.income);
        let alive = r.organism.step_with(&world, taken, RepairPolicy::AllOrNothing);
        field.regrow_all();

        mix(&mut h, step as u64);
        mix(&mut h, r.cell as u64);
        mix(&mut h, dir as i64 as u64);
        mix(&mut h, r.organism.energy().to_bits());
        mix(&mut h, r.organism.damage().to_bits());
        mix(&mut h, alive as u64);
        mix(&mut h, taken.to_bits());

        if alive {
            alive_steps += 1;
            energy_acc += r.organism.energy();
            taken_sum += taken;
            if at >= threshold {
                rich_steps += 1;
            }
        } else {
            lifetime = step + 1;
            cause = if r.organism.damage() >= 1.0 {
                "damage"
            } else {
                "energy"
            };
            energy_end = r.organism.energy();
            damage_end = r.organism.damage();
            break;
        }
        energy_end = r.organism.energy();
        damage_end = r.organism.damage();

        // The field after the last regrow: the state the run leaves behind.
        let n = cells as f64;
        field_mean = (0..cells).map(|c| field.level(c)).sum::<f64>() / n;
        field_min = (0..cells)
            .map(|c| field.level(c))
            .fold(f64::INFINITY, f64::min);
        field_max = (0..cells)
            .map(|c| field.level(c))
            .fold(f64::NEG_INFINITY, f64::max);
    }

    if alive_steps == 0 {
        // A run that never lived: no mean, no division by zero.
        field_mean = (0..cells).map(|c| field.level(c)).sum::<f64>() / cells as f64;
        field_min = (0..cells)
            .map(|c| field.level(c))
            .fold(f64::INFINITY, f64::min);
        field_max = (0..cells)
            .map(|c| field.level(c))
            .fold(f64::NEG_INFINITY, f64::max);
    }

    let frac_rich = if alive_steps > 0 {
        rich_steps as f64 / alive_steps as f64
    } else {
        0.0
    };
    let taken_mean = if alive_steps > 0 {
        taken_sum / alive_steps as f64
    } else {
        0.0
    };
    let pn = p_need(a.m, a.regrow, need);
    let pn_text = match pn {
        Some(p) => format!("{}", p),
        None => "null".to_string(),
    };

    println!(
        "{{\"arm\":\"{}\",\"sham_mode\":\"{}\",\"p_need\":{},\"m_need\":{:.12},\
         \"threshold\":{:.12},\"steps_requested\":{},\"lifetime\":{},\"alive\":{},\
         \"cause\":\"{}\",\"alive_steps\":{},\"energy_acc\":{:.12},\"energy_end\":{:.12},\
         \"damage_end\":{:.12},\"taken_mean\":{:.12},\"frac_rich\":{:.12},\
         \"moves\":{},\"field_mean\":{:.12},\"field_min\":{:.12},\"field_max\":{:.12},\
         \"cells\":{},\"read_budget\":{},\"move_cost\":{:.12},\"memory_life\":{},\
         \"read_cost\":{:.12},\"read_period\":{},\"look_on_shortfall\":{},\"shortfall_looks\":{},\"field\":\"{}\",\"period\":{},\"poor\":{:.12},\
         \"hash\":\"{:016x}\"}}",
        a.arm.name(),
        match a.sham_mode {
            ShamMode::Visited => "visited",
            ShamMode::Neighbour => "neighbour",
        },
        pn_text,
        need,
        threshold,
        a.steps,
        lifetime,
        lifetime == a.steps && cause == "alive",
        cause,
        alive_steps,
        energy_acc,
        energy_end,
        damage_end,
        taken_mean,
        frac_rich,
        moves,
        field_mean,
        field_min,
        field_max,
        cells,
        a.read_budget,
        a.move_cost,
        a.memory_life,
        a.read_cost,
        a.read_period,
        a.look_on_shortfall,
        shortfall_looks,
        a.field.name(),
        a.period,
        a.poor,
        h
    );
}
