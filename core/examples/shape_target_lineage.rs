//! Does a heritable target give the mutation a restoring force?
//!
//! `DESIGN-heredity.md` predicted, before any code: with `restore = 0` the lineage behaves exactly as in
//! `FINDING-247` (drift, spread, erosion to one cell, explosion to twenty-two); with `restore = 0.5` the
//! median stays within 0.02 of the start, the interquartile range falls below 0.10, and no lineage
//! reaches one cell or passes fifteen; with `restore = 1.0` the size does not move at all.
//!
//! The target here is fixed per lineage at the starting size, which isolates the restoring force from
//! the inheritance of the target itself.

use medium_core::form::Form;
use medium_core::Rng;

const LINEAGES: usize = 200;
const GENERATIONS: usize = 100;
const P_GROW: f64 = 0.27;

fn walk(restore: f64) -> (f64, f64, f64, usize, usize, f64) {
    let start = Form::square(2);
    let target = start.x();
    let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
    let mut rng = Rng::new(20250101);
    for _ in 0..GENERATIONS {
        for f in forms.iter_mut() {
            if let Some(next) = f.mutate_towards(&mut rng, P_GROW, Some(target), restore) {
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
        target,
        *cells.iter().min().unwrap(),
        *cells.iter().max().unwrap(),
        xs[0],
    )
}

fn main() {
    println!(
        "{:>9} {:>10} {:>8} {:>6} {:>6} {:>10}",
        "restore", "median x", "IQR", "min n", "max n", "start x"
    );
    let mut rows = Vec::new();
    for restore in [0.0, 0.5, 1.0] {
        let (med, iqr, target, min_n, max_n, _) = walk(restore);
        println!("{restore:>9.1} {med:>10.3} {iqr:>8.3} {min_n:>6} {max_n:>6} {target:>10.3}");
        rows.push((restore, med, iqr, min_n, max_n, target));
    }

    println!();
    let mut bad = 0;
    let at = |r: f64| rows.iter().find(|x| x.0 == r).copied().expect("row");
    let (_, med0, iqr0, min0, max0, target) = at(0.0);
    let (_, med5, iqr5, min5, max5, _) = at(0.5);
    let (_, _, iqr10, _, _, _) = at(1.0);

    let checks = [
        (
            format!("P1 restore 0 drifts and spreads: |{med0:.3} - {target:.3}| = {:.3}, IQR {iqr0:.3}", (med0 - target).abs()),
            (med0 - target).abs() >= 0.05 && iqr0 > 0.10,
        ),
        (
            format!("P2 at 0.5 the median holds: |{med5:.3} - {target:.3}| = {:.3}", (med5 - target).abs()),
            (med5 - target).abs() <= 0.02,
        ),
        (format!("P3 at 0.5 the IQR is below 0.10: {iqr5:.3}"), iqr5 < 0.10),
        (
            format!("P4 at 0.5 no lineage reaches 1 or passes 15: {min5}..{max5}"),
            min5 > 1 && max5 <= 15,
        ),
        (
            format!("P5 at 1.0 the size does not move: IQR {iqr10:.3}"),
            iqr10 < 0.02,
        ),
    ];
    for (label, ok) in checks {
        println!("  {} {label}", if ok { "ok   " } else { "WRONG" });
        if !ok {
            bad += 1;
        }
    }
    println!();
    println!("(control at restore 0 must reproduce FINDING-247: cells {min0}..{max0})");

    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
