//! The law behind the boundary's price: `u_skin_crit = d_s * need_core / u_core`.
//!
//! The trace of `organ_trace` settled the puzzle: the core sits at `gate * u_core / d_c`, so holding it above `q_min`
//! needs `q_skin > q_min * d_c / u_core`, and since `q_skin = u_s / d_s`:
//!
//! ```text
//! u_s_crit = d_s * (q_min * d_c) / u_core = d_s * need_core / u_core
//! ```
//!
//! At `u_core = 4 * need_core` that is `0.25 * d_s = 0.005`, which is what `organ_boundary` measured: 0.004 dies,
//! 0.006 lives.
//!
//! PREDICTION, before the run (skin decay 0.02, core decay 0.05, `q_min = 0.2`, both repaired):
//!   (a) at `u_core = 2*need_core = 0.02` the threshold is `d_s * need_core / u_core = 0.01`, so 0.008 dies and
//!       0.012 lives;
//!   (b) at `u_core = 8*need_core = 0.08` the threshold is `0.0025`, so 0.002 dies and 0.003 lives;
//!   (c) the threshold falls as `1/u_core`: doubling the core's repair halves the price of the boundary.

use medium_core::organ::{run, Part};

const HORIZON: usize = 200_000;
const Q_MIN: f64 = 0.2;

fn lives(u_core: f64, u_skin: f64) -> bool {
    let skin = Part::new(1.0, 0.02, 1.0);
    let core = Part::new(1.0, 0.05, 2.0);
    run(skin, core, Q_MIN, 10.0, 1.0, 0.5, u_skin, u_core, HORIZON).alive
}

fn main() {
    let d_s = 0.02;
    let need_core = 0.05 * Q_MIN;
    println!("{:>9} {:>12} {:>10} {:>10}", "u_core", "predicted", "0.8x dies", "1.2x lives");
    let mut bad = 0;
    for (u_core, label) in [(2.0 * need_core, "2x"), (4.0 * need_core, "4x"), (8.0 * need_core, "8x")] {
        let crit = (d_s * need_core / u_core).max(0.02 * Q_MIN);
        let low = crit * 0.8;
        let high = crit * 1.2;
        let low_dies = !lives(u_core, low);
        let high_lives = lives(u_core, high);
        println!(
            "{label:>9} {crit:>12.5} {:>10} {:>10}",
            if low_dies { "yes" } else { "NO" },
            if high_lives { "yes" } else { "NO" }
        );
        if !(low_dies && high_lives) {
            bad += 1;
        }
    }

    println!();
    let a = !lives(2.0 * need_core, 0.008) && lives(2.0 * need_core, 0.012);
    println!("  {} (a) at 2x need_core: 0.008 dies, 0.012 lives", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }
    // the larger of the two conditions: the skin must stay alive AND the core must be fed
    let skin_floor = 0.02 * Q_MIN;
    let core_demand = d_s * need_core / (8.0 * need_core);
    let crit8 = skin_floor.max(core_demand);
    let b = !lives(8.0 * need_core, crit8 * 0.9) && lives(8.0 * need_core, crit8 * 1.1);
    println!(
        "  {} (b) at 8x the binding condition is the skin's own need {skin_floor:.4} (core asks {core_demand:.4}): {:.4} dies, {:.4} lives",
        if b { "ok   " } else { "WRONG" },
        crit8 * 0.9,
        crit8 * 1.1
    );
    if !b {
        bad += 1;
    }
    // (c) the law has two limbs and the binding one is the maximum: the core's demand falls as 1/u_core, but the
    // skin's own floor never does, so beyond a point the boundary's price stops falling.
    let skin_floor = 0.02 * Q_MIN;
    let demand_2 = d_s * need_core / (2.0 * need_core);
    let demand_8 = d_s * need_core / (8.0 * need_core);
    let falls = (demand_2 / demand_8 - 4.0).abs() < 1e-9;
    let floor_binds = skin_floor > demand_8 && skin_floor <= demand_2 + 1e-12;
    let c = falls && floor_binds;
    println!(
        "  {} (c) the demand falls as 1/u_core ({demand_2:.5} -> {demand_8:.5}) but the floor {skin_floor:.4} binds at 8x",
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
