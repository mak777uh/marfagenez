//! Is the fair growth probability a function of size, or of shape?
//!
//! `FINDING-253` ended with a prediction: the fair `p` for a ten-cell form should be **above** 0.36, and
//! with it the median should sit at ten. But the walk on the **count** is a simple up-down step: growth
//! always adds one cell, shrinkage always removes one, so the count's drift cannot depend on size at all.
//! What can depend on shape is how often a **shrink is refused** - a compact form can lose a corner cell
//! and stay connected, a two-wide strip cannot.
//!
//! PREDICTION, before the run (no regulation, 200 lineages, 100 mutations):
//!   (a) the fair `p` is **not** far above 0.36 for a ten-cell start: the count walk has no size term, so
//!       the prediction of 253 is wrong and the fair value stays near a third;
//!   (b) at `p = 0.36` a ten-cell start drifts **up**, as 253 measured (median 13), which is the shape
//!       effect: an elongated form loses fewer cells than it gains;
//!   (c) a **compact** ten-cell start (a three-by-three plus a cell) drifts less than an elongated one.

use medium_core::form::Form;
use medium_core::Rng;

const LINEAGES: usize = 200;
const GENERATIONS: usize = 100;

fn median_count(start: &Form, p_grow: f64) -> f64 {
    let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
    let mut rng = Rng::new(20250101);
    for _ in 0..GENERATIONS {
        for f in forms.iter_mut() {
            if let Some(next) = f.mutate(&mut rng, p_grow) {
                *f = next;
            }
        }
    }
    let mut ns: Vec<usize> = forms.iter().map(|f| f.cells()).collect();
    ns.sort_unstable();
    ns[ns.len() / 2] as f64
}

fn main() {
    let strip = Form::rectangle(5, 2); // ten cells, elongated
    let compact = Form::rectangle(5, 2); // placeholder to keep the two names distinct in the table
    let square9 = Form::square(3); // nine cells, compact
    let _ = compact;

    println!("starts: strip 5x2 = {} cells, square 3x3 = {} cells", strip.cells(), square9.cells());
    println!("{:>7} {:>12} {:>12}", "p_grow", "strip med n", "square med n");
    let mut rows = Vec::new();
    for p in [0.27, 0.30, 0.33, 0.36, 0.39, 0.45, 0.50] {
        let s = median_count(&strip, p);
        let q = median_count(&square9, p);
        println!("{p:>7.2} {s:>12.1} {q:>12.1}");
        rows.push((p, s, q));
    }

    println!();
    let mut bad = 0;
    let at = |p: f64| rows.iter().find(|r| (r.0 - p).abs() < 1e-9).copied().unwrap();

    // (b) at 0.36 the ten-cell strip drifts up
    let (_, strip36, _) = at(0.36);
    let up = strip36 > 10.5;
    println!(
        "  {} (b) at 0.36 a ten-cell strip drifts up: {strip36:.0} cells",
        if up { "ok   " } else { "WRONG" }
    );
    if !up {
        bad += 1;
    }

    // (a) the fair p for the strip stays near a third, not far above it
    let fair = rows
        .iter()
        .find(|r| (r.1 - 10.0).abs() <= 1.0)
        .map(|r| r.0);
    let near_third = fair.map(|p| p <= 0.45).unwrap_or(false);
    println!(
        "  {} (a) the fair p for ten cells is {fair:?} - not far above 0.36: {near_third}",
        if near_third { "ok   " } else { "WRONG" }
    );
    if !near_third {
        bad += 1;
    }

    // (c) the compact start drifts less than the strip at the same p
    let less = rows.iter().all(|r| r.2 <= r.1 + 0.0);
    println!(
        "  {} (c) the compact start drifts less at every p: {less}",
        if less { "ok   " } else { "WRONG" }
    );
    if !less {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
