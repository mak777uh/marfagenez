//! Read-only probe for `checks/exp_competition_edge.py` (EXP-151).
//!
//! `rho_probe` reports the *first* organism's lifetime and the census's
//! survivor count. The competition experiment needs more than that: when `n`
//! organisms share one cell, the question is **which** of them survives and
//! for how long, because the two share protocols distribute the same meal
//! differently. One number (the mean `taken`) cannot say that, and a census
//! can only say how many are left.
//!
//! This probe builds the same `World`, `Field` and `Life` the binary builds,
//! advances one step at a time, and prints one JSON object: a record per
//! organism (lifetime, cause of death, energy, damage, mean `taken`) plus the
//! FNV hash of the per-step record of *all* organisms. It links against the
//! existing library and changes nothing under `core/src`.
//!
//! ```bash
//! cargo build --release --example share_probe
//! ./target/release/examples/share_probe --cells 1 --n 4 --m 4 --regrow 0.8 \
//!     --income 1.0 --maintenance 0.2 --repair-cost 10 --damage-rate 0.03 \
//!     --capacity 10 --share sequential --steps 10000
//! ```
//!
//! `--cells 1` puts every organism on the single cell; `--cells 3 --n 6` puts
//! two on each of three cells (`spawn_even` is round-robin), which is the
//! locality control: the crowd law is per cell, not per population.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{RepairPolicy, ShareProtocol, World};

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
    capacity: f64,
    read_budget: usize,
    share: ShareProtocol,
}

impl Default for Args {
    fn default() -> Self {
        Self {
            policy: Policy::Stay,
            repair: RepairPolicy::AllOrNothing,
            cells: 8,
            n: 1,
            steps: 100,
            seed: 1,
            m: 2.0,
            regrow: 0.8,
            income: 1.0,
            maintenance: 0.6,
            repair_cost: 1.5,
            damage_rate: 0.01,
            move_cost: 0.0,
            energy: 5.0,
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
    taken_sum: f64,
    taken_count: usize,
    taken_first: f64,
    taken_last: f64,
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
            taken_sum: 0.0,
            taken_count: 0,
            taken_first: 0.0,
            taken_last: 0.0,
        }
    }

    fn taken_mean(&self) -> f64 {
        if self.taken_count == 0 {
            0.0
        } else {
            self.taken_sum / self.taken_count as f64
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
                println!("usage: share_probe [--policy P] [--repair R] [--cells C] [--n N]");
                println!("                   [--steps S] [--seed Z] [--m M] [--regrow R]");
                println!("                   [--income I] [--maintenance T] [--repair-cost RC]");
                println!("                   [--damage-rate DR] [--move-cost MC] [--energy E0]");
                println!("                   [--capacity CAP] [--read-budget B] [--share S]");
                return;
            }
            other => {
                eprintln!("unknown argument: {}", other);
                std::process::exit(2);
            }
        }
        i += 1;
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
    let mut life = match Life::spawn_even(
        world,
        field,
        a.n,
        a.energy,
        a.move_cost,
        a.policy,
        a.seed,
        300,
    ) {
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
    for _ in 0..a.steps {
        if life.advance_with(a.repair).is_none() {
            break;
        }
        let step = life.step();
        let samples = life.samples();
        let mut alive_now = 0usize;
        for (i, s) in samples.iter().enumerate() {
            if i >= per.len() {
                break;
            }
            // What this organism ate: `Sample::taken` is the field's record of
            // the meal and `Organism::step` cuts it at `income`. The two
            // differ exactly when the cell holds less than `income`, which is
            // the whole question here.
            let taken = s.taken.min(a.income);
            mixed(&mut mix, &mut h, step, s, taken);
            let p = &mut per[i];
            if !p.alive {
                continue;
            }
            p.cell = s.cell;
            p.energy = s.energy;
            p.damage = s.damage;
            p.taken_sum += taken;
            p.taken_last = taken;
            if p.taken_count == 0 {
                p.taken_first = taken;
            }
            p.taken_count += 1;
            if s.alive {
                alive_now += 1;
            } else {
                p.alive = false;
                p.lifetime = step;
                // The step clamps energy at 0 on death, so `energy == 0` is the
                // energy death and `damage == 1` the damage death.
                p.cause = if s.damage >= 1.0 { "damage" } else { "energy" };
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
         \"steps\":{},\"total\":{},\"alive_end\":{},\"moves\":{},\"hash\":\"{:016x}\",\
         \"organisms\":[",
        life.policy_name(),
        a.repair.name(),
        a.share.name(),
        a.cells,
        a.n,
        a.steps,
        census.total,
        census.alive,
        census.moves,
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
        out.push_str(&format!(
            "{{\"i\":{},\"cell\":{},\"alive\":{},\"lifetime\":{},\"cause\":\"{}\",\
             \"energy\":{:.12},\"damage\":{:.12},\"taken_mean\":{:.12},\
             \"taken_first\":{:.12},\"taken_last\":{:.12}}}",
            i,
            p.cell,
            p.alive,
            lifetime,
            p.cause,
            p.energy,
            p.damage,
            p.taken_mean(),
            p.taken_first,
            p.taken_last
        ));
    }
    out.push_str("]}");
    println!("{}", out);
}

/// Folds one organism's step into the run hash.
fn mixed(
    mix: &mut impl FnMut(&mut u64, u64),
    h: &mut u64,
    step: usize,
    s: &medium_core::trace::Sample,
    taken: f64,
) {
    mix(h, step as u64);
    mix(h, s.slot as u64);
    mix(h, s.cell as u64);
    mix(h, s.energy.to_bits());
    mix(h, s.damage.to_bits());
    mix(h, s.alive as u64);
    mix(h, s.direction as i64 as u64);
    mix(h, taken.to_bits());
    mix(h, s.prev_cell as u64);
}
