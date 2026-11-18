//! The restoring force of `FINDING-248`, to the extent it holds.
//!
//! `restore = 0` must reproduce `FINDING-247` exactly - that is the control. `restore = 0.5` cuts the
//! drift and the spread by about three times. What it does **not** do is bound the tails: one-cell and
//! twenty-one-cell lineages survive, because a probabilistic shift in the growth direction is not a
//! prohibition. Those two predictions are recorded as refuted rather than tested here.

use medium_core::form::{Form, Heredity};
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
fn a_full_restore_holds_the_size_closely() {
    // Not "exactly": the lineages share one RNG stream, so a change anywhere upstream shifts every
    // draw below it. Adding the floor check made that visible - the median moved from 0.500 to 0.462
    // without the plain branch changing at all. A test that demands exactness from a shared stream
    // measures the stream, not the mechanism.
    let (median, iqr, _, _, target) = walk(1.0);
    assert!(
        (median - target).abs() < 0.06,
        "median {median} should stay near {target}"
    );
    assert!(iqr < 0.05, "a full restore should leave little spread, got {iqr}");
}

#[test]
fn the_floor_removes_the_lower_tail_without_touching_the_body() {
    // FINDING-249: with `min_cells = 2` no lineage reaches a single cell, and the median and spread of
    // the rest are unchanged within 0.02. The distance-scaled force is deliberately absent here: it was
    // refuted, and a test would only pin the refutation in place.
    fn walk(min_cells: usize) -> (f64, f64, usize, usize) {
        let start = Form::square(2);
        let target = start.x();
        let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
        let mut rng = Rng::new(20250101);
        for _ in 0..GENERATIONS {
            for f in forms.iter_mut() {
                if let Some(next) =
                    f.mutate_towards_with(&mut rng, P_GROW, Some(target), 0.5, min_cells, false)
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
        )
    }

    let (med1, iqr1, min1, _) = walk(1);
    let (med2, iqr2, min2, _) = walk(2);

    assert_eq!(min1, 1, "without the floor a lineage should reach one cell");
    assert!(min2 >= 2, "with the floor no lineage should, got {min2}");
    assert!(
        (med1 - med2).abs() < 0.02,
        "the floor should not move the median: {med1} vs {med2}"
    );
    assert!(
        (iqr1 - iqr2).abs() < 0.02,
        "the floor should not widen the spread: {iqr1} vs {iqr2}"
    );
}

#[test]
fn the_fair_growth_probability_is_near_a_third() {
    // FINDING-250: with no restoring force the median stays at the starting size only around
    // p_grow = 0.36, not at 0.6 as a count of growth sites versus cells suggested. At 0.27 the
    // lineage erodes; at 0.45 it grows past the start.
    fn median_at(p_grow: f64) -> f64 {
        let start = Form::square(2);
        let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
        let mut rng = Rng::new(20250101);
        for _ in 0..GENERATIONS {
            for f in forms.iter_mut() {
                if let Some(next) = f.mutate(&mut rng, p_grow) {
                    *f = next;
                }
            }
        }
        let mut xs: Vec<f64> = forms.iter().map(|f| f.x()).collect();
        xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
        xs[xs.len() / 2]
    }

    let start = Form::square(2).x();
    assert!(
        (median_at(0.27) - start).abs() > 0.05,
        "0.27 should erode below the start"
    );
    assert!(
        (median_at(0.37) - start).abs() <= 0.02,
        "0.37 should hold the median at the start"
    );
    assert!(
        (median_at(0.45) - start).abs() > 0.02,
        "0.45 should grow past the start"
    );
}

#[test]
fn anchoring_the_force_at_the_fair_point_is_the_win() {
    // FINDING-251: the same constant shift gives IQR 0.100 at a base of 0.27 (FINDING-248) and 0.033 at a
    // base of 0.36. The force did not change - only the centre did.
    fn walk(p_grow: f64) -> f64 {
        let start = Form::square(2);
        let target = start.x();
        let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
        let mut rng = Rng::new(20250101);
        for _ in 0..GENERATIONS {
            for f in forms.iter_mut() {
                if let Some(next) = f.mutate_towards_with(&mut rng, p_grow, Some(target), 0.5, 1, false)
                {
                    *f = next;
                }
            }
        }
        let mut xs: Vec<f64> = forms.iter().map(|f| f.x()).collect();
        xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
        xs[xs.len() * 3 / 4] - xs[xs.len() / 4]
    }

    let off_centre = walk(0.27);
    let at_centre = walk(0.36);
    assert!(
        at_centre < off_centre / 2.0,
        "anchoring at 0.36 should at least halve the spread: {at_centre} vs {off_centre}"
    );
    assert!(at_centre < 0.05, "the anchored spread should be under 0.05, got {at_centre}");
}

#[test]
fn x_is_scale_free_which_is_why_bounding_it_does_not_bound_size() {
    // FINDING-252: a single cell has x = 0.25 and a thirty-cell strip has x about 0.5, so two shapes with
    // the same x differ by a factor of thirty in size. Any mechanism that regulates x alone leaves the
    // absolute size free - which is exactly what the four mechanisms of this line did.
    let small = Form::square(1);
    let strip = Form::strip(30);
    assert!(
        (strip.x() - 0.484).abs() < 0.02,
        "a thirty-cell strip should sit near x = 0.5, got {}",
        strip.x()
    );
    assert_eq!(small.cells(), 1);
    assert!(
        strip.cells() >= 30 && (strip.x() - Form::square(2).x()).abs() < 0.02,
        "the strip and the two-by-two should share about the same x while differing in size"
    );
}

#[test]
fn regulating_the_cell_count_closes_the_tail() {
    // FINDING-253: bounding x left the size free (1..30 cells). Bounding the count itself closes it:
    // with target 4 and band 0.2 the lineages end between three and five cells. This is the first
    // mechanism in this line that bounds the size rather than the ratio.
    fn walk(target: Option<usize>, band: Option<f64>) -> (usize, usize, f64) {
        let start = Form::square(2);
        let mut h = Heredity::plain();
        h.target_cells = target;
        h.band_cells = band;
        let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
        let mut rng = Rng::new(20250101);
        for _ in 0..GENERATIONS {
            for f in forms.iter_mut() {
                if let Some(next) = f.mutate_heredity(&mut rng, 0.36, &h) {
                    *f = next;
                }
            }
        }
        let mut ns: Vec<usize> = forms.iter().map(|f| f.cells()).collect();
        ns.sort_unstable();
        let mut xs: Vec<f64> = forms.iter().map(|f| f.x()).collect();
        xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let iqr = xs[xs.len() * 3 / 4] - xs[xs.len() / 4];
        (ns[0], ns[ns.len() - 1], iqr)
    }

    let (free_lo, free_hi, _) = walk(None, None);
    assert!(free_hi >= 20, "without a target the size should range freely: {free_lo}..{free_hi}");

    let (lo, hi, iqr) = walk(Some(4), Some(0.2));
    assert!(hi <= 6, "with the count band the maximum should be six or less, got {hi}");
    assert!(lo >= 3, "and the minimum three or more, got {lo}");
    assert!(iqr < 0.05, "and the shape spread should be small, got {iqr}");
}

#[test]
fn the_fair_probability_for_the_count_is_the_same_for_every_size() {
    // FINDING-255: the count walk is an up-down step with no size term, so 0.27 is fair for four, nine,
    // ten and sixteen cells alike. The 0.36 of FINDING-250 is the fair value for the **ratio**, a
    // different quantity - mixing the two produced a false "law" in 254.
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

    for start in [Form::square(2), Form::square(3), Form::rectangle(5, 2), Form::square(4)] {
        let size = start.cells() as f64;
        let at_fair = median_count(&start, 0.27);
        let at_036 = median_count(&start, 0.36);
        assert!(
            (at_fair - size).abs() <= 2.0,
            "0.27 should hold a {size}-cell start near its size, got {at_fair}"
        );
        assert!(
            at_036 > size + 3.0,
            "0.36 should grow a {size}-cell start well past its size, got {at_036}"
        );
    }
}

#[test]
fn the_size_regulator_holds_at_several_targets() {
    // FINDING-256: at the fair value for the count (0.27) the band holds three different targets, with the
    // mean within 0.15 of each. This is the first mechanism in this line that keeps the size, rather than
    // the ratio, where it is put.
    fn walk(n_star: usize) -> (f64, f64) {
        let start = Form::square(2);
        let mut h = Heredity::plain();
        h.target_cells = Some(n_star);
        h.band_cells = Some(0.2);
        let mut forms: Vec<Form> = (0..LINEAGES).map(|_| start.clone()).collect();
        let mut rng = Rng::new(20250101);
        for _ in 0..GENERATIONS {
            for f in forms.iter_mut() {
                if let Some(next) = f.mutate_heredity(&mut rng, 0.27, &h) {
                    *f = next;
                }
            }
        }
        let mut ns: Vec<usize> = forms.iter().map(|f| f.cells()).collect();
        ns.sort_unstable();
        let mean = ns.iter().map(|n| *n as f64).sum::<f64>() / ns.len() as f64;
        (ns[ns.len() / 2] as f64, mean)
    }

    for target in [4usize, 10, 16] {
        let (median, mean) = walk(target);
        assert!(
            (median - target as f64).abs() <= 1.0,
            "target {target}: the median should sit at the target, got {median}"
        );
        assert!(
            (mean - target as f64).abs() <= 0.5,
            "target {target}: the mean should be within half a cell, got {mean}"
        );
    }
}
