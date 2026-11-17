//! The stock the world actually has, and whether that explains the boundary of `FINDING-226`.
//!
//! `checks/shape_fill.py` assumed a constant fill fraction and got the order right and the number
//! wrong: it predicted survival at `f0 = 12`, while 12 killed every run. The missing quantity is
//! the **distribution** of `f = stock/stock_max`, not its assumed value.
//!
//! This records that distribution in worlds that live and in a world that dies, and reports:
//!
//!   * the median and 10th percentile of `f`;
//!   * the share of steps on which the medium is rich enough for **any** square to pay, i.e.
//!     `f >= f0 / 14.679`.
//!
//! PREDICTION, before the run:
//!   (a) the share of affordable steps falls sharply from `f0 = 10.5` to `f0 = 12`;
//!   (b) in the dying world (`f0 = 12`) the median `f` sits **below** the required 0.817;
//!   (c) in living worlds it sits above their requirement, so the boundary is explained by the
//!       observed stock rather than by a constant.
//!
//! If (b) fails - if the dying world's stock is high enough and it dies anyway - then the cause is
//! not the stock and something else in the cycle is responsible.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const PEAK_G: f64 = 14.679;

fn rules(f0: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(f0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(100.0, 300.0, 100.0);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = 4.0;
    r
}

fn median(xs: &mut [f64]) -> f64 {
    if xs.is_empty() {
        return f64::NAN;
    }
    xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = xs.len();
    if n % 2 == 1 {
        xs[n / 2]
    } else {
        (xs[n / 2 - 1] + xs[n / 2]) / 2.0
    }
}

fn main() {
    println!(
        "{:>5} {:>8} {:>8} {:>9} {:>12} {:>10} {:>12}",
        "f0", "needs f*", "median f", "p10 f", "affordable", "alive at end", "died at"
    );
    for f0 in [10.5, 11.0, 12.0] {
        let need = f0 / PEAK_G;
        let mut all_f = Vec::new();
        let mut affordable = 0usize;
        let mut steps = 0usize;
        let mut alive_end = 0usize;
        let mut extinctions: Vec<usize> = Vec::new();
        for seed in 1..=8u64 {
            let mut world = ShapeWorld::new(rules(f0), vec![Form::square(3)]);
            let mut rng = Rng::new(seed);
            let mut died_at: Option<usize> = None;
            for step in 0..400 {
                world.step(&mut rng);
                // Only while something is alive. After the last death the pool refills and
                // stays full, so counting those steps makes a dead world look rich: the first
                // run of this probe reported 99.8% "affordable" at f0 = 12, a world in which
                // nothing survived at all.
                if world.alive() > 0 {
                    let f = world.stock / 100.0;
                    all_f.push(f);
                    if f >= need {
                        affordable += 1;
                    }
                    steps += 1;
                } else if died_at.is_none() {
                    died_at = Some(step);
                }
            }
            if let Some(step) = died_at {
                extinctions.push(step);
            }
            if world.alive() > 0 {
                alive_end += 1;
            }
        }
        all_f.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let p10 = all_f[all_f.len() / 10];
        let med = median(&mut all_f.clone());
        let died = if extinctions.is_empty() {
            "-".to_string()
        } else {
            format!("{:.0}", extinctions.iter().sum::<usize>() as f64 / extinctions.len() as f64)
        };
        println!(
            "{f0:>5.1} {need:>8.3} {med:>8.3} {p10:>9.3} {:>11.1}% {alive_end:>9}/8 {died:>12}",
            if steps == 0 { 0.0 } else { affordable as f64 / steps as f64 * 100.0 }
        );
    }
    println!();
    println!("(a) affordable share should fall sharply with f0");
    println!("(b) at f0 = 12 the median f should sit below 0.817");
    println!("(c) living worlds should sit above their own requirement");
}
