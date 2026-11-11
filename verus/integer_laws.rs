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
// ## Nonlinear arithmetic
//
// Verus's default solver does not multiply. Facts like `q * q == 0 <==> q == 0` need
// `nonlinear_arith` with explicit hints. That is a real cost of verification, and it
// is worth naming: the tool proves the property, but the proof is not free.

// ---------------------------------------------------------------------------
// 1. Saturation: `min(free_walk, wall_law)`
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
// 2. Filling time: `(b / sigma)^2`
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
        // The square must not overflow: `q * q <= u64::MAX`.
        // `q <= 0xFFFFFFFF` gives `q*q <= 0xFFFFFFFE00000001`, which fits.
        sigma == 0 || (b / sigma) <= 0xFFFFFFFF,
    ensures r as int == fill_time_spec(b as int, sigma as int),
{
    if sigma == 0 {
        0
    } else {
        let q = b / sigma;
        // State the bound to the solver: it does not derive `q*q` fits from
        // `q <= 0xFFFFFFFF` on its own.
        // Two steps, each stated to the solver: `q*q <= q*MAX` because `q <= MAX`,
        // then `q*MAX <= MAX*MAX` because `q <= MAX`.
        assert((q as int) * (q as int) <= (q as int) * 0xFFFFFFFF) by (nonlinear_arith)
            requires 0 <= q as int, (q as int) <= 0xFFFFFFFF;
        assert((q as int) * 0xFFFFFFFF <= 0xFFFFFFFF * 0xFFFFFFFF) by (nonlinear_arith)
            requires 0 <= q as int, (q as int) <= 0xFFFFFFFF;
        assert(0xFFFFFFFF * 0xFFFFFFFF == 0xFFFFFFFE00000001) by (compute);
        q * q
    }
}

// A square is zero exactly when its base is zero.
proof fn square_zero_iff(q: int)
    ensures q * q == 0 <==> q == 0,
{
    if q != 0 {
        // A non-zero integer is at least 1 in absolute value, and the square of a
        // number of absolute value at least 1 is at least 1. Verus needs the bound
        // stated explicitly: `nonlinear_arith` alone does not derive it.
        if q > 0 {
            assert(q >= 1);
            assert(q * q >= q) by (nonlinear_arith);
        } else {
            assert(q <= -1);
            assert(q * q >= -q) by (nonlinear_arith);
        }
    }
}

// The filling time is zero exactly when the quotient is zero.
proof fn fill_time_zero_iff(b: int, sigma: int)
    requires sigma > 0, b / sigma <= 0xFFFFFFFF,
    ensures fill_time_spec(b, sigma) == 0 <==> b / sigma == 0,
{
    square_zero_iff(b / sigma);
}

// Doubling the room quadruples the filling time when the divisor is one.
proof fn fill_time_doubles(t: int)
    requires 0 <= t <= 0xFFFFFFFF,
    ensures fill_time_spec(2 * t, 1) == 4 * fill_time_spec(t, 1),
{
    // (2t/1)^2 = (2t)^2 = 4t^2 = 4*(t/1)^2.
    assert((2 * t) * (2 * t) == 4 * (t * t)) by (nonlinear_arith);
}

// ---------------------------------------------------------------------------
// 3. The fold: reflection into `[-b, b]`, shifted to `[0, 2b]`
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

fn main() {}

}
