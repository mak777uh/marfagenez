//! The lineage result of `FINDING-247`, under test.
//!
//! Morphology is inherited - a child is a mutated copy of the parent - but a lineage does not keep its
//! shape. Two hundred lineages, a hundred mutations each, no selection at all: the median `x` drifts away
//! from the start, the spread widens, and lineages end between one cell and more than twenty. That last
//! part is what makes heredity a drift rather than a unit selection could accumulate, so it is worth a
//! test of its own.

use medium_core::form::Form;
use medium_core::Rng;

const LINEAGES: usize = 200;
const GENERATIONS: usize = 100;
const P_GROW: f64 = 0.27;

fn walk() -> (f64, f64, f64, usize, usize) {
    let start = Form::square(2);
    let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
    let mut rng = Rng::new(20250101);
    for _ in 0..GENERATIONS {
        for f in forms.iter_mut() {
            // `None` means the mutation would have left the form empty. The example keeps the form
            // unchanged in that case, and this test must mirror it exactly - replacing it with a
            // one-cell shape changes the spread (0.083 instead of 0.194) and would have hidden the
            // result rather than checked it.
            if let Some(next) = f.mutate(&mut rng, P_GROW) {
                *f = next;
            }
        }
    }
    let mut xs: Vec<f64> = forms.iter().map(|f| f.x()).collect();
    xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = xs.len();
    let med = xs[n / 2];
    let iqr = xs[n * 3 / 4] - xs[n / 4];
    let cells: Vec<usize> = forms.iter().map(|f| f.cells()).collect();
    (
        med,
        iqr,
        start.x(),
        *cells.iter().min().unwrap(),
        *cells.iter().max().unwrap(),
    )
}

#[test]
fn a_lineage_drifts_away_from_its_start() {
    let (median, _, start_x, _, _) = walk();
    assert!(
        (median - start_x).abs() > 0.05,
        "the median should drift from {start_x}, got {median}"
    );
}

#[test]
fn a_lineage_spreads_and_does_not_settle() {
    let (_, iqr, _, min_cells, max_cells) = walk();
    assert!(
        iqr > 0.10,
        "the interquartile range should widen past 0.10, got {iqr}"
    );
    assert!(
        min_cells <= 2 && max_cells >= 15,
        "lineages should end between one cell and many, got {min_cells}..{max_cells}"
    );
}

#[test]
fn the_mutation_operator_has_no_restoring_force() {
    // the same claim, stated as the property that matters: starting from the same shape, the
    // distribution after a hundred mutations is not concentrated around the start
    let (median, iqr, start_x, _, _) = walk();
    let within = (median - start_x).abs() <= iqr / 2.0;
    assert!(
        !within,
        "the median {median} should lie outside half an IQR of the start {start_x}"
    );
}
