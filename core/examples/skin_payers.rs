//! Payers against non-payers on a closed cycle: does keeping yourself whole pay, or is it a handicap?
//!
//! `FINDING-269` showed that a population survives a closed cycle because the dead return their matter. That makes
//! a sharp question possible. Inside a closed cycle a **non-payer** (`u = 0`) dies in 32 steps but returns its body
//! whole, while a **payer** (`u = u_min`) spends matter to stay alive and therefore **holds matter out of the
//! cycle**. If the cycle is the only source, holding matter may be a handicap.
//!
//! Mutation is switched off here (`u_noise = 0`, `u_shift = 0`) so the two classes stay distinct: this measures
//! competition between the two strategies, not drift.
//!
//! PREDICTION, before the run (closed cycle, `c = 1`, no inflow, 4000 steps, 50 payers and 50 non-payers):
//!   (a) the **non-payers win**: their share of the population rises towards one, because they return their whole
//!       body to the cycle and never hold matter back;
//!   (b) but the population keeps **both** for a while - a non-payer cannot breed before it is old enough, so
//!       there is a transient in which payers are still there;
//!   (c) the total population stays at its ceiling: matter is conserved either way, only the ownership changes.

use medium_core::skin::{SkinCycle, SkinForm, SkinPopRules, SkinRecycle, SkinRules};

const STEPS: usize = 4000;
const SEED: u64 = 5;
const PAYERS: usize = 50;
const NON_PAYERS: usize = 50;

fn rules(cap: usize) -> SkinPopRules {
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
        max_population: cap,
        demand_growth: None,
        repair_from_pool: false,
        local_recycle: false,
        local_share: 1.0,
        pocket_max: None,
    }
}

fn main() {
    for cap in [400usize, 5000] {
        run(cap);
        println!();
    }
    verdict();
}

fn run(cap: usize) {
    let r = rules(cap);
    let need = r.skin.u_min();
    let cycle = SkinCycle::new(200.0, 0.0, 2000.0, 100_000.0, 0.0, 1.0);
    let mut pop = SkinRecycle::new(r, cycle, 1.0, 10.0, need);

    // the two classes, side by side
    pop.forms.clear();
    for _ in 0..PAYERS {
        pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: need, age: 0, pocket: 0.0 });
    }
    for _ in 0..NON_PAYERS {
        pop.forms.push(SkinForm { q: 1.0, energy: 10.0, u: 0.0, age: 0, pocket: 0.0 });
    }

    println!("{:>6} {:>7} {:>8} {:>9} {:>8} {:>10}", "step", "alive", "payers", "share", "ready", "spent");
    let mut rng = medium_core::Rng::new(SEED);
    let mut rows = Vec::new();
    for step in 1..=STEPS {
        pop.step(&mut rng);
        if step % 500 == 0 {
            let payers = pop.forms.iter().filter(|f| f.u >= need).count();
            let alive = pop.forms.len();
            let share = payers as f64 / alive.max(1) as f64;
            println!(
                "{step:>6} {alive:>7} {payers:>8} {share:>9.2} {:>8.1} {:>10.1}",
                pop.cycle.ready, pop.cycle.spent
            );
            rows.push((step, alive, payers, share));
        }
    }

    println!();
    let first = rows[0];
    let last = rows[rows.len() - 1];

    println!(
        "cap {cap}: payer share {:.2} -> {:.2}, alive {}",
        first.3, last.3, last.1
    );
}

fn verdict() {
    println!("сравнение двух потолков — в выводе выше.");
}
