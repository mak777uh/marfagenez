//! Is the pocket's advantage really about locality - or just an endless pocket?
//!
//! `FINDING-274` found that with the ceiling on the **matter** the local share decides the population, from 450 to
//! 5000. It also named its own weak point: the pocket had **no ceiling**, so a form could hide matter the common
//! stock could not hold. That is a reason unrelated to locality.
//!
//! PREDICTION, before the run (no inflow, `ready_max = 5`, `c = 1`, 4000 steps, cap 5000):
//!   (a) with a **bottomless** pocket the population grows with the local share (the result of 274);
//!   (b) with the pocket capped at **1.0** the advantage **disappears**: the population no longer depends on the
//!       share in the same way, because there is nowhere to hide the surplus;
//!   (c) the capped pocket never yields more forms than the bottomless one at the same share.

use medium_core::skin::{SkinCycle, SkinForm, SkinPopRules, SkinRecycle, SkinRules};

const STEPS: usize = 4000;
const SEED: u64 = 5;

fn rules(share: f64, pocket_max: Option<f64>) -> SkinPopRules {
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
        max_population: 5000,
        demand_growth: None,
        repair_from_pool: false,
        local_recycle: true,
        local_share: share,
        pocket_max,
    }
}

fn run(share: f64, pocket_max: Option<f64>) -> usize {
    let r = rules(share, pocket_max);
    let need = r.skin.u_min();
    let cycle = SkinCycle::new(5.0, 0.0, 5.0, 100_000.0, 0.0, 1.0);
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
    pop.forms.len()
}

fn main() {
    println!("{:>7} {:>14} {:>12}", "share", "bottomless", "capped 1.0");
    let mut rows = Vec::new();
    for share in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0] {
        let free = run(share, None);
        let capped = run(share, Some(1.0));
        println!("{share:>7.2} {free:>14} {capped:>12}");
        rows.push((share, free, capped));
    }

    let mut bad = 0;
    println!();
    println!("sweep of the cap at full locality (share 1.0); a step's repair needs 0.01:");
    println!("{:>10} {:>7}", "cap", "alive");
    let mut cap_rows = Vec::new();
    for cap in [0.001, 0.005, 0.01, 0.02, 0.05, 0.2, 1.0] {
        let alive = run(1.0, Some(cap));
        println!("{cap:>10.3} {alive:>7}");
        cap_rows.push((cap, alive));
    }
    let uncapped = run(1.0, None);
    println!("{:>10} {uncapped:>7}", "none");

    let binding = cap_rows.iter().any(|r| r.1 < uncapped);
    println!(
        "  {} a small enough cap DOES bind: uncapped {uncapped}, smallest cap {}",
        if binding { "ok   " } else { "WRONG" },
        cap_rows[0].1
    );
    if !binding {
        bad += 1;
    }

    println!();

    let a = rows.windows(2).all(|w| w[1].1 >= w[0].1);
    println!(
        "  {} (a) bottomless: the population grows with the share: {:?}",
        if a { "ok   " } else { "WRONG" },
        rows.iter().map(|r| r.1).collect::<Vec<_>>()
    );
    if !a {
        bad += 1;
    }

    let free_range = rows.iter().map(|r| r.1).max().unwrap() - rows.iter().map(|r| r.1).min().unwrap();
    let capped_range = rows.iter().map(|r| r.2).max().unwrap() - rows.iter().map(|r| r.2).min().unwrap();
    let b = capped_range < free_range / 2;
    println!(
        "  {} (b) capped: the advantage shrinks: spread {capped_range} against {free_range}",
        if b { "ok   " } else { "WRONG" }
    );
    if !b {
        bad += 1;
    }

    let c = rows.iter().all(|r| r.2 <= r.1);
    println!(
        "  {} (c) a capped pocket never yields more forms: {:?}",
        if c { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.1, r.2)).collect::<Vec<_>>()
    );
    if !c {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
