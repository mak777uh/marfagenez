//! Read-only probe for `checks/exp_rho_window.py` (EXP-144).
//!
//! The `trace` binary cannot answer the question the harness asks. It records a
//! frame every `every` steps and `record` stops as soon as `advance()` returns
//! `None`, so on a point that dies early the trace holds no frame with
//! `alive == false` and the death step cannot be read off it. The JSON also
//! rounds every number to six decimals, so two policies that differ in the
//! seventh digit look identical.
//!
//! This probe builds the same `World`, `Field` and `Life` the binary builds,
//! advances one step at a time, and prints a single JSON object with the step
//! at which the organism stopped being alive, which bound it hit, the energy it
//! accumulated while alive, and the FNV hash of the per-step record. It links
//! against the existing library and changes nothing under `core/src`.
//!
//! ```bash
//! cargo build --release --example rho_probe
//! ./target/release/examples/rho_probe --policy stay --steps 100 \
//!     --m 2.0 --regrow 0.8 --income 1.0 --maintenance 0.6 \
//!     --repair-cost 1.5 --damage-rate 0.01
//! ```

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{RepairPolicy, ShareProtocol, World};

struct Args {
    policy: Policy,
    repair: RepairPolicy,
    cells: usize,
    n: usize,
    start_cell: usize,
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
            start_cell: 0,
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
            "--start-cell" => {
                i += 1;
                a.start_cell = number(&argv, i, "--start-cell");
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
                println!("usage: rho_probe [--policy P] [--repair R] [--cells C] [--n N] [--start-cell K]");
                println!("                 [--steps S] [--seed Z] [--m M] [--regrow R]");
                println!("                 [--income I] [--maintenance T] [--repair-cost RC]");
                println!("                 [--damage-rate DR] [--move-cost MC] [--energy E0]");
                println!("                 [--capacity CAP] [--read-budget B] [--share S]");
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
    // `uniform` is `(rich + poor) / 2` in the binary; here the level is given
    // directly, so there is no default level to fall back to.
    let field = match Field::new(a.cells, a.m, a.regrow) {
        Some(f) => f,
        None => {
            eprintln!("cannot build the field");
            std::process::exit(1);
        }
    };
    let cells: Vec<usize> = (0..a.n).map(|k| (a.start_cell + k) % a.cells).collect();
    let mut life = match Life::spawn_at(
        world,
        field,
        &cells,
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

    // FNV-1a over everything that moved, per step: the same mixing the library
    // uses in `Trace::compute_hash`, applied to the whole run rather than to
    // sampled frames.
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    let mut mix = |h: &mut u64, x: u64| {
        *h ^= x;
        *h = h.wrapping_mul(0x0000_0100_0000_01b3);
    };

    let mut alive_steps = 0usize;
    let mut energy_acc = 0.0f64;
    let mut taken_sum = 0.0f64;
    let mut lifetime = a.steps;
    let mut cause = "alive";
    let mut energy_end = 0.0f64;
    let mut damage_end = 0.0f64;
    let moves: u64;

    for _ in 0..a.steps {
        if life.advance_with(a.repair).is_none() {
            break;
        }
        let s = life.samples();
        let Some(s) = s.first() else { break };
        // What this organism ate this step. `Sample::taken` is the field's
        // record of the meal; `Organism::step` then cuts it at `income`
        // (`resource.max(0.0).min(world.income)`), and the two differ exactly
        // when the cell holds less than `income`. Reporting the raw field
        // value would hide the field limit this experiment is about.
        let taken = s.taken.min(a.income);
        mix(&mut h, life.step() as u64);
        mix(&mut h, s.cell as u64);
        mix(&mut h, s.energy.to_bits());
        mix(&mut h, s.damage.to_bits());
        mix(&mut h, s.alive as u64);
        mix(&mut h, s.direction as i64 as u64);
        mix(&mut h, taken.to_bits());
        mix(&mut h, s.prev_cell as u64);
        if s.alive {
            alive_steps += 1;
            energy_acc += s.energy;
        } else {
            lifetime = life.step();
            // Which bound was hit: `damage >= 1` or `energy <= 0`. The step
            // clamps energy at 0 on death, so `energy == 0` is the energy death.
            cause = if s.damage >= 1.0 { "damage" } else { "energy" };
            energy_end = s.energy;
            damage_end = s.damage;
            break;
        }
        energy_end = s.energy;
        damage_end = s.damage;
        taken_sum += taken;
    }
    let census = life.census();
    moves = census.moves;
    let alive_end = census.alive;
    let taken_mean = if alive_steps > 0 {
        taken_sum / alive_steps as f64
    } else {
        0.0
    };

    println!(
        "{{\"policy\":\"{}\",\"repair\":\"{}\",\"lifetime\":{},\"alive_steps\":{},\"cause\":\"{}\",\
         \"energy_acc\":{:.12},\"energy_end\":{:.12},\"damage_end\":{:.12},\
         \"taken_mean\":{:.12},\"moves\":{},\"steps_requested\":{},\
         \"alive_end\":{},\"total\":{},\"hash\":\"{:016x}\"}}",
        life.policy_name(),
        a.repair.name(),
        lifetime,
        alive_steps,
        cause,
        energy_acc,
        energy_end,
        damage_end,
        taken_mean,
        moves,
        a.steps,
        alive_end,
        census.total,
        h
    );
}
