//! Does a lineage hold its shape? A mutation chain with no selection at all.
//!
//! `STRUCTURES-LINE-CLOSED.md` said the model lacks inheritance of organisation. That is **wrong**:
//! `shape_world` births a `mutate`d copy of the parent, so morphology is inherited. What was open is
//! whether a lineage keeps anything: `FINDING-221` found the mutation has no stable size between
//! 0.18 and 0.28, but that was measured on populations, not on lineages.
//!
//! This walks pure lineages - one form, mutated a hundred times, no birth, no death, no economy.
//!
//! PREDICTION, before the run:
//!   (a) `x` drifts away from its starting value: the median over two hundred lineages after a hundred
//!       mutations is not the start value;
//!   (b) the spread grows with the number of mutations - a lineage does not settle;
//!   (c) some lineages erode to a single cell and some grow past the solvency limit `x_limit`, so a
//!       lineage is not a unit that selection could accumulate.

use medium_core::form::Form;
use medium_core::Rng;

const LINEAGES: u64 = 200;
const GENERATIONS: usize = 100;
const P_GROW: f64 = 0.27;

fn spread(v: &[f64]) -> (f64, f64, f64) {
    let mut s = v.to_vec();
    s.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let q = |p: f64| s[((s.len() - 1) as f64 * p) as usize];
    (q(0.5), q(0.25), q(0.75))
}

fn main() {
    let start = Form::square(2);
    println!("start: x = {:.3}, cells = {}", start.x(), start.cells());
    println!(
        "{:>6} {:>8} {:>8} {:>8} {:>10} {:>10}",
        "gen", "median x", "q25", "q75", "min cells", "max cells"
    );

    let mut lineages: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
    let mut rng = Rng::new(20250101);
    let mut snaps = Vec::new();
    for gen in 0..=GENERATIONS {
        if gen % 20 == 0 || gen == GENERATIONS {
            let xs: Vec<f64> = lineages.iter().map(|f| f.x()).collect();
            let (med, q1, q3) = spread(&xs);
            let cells: Vec<usize> = lineages.iter().map(|f| f.cells()).collect();
            println!(
                "{gen:>6} {med:>8.3} {q1:>8.3} {q3:>8.3} {:>10} {:>10}",
                cells.iter().min().unwrap(),
                cells.iter().max().unwrap()
            );
            snaps.push((gen, med, q3 - q1, *cells.iter().max().unwrap()));
        }
        for f in lineages.iter_mut() {
            // `mutate` returns None when the mutation would leave the form empty: that is a lineage
            // dying out, and it is a result, not an error - so the lineage is dropped.
            if let Some(next) = f.mutate(&mut rng, P_GROW) {
                *f = next;
            }
        }
    }

    println!();
    let mut bad = 0;
    let start_x = start.x();
    let (_, med_end, iqr_end, max_cells) = snaps[snaps.len() - 1];
    let (_, med_early, iqr_early, _) = snaps[1];

    let drift = (med_end - start_x).abs() > 0.05;
    println!(
        "  {} (a) the median drifted from the start: {start_x:.3} -> {med_end:.3}",
        if drift { "ok   " } else { "WRONG" }
    );
    if !drift {
        bad += 1;
    }

    let widened = iqr_end > iqr_early;
    println!(
        "  {} (b) the spread grew with generations: {iqr_early:.3} -> {iqr_end:.3}",
        if widened { "ok   " } else { "WRONG" }
    );
    if !widened {
        bad += 1;
    }

    let exploded = max_cells > 20;
    println!(
        "  {} (c) some lineages grew far past the start (max {max_cells} cells)",
        if exploded { "ok   " } else { "WRONG" }
    );
    if !exploded {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
