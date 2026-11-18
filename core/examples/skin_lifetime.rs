//! The numbers behind the skin, measured rather than asserted.
//!
//! `DESIGN-skin.md` recorded four predictions before the module existed; the unit tests in `skin.rs` check
//! them in the small. This prints the same quantities as a table, across a sweep, so the finding can quote
//! them.
//!
//! PREDICTION (from the design, before the run):
//!   P1  without repair the lifetime is `ln(q_min)/ln(1-decay)` = 31 whole steps, 32 in total, at every seed;
//!   P2  at `u = decay*q_min = 0.01` the form holds forever and `q` settles at `u/decay = 0.4`;
//!   P3  below the threshold the lifetime is finite and grows as `1/(decay*q_min - u)`;
//!   P4  the maintenance boundary moves by `repair_cost*decay*q_min = 0.1`.

use medium_core::skin::{run, SkinRules};

const HORIZON: usize = 200_000;
const Q0: f64 = 1.0;
const ENERGY0: f64 = 10.0;

fn rules() -> SkinRules {
    SkinRules {
        decay: 0.05,
        q_min: 0.2,
        repair_cost: 10.0,
        income: 1.0,
        maintenance: 0.6,
    }
}

fn main() {
    let r = rules();
    println!("u_min = {:.4}, skin cost per step = {:.4}", r.u_min(), r.skin_cost());

    println!("\nP1  no repair, three seeds of nothing: the arithmetic decides");
    for seed in 0..3 {
        let s = run(r, Q0, ENERGY0, 0.0, HORIZON);
        println!("  seed {seed}: lived {:>3} steps, q = {:.4}, predicted {}", s.steps, s.q, r.bare_lifetime(Q0) + 1);
    }

    println!("\nP2  at the threshold and above");
    for u in [0.010, 0.015, 0.020] {
        let s = run(r, Q0, ENERGY0, u, HORIZON);
        println!(
            "  u = {u:.3}: alive {:<5} q = {:.4} (q* = {:.3}), repaired {:.1}",
            s.alive,
            s.q,
            r.steady_integrity(u),
            s.repaired
        );
    }

    println!("\nP3  below the threshold: the closer to it, the longer");
    for u in [0.000, 0.005, 0.008, 0.009, 0.0095] {
        let s = run(r, Q0, ENERGY0, u, HORIZON);
        let gap = r.u_min() - u;
        let predicted = if gap > 0.0 { (1.0 / gap).round() as usize } else { 0 };
        println!(
            "  u = {u:.4}: lived {:>7} steps, gap {gap:.4}, 1/gap ≈ {predicted}",
            s.steps
        );
    }

    println!("\nP4  the maintenance boundary moves by the skin cost");
    for maintenance in [0.70, 0.80, 0.85, 0.90, 0.95] {
        let mut m = r;
        m.maintenance = maintenance;
        let surplus = m.income - maintenance;
        let s = run(m, Q0, ENERGY0, m.u_min(), HORIZON);
        println!(
            "  maintenance {maintenance:.2}: surplus {surplus:.2} vs skin {:.2} -> alive {:<5} steps {:>7}",
            m.skin_cost(),
            s.alive,
            s.steps
        );
    }
}
