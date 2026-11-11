//! Runs the medium and prints what an observer outside sees.
//!
//! This is the first program in the project: everything before it was a library.
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

    // A narrow room and a wide one, same noise, same time.
    let cases: [(f64, &str); 3] = [
        (3.0, "узкая"),
        (16.0, "средняя"),
        (30.0, "широкая"),
    ];

    println!("## Одна и та же жизнь в трёх комнатах");
    println!();
    println!("шум σ = 0.3, 800 детей, 3000 шагов");
    println!();
    println!(" комната   B     шаг    разброс   закон    доля");
    println!(" {}", "-".repeat(52));

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
                r.spread,
                r.half_width / 3.0_f64.sqrt(),
                100.0 * r.fraction_of_law()
            );
        }
        println!();
    }

    println!("## Что видно");
    println!();
    println!("Узкая комната заполнена почти сразу: доля близка к 100%.");
    println!("Широкая комната заполняется долго: доля растёт, но медленно.");
    println!();
    println!("Закон насыщения:");
    println!("  spread(t, B) = min( σ√t , B/√3 )");
    println!();
    println!("  σ√t при t=3000: {:.2}", 0.3 * (3000.0_f64).sqrt());
    println!("  B/√3 при B=30:  {:.2}", 30.0 / 3.0_f64.sqrt());
    println!();
    println!("При B=30 стена ещё не достигнута — разброс ограничен свободным ходом.");

    // A second demonstration: the medium keeps every child inside.
    println!();
    println!("## Граница держится");
    println!();
    let room = Room::new(Shape::Box, HalfWidth::new(3.0).unwrap(), 1).unwrap();
    let mut cycle = Cycle::born(room, 400, 0.5, 999).unwrap();
    cycle.run(5000, 5000);
    let outside = cycle
        .population()
        .iter()
        .filter(|c| !cycle.room().contains(c.position()))
        .count();
    println!("детей снаружи комнаты после 5000 шагов: {}", outside);
    println!(
        "{}",
        if outside == 0 {
            "граница держится."
        } else {
            "ГРАНИЦА НАРУШЕНА."
        }
    );

    // A third: the medium has no way to measure.
    println!();
    println!("## Среда не измеряет");
    println!();
    println!("Среда может только:");
    println!("  - двигать ребёнка его дрейфом и шумом");
    println!("  - возвращать его в комнату");
    println!();
    println!("Наблюдатель снаружи видит:");
    let room = Room::new(Shape::Box, HalfWidth::new(3.0).unwrap(), 1).unwrap();
    let c = Cycle::born(room, 100, 0.3, 7).unwrap();
    let r = c.read();
    println!(
        "  шаг {}, среднее {:.3}, разброс {:.3}",
        r.step, r.mean, r.spread
    );
    println!();
    println!("Среда этого не видит. Она не спрашивает.");
}
