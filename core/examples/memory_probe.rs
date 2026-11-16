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
    /// Memory plus the rule that the peak travels. `intact` remembers an address
    /// and walks to it; on a moving field that address is already wrong by the
    /// time the organism arrives (FINDING-163). This arm advances the remembered
    /// address by the field's own shift every step -- the smallest possible
    /// "model of the transition" -- and is the test of whether the deficit of
    /// 163 is memory or memory *without a rule*.
    Predict,
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
            Self::Predict => "predict",
            Self::Sham => "sham",
            Self::Erased => "erased",
            Self::Stay => "stay",
            Self::Random => "random",
        }
    }

    /// Arms that read the local window and therefore pay the same reads.
    fn looks(self) -> bool {
        matches!(self, Self::Sighted | Self::Intact | Self::Predict | Self::Sham)
    }
}

/// The field the probe runs on. `Uniform` is FINDING-155's world, where the
/// richest cell is always adjacent; `Peaks` is FINDING-156's, where it may be
/// outside the visible window.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum FieldKind {
    Uniform,
    Peaks,
    /// A single lit patch that moves `shift` cells per step. This is the only
    /// field in the probe where the past says something the present does not:
    /// a peak seen two steps ago is two cells away now, and where it *is* can be
    /// inferred from where it *was* only if the organism knows the rule.
    Moving,
    /// A lattice of `period`-spaced peaks that travels. The target is both out
    /// of the local window and changing position: the last cell of the table in
    /// FINDING-164, and the only one where memory could beat perception.
    PeaksMoving,
}

impl FieldKind {
    fn name(self) -> &'static str {
        match self {
            Self::Uniform => "uniform",
            Self::Peaks => "peaks",
            Self::Moving => "moving",
            Self::PeaksMoving => "peaks-moving",
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
    /// Cells per step the lit patch of a moving field travels.
    shift: f64,

    /// E4, the second channel (`docs/SYNTHESIS-readings.md` Part 6): how much
    /// mark the form writes into the cell it stands on each step. Zero by
    /// default, so every recorded number stays reproducible.
    mark_write: f64,

    /// How much of the mark survives each step. `1.0` never decays; `0.0`
    /// leaves the mark as it was written this step only.
    mark_decay: f64,

    /// How much the form's own mark lowers the upkeep in that cell:
    /// `upkeep_eff = maintenance * max(0, 1 - mark_income * mark)`. The region
    /// carries part of the cost of existing, which is how "the form earns from
    /// its region" is built without creating energy out of nothing.
    mark_income: f64,

    /// How many cells either side of itself the form maintains. `0` is the old
    /// behaviour: one stamp where it stands, which `FINDING-170` showed is a
    /// memory of a path and not a region. `1` or more makes a block, and a block
    /// is what can be lost.
    region_radius: usize,

    /// How far from the form the paid keep restores health. `0` is only the
    /// cell underfoot, so a region wider than one cell can be kept only by
    /// **returning** to each part of it -- which is the last step the synthesis
    /// needs: the form must leave and come back, not merely stand.
    keep_radius: usize,

    /// When on, the yield is scaled by the **mean** health of the region, not by
    /// the health of the cell underfoot. Then a neglected far cell costs income
    /// and the form has a reason to visit parts of its region it cannot see.
    region_yield: bool,

    /// The policy the medium now demands (`docs/FINDING-172.md`): when the cell
    /// underfoot cannot pay the upkeep, a step is allowed toward a neighbour
    /// **even if that neighbour is poorer**. With this off, a form on a failing
    /// cell stands there and dies, which is what 172 measured.
    leave_when_worn: bool,

    /// Region health lost per step underfoot: use wears the place. `0.0`
    /// leaves the old behaviour, so every recorded number stays reproducible.
    region_wear: f64,

    /// Region health restored per step while the form pays to keep it.
    region_keep: f64,

    /// What keeping costs per step. Standing still stops being free only when
    /// this is above zero together with the wear.
    region_keep_cost: f64,

    /// How much of the cell's yield is lost when its region health is zero.
    region_loss: f64,

    /// The pull acts only when the cell underfoot cannot pay the upkeep -- the
    /// consequence is the need itself, as Neill's saw in the rain, and
    /// `FINDING-170` showed that an unconditional pull turns standing into
    /// walking.
    region_needed_only: bool,

    /// How strongly the decision rule is pulled toward a higher mark. This is
    /// the **return path**: the form's own trace changes its own terms. The
    /// E4 control is to cut exactly this, leaving the mark and the field alone.
    mark_read_gain: f64,

    /// `true` is the ring the probe has always used; `false` is the line the
    /// core uses. Defaults to the ring so that every recorded number stays
    /// reproducible; `--boundary line` gives the same experiment on the geometry
    /// the core actually has.
    boundary_wraps: bool,
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
            shift: 1.0,
            boundary_wraps: true,
            mark_write: 0.0,
            mark_decay: 1.0,
            mark_income: 0.0,
            mark_read_gain: 0.0,
            region_radius: 1,
            region_needed_only: true,
            leave_when_worn: false,
            keep_radius: 0,
            region_yield: false,
            region_wear: 0.0,
            region_keep: 0.0,
            region_keep_cost: 0.0,
            region_loss: 0.0,
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

/// The same neighbour, on a line: `None` past an edge.
///
/// All three reviews of `docs/RESEARCH-BRIEF-5.md` made the same point: the
/// probe has been a ring while `Field` and `Life` are a line
/// (`core/src/field.rs:297-303`), and that is a difference of topology, not of
/// arithmetic. Substituting one for the other without a run is its own mistake.
fn side(cell: usize, delta: i64, cells: usize, wrap: bool) -> Option<usize> {
    if wrap {
        Some(ring(cell, delta, cells))
    } else {
        let t = cell as i64 + delta;
        if t < 0 || t >= cells as i64 {
            None
        } else {
            Some(t as usize)
        }
    }
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
                Some("predict") => Arm::Predict,
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
                    Some("moving") => FieldKind::Moving,
                    Some("peaks-moving") => FieldKind::PeaksMoving,
                    other => {
                        eprintln!("unknown field: {:?}", other);
                        std::process::exit(2);
                    }
                };
            }
            "--mark-write" => {
                i += 1;
                a.mark_write = number(&argv, i, "--mark-write");
            }
            "--mark-decay" => {
                i += 1;
                a.mark_decay = number(&argv, i, "--mark-decay");
            }
            "--mark-income" => {
                i += 1;
                a.mark_income = number(&argv, i, "--mark-income");
            }
            "--keep-radius" => {
                i += 1;
                let v: f64 = number(&argv, i, "--keep-radius");
                a.keep_radius = v.max(0.0) as usize;
            }
            "--region-yield" => {
                i += 1;
                a.region_yield = !matches!(argv.get(i).map(|s| s.as_str()), Some("off"));
            }
            "--leave-when-worn" => {
                i += 1;
                a.leave_when_worn = !matches!(argv.get(i).map(|s| s.as_str()), Some("off"));
            }
            "--region-wear" => {
                i += 1;
                a.region_wear = number(&argv, i, "--region-wear");
            }
            "--region-keep" => {
                i += 1;
                a.region_keep = number(&argv, i, "--region-keep");
            }
            "--region-keep-cost" => {
                i += 1;
                a.region_keep_cost = number(&argv, i, "--region-keep-cost");
            }
            "--region-loss" => {
                i += 1;
                a.region_loss = number(&argv, i, "--region-loss");
            }
            "--region-radius" => {
                i += 1;
                let radius: f64 = number(&argv, i, "--region-radius");
                a.region_radius = radius.max(0.0) as usize;
            }
            "--region-needed-only" => {
                i += 1;
                a.region_needed_only = !matches!(argv.get(i).map(|s| s.as_str()), Some("off"));
            }
            "--mark-read-gain" => {
                i += 1;
                a.mark_read_gain = number(&argv, i, "--mark-read-gain");
            }
            "--boundary" => {
                i += 1;
                a.boundary_wraps = match argv.get(i).map(|s| s.as_str()) {
                    Some("ring") => true,
                    Some("line") => false,
                    other => {
                        eprintln!("unknown boundary: {:?}", other);
                        std::process::exit(2);
                    }
                };
            }
            "--shift" => {
                i += 1;
                a.shift = number(&argv, i, "--shift");
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
                println!("       [--field uniform|peaks|moving|peaks-moving] [--shift S] [--boundary ring|line] [--mark-write X --mark-decay D --mark-income B --mark-read-gain G --region-radius R --region-needed-only on|off --region-wear W --region-keep K --region-keep-cost C --region-loss L --leave-when-worn on|off --keep-radius R --region-yield on|off] [--period P] [--poor V]");
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
        FieldKind::Moving => Field::moving(cells, a.m, a.poor, a.regrow, a.shift),
        FieldKind::PeaksMoving => {
            Field::peaks_moving(cells, a.m, a.poor, a.regrow, a.period, a.shift)
        }
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

    // E4's second channel. It is not the resource: it is never consumed, it
    // decays unless maintained, and it is read only by the form's own rule.
    let mut marks = vec![0.0f64; cells];

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
            Arm::Intact | Arm::Predict | Arm::Sham => step % a.read_period.max(1) == 0,
            _ => true,
        };
        let needy = matches!(a.arm, Arm::Intact | Arm::Predict | Arm::Sham)
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
            field.level(side(r.cell, -1, cells, a.boundary_wraps).unwrap_or(r.cell))
        } else {
            f64::NEG_INFINITY
        };
        let right_level = if a.arm.looks() && reads > 0 && sample && r.organism.spend(a.read_cost) {
            field.level(side(r.cell, 1, cells, a.boundary_wraps).unwrap_or(r.cell))
        } else {
            f64::NEG_INFINITY
        };

        // The return path, and it must be **structural**, not a gate (the
        // E2c lesson: a term multiplied by a factor that vanishes where the
        // form is, is blind). At `mark_read_gain == 0.0` the two sums below are
        // the levels themselves, bit for bit, so every recorded number stays
        // reproducible -- that identity is what the `silent` control then
        // proves empirically instead of assuming.
        // The region is a **windowed mass**, not the highest single stamp: a
        // fresh stamp behind the form must not outbid the block it maintains
        // (`docs/FINDING-170.md` is that failure). And the pull acts only when
        // the cell underfoot cannot pay the upkeep.
        let span = a.region_radius as i64;
        let window_mass = |c: usize| -> f64 {
            let mut acc = 0.0;
            for d in -span..=span {
                acc += marks[side(c, d, cells, a.boundary_wraps).unwrap_or(c)];
            }
            acc
        };
        let pull_on = a.mark_read_gain > 0.0
            && (!a.region_needed_only || here < need);
        let (left_level, right_level) = if pull_on {
            let lc = side(r.cell, -1, cells, a.boundary_wraps).unwrap_or(r.cell);
            let rc = side(r.cell, 1, cells, a.boundary_wraps).unwrap_or(r.cell);
            (
                left_level + a.mark_read_gain * window_mass(lc),
                right_level + a.mark_read_gain * window_mass(rc),
            )
        } else {
            (left_level, right_level)
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
                // The leave rule: a failing cell is a reason to go, even to a
                // poorer neighbour. With the flag off, `worn` is false and this
                // is the rule it always was, bit for bit.
                let yield_now = if a.region_loss > 0.0 {
                    1.0 - a.region_loss * (1.0 - marks[r.cell]).max(0.0)
                } else {
                    1.0
                };
                // "The place can no longer pay": the effective yield, not the raw
                // level. Using the level was wrong and made the rule silent.
                let worn = a.leave_when_worn && here * yield_now.max(0.0) < need;
                let best = here.max(left_level).max(right_level);
                if best > here || worn {
                    if left_level > right_level {
                        -1
                    } else if right_level > left_level {
                        1
                    } else if worn {
                        world.tiebreak.pick(&mut r.rng) as i32
                    } else {
                        0
                    }
                } else {
                    0
                }
            }
            Arm::Intact | Arm::Predict | Arm::Sham => {
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
                if a.arm == Arm::Predict && !sample && r.memory.best_level > 0.0 {
                    // The remembered place moves the way the field moves, and the
                    // address is only stale on the steps where nothing was looked
                    // at. Advancing it on a step that *did* look would aim one cell
                    // ahead of a peak that was just seen, which is how the first
                    // version of this arm managed to be worse than `intact`
                    // (`docs/FINDING-164.md`). Round rather than truncate: `shift`
                    // may be fractional, and a policy that cannot represent half a
                    // cell should still track a whole one.
                    let step = a.shift.round() as i64;
                    r.memory.best_cell = ring(r.memory.best_cell, step, cells);
                }
                if r.memory.best_level <= 0.0 {
                    if r.rng.uniform() < 0.5 {
                        -1
                    } else {
                        1
                    }
                } else {
                    let d = r.direction();
                    let yield_now = if a.region_loss > 0.0 {
                        1.0 - a.region_loss * (1.0 - marks[r.cell]).max(0.0)
                    } else {
                        1.0
                    };
                    if d == 0 && a.leave_when_worn && here * yield_now.max(0.0) < need {
                        world.tiebreak.pick(&mut r.rng) as i32
                    } else {
                        d
                    }
                }
            }
        };

        // --- 3. Move. A blocked step at the edge cannot happen on a ring; the
        //        cost is paid only when the move happens, as in `Field::Walker`.
        if dir != 0 && r.organism.spend(a.move_cost) {
            r.cell = side(r.cell, dir as i64, cells, a.boundary_wraps).unwrap_or(r.cell);
            moves += 1;
            if !visited[r.cell] {
                visited[r.cell] = true;
                visited_list.push(r.cell);
            }
        }

        // --- 3a. E4: the form marks where it is, and the mark ages. It is not
        //         a resource: `field.take` never touches it.
        if a.mark_write > 0.0 {
            let span = a.region_radius as i64;
            for d in -span..=span {
                let c = side(r.cell, d, cells, a.boundary_wraps).unwrap_or(r.cell);
                marks[c] = (marks[c] + a.mark_write).min(1.0);
            }
        }
        if a.mark_decay < 1.0 {
            for m in marks.iter_mut() {
                *m *= a.mark_decay;
            }
        }

        // --- 3b. The region wears where the form stands, and is kept only by
        //         paying. This is the force `FINDING-169` and `FINDING-171`
        //         found missing: standing still stops being free.
        if a.region_wear > 0.0 {
            marks[r.cell] = (marks[r.cell] - a.region_wear).max(0.0);
        }
        let mut kept = false;
        if a.region_keep > 0.0 && a.region_keep_cost > 0.0 && r.organism.spend(a.region_keep_cost) {
            let span = a.keep_radius as i64;
            for d in -span..=span {
                let c = side(r.cell, d, cells, a.boundary_wraps).unwrap_or(r.cell);
                marks[c] = (marks[c] + a.region_keep).min(1.0);
            }
            kept = true;
        }
        let _ = kept;

        // --- 4. Eat and live. The order is `Remembering::step`'s and `Life`'s:
        //        move, take, live, regrow.
        let at = field.level(r.cell);
        // A worn region yields less: at zero health the cell gives
        // `1 - region_loss` of what it holds. This is what makes movement
        // forced rather than merely possible.
        let health = if a.region_yield && a.region_radius > 0 {
            // The region feeds the form: the mean over the whole owned block, so
            // a neglected part of it costs income even when the form is not there.
            let span = a.region_radius as i64;
            let mut acc = 0.0;
            for d in -span..=span {
                let c = side(r.cell, d, cells, a.boundary_wraps).unwrap_or(r.cell);
                acc += marks[c];
            }
            acc / (2 * span + 1) as f64
        } else {
            marks[r.cell]
        };
        let yield_factor = if a.region_loss > 0.0 {
            1.0 - a.region_loss * (1.0 - health).max(0.0)
        } else {
            1.0
        };
        let taken = field.take(r.cell, a.income * yield_factor.max(0.0));
        let upkeep = if a.mark_income > 0.0 {
            (world.maintenance_cost * (1.0 - a.mark_income * marks[r.cell]).max(0.0))
        } else {
            world.maintenance_cost
        };
        let mut owned = world;
        owned.maintenance_cost = upkeep;
        let alive = r.organism.step_with(&owned, taken, RepairPolicy::AllOrNothing);
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
