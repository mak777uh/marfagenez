//! Capping the matter instead of the population: does the pocket become an advantage?
//!
//! `FINDING-273` found that no parameter choice made matter scarce on the population side, because a form takes
//! `c*d*q_min` and returns `q*d`, a fourfold surplus at `q = 1`. The ceiling that was never tried is the one on the
//! **medium**: `ready_max = 5` with no inflow, so surplus matter has nowhere to sit.
//!
//! A pocket is **not** capped by the medium - it belongs to the form. So a capped medium should make local
//! recycling an advantage, and the sweep over `local_share` should finally show a difference.
//!
//! PREDICTION, before the run (no inflow, `ready_max = 5`, `c = 1`, 4000 steps, population cap 5000):
//!   (a) the population is **far below** its cap - the medium, not the room, limits it now;
//!   (b) the population **grows with `local_share`**, because the pocket is matter the cap cannot hold;
//!   (c) the payers still take everything: a non-payer never repairs, so no pocket can help it.

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
        max_population: 5000,
        demand_growth: None,
        repair_from_pool: false,
        local_recycle: true,
        local_share: share,
    }
}

fn run(share: f64) -> (usize, usize, f64, f64) {
    let r = rules(share);
    let need = r.skin.u_min();
    // the ceiling is on the matter: five units, and nothing arrives from outside
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
    let payers = pop.forms.iter().filter(|f| f.u >= need).count();
    let mean_pocket = if pop.forms.is_empty() {
        0.0
    } else {
        pop.forms.iter().map(|f| f.pocket).sum::<f64>() / pop.forms.len() as f64
    };
    (pop.forms.len(), payers, pop.cycle.ready, mean_pocket)
}

fn run_seed(share: f64, seed: u64) -> usize {
    let r = rules(share);
    let need = r.skin.u_min();
    let cycle = SkinCycle::new(5.0, 0.0, 5.0, 100_000.0, 0.0, 1.0);
    let mut pop = SkinRecycle::new(r, cycle, 1.0, 10.0, need);
    pop.forms.clear();
    for _ in 0..50 {
        pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: need, age: 0, pocket: 0.0 });
        pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: 0.0, age: 0, pocket: 0.0 });
    }
    let mut rng = medium_core::Rng::new(seed);
    for _ in 0..STEPS {
        pop.step(&mut rng);
    }
    pop.forms.len()
}

fn main() {
    println!("ten seeds at shares 0.2, 0.4, 0.6 (does the dip repeat?)");
    for share in [0.2, 0.4, 0.6] {
        let counts: Vec<usize> = (1..=10).map(|s| run_seed(share, s)).collect();
        let mean = counts.iter().sum::<usize>() as f64 / counts.len() as f64;
        let lo = counts.iter().min().unwrap();
        let hi = counts.iter().max().unwrap();
        println!("  share {share:.1}: mean {mean:>7.0} range {lo}..{hi}  {counts:?}");
    }
    println!();
    println!(
        "{:>7} {:>7} {:>7} {:>8} {:>9}",
        "share", "alive", "payers", "ready", "pocket"
    );
    let mut rows = Vec::new();
    for share in [0.0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0] {
        let (alive, payers, ready, pocket) = run(share);
        println!("{share:>7.2} {alive:>7} {payers:>7} {ready:>8.1} {pocket:>9.3}");
        rows.push((share, alive, payers, ready, pocket));
    }

    println!();
    let mut bad = 0;

    let a = rows.iter().all(|r| r.1 < 5000);
    println!(
        "  {} (a) the medium, not the room, limits the population: max {}",
        if a { "ok   " } else { "WRONG" },
        rows.iter().map(|r| r.1).max().unwrap()
    );
    if !a {
        bad += 1;
    }

    let grows = rows.windows(2).all(|w| w[1].1 >= w[0].1);
    println!(
        "  {} (b) the population grows with the local share: {:?}",
        if grows { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.0, r.1)).collect::<Vec<_>>()
    );
    if !grows {
        bad += 1;
    }

    let payers_all = rows.iter().all(|r| r.2 == r.1);
    println!("  {} (c) the payers take everything", if payers_all { "ok   " } else { "WRONG" });
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
