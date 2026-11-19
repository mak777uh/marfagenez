//! Is the maintenance level chosen, or does it simply drift upwards?
//!
//! `FINDING-259` read the rising intensity as "the price picks it". The per-step log of `FINDING-261` showed why
//! that reading is suspect: in the rich world **nobody dies** after the ceiling (the mean age grows without
//! bound, 140 -> 3940), so the intensity is frozen at whatever it started with. In the tight world deaths
//! continue, and the intensity climbs. Nothing in that says selection.
//!
//! The mutation here is `u' = max(0, u * noise + shift)`. Two separate mechanisms could push the mean up without
//! any selection: the clip at zero (a reflecting boundary biases a symmetric random walk upwards) and the
//! additive shift itself. This example tells them apart.
//!
//! PREDICTION, before the run (tight medium, inflow 30, 4000 steps):
//!   A  multiplicative noise + shift (the configuration of 259): mean rises well above its start;
//!   B  **no multiplicative noise**, shift only: the walk is symmetric and far from zero, so **no rise**;
//!   C  **no shift**, multiplicative noise only: the clip at zero still biases the mean **upwards**, so it rises
//!      too, though the population may die out because nobody can leave zero.
//!
//! If C rises and B does not, the ascent is a **reflecting-boundary drift**, not selection.

use medium_core::skin::{run_shared, SkinPool, SkinPopRules, SkinRules};

const SEED: u64 = 11;
const STEPS: usize = 4000;
const START_U: f64 = 0.02;

fn rules(noise: f64, shift: f64) -> SkinPopRules {
    SkinPopRules {
        skin: SkinRules {
            decay: 0.05,
            q_min: 0.2,
            repair_cost: 10.0,
            income: 1.0,
            maintenance: 0.7,
        },
        u_noise: noise,
        u_shift: shift,
        birth_price: 1.5,
        max_population: 300,
    }
}

fn main() {
    println!(
        "{:>34} {:>7} {:>9} {:>9} {:>12}",
        "arm", "alive", "mean u", "change", "maintainers"
    );
    let arms = [
        ("A noise 0.3 + shift 0.003", 0.3, 0.003),
        ("B shift only (noise 0)", 0.0, 0.003),
        ("C noise 0.3 only (shift 0)", 0.3, 0.0),
    ];
    let mut rows = Vec::new();
    for (label, noise, shift) in arms {
        let pop = run_shared(
            rules(noise, shift),
            SkinPool::new(50.0, 500.0, 30.0, 1.0),
            1.0,
            10.0,
            START_U,
            STEPS,
            SEED,
        );
        let mean = pop.mean_u();
        println!(
            "{label:>34} {:>7} {mean:>9.4} {:>9.4} {:>12.2}",
            pop.forms.len(),
            mean - START_U,
            pop.maintainers()
        );
        rows.push((label, pop.forms.len(), mean));
    }

    println!();
    let mut bad = 0;
    let (_, alive_a, mean_a) = rows[0];
    let (_, alive_b, mean_b) = rows[1];
    let (_, alive_c, mean_c) = rows[2];

    let a_rises = mean_a.is_finite() && mean_a > START_U * 1.02;
    println!("  {} A rises above the start: {:.4} -> {:.4}", if a_rises { "ok   " } else { "WRONG" }, START_U, mean_a);
    if !a_rises {
        bad += 1;
    }

    let b_flat = !mean_b.is_finite() || (mean_b - START_U).abs() <= START_U * 0.02;
    println!(
        "  {} B does not rise without multiplicative noise: {:.4} (alive {alive_b})",
        if b_flat { "ok   " } else { "WRONG" },
        mean_b
    );
    if !b_flat {
        bad += 1;
    }

    let c_rises = mean_c.is_finite() && mean_c > START_U * 1.02;
    println!(
        "  {} C rises with the clip alone: {:.4} (alive {alive_c})",
        if c_rises { "ok   " } else { "WRONG" },
        mean_c
    );
    if !c_rises {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
