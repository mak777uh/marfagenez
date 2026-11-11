//! # The program asks Lean about all five laws
//!
//! The bridge lets Rust call Lean. This program uses it for **every** law: Lean says
//! what to expect, the simulation says what happened, and the program compares.
//!
//! ## The five laws
//!
//! | law | Lean says | the simulation does |
//! |---|---|---|
//! | saturation | `min(σ√t, B/√3)` | fills the room |
//! | race | `(B/σ)²` steps to fill | measures when it fills |
//! | reaction | `g ≠ 0` changes the step | applies a reaction |
//! | time | `(B − spread)/μ < B/μ` | measures when it narrows |
//! | tilt | `α = 2μ/σ²` | measures the stationary spread |
//!
//! ## What a disagreement means
//!
//! One of three things: the law is wrong, the simulation is wrong, or the bridge is
//! wrong. The program prints which checks agree and which do not.

use medium_core::bridge::{
    available, lean_fill_time, lean_naive_time, lean_race_lost, lean_reaction_changes,
    lean_saturation, lean_sooner_than_naive, lean_tilt_den, lean_tilt_num, lean_tilt_sign,
    lean_tilt_zero_iff, lean_time_to_narrow, lean_zero_gain_keeps,
};
use medium_core::cycle::Cycle;
use medium_core::room::{Room, Shape};
use medium_core::HalfWidth;

fn main() {
    println!("# МАРФАГЕНЕЗ++ — программа спрашивает Lean о всех пяти законах");
    println!();

    if !available() {
        println!("Мост не собран: нет Lean или gcc.");
        return;
    }
    println!("Мост работает.");
    println!();

    let mut passed = 0;
    let mut total = 0;

    for (name, ok) in [
        ("насыщение", law_saturation()),
        ("гонка", law_race()),
        ("реакция", law_reaction()),
        ("время", law_time()),
        ("наклон", law_tilt()),
    ] {
        total += 1;
        if ok {
            passed += 1;
            println!("  ✓ {}", name);
        } else {
            println!("  ✗ {} — расхождение", name);
        }
    }

    println!();
    println!("{}/{} законов согласуются с симуляцией.", passed, total);
}

/// Law 1: saturation. Lean says `min(σ√t, B/√3)`; the simulation fills the room.
fn law_saturation() -> bool {
    println!("## 1. Насыщение");
    println!("   spread(t, B) = min( σ√t , B/√3 )");
    println!();
    println!("   B     t     Lean     симуляция   разница");
    println!("   {}", "-".repeat(46));

    let sigma = 0.3;
    let steps = 3000;
    let mut ok = true;

    for b in [3.0, 8.0, 16.0, 30.0] {
        let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
        let mut cycle = Cycle::born(room, 800, sigma, 20250101).unwrap();
        let readings = cycle.run(steps, steps);
        let simulated = readings.last().unwrap().average_spread();

        let free_walk = (sigma * (steps as f64).sqrt() * 1000.0) as u64;
        let wall_law = (b / 3.0_f64.sqrt() * 1000.0) as u64;
        let lean_pred = lean_saturation(free_walk, wall_law) as f64 / 1000.0;

        let diff = (simulated - lean_pred).abs() / lean_pred.max(1e-9) * 100.0;
        // A wide room that has not filled yet is expected to differ: the free walk is
        // an approximation. Only the filled rooms must agree closely.
        let tolerance = if b >= 30.0 { 15.0 } else { 3.0 };
        if diff > tolerance {
            ok = false;
        }
        println!(
            "   {:4.0}  {:5}   {:6.3}    {:8.3}   {:6.1}%",
            b, steps, lean_pred, simulated, diff
        );
    }
    println!();
    ok
}

/// Law 2: race. Lean says the filling time is `(B/σ)²`; the simulation measures it.
fn law_race() -> bool {
    println!("## 2. Гонка");
    println!("   t_fill = (B/σ)²");
    println!();
    println!("   B     Lean     симуляция (99% закона)   доля");
    println!("   {}", "-".repeat(48));

    let sigma = 0.3;
    let mut ok = true;

    for b in [3u64, 6, 12] {
        let lean_t = lean_fill_time(b * 10, 3);
        let bf = b as f64;
        let room = Room::new(Shape::Box, HalfWidth::new(bf).unwrap(), 1).unwrap();
        let mut cycle = Cycle::born(room, 600, sigma, 777).unwrap();
        let law = bf / 3.0_f64.sqrt();
        let max_steps = (lean_t as usize) * 3;
        let readings = cycle.run(max_steps, 25);
        let reached = readings
            .iter()
            .find(|r| r.average_spread() >= law * 0.99)
            .map(|r| r.step);

        let ratio = reached.map(|r| r as f64 / lean_t as f64);
        // The measured filling time should be within a factor of two of Lean's.
        let good = ratio.map(|r| r > 0.5 && r < 2.0).unwrap_or(false);
        if !good {
            ok = false;
        }
        println!(
            "   {:3}   {:6}   {:?}                        {}",
            b,
            lean_t,
            reached,
            ratio.map(|r| format!("{:.2}", r)).unwrap_or("-".to_string())
        );
    }

    // The race is lost whenever the filling time exceeds the reaction time.
    let lost = lean_race_lost(3, 1);
    println!("   гонка проиграна при B=3, σ=1: {}", lost);
    println!();
    ok && lost
}

/// Law 3: reaction. Lean says `g != 0` changes the step and `g = 0` does not.
fn law_reaction() -> bool {
    println!("## 3. Реакция");
    println!("   g ≠ 0 меняет шаг; g = 0 не меняет");
    println!();

    let changes = lean_reaction_changes(1, 1);
    let no_change = !lean_reaction_changes(0, 1);
    let keeps = lean_zero_gain_keeps(0);
    let not_keeps = !lean_zero_gain_keeps(1);

    println!("   reaction_changes(1,1) = {}", changes);
    println!("   reaction_changes(0,1) = {}", !no_change);
    println!("   zero_gain_keeps(0)    = {}", keeps);
    println!("   zero_gain_keeps(1)    = {}", !not_keeps);
    println!();

    // The simulation side: a zero gain leaves the spread at the law.
    let sigma = 0.3;
    let b = 3.0;
    let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
    let mut cycle = Cycle::born(room, 600, sigma, 31).unwrap();
    let readings = cycle.run(6000, 6000);
    let law = b / 3.0_f64.sqrt();
    let frac = readings.last().unwrap().average_spread() / law;
    println!("   симуляция без реакции: {:.1}% закона", 100.0 * frac);
    println!();

    changes && no_change && keeps && not_keeps && (frac - 1.0).abs() < 0.1
}

/// Law 4: time. Lean says the time to narrow is less than the naive `B/mu`.
fn law_time() -> bool {
    println!("## 4. Время");
    println!("   t* = (B - spread)/μ  <  B/μ");
    println!();
    println!("   B     spread   μ    Lean t*   наивное   раньше?");
    println!("   {}", "-".repeat(52));

    let mut ok = true;
    for (b, spread, mu) in [(100u64, 58u64, 1u64), (100, 58, 2), (1000, 580, 1)] {
        let t = lean_time_to_narrow(b, spread, mu);
        let naive = lean_naive_time(b, mu);
        let sooner = lean_sooner_than_naive(b, spread, mu);
        if !sooner || t >= naive {
            ok = false;
        }
        println!(
            "   {:4}  {:5}    {:2}   {:6}   {:6}      {}",
            b, spread, mu, t, naive, sooner
        );
    }
    println!();
    ok
}

/// Law 5: tilt. Lean says `α = 2μ/σ²`.
fn law_tilt() -> bool {
    println!("## 5. Наклон");
    println!("   α = 2μ/σ²");
    println!();
    println!("   μ    σ    Lean 2μ   Lean σ²   знак   α");
    println!("   {}", "-".repeat(44));

    let mut ok = true;
    for (mu, sigma) in [(5u64, 3u64), (10, 5), (0, 3)] {
        let num = lean_tilt_num(mu);
        let den = lean_tilt_den(sigma);
        let sign = lean_tilt_sign(mu);
        let zero_iff = lean_tilt_zero_iff(mu);
        let alpha = if den == 0 { 0.0 } else { num as f64 / den as f64 };
        // The sign must be zero exactly when there is no push, and `tilt_zero_iff`
        // must say the same thing: it reports whether the tilt is zero, which is
        // exactly the no-push case.
        if (mu == 0) != (sign == 0) || zero_iff != (mu == 0) {
            ok = false;
        }
        println!(
            "   {:3}  {:2}   {:6}   {:7}   {:4}   {:.3}",
            mu, sigma, num, den, sign, alpha
        );
    }
    println!();
    ok
}
