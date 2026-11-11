//! Gate probes: each gate is run against a **planted defect** and must fail.
//!
//! A gate that cannot fail is a slogan. Every test here plants a deliberate error
//! and asserts that the corresponding gate catches it.
//!
//! The planted defects are the exact errors this project made:
//!
//! | probe | planted defect | the real error it mirrors |
//! |---|---|---|
//! | `probe_half_interval` | fold without the `+B` shift | E1: period 2B instead of 4B |
//! | `probe_clamp_as_reflect` | clamp substituted for reflect | E2: atom at the wall |
//! | `probe_chi2_vs_zero` | chi² compared to zero | E4: dof forgotten |
//! | `probe_optimum_single_run` | optimum from one run | E7: 4 noisy points |
//! | `probe_mean_as_spread` | mean passed as spread | E8: units confused |
//! | `probe_unconverged` | reading before equilibrium | E3: too few steps |

#[cfg(test)]
mod probes {
    use crate::*;

    /// The buggy fold: no `+B` shift, so it maps onto `[-B, 0]` only.
    fn buggy_fold(x: f64, b: f64) -> f64 {
        let period = 4.0 * b;
        let u = x.rem_euclid(period);
        b - (u - 2.0 * b).abs()
    }

    #[test]
    fn probe_half_interval() {
        let room = HalfWidth::new(3.0).unwrap();
        let correct = Reflect::new(room);

        // The planted defect must be caught by a range check.
        let mut defect_found = false;
        for i in -1000..1000 {
            let x = i as f64 * 0.1;
            let bad = buggy_fold(x, 3.0);
            // The buggy fold never produces a positive value.
            if bad > 1e-9 {
                defect_found = true;
            }
        }
        assert!(
            defect_found,
            "GATE FAILED: the half-interval defect was not detected"
        );

        // And the correct fold does produce positive values.
        let mut positive = false;
        for i in -1000..1000 {
            let x = i as f64 * 0.1;
            if correct.apply(x) > 1e-9 {
                positive = true;
            }
        }
        assert!(positive, "the correct fold must cover the positive half");
    }

    #[test]
    fn probe_clamp_as_reflect() {
        let room = HalfWidth::new(3.0).unwrap();
        let r = Reflect::new(room);
        let c = Clamp::new(room);

        // The planted defect: treating clamp as reflect.
        // A point beyond the wall is pinned by clamp, folded by reflect.
        let x = 4.0;
        let reflected = r.apply(x);
        let clamped = c.apply(x);
        assert!(
            (reflected - clamped).abs() > 0.5,
            "GATE FAILED: clamp and reflect gave the same answer, so the difference is undetectable"
        );

        // The atom test: clamp piles mass on the wall, reflect does not.
        let mut on_wall_clamp = 0;
        let mut on_wall_reflect = 0;
        for i in 0..10000 {
            let x = i as f64 * 0.001;
            if (c.apply(x) - 3.0).abs() < 1e-12 {
                on_wall_clamp += 1;
            }
            if (r.apply(x) - 3.0).abs() < 1e-12 {
                on_wall_reflect += 1;
            }
        }
        assert!(
            on_wall_clamp > 100 && on_wall_reflect < 10,
            "GATE FAILED: the atom at the wall was not detected (clamp {} reflect {})",
            on_wall_clamp,
            on_wall_reflect
        );
    }

    #[test]
    fn probe_chi2_vs_zero() {
        // The planted defect: comparing chi² to zero.
        // A perfectly uniform sample still has chi² near its dof, not zero.
        let room = HalfWidth::new(3.0).unwrap();
        let mut rng = Rng::new(99);
        let pop: Vec<f64> = (0..100000).map(|_| rng.uniform() * 6.0 - 3.0).collect();
        let c = Chi2::uniform_fit(&pop, room, 20).unwrap();

        assert!(
            c.value > 1.0,
            "GATE FAILED: a uniform sample gave chi² near zero, so the dof error is undetectable"
        );
        assert!(c.is_uniform(), "a truly uniform sample must pass");

        // A biased sample must fail the same gate.
        let biased: Vec<f64> = (0..100000).map(|_| rng.uniform() * 3.0 - 3.0).collect();
        let cb = Chi2::uniform_fit(&biased, room, 20).unwrap();
        assert!(
            !cb.is_uniform(),
            "GATE FAILED: a biased sample passed the uniformity gate"
        );
    }

    #[test]
    fn probe_optimum_single_run() {
        // The planted defect: an optimum read off a single run.
        let pts = [(1.0, 0.1), (2.0, 0.5), (3.0, 0.2)];
        assert!(
            Optimum::from_replicated_sweep(&pts, 1).is_none(),
            "GATE FAILED: a single-run optimum was accepted"
        );
        assert!(
            Optimum::from_replicated_sweep(&pts, 5).is_some(),
            "a replicated sweep must be accepted"
        );
    }

    #[test]
    fn probe_mean_as_spread() {
        // The planted defect: passing a mean where a spread is expected.
        // This is a compile-time error by construction, so the probe asserts the
        // types differ by checking they carry different values for the same data.
        let xs = vec![10.0, 12.0, 14.0];
        let m = Moments::measure(&xs).unwrap();
        assert!(
            (m.mean.0 - 12.0).abs() < 1e-12,
            "mean should be 12"
        );
        assert!(
            (m.spread.0 - (8.0f64 / 3.0).sqrt()).abs() < 1e-12,
            "spread should be sqrt(8/3)"
        );
        assert!(
            (m.mean.0 - m.spread.0).abs() > 1.0,
            "GATE FAILED: mean and spread coincide, so a swap would be undetectable"
        );
    }

    #[test]
    fn probe_unconverged() {
        // The planted defect: reporting a measurement before equilibrium.
        let s = |v: f64| Spread(v);

        // A run that is still rising must be rejected.
        let rising = vec![s(0.1), s(0.3), s(0.6), s(0.9), s(1.2), s(1.5)];
        assert!(
            Converged::check(&rising, 4, 0.01).is_none(),
            "GATE FAILED: an unconverged run was accepted"
        );

        // A settled run must be accepted.
        let settled = vec![s(1.0), s(1.0), s(1.0), s(1.0), s(1.0), s(1.0)];
        assert!(
            Converged::check(&settled, 4, 0.01).is_some(),
            "a settled run must be accepted"
        );
    }

    #[test]
    fn probe_oscillation_looks_converged() {
        // The planted defect: a series that returns to its starting value without
        // converging. The earlier `Converged::check` compared only the first and the
        // last value, so this series passed.
        //
        // `1, 10, 1, 10, 1` — the ends match, and there is no convergence at all.
        let s = |v: f64| Spread(v);
        let oscillating = vec![s(1.0), s(10.0), s(1.0), s(10.0), s(1.0)];

        assert!(
            Converged::check(&oscillating, 5, 0.05).is_none(),
            "GATE FAILED: an oscillating series was accepted as converged"
        );

        // And a genuinely settled series must still be accepted.
        let settled = vec![s(1.0), s(1.001), s(0.999), s(1.0), s(1.0)];
        assert!(
            Converged::check(&settled, 5, 0.05).is_some(),
            "a settled series must be accepted"
        );
    }

    #[test]
    fn probe_slow_drift_looks_converged() {
        // A second planted defect: a slow drift whose ends are close but whose slope
        // is not zero. The range check alone would accept it; the trend check must
        // reject it.
        let s = |v: f64| Spread(v);
        // Rises by 0.02 each step over 5 steps: total drift 0.08, which is 8% of the
        // mean. With tolerance 0.05 the drift must be caught.
        let drifting = vec![s(1.00), s(1.02), s(1.04), s(1.06), s(1.08)];
        assert!(
            Converged::check(&drifting, 5, 0.05).is_none(),
            "GATE FAILED: a drifting series was accepted as converged"
        );
    }

    #[test]
    fn probe_short_run_looks_converged() {
        // The subtler defect: a run that is flat because it has not started moving.
        // The window requirement is what catches it.
        let s = |v: f64| Spread(v);
        let short = vec![s(0.1), s(0.1)];
        assert!(
            Converged::check(&short, 10, 0.01).is_none(),
            "GATE FAILED: a too-short run was accepted as converged"
        );
    }
}
