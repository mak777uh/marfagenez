//! The restoring force of `FINDING-248`, to the extent it holds.
//!
//! `restore = 0` must reproduce `FINDING-247` exactly - that is the control. `restore = 0.5` cuts the
//! drift and the spread by about three times. What it does **not** do is bound the tails: one-cell and
//! twenty-one-cell lineages survive, because a probabilistic shift in the growth direction is not a
//! prohibition. Those two predictions are recorded as refuted rather than tested here.

use medium_core::form::Form;
use medium_core::Rng;

const LINEAGES: usize = 200;
const GENERATIONS: usize = 100;
const P_GROW: f64 = 0.27;

fn walk(restore: f64) -> (f64, f64, usize, usize, f64) {
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
        *cells.iter().min().unwrap(),
        *cells.iter().max().unwrap(),
        target,
    )
}

#[test]
fn restore_zero_reproduces_the_drifting_lineage() {
    let (median, iqr, min_cells, max_cells, target) = walk(0.0);
    assert!((median - target).abs() >= 0.05, "median {median} should drift from {target}");
    assert!(iqr > 0.10, "IQR should widen past 0.10, got {iqr}");
    assert!(
        min_cells <= 2 && max_cells >= 15,
        "lineages should span one cell to many, got {min_cells}..{max_cells}"
    );
}

#[test]
fn a_half_restore_cuts_the_drift_and_the_spread() {
    let (median0, iqr0, _, _, target) = walk(0.0);
    let (median5, iqr5, _, _, _) = walk(0.5);
    assert!(
        (median5 - target).abs() < (median0 - target).abs(),
        "0.5 should drift less than 0: {median5} vs {median0}"
    );
    assert!(iqr5 < 0.10, "0.5 should keep the IQR under 0.10, got {iqr5}");
    assert!(iqr5 < iqr0, "0.5 should be tighter than 0: {iqr5} vs {iqr0}");
}

#[test]
fn a_full_restore_holds_the_size_exactly() {
    let (median, iqr, _, _, target) = walk(1.0);
    assert!((median - target).abs() < 0.01, "median {median} should stay at {target}");
    assert!(iqr < 0.02, "a full restore should leave no spread, got {iqr}");
}
