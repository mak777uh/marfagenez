use vstd::prelude::*;

verus! {

// The integer laws from `core/src/bridge.rs`, verified.
//
// This is the same experiment the Aeneas plan proposes, done with the tool that is
// actually installed. The point is the same: prove properties of the **real Rust
// functions**, not of a separate Lean copy.
//
// ## The two levels
//
// Verus separates the **specification** (on mathematical `int`) from the
// **implementation** (on machine `u64`). The postcondition says the machine code
// computes the specification, and the preconditions name the overflow limits
// explicitly — which is exactly what the current code is missing.
//
// ## Coverage
//
// All sixteen functions exported by `laws/FFI.lean` are covered:
//
// | law | functions |
// |---|---|
// | saturation | `saturation`, `fraction_pct`, `fold_shifted` |
// | race | `fill_time`, `reaction_time`, `race_lost` |
// | reaction | `reaction_changes`, `zero_gain_keeps` |
// | time | `distance_to_wall`, `time_to_narrow`, `naive_time`, `sooner_than_naive` |
// | tilt | `tilt_num`, `tilt_den`, `tilt_sign`, `tilt_zero_iff` |

// ---------------------------------------------------------------------------
// 1. Saturation
// ---------------------------------------------------------------------------

spec fn saturation_spec(free_walk: int, wall_law: int) -> int {
    if free_walk < wall_law { free_walk } else { wall_law }
}

fn rust_saturation(free_walk: u64, wall_law: u64) -> (r: u64)
    ensures r as int == saturation_spec(free_walk as int, wall_law as int),
{
    if free_walk < wall_law { free_walk } else { wall_law }
}

proof fn bounded_by_wall(free_walk: int, wall_law: int)
    ensures saturation_spec(free_walk, wall_law) <= wall_law,
{
}

proof fn bounded_by_free_walk(free_walk: int, wall_law: int)
    ensures saturation_spec(free_walk, wall_law) <= free_walk,
{
}

proof fn saturation_when_wide(free_walk: int, wall_law: int)
    requires free_walk <= wall_law,
    ensures saturation_spec(free_walk, wall_law) == free_walk,
{
}

proof fn wall_binds_when_narrow(free_walk: int, wall_law: int)
    requires wall_law <= free_walk,
    ensures saturation_spec(free_walk, wall_law) == wall_law,
{
}

proof fn wider_never_worse(free_walk: int, w1: int, w2: int)
    requires w1 <= w2,
    ensures saturation_spec(free_walk, w1) <= saturation_spec(free_walk, w2),
{
}

// ---------------------------------------------------------------------------
// 2. Fraction of the law, in percent
// ---------------------------------------------------------------------------

spec fn fraction_pct_spec(spread: int, law: int) -> int {
    if law == 0 { 0 } else { (100 * spread) / law }
}

fn rust_fraction_pct(spread: u64, law: u64) -> (r: u64)
    requires
        // `100 * spread` must not overflow.
        spread <= u64::MAX / 100,
    ensures r as int == fraction_pct_spec(spread as int, law as int),
{
    if law == 0 {
        0
    } else {
        (100 * spread) / law
    }
}

// When the spread equals the law, the fraction is 100 percent.
proof fn fraction_at_law(law: int)
    requires law > 0,
    ensures fraction_pct_spec(law, law) == 100,
{
    // fraction_pct_spec(law, law) = (100 * law) / law = 100.
    assert((100 * law) / law == 100) by (nonlinear_arith)
        requires law > 0;
}

// ---------------------------------------------------------------------------
// 3. The fold
// ---------------------------------------------------------------------------

spec fn fold_shifted_spec(b: int, x: int) -> int {
    let period = 4 * b;
    let u = (x + b) % period;
    if u <= 2 * b { u } else { period - u }
}

fn rust_fold_shifted(b: u64, x: u64) -> (r: u64)
    requires
        b > 0,
        b <= u64::MAX / 4,
        x <= u64::MAX - b,
    ensures
        r as int <= 2 * (b as int),
        r as int == fold_shifted_spec(b as int, x as int),
{
    let period = 4 * b;
    let u = (x + b) % period;
    if u <= 2 * b { u } else { period - u }
}

proof fn fold_stays_in_room(b: int, x: int)
    requires b > 0, x >= 0,
    ensures fold_shifted_spec(b, x) <= 2 * b,
{
}

// ---------------------------------------------------------------------------
// 4. Filling time
// ---------------------------------------------------------------------------

spec fn fill_time_spec(b: int, sigma: int) -> int {
    if sigma == 0 {
        0
    } else {
        let q = b / sigma;
        q * q
    }
}

fn rust_fill_time(b: u64, sigma: u64) -> (r: u64)
    requires
        sigma == 0 || (b / sigma) <= 0xFFFFFFFF,
    ensures r as int == fill_time_spec(b as int, sigma as int),
{
    if sigma == 0 {
        0
    } else {
        let q = b / sigma;
        assert((q as int) * (q as int) <= (q as int) * 0xFFFFFFFF) by (nonlinear_arith)
            requires 0 <= q as int, (q as int) <= 0xFFFFFFFF;
        assert((q as int) * 0xFFFFFFFF <= 0xFFFFFFFF * 0xFFFFFFFF) by (nonlinear_arith)
            requires 0 <= q as int, (q as int) <= 0xFFFFFFFF;
        assert(0xFFFFFFFF * 0xFFFFFFFF == 0xFFFFFFFE00000001) by (compute);
        q * q
    }
}

proof fn square_zero_iff(q: int)
    ensures q * q == 0 <==> q == 0,
{
    if q != 0 {
        if q > 0 {
            assert(q >= 1);
            assert(q * q >= q) by (nonlinear_arith);
        } else {
            assert(q <= -1);
            assert(q * q >= -q) by (nonlinear_arith);
        }
    }
}

proof fn fill_time_zero_iff(b: int, sigma: int)
    requires sigma > 0, b / sigma <= 0xFFFFFFFF,
    ensures fill_time_spec(b, sigma) == 0 <==> b / sigma == 0,
{
    square_zero_iff(b / sigma);
}

proof fn fill_time_doubles(t: int)
    requires 0 <= t <= 0xFFFFFFFF,
    ensures fill_time_spec(2 * t, 1) == 4 * fill_time_spec(t, 1),
{
    assert((2 * t) * (2 * t) == 4 * (t * t)) by (nonlinear_arith);
}

// ---------------------------------------------------------------------------
// 5. Reaction time and the race
// ---------------------------------------------------------------------------

/// The room reacts in one step. This is a constant, so the specification and the
/// implementation are the same value.
spec fn reaction_time_spec() -> int { 1 }

fn rust_reaction_time() -> (r: u64)
    ensures r as int == reaction_time_spec(),
{
    1
}

spec fn race_lost_spec(b: int, sigma: int) -> bool {
    reaction_time_spec() < fill_time_spec(b, sigma)
}

fn rust_race_lost(b: u64, sigma: u64) -> (r: bool)
    requires
        sigma == 0 || (b / sigma) <= 0xFFFFFFFF,
    ensures r == race_lost_spec(b as int, sigma as int),
{
    if sigma == 0 {
        // fill_time = 0, reaction = 1, so 1 < 0 is false.
        assert(fill_time_spec(b as int, 0) == 0);
        false
    } else {
        let q = b / sigma;
        assert((q as int) * (q as int) <= (q as int) * 0xFFFFFFFF) by (nonlinear_arith)
            requires 0 <= q as int, (q as int) <= 0xFFFFFFFF;
        assert((q as int) * 0xFFFFFFFF <= 0xFFFFFFFF * 0xFFFFFFFF) by (nonlinear_arith)
            requires 0 <= q as int, (q as int) <= 0xFFFFFFFF;
        assert(0xFFFFFFFF * 0xFFFFFFFF == 0xFFFFFFFE00000001) by (compute);
        let ft = q * q;
        // reaction_time is 1, so the race is lost when 1 < ft.
        1 < ft
    }
}

// The race is lost whenever the filling time exceeds one step.
proof fn race_lost_iff(b: int, sigma: int)
    requires sigma > 0, b / sigma <= 0xFFFFFFFF,
    ensures race_lost_spec(b, sigma) <==> 1 < fill_time_spec(b, sigma),
{
}

// ---------------------------------------------------------------------------
// 6. Reaction law
// ---------------------------------------------------------------------------

spec fn reaction_changes_spec(gain: int, reaction: int) -> bool {
    gain != 0 && reaction != 0
}

fn rust_reaction_changes(gain: u64, reaction: u64) -> (r: bool)
    ensures r == reaction_changes_spec(gain as int, reaction as int),
{
    gain != 0 && reaction != 0
}

spec fn zero_gain_keeps_spec(gain: int) -> bool {
    gain == 0
}

fn rust_zero_gain_keeps(gain: u64) -> (r: bool)
    ensures r == zero_gain_keeps_spec(gain as int),
{
    gain == 0
}

// A zero gain never changes the step, and a non-zero gain with a non-zero reaction
// always does. The two are exact complements.
proof fn reaction_is_dichotomy(gain: int, reaction: int)
    ensures
        reaction_changes_spec(gain, reaction) <==> !(gain == 0 || reaction == 0),
{
}

// ---------------------------------------------------------------------------
// 7. Time law
// ---------------------------------------------------------------------------

spec fn distance_to_wall_spec(b: int, spread: int) -> int {
    if spread <= b { b - spread } else { 0 }
}

fn rust_distance_to_wall(b: u64, spread: u64) -> (r: u64)
    ensures r as int == distance_to_wall_spec(b as int, spread as int),
{
    if spread <= b { b - spread } else { 0 }
}

// The distance is never more than the room.
proof fn distance_le_room(b: int, spread: int)
    requires b >= 0, spread >= 0,
    ensures distance_to_wall_spec(b, spread) <= b,
{
    // If spread <= b then b - spread <= b; otherwise the distance is 0 <= b.
}

spec fn time_to_narrow_spec(b: int, spread: int, mu: int) -> int {
    if mu == 0 {
        0
    } else {
        let d = distance_to_wall_spec(b, spread);
        if d == 0 { 0 } else { (d + (mu - 1)) / mu }
    }
}

fn rust_time_to_narrow(b: u64, spread: u64, mu: u64) -> (r: u64)
    requires
        // `d + mu - 1` must not overflow, where `d` is at most `b`.
        mu == 0 || (b as int) + (mu as int) - 1 <= u64::MAX,
    ensures r as int == time_to_narrow_spec(b as int, spread as int, mu as int),
{
    if mu == 0 {
        0
    } else {
        let d = if spread <= b { b - spread } else { 0 };
        if d == 0 {
            0
        } else {
            // `d <= b`, and `b + mu - 1 <= u64::MAX` by the precondition.
            assert(d <= b);
            (d + (mu - 1)) / mu
        }
    }
}

spec fn naive_time_spec(b: int, mu: int) -> int {
    if mu == 0 { 0 } else { (b + (mu - 1)) / mu }
}

fn rust_naive_time(b: u64, mu: u64) -> (r: u64)
    requires
        mu == 0 || (b as int) + (mu as int) - 1 <= u64::MAX,
    ensures r as int == naive_time_spec(b as int, mu as int),
{
    if mu == 0 {
        0
    } else {
        (b + (mu - 1)) / mu
    }
}

spec fn sooner_than_naive_spec(b: int, spread: int, mu: int) -> bool {
    time_to_narrow_spec(b, spread, mu) < naive_time_spec(b, mu)
}

fn rust_sooner_than_naive(b: u64, spread: u64, mu: u64) -> (r: bool)
    requires
        mu == 0 || (b as int) + (mu as int) - 1 <= u64::MAX,
    ensures r == sooner_than_naive_spec(b as int, spread as int, mu as int),
{
    if mu == 0 {
        false
    } else {
        let d = if spread <= b { b - spread } else { 0 };
        let t = if d == 0 {
            0
        } else {
            assert(d <= b);
            (d + (mu - 1)) / mu
        };
        let naive = (b + (mu - 1)) / mu;
        t < naive
    }
}

// ---------------------------------------------------------------------------
// 8. Tilt
// ---------------------------------------------------------------------------

spec fn tilt_num_spec(mu: int) -> int { 2 * mu }

fn rust_tilt_num(mu: u64) -> (r: u64)
    requires mu <= u64::MAX / 2,
    ensures r as int == tilt_num_spec(mu as int),
{
    2 * mu
}

spec fn tilt_den_spec(sigma: int) -> int { sigma * sigma }

fn rust_tilt_den(sigma: u64) -> (r: u64)
    requires sigma <= 0xFFFFFFFF,
    ensures r as int == tilt_den_spec(sigma as int),
{
    assert((sigma as int) * (sigma as int) <= (sigma as int) * 0xFFFFFFFF) by (nonlinear_arith)
        requires 0 <= sigma as int, (sigma as int) <= 0xFFFFFFFF;
    assert((sigma as int) * 0xFFFFFFFF <= 0xFFFFFFFF * 0xFFFFFFFF) by (nonlinear_arith)
        requires 0 <= sigma as int, (sigma as int) <= 0xFFFFFFFF;
    assert(0xFFFFFFFF * 0xFFFFFFFF == 0xFFFFFFFE00000001) by (compute);
    sigma * sigma
}

spec fn tilt_sign_spec(mu: int) -> int { if mu == 0 { 0 } else { 1 } }

fn rust_tilt_sign(mu: u64) -> (r: u64)
    ensures r as int == tilt_sign_spec(mu as int),
{
    if mu == 0 { 0 } else { 1 }
}

// `tilt_zero_iff` reports whether the tilt is zero. The name says "iff" because
// the tilt is zero exactly when there is no push; the function returns that
// condition, not the biconditional.
spec fn tilt_zero_iff_spec(mu: int) -> bool {
    tilt_num_spec(mu) == 0
}

fn rust_tilt_zero_iff(mu: u64) -> (r: bool)
    requires mu <= u64::MAX / 2,
    ensures r == tilt_zero_iff_spec(mu as int),
{
    2 * mu == 0
}

// The tilt is zero exactly when there is no push.
proof fn tilt_zero_iff_mu_zero(mu: int)
    requires 0 <= mu,
    ensures tilt_num_spec(mu) == 0 <==> mu == 0,
{
}

fn main() {}

}
