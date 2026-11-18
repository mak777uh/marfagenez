//! The two refinements `FINDING-248` proposed, tested against each other.
//!
//! The constant shift cut the drift three times but left the tails alone, because a probability is not a
//! prohibition. Two changes are on the table: a **floor** that refuses shrinkage at the minimum size, and
//! a **force proportional to the error** rather than a constant shift.
//!
//! PREDICTION, before the run (`restore = 0.5`, target = 0.5, 200 lineages, 100 mutations):
//!   A. plain constant shift: median about 0.455, IQR about 0.071, cells 1..21 (this is 248, as control);
//!   B. with the floor `n >= 2`: no lineage reaches one cell; the median and the IQR are **unchanged**,
//!      because the floor only touches the extreme;
//!   C. with a distance-scaled force: the median returns within 0.02 of 0.5 and the upper tail is gone;
//!   D. both together: the tightest of the four.

use medium_core::form::Form;
use medium_core::Rng;

const LINEAGES: usize = 200;
const GENERATIONS: usize = 100;
const P_GROW: f64 = 0.27;

fn walk(restore: f64, min_cells: usize, distance_scaled: bool) -> (f64, f64, usize, usize, f64) {
    let start = Form::square(2);
    let target = start.x();
    let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
    let mut rng = Rng::new(20250101);
    for _ in 0..GENERATIONS {
        for f in forms.iter_mut() {
            if let Some(next) =
                f.mutate_towards_with(&mut rng, P_GROW, Some(target), restore, min_cells, distance_scaled)
            {
                *f = next;
            }
        }
    }
    let mut xs: Vec<f64> = forms.iter().map(|f| f.x()).collect();
    xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = xs.len();
    let cells: Vec<usize> = forms.iter().map(|f| f.cells()).collect();
    (
        xs[n / 2],
        xs[n * 3 / 4] - xs[n / 4],
        *cells.iter().min().unwrap(),
        *cells.iter().max().unwrap(),
        target,
    )
}

fn main() {
    println!(
        "{:>2} {:>24} {:>10} {:>8} {:>12}",
        "#", "variant", "median x", "IQR", "cells"
    );
    let configs = [
        ("A plain shift", 0.5, 1usize, false),
        ("B floor n>=2", 0.5, 2, false),
        ("C distance force", 0.5, 1, true),
        ("D floor + distance", 0.5, 2, true),
    ];
    let mut rows = Vec::new();
    for (i, (name, r, min_cells, dist)) in configs.iter().enumerate() {
        let (med, iqr, min_n, max_n, target) = walk(*r, *min_cells, *dist);
        println!("{:>2} {name:>24} {med:>10.3} {iqr:>8.3} {min_n:>5}..{max_n:<6}", i + 1);
        rows.push((name.to_string(), med, iqr, min_n, max_n, target));
    }

    println!();
    let mut bad = 0;
    let a = &rows[0];
    let b = &rows[1];
    let c = &rows[2];
    let d = &rows[3];

    let checks: Vec<(String, bool)> = vec![
        (
            format!("A control matches 248: median {:.3}, IQR {:.3}, cells {}..{}", a.1, a.2, a.3, a.4),
            (a.1 - 0.455).abs() < 0.02 && a.3 == 1 && a.4 >= 15,
        ),
        (
            format!("B the floor removes the lower tail: min {} cells", b.3),
            b.3 >= 2,
        ),
        (
            format!("B leaves the body alone: median {:.3} (A {:.3}), IQR {:.3} (A {:.3})", b.1, a.1, b.2, a.2),
            (b.1 - a.1).abs() < 0.02 && (b.2 - a.2).abs() < 0.02,
        ),
        (
            format!("C the distance force holds the median: {:.3} vs target {:.3}", c.1, c.5),
            (c.1 - c.5).abs() <= 0.02,
        ),
        (
            format!("C removes the upper tail: max {} cells", c.4),
            c.4 <= 15,
        ),
        (
            format!("D is the tightest: IQR {:.3} (A {:.3}, B {:.3}, C {:.3})", d.2, a.2, b.2, c.2),
            d.2 <= a.2 && d.2 <= b.2 && d.2 <= c.2,
        ),
    ];
    for (label, ok) in checks {
        println!("  {} {label}", if ok { "ok   " } else { "WRONG" });
        if !ok {
            bad += 1;
        }
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
