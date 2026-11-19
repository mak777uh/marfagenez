//! Four arms of the division threshold, printed as JSON for `checks/exp_division_threshold.py`.
//!
//! `FINDING-290` and `FINDING-292` measured the threshold by hand. This binary prints the same arms with a hash of the
//! dynamics so the experiment can be recorded through the contract in `AGENTS.md` §1–§6.

use medium_core::organ::{Flow, Part};

const Q_MIN: f64 = 0.2;
const D: f64 = 0.05;
const HORIZON: usize = 200_000;

/// A cheap hash over the trajectory, so two arms that move identically hash equally.
fn hash_of(samples: &[f64]) -> String {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for v in samples {
        let bits = v.to_bits();
        h ^= bits;
        h = h.wrapping_mul(0x100_0000_01b3);
    }
    format!("{h:016x}")
}

fn run(yield_rate: f64, support: f64, stock_max: f64) -> (bool, usize, f64, f64, String) {
    let mut f = Flow::new(Part::new(1.0, D, 1.0), Part::new(1.0, D, 1.0), Q_MIN, 10.0);
    f.yield_rate = yield_rate;
    f.support = support;
    f.stock_max = stock_max;
    let mut samples = Vec::with_capacity(256);
    let mut steps = 0;
    for step in 1..=HORIZON {
        let alive = f.step();
        if step % 1000 == 0 {
            samples.push(f.a.q);
            samples.push(f.b.q);
        }
        steps = step;
        if !alive {
            break;
        }
    }
    (f.alive, steps, f.a.q, f.b.q, hash_of(&samples))
}

fn main() {
    let arms = [
        ("A", "yield=1.0", 1.0, 0.0, 1_000.0),
        ("B", "yield=1.5", 1.5, 0.0, 1_000.0),
        ("C", "yield=2.0", 2.0, 0.0, 1_000.0),
        ("D", "yield=3.0", 3.0, 0.0, 1_000.0),
        ("E", "yield=1.5, stock_max=100000", 1.5, 0.0, 100_000.0),
    ];
    for (key, label, y, support, stock_max) in arms {
        let (alive, steps, qa, qb, hash) = run(y, support, stock_max);
        println!(
            "{{\"arm\":\"{key}\",\"label\":\"{label}\",\"alive\":{alive},\"steps\":{steps},\"q_a\":{qa:.6},\"q_b\":{qb:.6},\"hash\":\"{hash}\"}}"
        );
    }
}
