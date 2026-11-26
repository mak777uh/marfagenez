//! The (gamma, cR) phase diagram of the compartment: three ways out, one grid.
//!
//! I-018/I-019 predicted, before this binary existed: homeostasis below the collapse threshold
//! at any price; collapse above it at no price; starvation on a diagonal of its own where the
//! border cannot be paid for. This program prints the grid and the two theory lines.

use medium_core::compartment::{collapse_gamma, stationary_capacity, Compartment, CompartmentRules};

fn main() {
    println!("# ОТСЕК: фазовая диаграмма (gamma, cR)");
    println!();
    println!("C0=1, Cmin=0.2, tau=20, D=1; теория: gamma* = {:.3}, C*(gamma) = C0/(1+tau*gamma*D)",
        collapse_gamma(1.0, 0.2, 20.0, 1.0));
    println!();
    print!("  gamma \\\\ cR");
    let prices = [1.0_f64, 5.0, 10.0, 20.0, 30.0, 60.0];
    for p in prices {
        print!("{:8.2}", p);
    }
    println!();
    println!("{}", "-".repeat(60));
    for gamma in [0.0_f64, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30] {
        print!("  {:6.2}  ", gamma);
        for p in prices {
            let r = CompartmentRules {
                c0: 1.0,
                tau: 20.0,
                gamma,
                damage_load: 1.0,
                c_min: 0.2,
                q_decay: 0.05,
                q_min: 0.2,
                repair_cost: p,
                repair_scale: 1.0,
                income: 0.3,
                maintenance: 0.05,
            };
            let mut w = Compartment::born(&r, 1.0);
            w.run(&r, 4000);
            let mark = match w.death {
                None => "Ж",
                Some(m) => match m {
                    medium_core::compartment::DeathMode::Collapse => "К",
                    medium_core::compartment::DeathMode::Starved => "Г",
                    medium_core::compartment::DeathMode::FellApart => "П",
                },
            };
            print!("{:>8}", mark);
        }
        println!("   C*(theory)={:.3}", stationary_capacity(1.0, 20.0, gamma, 1.0));
    }
    println!();
    println!("Ж = жив, К = коллапс ремонтной способности (I-018), Г = голод (I-019), П = распад границы.");
}
