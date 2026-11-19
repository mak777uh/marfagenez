//! The mixture: how much of the decay stays with the form, and where the two worlds meet.
//!
//! `FINDING-270` gave a fully communal cycle (payers take everything, death donates to competitors) and
//! `FINDING-271` a fully local one (self-sufficient forms, the medium empty and irrelevant). Between them sits a
//! fraction: `local_share` of the decay goes into the form's own pocket, the rest back to the shared stock.
//!
//! The arithmetic of the pocket says the moment `local_share` is enough for `q*d*share >= u` the form is
//! self-funding, i.e. `share >= u/(q*d) = q_min/q`. With `q = 1` that is `share >= 0.2`, so the transition should be
//! **sharp** around 0.2, not gradual.
//!
//! PREDICTION, before the run (no inflow, `c = 1`, 4000 steps, 50 payers + 50 non-payers, cap 500):
//!   (a) the transition is **sharp**: the population and the payer share change abruptly between two neighbouring
//!       values of `local_share`, not smoothly;
//!   (b) the switch happens at a **small** share - my guess is the window 0.1 ... 0.4, because 0.2 is where the
//!       pocket first covers the need;
//!   (c) at every share the payers take everything: a non-payer never repairs, so the mixture cannot help it.

use medium_core::skin::{SkinCycle, SkinForm, SkinPopRules, SkinRecycle, SkinRules};

const STEPS: usize = 4000;
const SEED: u64 = 5;

fn rules(share: f64) -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost: 1.0,
            income: 1.0,
            maintenance: 0.0,
        },
        u_noise: 0.0,
        u_shift: 0.0,
        birth_price: 0.5,
        max_population: 500,
        demand_growth: None,
        repair_from_pool: false,
        local_recycle: true,
        local_share: share,
    }
}

fn run(share: f64, cost: f64, cap: usize) -> (usize, usize, f64, f64) {
    let mut r = rules(share);
    r.skin.repair_cost = cost;
    r.max_population = cap;
    let need = r.skin.u_min();
    let cycle = SkinCycle::new(0.0, 0.0, 2000.0, 100_000.0, 0.0, 1.0);
    let mut pop = SkinRecycle::new(r, cycle, 1.0, 10.0, need);
    pop.forms.clear();
    for _ in 0..50 {
        pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: need, age: 0, pocket: 0.0 });
        pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: 0.0, age: 0, pocket: 0.0 });
    }
    let mut rng = medium_core::Rng::new(SEED);
    for _ in 0..STEPS {
        pop.step(&mut rng);
    }
    let payers = pop.forms.iter().filter(|f| f.u >= need).count();
    let mean_pocket = if pop.forms.is_empty() {
        0.0
    } else {
        pop.forms.iter().map(|f| f.pocket).sum::<f64>() / pop.forms.len() as f64
    };
    (pop.forms.len(), payers, pop.cycle.spent, mean_pocket)
}

fn main() {
    println!(
        "{:>7} {:>7} {:>7} {:>9} {:>9}",
        "share", "alive", "payers", "spent", "pocket"
    );
    let mut rows = Vec::new();
    for share in [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.6, 1.0] {
        let (alive, payers, spent, pocket) = run(share, 1.0, 500);
        println!("{share:>7.2} {alive:>7} {payers:>7} {spent:>9.1} {pocket:>9.3}");
        rows.push((share, alive, payers, spent, pocket));
    }

    println!();
    println!("scarce: cost 0.9, cap 5000, no inflow");
    println!("{:>7} {:>7} {:>7} {:>9} {:>9}", "share", "alive", "payers", "spent", "pocket");
    for share in [0.0, 0.1, 0.2, 0.3, 0.5, 1.0] {
        let (alive, payers, spent, pocket) = run(share, 0.9, 5000);
        println!("{share:>7.2} {alive:>7} {payers:>7} {spent:>9.1} {pocket:>9.3}");
    }

    println!();
    let mut bad = 0;

    // (a) sharpness: the largest jump between neighbouring shares, relative to the range
    let alive: Vec<i64> = rows.iter().map(|r| r.1 as i64).collect();
    let max_jump = alive.windows(2).map(|w| (w[1] - w[0]).abs()).max().unwrap_or(0);
    let range = alive.iter().max().unwrap() - alive.iter().min().unwrap();
    let sharp = range > 0 && (max_jump as f64) >= 0.5 * (range as f64);
    println!(
        "  {} (a) the transition is sharp: largest step {max_jump} of a range of {range}",
        if sharp { "ok   " } else { "WRONG" }
    );
    if !sharp {
        bad += 1;
    }

    // (b) the switch is a small share
    let switch = rows
        .iter()
        .find(|r| r.1 >= 400)
        .map(|r| r.0);
    let small = switch.map(|s| s <= 0.4).unwrap_or(false);
    println!(
        "  {} (b) the switch happens at a small share: {switch:?}",
        if small { "ok   " } else { "WRONG" }
    );
    if !small {
        bad += 1;
    }

    // (c) the payers take everything at every share
    let payers_all = rows.iter().all(|r| r.2 == r.1);
    println!("  {} (c) the payers take everything at every share", if payers_all { "ok   " } else { "WRONG" });
    if !payers_all {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
