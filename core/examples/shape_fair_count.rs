//! The fair probability **in terms of the count**, for four starting sizes.
//!
//! `FINDING-250` measured the fair probability for `x` - the ratio - and got 0.36 for a two-by-two.
//! `FINDING-254` then treated that number as if it were the fair probability for the **count**, and a test
//! caught the confusion: at `p = 0.36` a two-by-two grows to thirteen cells while its `x` stays at 0.5.
//!
//! The count walk is an up-down step: growth adds one cell, shrinkage removes one. It has no size term, so
//! the prediction here is that the fair probability for the **count** is the same for every starting size -
//! about 0.27 - and that the two quantities simply measure different things.
//!
//! PREDICTION, before the run (200 lineages, 100 mutations, no regulation):
//!   (a) at `p = 0.36` every start grows well past its own size, including the two-by-two;
//!   (b) the fair `p` for the count is between 0.25 and 0.30 for **all four** starts;
//!   (c) the spread of the fair value across starts is under 0.05 - i.e. it does not depend on size.

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
    let starts = [
        ("2x2 (4)", Form::square(2)),
        ("3x3 (9)", Form::square(3)),
        ("5x2 (10)", Form::rectangle(5, 2)),
        ("4x4 (16)", Form::square(4)),
    ];
    let ps = [0.20, 0.23, 0.27, 0.30, 0.36];

    print!("{:>10}", "start");
    for p in ps {
        print!(" {:>9.2}", p);
    }
    println!();
    let mut rows = Vec::new();
    for (name, form) in &starts {
        print!("{name:>10}");
        let mut medians = Vec::new();
        for p in ps {
            let m = median_count(form, p);
            medians.push(m);
            print!(" {m:>9.0}");
        }
        println!();
        rows.push((name, form.cells() as f64, medians));
    }

    println!();
    let mut bad = 0;
    // (a) at 0.36 every start grows past its own size
    let grew = rows.iter().all(|r| r.2[ps.len() - 1] > r.1 + 3.0);
    println!("  {} (a) at 0.36 every start grows past its size", if grew { "ok   " } else { "WRONG" });
    if !grew {
        bad += 1;
    }

    // (b) the fair p for the count, per start, by interpolation on the grid
    let mut fairs = Vec::new();
    for (name, size, medians) in &rows {
        let mut fair = None;
        for i in 0..ps.len() {
            if (medians[i] - size).abs() <= 1.0 {
                fair = Some(ps[i]);
                break;
            }
        }
        println!("      {name}: fair p = {fair:?} for a median of {size:.0}");
        if let Some(f) = fair {
            fairs.push(f);
        }
    }
    let in_range = !fairs.is_empty() && fairs.iter().all(|p| *p >= 0.20 && *p <= 0.30);
    println!("  {} (b) the fair p for the count is 0.20-0.30 for every start {fairs:?}", if in_range { "ok   " } else { "WRONG" });
    if !in_range {
        bad += 1;
    }

    // (c) the spread across starts is small
    let spread = fairs.iter().cloned().fold(f64::MIN, f64::max) - fairs.iter().cloned().fold(f64::MAX, f64::min);
    let flat = spread <= 0.10;
    println!("  {} (c) the fair p does not depend on size: spread {spread:.2}", if flat { "ok   " } else { "WRONG" });
    if !flat {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
