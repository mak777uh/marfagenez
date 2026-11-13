//! # `trace` binary
//!
//! Runs the cycle with each policy and writes a JSON trace to `results/`.
//!
//! ```bash
//! cargo run --release --bin trace -- --policy remember --steps 500 --every 10
//! ```
//!
//! The output goes to `results/<policy>/trace-<timestamp>.json`.
//!
//! ## Why a binary and not a test
//!
//! A test asserts something. This **records** — it has no expectation, only a
//! description. That is Krishnamurti's P204: watch without judging.

use std::fs;
use std::path::PathBuf;

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::World;
use medium_core::trace::record;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut policy = Policy::Remember;
    let mut steps = 500usize;
    let mut every = 10usize;
    let mut seed = 20250101u64;
    let mut n = 40usize;
    let mut cells = 40usize;
    let mut capacity = 10.0f64;
    let mut damage_rate = 0.02f64;
    let mut income = 0.8f64;
    let mut maintenance = 0.6f64;
    let mut repair_cost = 1.5f64;
    let mut move_cost = 0.1f64;
    let mut energy = 5.0f64;
    let mut field_kind = "alternating".to_string();
    let mut memory_life = 300usize;
    let mut shift = 0.0f64;
    let mut rich = 2.0f64;
    let mut poor = 0.2f64;
    // Whether the level was chosen or left at the default. A uniform
    // field built from defaults is a field nobody asked for.
    let mut rich_set = false;
    let mut poor_set = false;
    let mut regrow = 0.8f64;
    let mut read_budget: usize = 0;
    let mut feed = false;
    let mut even = false;
    let mut start_cells: Option<Vec<usize>> = None;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--policy" => {
                i += 1;
                policy = match args.get(i).map(|s| s.as_str()) {
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
            "--steps" => {
                i += 1;
                steps = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(steps);
            }
            "--every" => {
                i += 1;
                every = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(every);
            }
            "--seed" => {
                i += 1;
                seed = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(seed);
            }
            "--n" => {
                i += 1;
                n = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(n);
            }
            "--cells" => {
                i += 1;
                cells = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(cells);
            }
            "--capacity" => {
                i += 1;
                capacity = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(capacity);
            }
            "--damage-rate" => {
                i += 1;
                damage_rate = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(damage_rate);
            }
            "--income" => {
                i += 1;
                income = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(income);
            }
            "--maintenance" => {
                i += 1;
                maintenance = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(maintenance);
            }
            "--repair-cost" => {
                i += 1;
                repair_cost = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(repair_cost);
            }
            "--move-cost" => {
                i += 1;
                move_cost = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(move_cost);
            }
            "--energy" => {
                i += 1;
                energy = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(energy);
            }
            "--field" => {
                i += 1;
                field_kind = args.get(i).cloned().unwrap_or(field_kind);
            }
            "--memory-life" => {
                i += 1;
                memory_life = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(memory_life);
            }
            "--shift" => {
                i += 1;
                shift = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(shift);
            }
            "--rich" => {
                i += 1;
                rich = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(rich);
                rich_set = true;
            }
            "--poor" => {
                i += 1;
                poor = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(poor);
                poor_set = true;
            }
            "--feed" => {
                feed = true;
            }
            "--layout" => {
                i += 1;
                even = matches!(args.get(i).map(|s| s.as_str()), Some("even"));
            }
            "--start-cell" => {
                i += 1;
                let raw = args.get(i).map(|s| s.as_str()).unwrap_or("");
                let mut v = Vec::new();
                for part in raw.split(',') {
                    let part = part.trim();
                    if part.is_empty() {
                        continue;
                    }
                    match part.parse::<usize>() {
                        Ok(c) => v.push(c),
                        Err(_) => {
                            eprintln!(
                                "refusing to run: --start-cell {} is not a list of cell indices.\n             Pass e.g. --start-cell 0,2 to put organism 0 on cell 0 and\n             organism 1 on cell 2. The list must have exactly --n entries.",
                                raw
                            );
                            std::process::exit(2);
                        }
                    }
                }
                start_cells = Some(v);
            }
            "--read-budget" => {
                i += 1;
                read_budget = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(read_budget);
            }
            "--regrow" => {
                i += 1;
                regrow = args.get(i).and_then(|s| s.parse().ok()).unwrap_or(regrow);
            }
            "--help" | "-h" => {
                println!("usage: trace [--policy stay|random|remember|memory|sighted] [--steps N] [--every K] [--seed S] [--n N] [--cells C]");
                println!("             [--capacity X] [--damage-rate X] [--income X] [--maintenance X]");
                println!("             [--repair-cost X] [--move-cost X] [--energy X]");
                println!("             [--field alternating|gradient|uniform|moving] [--memory-life N] [--shift X]");
                println!("             [--rich X] [--poor X] [--regrow X] [--layout even] [--start-cell 0,2]");
                println!("             [--read-budget N]  cells the organism may read per step without eating");
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
        income,
        maintenance_cost: maintenance,
        repair_cost,
        damage_rate,
        capacity,
        read_budget,
    };
    let field = match field_kind.as_str() {
        "alternating" => Field::alternating(cells, rich, poor, regrow),
        "gradient" => Field::gradient(cells, poor, rich, regrow),
        "uniform" => Field::new(cells, (rich + poor) / 2.0, regrow),
        "moving" => Field::moving(cells, rich, poor, regrow, if shift > 0.0 { shift } else { 1.0 }),
        other => {
            eprintln!("unknown field: {} (expected alternating, gradient, uniform)", other);
            std::process::exit(2);
        }
    };
    let field = match field {
        Some(f) => f,
        None => {
            eprintln!("cannot build the field");
            std::process::exit(1);
        }
    };
    // A field that is asked to be uneven but is built from equal levels is not
    // uneven. `uniform` is `(rich + poor) / 2`, so `--rich 2 --poor 2` makes
    // `alternating`, `gradient` and `uniform` the same constant field, with the
    // same dynamics hash. EXP-31 measured a gradient arm that was a flat field
    // for exactly this reason.
    if rich == poor && (field_kind == "alternating" || field_kind == "gradient") {
        eprintln!(
            "refusing to run: --field {} with --rich {} == --poor {} is a flat field.\n             uniform is built as (rich + poor) / 2, so all three kinds coincide\n             and the uneven arm measures nothing. Give the two levels different\n             values, e.g. --rich 2.4 --poor 1.6, or pass --field uniform if a\n             flat field is what you mean.",
            field_kind, rich, poor
        );
        std::process::exit(2);
    }
    // A uniform field is `(rich + poor) / 2`, so leaving both at their defaults
    // builds a field at a level nobody chose -- and it does so silently. The
    // defaults are `rich 2.0`, `poor 0.2`, so the level is 1.1, not the 2.0 a
    // reader of the command line would assume. A run at `M = 1.1` with
    // `income 1.2` saturates at `M*r = 0.88` and reports a capacity of 40 with
    // a surplus of 2 that looks like a rotation and is really a different
    // world. See `docs/FINDING-the-surplus-was-a-field-built-at-the-wrong-level.md`.
    if field_kind == "uniform" && !(rich_set && poor_set) {
        eprintln!(
            "refusing to run: --field uniform without both --rich and --poor.\n             uniform is built as (rich + poor) / 2, so an unset one falls\n             back to its default and the level becomes one nobody chose.\n             The defaults are\n             rich 2.0, poor 0.2, so this would build a field at M = 1.10 --\n             a level nobody chose. Pass the level you mean, e.g.\n             --rich 2.4 --poor 1.6 for M = 2.0."
        );
        std::process::exit(2);
    }
    // A sighted policy with a read budget of zero cannot see. It does not error
    // and it does not warn: `best > here` is never true, so it silently becomes
    // `Stay`. EXP-26 measured that default for months and called it a law.
    if matches!(policy, Policy::Sighted) && read_budget == 0 {
        eprintln!(
            "refusing to run: --policy sighted with --read-budget 0 is not sighted.\n             A budget of zero reads neither neighbour, so the policy degenerates to
             stay without any error. Pass --read-budget 3 (underfoot + both
             neighbours) or choose --policy stay if standing still is what you mean."
        );
        std::process::exit(2);
    }

    // `--start-cell` is the only way to ask a question about a particular
    // cell: `spawn` places organisms at random and `spawn_even` puts organism
    // `i` on cell `i % cells`, so without it a placement arm silently becomes
    // the even arm (EXP-83 D, EXP-84).
    if let Some(ref sc) = start_cells {
        if sc.len() != n {
            eprintln!(
                "refusing to run: --start-cell has {} entries but --n is {}.\n             One index per organism, e.g. --n 2 --start-cell 0,2.",
                sc.len(),
                n
            );
            std::process::exit(2);
        }
        let cells_now = field.cells();
        for (i, c) in sc.iter().enumerate() {
            if *c >= cells_now {
                eprintln!(
                    "refusing to run: --start-cell puts organism {} on cell {} but the field has {} cells (0..{}).",
                    i,
                    c,
                    cells_now,
                    cells_now - 1
                );
                std::process::exit(2);
            }
        }
    }

    let spawned = if let Some(ref sc) = start_cells {
        Life::spawn_at(world, field, sc, energy, move_cost, policy, seed, memory_life)
    } else if even {
        Life::spawn_even(world, field, n, energy, move_cost, policy, seed, memory_life)
    } else {
        Life::spawn(world, field, n, energy, move_cost, policy, seed, memory_life)
    };
    let mut life = match spawned {
        Some(l) => l,
        None => {
            eprintln!("cannot build the cycle");
            std::process::exit(1);
        }
    };

    if feed {
        life.feed = true;
    }
    let trace = record(&mut life, steps, every);

    let name = match policy {
        Policy::Stay => "stay",
        Policy::Random => "random",
        Policy::Remember => "remember",
        Policy::Memory => "memory",
        Policy::Sighted => "sighted",
    };
    let dir = PathBuf::from("results").join(name);
    if let Err(e) = fs::create_dir_all(&dir) {
        eprintln!("cannot create {}: {}", dir.display(), e);
        std::process::exit(1);
    }
    // Milliseconds, not seconds. A second is long enough for several runs to
    // land on the same name, and the later one silently overwrites the earlier
    // one. That happened: three different hashes were written to
    // `trace-sighted-1794524986.json` in one second, and a check that looked
    // for "the newest file" read whichever survived. If the name still
    // collides, add a counter rather than overwrite.
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis())
        .unwrap_or(0);
    let mut path = dir.join(format!("trace-{}-{}.json", name, stamp));
    let mut n = 1;
    while path.exists() {
        path = dir.join(format!("trace-{}-{}-{}.json", name, stamp, n));
        n += 1;
    }
    if let Err(e) = fs::write(&path, trace.to_json()) {
        eprintln!("cannot write {}: {}", path.display(), e);
        std::process::exit(1);
    }

    println!("policy:   {}", name);
    println!("capacity: {}", capacity);
    println!("damage:   {}", damage_rate);
    println!("field:    {}", field_kind);
    println!("memlife:  {}", memory_life);
    println!("shift:    {}", shift);
    println!("rich:     {}", rich);
    println!("poor:     {}", poor);
    println!("regrow:   {}", regrow);
    println!("feed:     {}", feed);
    println!("steps:    {}", steps);
    println!("frames:   {}", trace.frames.len());
    println!("hash:     {:016x}", trace.hash);
    println!("written:  {}", path.display());
}
