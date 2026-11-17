//! Does making birth cost proportional to the child's size stop the growth?
//!
//! `FINDING-222` found why the interval of solvency never bounded the outcome: absolute margin
//! grows with size (`income` is proportional to the boundary, which grows as the square root of
//! the area), so bigger forms breed faster. A birth price proportional to the child's size is
//! the straightest correction.
//!
//! PREDICTION, before the run:
//!   (a) with `birth_cost_per_cell = 0` the growth of `FINDING-222` reproduces (sizes 9 -> 17);
//!   (b) with a per-cell cost the sizes stop growing and settle below the start;
//!   (c) they settle **at the lower end** of the solvency interval (1.571 for `f0 = 10`),
//!       because the fixed cost excludes the atom and the per-cell cost punishes the large.
//!
//! If (b) fails, the growth has another source and the per-cell price is not the fix.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

fn rules(per_cell: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(10.0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(100.0, 300.0, 100.0);
    r.p_grow = 0.27;
    r.birth_cost_per_cell = per_cell;
    r
}

fn side_of(f: &Form) -> f64 {
    let (lo, hi) = f.extent();
    ((hi.0 - lo.0 + 1) as f64).max((hi.1 - lo.1 + 1) as f64)
}

fn main() {
    for per_cell in [0.0, 2.0, 4.0, 8.0] {
        let mut world = ShapeWorld::new(rules(per_cell), vec![Form::square(3)]);
        let mut rng = Rng::new(41);
        let mut path = Vec::new();
        for step in 0..400 {
            world.step(&mut rng);
            if step % 100 == 0 {
                path.push((step, world.alive(), world.mean_cells()));
            }
        }
        let mut sides: Vec<f64> = world.forms.iter().map(|f| side_of(&f.form)).collect();
        sides.sort_by(|a, b| a.partial_cmp(b).unwrap());
        println!("=== birth_cost_per_cell {per_cell} ===");
        let path_str: Vec<String> = path
            .iter()
            .map(|(s, a, c)| format!("{s}:{a}/{c:.1}"))
            .collect();
        println!("  step:alive/mean_cells  {}", path_str.join("  "));
        println!(
            "  final alive {:>3}  mean_cells {:>5.1}  mean_x {:.3}  sides [{:.1}, {:.1}]  \
             births {}  deaths {}",
            world.alive(),
            world.mean_cells(),
            world.mean_x(),
            sides.first().copied().unwrap_or(0.0),
            sides.last().copied().unwrap_or(0.0),
            world.births,
            world.deaths
        );
        println!();
    }
}
