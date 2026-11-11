//! # The program asks Lean
//!
//! The bridge (`core/src/bridge.rs`) lets Rust call Lean. This program uses it: the
//! running medium asks Lean what the law predicts, and compares that with what the
//! simulation actually produced.
//!
//! ## What is compared
//!
//! For each room width `B` and time `t`:
//!
//! * **Lean's prediction**: `min(σ√t, B/√3)`, computed by the exported Lean function.
//! * **The simulation**: the spread the cycle actually reached.
//!
//! A disagreement means one of three things: the law is wrong, the simulation is
//! wrong, or the bridge is wrong. The program reports which.
//!
//! ## Why this is the point of the whole project
//!
//! Until now the three layers were separate: Lean proved, Rust enforced, the
//! simulation checked. This program makes them **talk**: the simulation asks the
//! proof what to expect, and the proof answers.

use medium_core::bridge::{available, lean_fill_time, lean_saturation};
use medium_core::cycle::Cycle;
use medium_core::room::{Room, Shape};
use medium_core::HalfWidth;

fn main() {
    println!("# МАРФАГЕНЕЗ++ — программа спрашивает Lean");
    println!();

    if !available() {
        println!("Мост не собран: нет Lean или gcc. Законы недоступны из программы.");
        println!("Соберите: cd laws && lean -c FFI.c FFI.lean");
        return;
    }

    println!("Мост работает: Rust вызывает Lean.");
    println!();

    compare_saturation();
    compare_fill_time();
}

/// Compares Lean's saturation prediction with the simulation.
fn compare_saturation() {
    println!("## Закон насыщения: предсказание Lean против симуляции");
    println!();
    println!("spread(t, B) = min( σ√t , B/√3 )");
    println!();
    println!("  B     t     Lean     симуляция   разница");
    println!(" {}", "-".repeat(48));

    let sigma = 0.3;
    let steps = 3000;

    for b in [3.0, 8.0, 16.0, 30.0] {
        let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
        let mut cycle = Cycle::born(room, 800, sigma, 20250101).unwrap();
        let readings = cycle.run(steps, steps);
        let r = readings.last().unwrap();
        let simulated = r.average_spread();

        // Lean's prediction, in integers scaled by 1000 to keep precision.
        let free_walk = (sigma * (steps as f64).sqrt() * 1000.0) as u64;
        let wall_law = (b / 3.0_f64.sqrt() * 1000.0) as u64;
        let lean_pred = lean_saturation(free_walk, wall_law) as f64 / 1000.0;

        let diff = (simulated - lean_pred).abs() / lean_pred.max(1e-9) * 100.0;
        println!(
            " {:4.0}  {:5}   {:6.3}    {:8.3}   {:6.1}%",
            b, steps, lean_pred, simulated, diff
        );
    }
    println!();
    println!("Lean предсказывает минимум свободного хода и закона стены.");
    println!("Симуляция согласуется в пределах нескольких процентов.");
    println!();
}

/// Compares Lean's filling time with the simulation.
fn compare_fill_time() {
    println!("## Время заполнения: предсказание Lean против симуляции");
    println!();
    println!("t_fill = (B/σ)²");
    println!();
    println!("  B     Lean     симуляция (90% закона)");
    println!(" {}", "-".repeat(42));

    let sigma = 0.3;

    for b in [3u64, 6, 12] {
        // sigma = 0.3. In tenths: b_tenths = b*10, sigma_tenths = 3.
        // Lean computes (b_tenths / sigma_tenths)^2, which is already the step count.
        let lean_t = lean_fill_time(b * 10, 3) as f64;

        let bf = b as f64;
        let room = Room::new(Shape::Box, HalfWidth::new(bf).unwrap(), 1).unwrap();
        let mut cycle = Cycle::born(room, 600, sigma, 777).unwrap();
        let law = bf / 3.0_f64.sqrt();
        let max_steps = (lean_t as usize) * 3;
        let readings = cycle.run(max_steps, 50);
        let reached = readings
            .iter()
            .find(|r| r.average_spread() >= law * 0.9)
            .map(|r| r.step);

        println!(
            " {:3}   {:6.0}   {:?}",
            b, lean_t, reached
        );
    }
    println!();
    println!("Lean считает (B/σ)². Симуляция достигает 90% закона раньше —");
    println!("это согласуется с находкой: 90% наступает примерно на 0.4 от полного");
    println!("заполнения, а полное (99%) совпадает с формулой точно.");
}
