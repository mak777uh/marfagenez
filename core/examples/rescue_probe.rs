//! Read-only probe for `checks/exp_rescue.py` (EXP-152).
//!
//! `share_probe` answers "who survives a crowd and with what edge". This
//! experiment asks a different question: after one organism of a crowd dies,
//! **how much more does a survivor eat**, and does that be enough to keep it
//! alive. That number is a share, so the probe has to report the share as a
//! function of time, and it has to be able to give one organism a smaller
//! reserve than the others (the "one weak" configuration).
//!
//! `share_probe` cannot do either: it takes one `--energy` for the whole
//! population and reports only the mean last/first meal. This probe builds the
//! same `World`, `Field` and `Life` the binary builds, advances one step at a
//! time, and prints one JSON object:
//!
//! * per organism -- lifetime, cause of death, energy, damage, and
//!   `segments`: the runs of steps over which its meal did not change, as
//!   `[[from, to, taken], ...]`. Under `Proportional` the meal is
//!   `income / (live crowd on the cell)`, so a death shows up as a new
//!   segment and its size is the number the experiment reports;
//! * the FNV hash of the per-step record of *all* organisms.
//!
//! It links against the existing library and changes nothing under `core/src`.
//!
//! ```bash
//! cargo build --release --example rescue_probe
//! ./target/release/examples/rescue_probe --cells 1 --n 2 --m 2 --regrow 0.8 \
//!     --income 1.0 --maintenance 0.2 --repair-cost 10 --damage-rate 0.03 \
//!     --capacity 10 --share proportional --steps 10000 --energy 5 \
//!     --energy-weak 0.5 --weak-rank 0
//! ```

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, RepairPolicy, ShareProtocol, World};

struct Args {
    policy: Policy,
    repair: RepairPolicy,
    cells: usize,
    n: usize,
    steps: usize,
    seed: u64,
    m: f64,
    regrow: f64,
    income: f64,
    maintenance: f64,
    repair_cost: f64,
    damage_rate: f64,
    move_cost: f64,
    energy: f64,
    /// `Some(e)` gives organism `weak_rank` the reserve `e`; the rest keep
    /// `energy`. `None` is the equal configuration.
    energy_weak: Option<f64>,
    weak_rank: usize,
    capacity: f64,
    read_budget: usize,
    share: ShareProtocol,
}

impl Default for Args {
    fn default() -> Self {
        Self {
            policy: Policy::Stay,
            repair: RepairPolicy::AllOrNothing,
            cells: 1,
            n: 1,
            steps: 100,
            seed: 1,
            m: 2.0,
            regrow: 0.8,
            income: 1.0,
            maintenance: 0.2,
            repair_cost: 1.5,
            damage_rate: 0.01,
            move_cost: 0.0,
            energy: 5.0,
            energy_weak: None,
            weak_rank: 0,
            capacity: 10.0,
            read_budget: 0,
            share: ShareProtocol::Sequential,
        }
    }
}

/// One organism's record: the whole point of the probe.
struct Per {
    alive: bool,
    lifetime: usize,
    cause: &'static str,
    cell: usize,
    energy: f64,
    damage: f64,
    /// Runs of steps over which the meal did not change:
    /// `(first step, last step, taken)`.
    segments: Vec<(usize, usize, f64)>,
    /// This organism's damage and meal on the step when the FIRST organism of
    /// the population died. That is the damage it has to repay out of the
    /// grown share, and it is the number the race in EXP-152 is about.
    damage_at_first_death: Option<f64>,
    taken_at_first_death: Option<f64>,
}

impl Per {
    fn new() -> Self {
        Self {
            alive: true,
            lifetime: 0,
            cause: "alive",
            cell: 0,
            energy: 0.0,
            damage: 0.0,
            segments: Vec::new(),
            damage_at_first_death: None,
            taken_at_first_death: None,
        }
    }

    fn record(&mut self, step: usize, taken: f64) {
        match self.segments.last_mut() {
            Some(last) if (last.2 - taken).abs() <= 1e-12 => {
                last.1 = step;
            }
            _ => self.segments.push((step, step, taken)),
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

fn main() {
    let argv: Vec<String> = std::env::args().collect();
    let mut a = Args::default();
    let mut i = 1;
    while i < argv.len() {
        match argv[i].as_str() {
            "--policy" => {
                i += 1;
                a.policy = match argv.get(i).map(|s| s.as_str()) {
                    Some("stay") => Policy::Stay,
                    Some("random") => Policy::Random,
                    Some("remember") => Policy::Remember,
                    Some("memory") => Policy::Memory,
                    Some("sighted") => Policy::Sighted,
                    other => {
                        eprintln!("unknown policy: {:?}", other);
                        std::process::exit(2);
                    }
                };
            }
            "--repair" => {
                i += 1;
                a.repair = match argv.get(i).map(|s| s.as_str()) {
                    Some("none") => RepairPolicy::None,
                    Some("all-or-nothing") | Some("all") => RepairPolicy::AllOrNothing,
                    Some("proportional") => RepairPolicy::Proportional,
                    other => {
                        eprintln!("unknown repair policy: {:?}", other);
                        std::process::exit(2);
                    }
                };
            }
            "--cells" => {
                i += 1;
                a.cells = number(&argv, i, "--cells");
            }
            "--n" => {
                i += 1;
                a.n = number(&argv, i, "--n");
            }
            "--steps" => {
                i += 1;
                a.steps = number(&argv, i, "--steps");
            }
            "--seed" => {
                i += 1;
                a.seed = number(&argv, i, "--seed");
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
            "--energy-weak" => {
                i += 1;
                a.energy_weak = Some(number(&argv, i, "--energy-weak"));
            }
            "--weak-rank" => {
                i += 1;
                a.weak_rank = number(&argv, i, "--weak-rank");
            }
            "--capacity" => {
                i += 1;
                a.capacity = number(&argv, i, "--capacity");
            }
            "--read-budget" => {
                i += 1;
                a.read_budget = number(&argv, i, "--read-budget");
            }
            "--share" => {
                i += 1;
                a.share = match argv.get(i).map(|s| s.as_str()) {
                    Some("sequential") => ShareProtocol::Sequential,
                    Some("proportional") => ShareProtocol::Proportional,
                    other => {
                        eprintln!("unknown share protocol: {:?}", other);
                        std::process::exit(2);
                    }
                };
            }
            "--help" | "-h" => {
                println!("usage: rescue_probe [--policy P] [--repair R] [--cells C] [--n N]");
                println!("                    [--steps S] [--seed Z] [--m M] [--regrow R]");
                println!("                    [--income I] [--maintenance T] [--repair-cost RC]");
                println!("                    [--damage-rate DR] [--move-cost MC] [--energy E0]");
                println!("                    [--energy-weak EW] [--weak-rank WR]");
                println!("                    [--capacity CAP] [--read-budget B] [--share S]");
                return;
            }
            other => {
                eprintln!("unknown argument: {}", other);
                std::process::exit(2);
            }
        }
        i += 1;
    }
    if a.n == 0 || a.cells == 0 || a.weak_rank >= a.n {
        eprintln!("refusing to run: n, cells and weak-rank must name a population");
        std::process::exit(2);
    }

    let world = World {
        income: a.income,
        maintenance_cost: a.maintenance,
        repair_cost: a.repair_cost,
        damage_rate: a.damage_rate,
        capacity: a.capacity,
        read_budget: a.read_budget,
        share: a.share,
        ..World::default()
    };
    let field = match Field::new(a.cells, a.m, a.regrow) {
        Some(f) => f,
        None => {
            eprintln!("cannot build the field");
            std::process::exit(1);
        }
    };
    // The one difference from `spawn_even`: the reserve can differ per rank.
    let mut pop = Vec::with_capacity(a.n);
    for k in 0..a.n {
        let energy = match a.energy_weak {
            Some(e) if k == a.weak_rank => e,
            _ => a.energy,
        };
        let o = match Organism::healthy(energy) {
            Some(o) => o,
            None => {
                eprintln!("cannot build an organism with energy {}", energy);
                std::process::exit(1);
            }
        };
        let mut r = match Remembering::new(o, k % a.cells, 0.0, a.move_cost, 300) {
            Some(r) => r,
            None => {
                eprintln!("cannot build a remembering organism");
                std::process::exit(1);
            }
        };
        r.memory.best_level = 0.0;
        pop.push(r);
    }
    let mut life = match Life::new(world, field, pop, a.policy, a.seed, 300) {
        Some(l) => l,
        None => {
            eprintln!("cannot build the cycle");
            std::process::exit(1);
        }
    };

    // FNV-1a over everything that moved, per step, for every organism: the
    // same mixing the library uses in `Trace::compute_hash`.
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    let mut mix = |h: &mut u64, x: u64| {
        *h ^= x;
        *h = h.wrapping_mul(0x0000_0100_0000_01b3);
    };

    let mut per: Vec<Per> = (0..a.n).map(|_| Per::new()).collect();
    let mut first_death: Option<usize> = None;
    let mut steps_run = 0usize;
    for _ in 0..a.steps {
        if life.advance_with(a.repair).is_none() {
            break;
        }
        let step = life.step();
        steps_run = step;
        let samples = life.samples();
        // Did anybody die ON THIS STEP? Read before the per-organism update:
        // `per[slot].alive` is still the state of the step before.
        let death_this_step = samples.iter().any(|s| {
            s.slot < per.len() && per[s.slot].alive && !s.alive
        });
        let mut alive_now = 0usize;
        for (i, s) in samples.iter().enumerate() {
            if i >= per.len() {
                break;
            }
            // What this organism ate: `Sample::taken` is the field's record of
            // the meal and `Organism::step` cuts it at `income`. The two differ
            // exactly when the cell holds less than `income`.
            let taken = s.taken.min(a.income);
            mix(&mut h, step as u64);
            mix(&mut h, s.slot as u64);
            mix(&mut h, s.cell as u64);
            mix(&mut h, s.energy.to_bits());
            mix(&mut h, s.damage.to_bits());
            mix(&mut h, s.alive as u64);
            mix(&mut h, s.direction as i64 as u64);
            mix(&mut h, taken.to_bits());
            mix(&mut h, s.prev_cell as u64);
            let p = &mut per[i];
            if !p.alive {
                continue;
            }
            p.cell = s.cell;
            p.energy = s.energy;
            p.damage = s.damage;
            p.record(step, taken);
            if death_this_step && p.damage_at_first_death.is_none() {
                // The FIRST death only. Without the guard the number is
                // overwritten on the step this organism itself dies, where its
                // damage is 1.0 by definition -- and then the "damage it
                // carried into the rescue" reads 1.0 for everybody.
                p.damage_at_first_death = Some(s.damage);
                p.taken_at_first_death = Some(taken);
            }
            if s.alive {
                alive_now += 1;
            } else {
                p.alive = false;
                p.lifetime = step;
                // The step clamps energy at 0 on death, so `energy == 0` is the
                // energy death and `damage == 1` the damage death.
                p.cause = if s.damage >= 1.0 { "damage" } else { "energy" };
                if first_death.is_none() {
                    first_death = Some(step);
                }
            }
        }
        if alive_now == 0 {
            break;
        }
    }

    let census = life.census();
    let mut out = String::new();
    out.push_str(&format!(
        "{{\"policy\":\"{}\",\"repair\":\"{}\",\"share\":\"{}\",\"cells\":{},\"n\":{},\
         \"steps\":{},\"steps_run\":{},\"total\":{},\"alive_end\":{},\"moves\":{},\
         \"first_death\":{},\"energy\":{:.12},\"energy_weak\":{},\"weak_rank\":{},\
         \"income\":{:.12},\"damage_rate\":{:.12},\"capacity\":{:.12},\
         \"hash\":\"{:016x}\",\"organisms\":[",
        life.policy_name(),
        a.repair.name(),
        a.share.name(),
        a.cells,
        a.n,
        a.steps,
        steps_run,
        census.total,
        census.alive,
        census.moves,
        match first_death {
            Some(s) => s.to_string(),
            None => "null".to_string(),
        },
        a.energy,
        match a.energy_weak {
            Some(e) => format!("{:.12}", e),
            None => "null".to_string(),
        },
        a.weak_rank,
        a.income,
        a.damage_rate,
        a.capacity,
        h
    ));
    for (i, p) in per.iter().enumerate() {
        if i > 0 {
            out.push(',');
        }
        let lifetime = if p.alive {
            "null".to_string()
        } else {
            p.lifetime.to_string()
        };
        let segments: Vec<String> = p
            .segments
            .iter()
            .map(|(from, to, taken)| format!("[{},{},{:.12}]", from, to, taken))
            .collect();
        out.push_str(&format!(
            "{{\"i\":{},\"cell\":{},\"alive\":{},\"lifetime\":{},\"cause\":\"{}\",\
             \"energy\":{:.12},\"damage\":{:.12},\
             \"damage_at_first_death\":{},\"taken_at_first_death\":{},\
             \"segments\":[{}]}}",
            i,
            p.cell,
            p.alive,
            lifetime,
            p.cause,
            p.energy,
            p.damage,
            match p.damage_at_first_death {
                Some(v) => format!("{:.12}", v),
                None => "null".to_string(),
            },
            match p.taken_at_first_death {
                Some(v) => format!("{:.12}", v),
                None => "null".to_string(),
            },
            segments.join(",")
        ));
    }
    out.push_str("]}");
    println!("{}", out);
}
