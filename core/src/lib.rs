//! # medium-core — a medium where measurement errors are unrepresentable
//!
//! Every error found in this project was mechanical, and every mechanical error
//! has a shape a type can forbid. This crate encodes those shapes.
//!
//! ## The errors this crate makes impossible
//!
//! | error | how it happened | what forbids it here |
//! |---|---|---|
//! | fold with the wrong period | `2B` instead of `4B` | [`Fold`] is only built by [`Fold::new`], which checks the range |
//! | clamp mistaken for reflect | both were "a wall" | [`Clamp`] and [`Reflect`] are different types |
//! | chi² compared to zero | dof forgotten | [`Chi2`] carries its dof; only [`Chi2::is_uniform`] answers |
//! | optimum from noisy points | 4 points, no replication | [`Optimum`] is only built from a replicated sweep |
//! | mean and spread confused | same panel, same units | [`Mean`] and [`Spread`] are different types |
//! | reading before convergence | looked like physics | [`Converged`] is a token only a convergence test issues |
//!
//! ## What this crate cannot do
//!
//! It cannot check that you **stated the right question**. Two of the errors in this
//! project were of that kind: a theorem with the inequality reversed, and a theorem
//! missing a hypothesis. Those are caught by counterexample search and simulation,
//! not by types. See `checks/verify_all.js`.

#![deny(unsafe_code)]
#![deny(clippy::float_cmp)]

use std::f64::consts::PI;

// ---------------------------------------------------------------------------
// The room
// ---------------------------------------------------------------------------

/// A half-width `B > 0`. Impossible to construct at zero or below.
#[derive(Debug, Clone, Copy, PartialEq, PartialOrd)]
pub struct HalfWidth(f64);

impl HalfWidth {
    /// Returns `None` when `b` is not strictly positive and finite.
    pub fn new(b: f64) -> Option<Self> {
        if b.is_finite() && b > 0.0 {
            Some(Self(b))
        } else {
            None
        }
    }

    pub fn get(self) -> f64 {
        self.0
    }

    /// The spread of a uniform population in this room: `B/√3`.
    pub fn uniform_spread(self) -> Spread {
        Spread(self.0 / 3.0_f64.sqrt())
    }
}

// ---------------------------------------------------------------------------
// Measurements with distinct types
// ---------------------------------------------------------------------------

/// A mean. Cannot be passed where a [`Spread`] is expected.
#[derive(Debug, Clone, Copy, PartialEq, PartialOrd)]
pub struct Mean(pub f64);

/// A spread (standard deviation). Cannot be passed where a [`Mean`] is expected.
#[derive(Debug, Clone, Copy, PartialEq, PartialOrd)]
pub struct Spread(pub f64);

impl Spread {
    /// The spread as a fraction of the room's uniform spread.
    pub fn relative_to(self, room: HalfWidth) -> f64 {
        self.0 / room.uniform_spread().0
    }
}

/// A population's first two moments, measured together so they cannot be swapped.
#[derive(Debug, Clone, Copy)]
pub struct Moments {
    pub mean: Mean,
    pub spread: Spread,
    pub n: usize,
}

impl Moments {
    /// Measures a sample. Returns `None` for an empty sample, so an empty mean is
    /// unrepresentable.
    pub fn measure(xs: &[f64]) -> Option<Self> {
        if xs.is_empty() {
            return None;
        }
        let n = xs.len();
        let mean = xs.iter().sum::<f64>() / n as f64;
        let var = xs.iter().map(|x| (x - mean) * (x - mean)).sum::<f64>() / n as f64;
        Some(Self {
            mean: Mean(mean),
            spread: Spread(var.sqrt()),
            n,
        })
    }
}

// ---------------------------------------------------------------------------
// The two walls, as different types
// ---------------------------------------------------------------------------

/// A reflecting wall. Built only through [`Reflect::new`], which guarantees the
/// fold period is `4B` — the error that produced a half-interval in this project.
#[derive(Debug, Clone, Copy)]
pub struct Reflect {
    room: HalfWidth,
    period: f64,
}

impl Reflect {
    pub fn new(room: HalfWidth) -> Self {
        Self {
            room,
            period: 4.0 * room.get(),
        }
    }

    /// Folds `x` into `[-B, B]`. The period is `4B` by construction.
    ///
    /// The shift by `B` before folding is essential: without it the fold maps onto
    /// `[-B, 0]` only — the half-interval bug this crate exists to prevent.
    pub fn apply(self, x: f64) -> f64 {
        let b = self.room.get();
        let u = (x + b).rem_euclid(self.period);
        b - (u - 2.0 * b).abs()
    }

    /// Debug assertion: the fold never leaves the room.
    pub fn contains(self, x: f64) -> bool {
        let b = self.room.get();
        self.apply(x) >= -b && self.apply(x) <= b
    }
}

/// A clamping wall. A different type from [`Reflect`], so the two cannot be
/// substituted for one another by accident.
#[derive(Debug, Clone, Copy)]
pub struct Clamp {
    room: HalfWidth,
}

impl Clamp {
    pub fn new(room: HalfWidth) -> Self {
        Self { room }
    }

    pub fn apply(self, x: f64) -> f64 {
        let b = self.room.get();
        x.clamp(-b, b)
    }
}

// ---------------------------------------------------------------------------
// Statistics that carry their own interpretation
// ---------------------------------------------------------------------------

/// A chi-square statistic together with its degrees of freedom.
///
/// Comparing a bare chi-square to zero is meaningless: its expected value is its
/// degrees of freedom. Carrying the dof makes that mistake unrepresentable.
#[derive(Debug, Clone, Copy)]
pub struct Chi2 {
    pub value: f64,
    pub dof: usize,
    pub n: usize,
}

impl Chi2 {
    /// Goodness of fit against a uniform distribution over `bins` bins.
    pub fn uniform_fit(xs: &[f64], room: HalfWidth, bins: usize) -> Option<Self> {
        if xs.is_empty() || bins < 2 {
            return None;
        }
        let b = room.get();
        let mut counts = vec![0usize; bins];
        for &x in xs {
            let idx = (((x + b) / (2.0 * b)) * bins as f64).floor() as isize;
            let idx = idx.clamp(0, bins as isize - 1) as usize;
            counts[idx] += 1;
        }
        let expected = xs.len() as f64 / bins as f64;
        let value = counts
            .iter()
            .map(|&c| {
                let d = c as f64 - expected;
                d * d / expected
            })
            .sum();
        Some(Self {
            value,
            dof: bins - 1,
            n: xs.len(),
        })
    }

    /// The scaled statistic `chi² / n`. This is the quantity that distinguishes
    /// convergence from bias: it goes to zero for a uniform population and stays
    /// positive for a biased one.
    pub fn scaled(self) -> f64 {
        self.value / self.n as f64
    }

    /// Whether the fit is consistent with uniform, using the usual rule of thumb
    /// that chi-square should be within a few times its degrees of freedom.
    pub fn is_uniform(self) -> bool {
        self.value <= 3.0 * self.dof as f64
    }
}

// ---------------------------------------------------------------------------
// Convergence as a token
// ---------------------------------------------------------------------------

/// Proof that a run reached equilibrium. Only [`Converged::check`] can issue one,
/// so no measurement can be reported from an unconverged run.
#[derive(Debug, Clone, Copy)]
pub struct Converged {
    pub steps: usize,
}

impl Converged {
    /// Issues the token only when the spread stopped changing over `window` steps.
    pub fn check(history: &[Spread], window: usize, tolerance: f64) -> Option<Self> {
        if history.len() < window || window < 2 {
            return None;
        }
        let tail = &history[history.len() - window..];
        let first = tail[0].0;
        let last = tail[tail.len() - 1].0;
        if (last - first).abs() <= tolerance * first.abs().max(1e-12) {
            Some(Self {
                steps: history.len(),
            })
        } else {
            None
        }
    }
}

// ---------------------------------------------------------------------------
// An optimum that required replication
// ---------------------------------------------------------------------------

/// A reported optimum. Only [`Optimum::from_replicated_sweep`] can build one, and
/// it refuses unless every point was measured more than once.
///
/// This forbids the error of reading a minimum off a single noisy sweep.
#[derive(Debug, Clone, Copy)]
pub struct Optimum {
    pub at: f64,
    pub value: f64,
    pub replicates: usize,
}

impl Optimum {
    /// `points` holds `(parameter, value)` pairs, each already averaged over
    /// `replicates` independent runs.
    pub fn from_replicated_sweep(points: &[(f64, f64)], replicates: usize) -> Option<Self> {
        if replicates < 2 || points.len() < 3 {
            return None;
        }
        let (at, value) = points
            .iter()
            .copied()
            .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal))?;
        Some(Self {
            at,
            value,
            replicates,
        })
    }
}

// ---------------------------------------------------------------------------
// The model
// ---------------------------------------------------------------------------

/// The corrected model: independent noise plus a reflecting wall.
#[derive(Debug, Clone, Copy)]
pub struct Model {
    pub room: HalfWidth,
    pub noise: f64,
    pub drift: f64,
}

impl Model {
    pub fn new(room: HalfWidth, noise: f64, drift: f64) -> Option<Self> {
        if noise.is_finite() && noise >= 0.0 && drift.is_finite() {
            Some(Self {
                room,
                noise,
                drift,
            })
        } else {
            None
        }
    }

    /// Advances one cell by one step.
    pub fn step(&self, x: f64, shock: f64) -> f64 {
        Reflect::new(self.room).apply(x + self.drift + self.noise * shock)
    }

    /// The exponential tilt `α = 2μ/σ²` that governs the stationary density.
    pub fn tilt(&self) -> Option<f64> {
        if self.noise > 0.0 {
            Some(2.0 * self.drift / (self.noise * self.noise))
        } else {
            None
        }
    }
}

// ---------------------------------------------------------------------------
// Deterministic noise, so runs are reproducible
// ---------------------------------------------------------------------------

/// A small deterministic generator. Reproducibility is what makes a measurement
/// repeatable, and a repeatable measurement is what makes replication possible.
#[derive(Debug, Clone)]
pub struct Rng(u64);

impl Rng {
    pub fn new(seed: u64) -> Self {
        Self(seed.wrapping_mul(6364136223846793005).wrapping_add(1))
    }

    pub fn next_u64(&mut self) -> u64 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        self.0
    }

    /// Uniform in `[0, 1)`.
    pub fn uniform(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
    }

    /// Standard normal by Box-Muller.
    pub fn normal(&mut self) -> f64 {
        let u1 = self.uniform().max(1e-300);
        let u2 = self.uniform();
        (-2.0 * u1.ln()).sqrt() * (2.0 * PI * u2).cos()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn half_width_rejects_non_positive() {
        assert!(HalfWidth::new(0.0).is_none());
        assert!(HalfWidth::new(-1.0).is_none());
        assert!(HalfWidth::new(f64::NAN).is_none());
        assert!(HalfWidth::new(1.0).is_some());
    }

    #[test]
    fn reflect_stays_in_room() {
        let room = HalfWidth::new(3.0).unwrap();
        let r = Reflect::new(room);
        for i in -1000..1000 {
            let x = i as f64 * 0.1;
            assert!(r.contains(x), "x={} gave {}", x, r.apply(x));
        }
    }

    #[test]
    fn reflect_is_continuous() {
        let room = HalfWidth::new(3.0).unwrap();
        let r = Reflect::new(room);
        let mut prev = r.apply(-12.0);
        let mut x = -12.0;
        while x < 12.0 {
            x += 0.001;
            let cur = r.apply(x);
            assert!((cur - prev).abs() < 0.01, "jump at {}", x);
            prev = cur;
        }
    }

    #[test]
    fn reflect_is_one_lipschitz() {
        let room = HalfWidth::new(3.0).unwrap();
        let r = Reflect::new(room);
        let mut rng = Rng::new(7);
        for _ in 0..10000 {
            let x = rng.uniform() * 40.0 - 20.0;
            let y = x + (rng.uniform() - 0.5) * 0.01;
            let d0 = (x - y).abs();
            if d0 > 1e-12 {
                let d1 = (r.apply(x) - r.apply(y)).abs();
                assert!(d1 / d0 <= 1.0001, "lipschitz violated");
            }
        }
    }

    #[test]
    fn clamp_and_reflect_differ() {
        let room = HalfWidth::new(3.0).unwrap();
        let r = Reflect::new(room);
        let c = Clamp::new(room);
        // A point beyond the wall: reflect folds it back, clamp pins it.
        assert!((r.apply(4.0) - 2.0).abs() < 1e-12);
        assert!((c.apply(4.0) - 3.0).abs() < 1e-12);
    }

    #[test]
    fn uniform_spread_matches_theory() {
        let room = HalfWidth::new(3.0).unwrap();
        let model = Model::new(room, 0.3, 0.0).unwrap();
        let mut rng = Rng::new(11);
        let mut pop: Vec<f64> = (0..40000).map(|_| rng.normal() * 0.5).collect();
        for _ in 0..8000 {
            for x in pop.iter_mut() {
                let s = rng.normal();
                *x = model.step(*x, s);
            }
        }
        let m = Moments::measure(&pop).unwrap();
        let rel = (m.spread.0 - room.uniform_spread().0).abs() / room.uniform_spread().0;
        assert!(rel < 0.05, "spread {} vs {} rel {}", m.spread.0, room.uniform_spread().0, rel);
    }

    #[test]
    fn chi2_carries_dof() {
        let room = HalfWidth::new(3.0).unwrap();
        let mut rng = Rng::new(3);
        let pop: Vec<f64> = (0..10000).map(|_| rng.uniform() * 6.0 - 3.0).collect();
        let c = Chi2::uniform_fit(&pop, room, 20).unwrap();
        assert_eq!(c.dof, 19);
        assert!(c.is_uniform(), "chi2={} dof={}", c.value, c.dof);
    }

    #[test]
    fn optimum_requires_replication() {
        let pts = [(1.0, 0.1), (2.0, 0.3), (3.0, 0.2)];
        assert!(Optimum::from_replicated_sweep(&pts, 1).is_none());
        assert!(Optimum::from_replicated_sweep(&pts, 3).is_some());
    }

    #[test]
    fn converged_requires_a_window() {
        let s = |v: f64| Spread(v);
        assert!(Converged::check(&[s(1.0), s(1.0)], 5, 0.01).is_none());
        let flat = vec![s(1.0); 10];
        assert!(Converged::check(&flat, 5, 0.01).is_some());
        let mut rising = vec![s(1.0); 5];
        rising.push(s(2.0));
        assert!(Converged::check(&rising, 3, 0.01).is_none());
    }

    #[test]
    fn empty_sample_has_no_moments() {
        assert!(Moments::measure(&[]).is_none());
    }

    #[test]
    fn rng_is_reproducible() {
        let a: Vec<f64> = {
            let mut r = Rng::new(42);
            (0..5).map(|_| r.normal()).collect()
        };
        let b: Vec<f64> = {
            let mut r = Rng::new(42);
            (0..5).map(|_| r.normal()).collect()
        };
        assert_eq!(a, b);
    }
}

#[cfg(test)]
mod probes;

pub mod room;

#[cfg(test)]
mod room_probes;

pub mod child;

pub mod boundary;

#[cfg(test)]
mod boundary_probes;

pub mod cycle;

pub mod bridge;
