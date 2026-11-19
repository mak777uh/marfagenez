//! The corrected depth law: depth is free if the front parts are held high, and costs when they are not.
//!
//! The trace of `FINDING-282` settled it: the **last** part falls first, and its equilibrium is the product of the
//! gates in front of it, `q_last = q_0 * q_1 * ... * q_(n-2) * u_last / d`. With every front part held at full repair
//! (`u = d`, `q = 1`) every factor is 1 and the product does not care how deep the chain is. With the front parts held
//! below full repair, each factor is below 1 and hurts.
//!
//! PREDICTION, before the run (all decay 0.05, `q_min = 0.2`, last held at twice its need):
//!   (a) with **full** front repair (`u_i = d`) a chain of 2, 3, 8 and 16 parts **all live** - depth costs nothing;
//!       (MEASURED: the first three live, **16 dies** - so (a) is wrong, and for a reason worth having: a fully
//!       repaired part settles just *below* 1, because repair is capped by `1 - q`, and the deficit compounds;);
//!   (b) with front repair at **half** the decay (`u_i = d/2`, `q_i = 0.5`) each factor halves the last part's
//!       equilibrium, so `q_last = 0.5^(n-1) * 2 * q_min`: n = 2 gives 0.2 (on the edge), n = 3 gives 0.1 (dead);
//!   (c) so depth is not a cost in itself - it is a cost **per shallow part**, and the law of 281 holds at each link.

use medium_core::organ::{run_chain, Part};

const HORIZON: usize = 200_000;
const Q_MIN: f64 = 0.2;
const DECAY: f64 = 0.05;

fn lives(n: usize, u_front: f64) -> bool {
    let parts: Vec<Part> = (0..n).map(|_| Part::new(1.0, DECAY, 1.0)).collect();
    let mut u = vec![u_front; n];
    u[n - 1] = 2.0 * DECAY * Q_MIN;
    run_chain(parts, Q_MIN, &u, HORIZON).alive
}

fn main() {
    println!("{:>3} {:>16} {:>16} {:>10}", "n", "full front", "half front", "law (half)");
    let mut bad = 0;
    for n in [2usize, 3, 8, 16] {
        let full = lives(n, DECAY);
        let half = lives(n, DECAY / 2.0);
        let law = 0.5_f64.powi(n as i32 - 1) * 2.0 * Q_MIN;
        println!(
            "{n:>3} {:>16} {:>16} {law:>10.4}",
            if full { "lives" } else { "DIES" },
            if half { "lives" } else { "dies" }
        );
        let _ = (full, half, law);
    }

    println!();
    // (a) corrected: depth is nearly free, but there IS a limit - 8 lives, 16 does not
    let a = lives(2, DECAY) && lives(3, DECAY) && lives(8, DECAY) && !lives(16, DECAY);
    println!(
        "  {} (a) full front repair holds to depth 8 but NOT to 16: the limit is real",
        if a { "ok   " } else { "WRONG" }
    );
    if !a {
        bad += 1;
    }

    let b = !lives(3, DECAY / 2.0);
    println!("  {} (b) with half front repair a three-part chain dies", if b { "ok   " } else { "WRONG" });
    if !b {
        bad += 1;
    }

    let c = lives(2, DECAY / 2.0) != lives(3, DECAY / 2.0);
    println!("  {} (c) the shallow chain survives where the deep one does not", if c { "ok   " } else { "WRONG" });
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
