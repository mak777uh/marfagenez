//! Runs the medium and prints what an observer outside sees.
//!
//! The medium runs blind. This program watches from outside and prints. It never
//! feeds anything back — the medium does not know it is being watched.

use medium_core::cycle::Cycle;
use medium_core::room::{Room, Shape};
use medium_core::HalfWidth;

fn main() {
    println!("# МАРФАГЕНЕЗ++ — среда в работе");
    println!();
    println!("Среда молчит. Наблюдатель снаружи смотрит.");
    println!();

    narrow_wide();
    box_vs_ball();
    boundary_holds();
}

/// One life in three rooms of different width.
fn narrow_wide() {
    println!("## Одна и та же жизнь в трёх комнатах");
    println!();
    println!("шум σ = 0.3, 800 детей, 3000 шагов, одна черта");
    println!();
    println!(" комната   B     шаг    разброс   закон    доля");
    println!(" {}", "-".repeat(52));

    let cases: [(f64, &str); 3] = [(3.0, "узкая"), (16.0, "средняя"), (30.0, "широкая")];

    for (b, name) in cases {
        let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
        let mut cycle = Cycle::born(room, 800, 0.3, 12345).unwrap();
        let readings = cycle.run(3000, 1000);

        for r in &readings {
            println!(
                " {:7}  {:5.1}  {:5}   {:7.3}  {:6.3}   {:5.1}%",
                name,
                b,
                r.step,
                r.spread(),
                r.half_width / 3.0_f64.sqrt(),
                100.0 * r.fraction_of_law()
            );
        }
        println!();
    }

    println!("Закон насыщения:");
    println!("  spread(t, B) = min( σ√t , B/√3 )");
    println!();
    println!("  σ√t при t=3000: {:.2}", 0.3 * (3000.0_f64).sqrt());
    println!("  B/√3 при B=30:  {:.2}", 30.0 / 3.0_f64.sqrt());
    println!();
    println!("При B=30 стена ещё не достигнута — разброс ограничен свободным ходом.");
    println!();
}

/// A child is not one number: a box keeps the law for every number of traits, a ball
/// squeezes.
fn box_vs_ball() {
    println!("## Ребёнок — не одно число");
    println!();
    println!("Та же комната, разное число черт. 600 детей, 8000 шагов.");
    println!();
    println!(" форма   d     разброс   закон    доля");
    println!(" {}", "-".repeat(44));

    for shape in [Shape::Box, Shape::Ball] {
        let name = match shape {
            Shape::Box => "куб",
            Shape::Ball => "шар",
        };
        for dims in [1, 4, 8] {
            let room = Room::new(shape, HalfWidth::new(3.0).unwrap(), dims).unwrap();
            let mut cycle = Cycle::born(room, 600, 0.3, 777).unwrap();
            let readings = cycle.run(8000, 8000);
            let r = readings.last().unwrap();
            let law = r.half_width / 3.0_f64.sqrt();
            println!(
                " {:6}  {:2}   {:7.3}  {:6.3}   {:5.1}%",
                name,
                dims,
                r.average_spread(),
                law,
                100.0 * r.fraction_of_law()
            );
        }
        println!();
    }

    println!("Куб держит закон при любом числе черт.");
    println!("Шар душит: каждая черта получает B²/d, и при d=8 остаётся половина.");
    println!();
    println!("Формула: Var = d/(d+2) · R² для шара, B²/3 для куба.");
    println!();
}

/// The medium keeps every child inside.
fn boundary_holds() {
    println!("## Граница держится");
    println!();
    for shape in [Shape::Box, Shape::Ball] {
        let name = match shape {
            Shape::Box => "куб",
            Shape::Ball => "шар",
        };
        let room = Room::new(shape, HalfWidth::new(3.0).unwrap(), 4).unwrap();
        let mut cycle = Cycle::born(room, 400, 0.5, 999).unwrap();
        cycle.run(5000, 5000);
        let outside = cycle
            .population()
            .iter()
            .filter(|c| !cycle.room().contains(c.position()))
            .count();
        println!(
            " {} (4 черты, 5000 шагов): детей снаружи — {}{}",
            name,
            outside,
            if outside == 0 { "  ✓" } else { "  ГРАНИЦА НАРУШЕНА" }
        );
    }
    println!();
    println!("## Среда не измеряет");
    println!();
    println!("Среда может только:");
    println!("  - двигать ребёнка его дрейфом и шумом");
    println!("  - возвращать его в комнату");
    println!();
    println!("Наблюдатель снаружи видит то, чего среда не видит. Она не спрашивает.");
}
