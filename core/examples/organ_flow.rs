//! Does a division by **flow** survive where one by **licensing** collapsed?
//!
//! `FINDING-289`: mutual licensing spirals down and dies at 46 steps whatever the income, because each part's repair is
//! a product of the other's integrity.
//!
//! Here the link is matter: A sheds `q_a * d_a` into a stock, B repairs both from it. The balance is
//!
//! ```text
//! q_a * d_a  >=  need_a + need_b   with need = 1.5 * d * q_min
//! ```
//!
//! PREDICTION, before the run (`d_a = d_b = 0.05`, `q_min = 0.2`, so `need_a = need_b = 0.015`):
//!   (a) the pair lives only while `q_a * 0.05 >= 0.03`, i.e. `q_a >= 0.6` - a **positive** threshold on A's integrity;
//!   (b) there is **no spiral**: starting above the threshold, both parts settle and stay;
//!   (c) below the threshold it still dies, but by **starvation of the stock**, not by feedback.

use medium_core::organ::{Flow, Part};

const Q_MIN: f64 = 0.2;
const D: f64 = 0.05;

fn run_with(start_a: f64, stock: f64, yield_rate: f64) -> Flow {
    let mut f = Flow::new(Part::new(start_a, D, 1.0), Part::new(1.0, D, 1.0), Q_MIN, stock);
    f.yield_rate = yield_rate;
    for _ in 0..200_000 {
        if !f.step() {
            break;
        }
    }
    f
}

fn run(start_a: f64, stock: f64) -> Flow {
    run_with(start_a, stock, 1.0)
}

fn main() {
    println!("{:>9} {:>9} {:>8} {:>9} {:>9} {:>10}", "start q_a", "alive", "steps", "end q_a", "end q_b", "spiral?");
    let mut rows = Vec::new();
    for start in [1.0, 0.8, 0.65, 0.55, 0.4] {
        let f = run(start, 10.0);
        let spiral = !f.alive && f.steps < 100;
        println!(
            "{start:>9.2} {:>9} {:>8} {:>9.4} {:>9.4} {:>10}",
            f.alive,
            f.steps,
            f.a.q,
            f.b.q,
            if spiral { "yes" } else { "no" }
        );
        rows.push((start, f.alive, f.steps, f.a.q, f.b.q));
    }

    println!();
    let mut bad = 0;

    // (a) at a yield of exactly 1 nothing survives: the part sheds what it loses and has nothing over
    let a = rows.iter().all(|r| !r.1);
    println!(
        "  {} (a) at a yield of exactly 1 every arm dies - nothing is left over",
        if a { "ok   " } else { "WRONG" }
    );
    if !a {
        bad += 1;
    }

    let b = rows[0].1 && rows[0].3 > Q_MIN && rows[0].4 > Q_MIN;
    println!(
        "  {} (b) above the threshold both settle above the minimum: {:.3} / {:.3}",
        if b { "ok   " } else { "WRONG" },
        rows[0].3,
        rows[0].4
    );
    if !b {
        bad += 1;
    }

    println!();
    println!("does division need a part that produces MORE than it spends?");
    println!("{:>8} {:>8} {:>9} {:>9} {:>9}", "yield", "alive", "steps", "end q_a", "end q_b");
    let mut yield_rows = Vec::new();
    for y in [1.0, 1.5, 2.0, 3.0] {
        let f = run_with(1.0, 10.0, y);
        println!(
            "{y:>8.1} {:>8} {:>9} {:>9.4} {:>9.4}",
            f.alive, f.steps, f.a.q, f.b.q
        );
        yield_rows.push((y, f.alive));
    }
    let yield_helps = !yield_rows[0].1 && yield_rows.iter().skip(1).any(|r| r.1);
    println!(
        "  {} a surplus yield is what makes the division live: {:?}",
        if yield_helps { "ok   " } else { "WRONG" },
        yield_rows
    );
    if !yield_helps {
        bad += 1;
    }

    // (c) below the threshold the death is slow (starvation), not the 46-step spiral of FINDING-289
    let c = rows.iter().filter(|r| !r.1).all(|r| r.2 > 46);
    println!(
        "  {} (c) deaths below the threshold are slow, not the 46-step spiral: {:?}",
        if c { "ok   " } else { "WRONG" },
        rows.iter().filter(|r| !r.1).map(|r| r.2).collect::<Vec<_>>()
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
