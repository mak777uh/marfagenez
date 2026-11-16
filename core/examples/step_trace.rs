//! Per-step trace for `checks/exp_repair_edge.py` (EXP-148).
//!
//! `rho_probe` answers "how long did it live and why did it stop"; it does not
//! say what happened *during* the steps, and the two boundary defects of
//! `FINDING-147` are statements about the cycle, not about the endpoint:
//!
//!   * `dr = 0.21, rc = 2.0` dies on the cadence equality after 350 steps,
//!     while `FINDING-145` measured an equality alive at `dr = 0.3, rc = 1.6`;
//!   * `proportional` at `dr = 0.6, rc = 1.6500000000000004` survives because
//!     `(energy / rc) * rc` lands one ulp below `energy`.
//!
//! Both are claims about the state one step before the death, so they need a
//! trace, not a lifetime. This probe builds the same `World`, `Field` and `Life`
//! the other probe and the binary build, advances one step at a time, and prints
//! one JSON object with the first `--head` and the last `--tail` step records,
//! plus the same summary fields `rho_probe` prints.
//!
//! Each record is `{step, e_in, e, d_in, d, taken, repaired, price}` where
//! `e_in`/`d_in` are the state **before** the step and `e`/`d` are the state
//! **after** it. The step order is fixed (`core/src/organism.rs`): income,
//! maintenance, `damage += dr` capped at 1.0, repair, capacity cap, death test.
//! A record with `repaired = true` therefore has `d == 0` under
//! `all-or-nothing`, and `price = d_in_after_damage * repair_cost`, which is
//! computed here rather than inferred by a reader of the trace.
//!
//! Nothing under `core/src` is touched and the default output of `rho_probe`
//! does not move, so no committed number changes.
//!
//! ```bash
//! cargo build --release --example step_trace
//! ./target/release/examples/step_trace --damage-rate 0.21 --repair-cost 2.0 \
//!     --income 1.0 --maintenance 0.6 --energy 5.0 --capacity 10.0 \
//!     --steps 400 --head 30 --tail 20
//! ```

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{RepairPolicy, ShareProtocol, World};

struct Args {
    repair: RepairPolicy,
    cells: usize,
    n: usize,
    start_cell: usize,
    steps: usize,
    head: usize,
    tail: usize,
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
}

impl Default for Args {
    fn default() -> Self {
        Self {
            repair: RepairPolicy::AllOrNothing,
            cells: 8,
            n: 1,
            start_cell: 0,
            steps: 20000,
            head: 0,
            tail: 0,
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
        }
    }
}

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

/// One step, as it is written into the trace.
#[derive(Clone, Copy)]
struct Record {
    step: usize,
    e_in: f64,
    e: f64,
    d_in: f64,
    d: f64,
    taken: f64,
    repaired: bool,
    price: f64,
}

impl Record {
    fn json(&self) -> String {
        format!(
            "{{\"step\":{},\"e_in\":{:.17},\"e\":{:.17},\"d_in\":{:.17},\"d\":{:.17},\
             \"taken\":{:.17},\"repaired\":{},\"price\":{:.17}}}",
            self.step, self.e_in, self.e, self.d_in, self.d, self.taken, self.repaired, self.price
        )
    }
}

fn main() {
    let argv: Vec<String> = std::env::args().collect();
    let mut a = Args::default();
    let mut i = 1;
    while i < argv.len() {
        match argv[i].as_str() {
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
            "--policy" => {
                i += 1;
                match argv.get(i).map(|s| s.as_str()) {
                    Some("stay") => {}
                    other => {
                        eprintln!("this probe only walks `stay`, got {:?}", other);
                        std::process::exit(2);
                    }
                }
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
            "--head" => {
                i += 1;
                a.head = number(&argv, i, "--head");
            }
            "--tail" => {
                i += 1;
                a.tail = number(&argv, i, "--tail");
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
            "--help" | "-h" => {
                println!("usage: step_trace [--repair R] [--steps S] [--head H] [--tail T]");
                println!("                  [--income I] [--maintenance T] [--repair-cost RC]");
                println!("                  [--damage-rate DR] [--energy E0] [--capacity CAP]");
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
        share: ShareProtocol::Sequential,
        ..World::default()
    };
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
        Policy::Stay,
        a.seed,
        300,
    ) {
        Some(l) => l,
        None => {
            eprintln!("cannot build the cycle");
            std::process::exit(1);
        }
    };

    let mut head: Vec<Record> = Vec::new();
    // The ring buffer that makes `--tail` possible without holding a million
    // records: the trace is read as the last `tail` states before the stop.
    let mut ring: Vec<Record> = Vec::with_capacity(a.tail.max(1));
    let mut lifetime = a.steps;
    let mut cause = "alive".to_string();
    let mut energy_end = 0.0f64;
    let mut damage_end = 0.0f64;
    let mut energy_acc = 0.0f64;
    let mut repairs = 0usize;
    let mut spend = 0.0f64;
    let mut e_prev = a.energy;
    let mut d_prev = 0.0f64;

    for _ in 0..a.steps {
        let before = life.step();
        if life.advance_with(a.repair).is_none() {
            break;
        }
        let samples = life.samples();
        let Some(s) = samples.first() else { break };
        let taken = s.taken.min(a.income);
        let d_after_damage = (d_prev + a.damage_rate).min(1.0);
        let repaired = d_after_damage > 0.0
            && match a.repair {
                RepairPolicy::None => false,
                RepairPolicy::AllOrNothing => s.damage == 0.0,
                RepairPolicy::Proportional => s.damage < d_after_damage,
            };
        let price = if repaired {
            match a.repair {
                RepairPolicy::Proportional => {
                    let repaired_amount = d_after_damage - s.damage;
                    repaired_amount * a.repair_cost
                }
                _ => d_after_damage * a.repair_cost,
            }
        } else {
            0.0
        };
        let rec = Record {
            step: before + 1,
            e_in: e_prev,
            e: s.energy,
            d_in: d_prev,
            d: s.damage,
            taken,
            repaired,
            price,
        };
        if head.len() < a.head {
            head.push(rec);
        }
        if a.tail > 0 {
            if ring.len() == a.tail {
                ring.remove(0);
            }
            ring.push(rec);
        }
        if repaired {
            repairs += 1;
            spend += price;
        }
        if s.alive {
            energy_acc += s.energy;
        } else {
            lifetime = life.step();
            cause = if s.damage >= 1.0 { "damage" } else { "energy" }.to_string();
            energy_end = s.energy;
            damage_end = s.damage;
            break;
        }
        energy_end = s.energy;
        damage_end = s.damage;
        e_prev = s.energy;
        d_prev = s.damage;
    }
    let head_json: Vec<String> = head.iter().map(|r| r.json()).collect();
    let tail_json: Vec<String> = ring.iter().map(|r| r.json()).collect();
    println!(
        "{{\"repair\":\"{}\",\"lifetime\":{},\"cause\":\"{}\",\
         \"energy_end\":{:.17},\"damage_end\":{:.17},\"energy_acc\":{:.17},\
         \"repairs\":{},\"spend\":{:.17},\"steps_requested\":{},\
         \"head\":[{}],\"tail\":[{}]}}",
        a.repair.name(),
        lifetime,
        cause,
        energy_end,
        damage_end,
        energy_acc,
        repairs,
        spend,
        a.steps,
        head_json.join(","),
        tail_json.join(",")
    );
}
