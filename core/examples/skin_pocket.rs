//! Local recycling: what falls off a form lands in its own pocket, not in the common stock.
//!
//! `FINDING-270` found that on a **communal** cycle dying donates your body to the competitors, so keeping yourself
//! whole is the only way a line keeps its matter - the payers took everything.
//!
//! With a **pocket** the return goes to the line instead. The arithmetic of a pocket is simple and worth stating
//! before the run: decay returns `q * d` per step, repair wants `u = d * q_min`, so the pocket is self-funding
//! exactly while
//!
//! ```text
//! q * d >= d * q_min    i.e.    q >= q_min
//! ```
//!
//! which is true for any living form. So a pocket should make self-maintenance **free**, and a form should need no
//! medium at all.
//!
//! PREDICTION, before the run (no external inflow, `c = 1`, 4000 steps, 50 payers and 50 non-payers, cap 500):
//!   (a) the payers still win - a non-payer never repairs, so a pocket does not help it at all;
//!   (b) the pocket makes the payers independent of the common stock: `ready` stays at zero and the population is
//!       supported by pockets alone;
//!   (c) a payer's pocket is **small but never empty** - it is spent immediately on repair, so it hovers near the
//!       step's loss rather than accumulating.

use medium_core::skin::{SkinCycle, SkinForm, SkinPopRules, SkinRecycle, SkinRules};

const STEPS: usize = 4000;
const SEED: u64 = 5;

fn rules(local: bool) -> SkinPopRules {
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
        local_recycle: local,
    }
}

fn run(local: bool) -> SkinRecycle {
    let r = rules(local);
    let need = r.skin.u_min();
    // an empty medium: no inflow, and nothing in the stock
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
    pop
}

fn main() {
    for local in [false, true] {
        let pop = run(local);
        let need = pop.rules.skin.u_min();
        let payers = pop.forms.iter().filter(|f| f.u >= need).count();
        let mean_pocket = if pop.forms.is_empty() {
            0.0
        } else {
            pop.forms.iter().map(|f| f.pocket).sum::<f64>() / pop.forms.len() as f64
        };
        println!(
            "local_recycle = {:<5} alive {:>4} payers {:>4} ready {:>6.1} spent {:>8.1} mean pocket {:.3}",
            local,
            pop.forms.len(),
            payers,
            pop.cycle.ready,
            pop.cycle.spent,
            mean_pocket
        );
    }

    let communal = run(false);
    let local = run(true);
    let need = local.rules.skin.u_min();

    println!();
    let mut bad = 0;

    let a = local.forms.iter().filter(|f| f.u >= need).count() == local.forms.len() && !local.forms.is_empty();
    println!(
        "  {} (a) with pockets the payers still take everything: {} of {}",
        if a { "ok   " } else { "WRONG" },
        local.forms.iter().filter(|f| f.u >= need).count(),
        local.forms.len()
    );
    if !a {
        bad += 1;
    }

    let b = local.forms.len() > communal.forms.len() / 2;
    println!(
        "  {} (b) the pocket supports the population on its own: {} forms vs {} communally",
        if b { "ok   " } else { "WRONG" },
        local.forms.len(),
        communal.forms.len()
    );
    if !b {
        bad += 1;
    }

    let mean_pocket = local.forms.iter().map(|f| f.pocket).sum::<f64>() / local.forms.len().max(1) as f64;
    let c = mean_pocket < 1.0;
    println!(
        "  {} (c) the pocket stays small: mean {mean_pocket:.3}",
        if c { "ok   " } else { "WRONG" }
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
