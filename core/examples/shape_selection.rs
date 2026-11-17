//! Does the shape economy select thin forms, as the arithmetic says it should?
//!
//! `docs/DESIGN-structures.md` (with the correction in `FINDING-215`) predicts, for an economy
//! where income is proportional to the boundary and transport costs depth:
//!
//!   (a) forms drift towards **low** `x = n/p`, i.e. thin and hollow, because boundary is
//!       income while cells are cost;
//!   (b) compact forms die above side ~6.8, because `x = side/4` hits the limit;
//!   (c) the population persists at the cap, so this is selection and not decay.
//!
//! The start is deliberately mixed: one square of each size 2..9 plus two strips, with the
//! same energy, so the first steps are pure economy and not luck.
//!
//! pred: mean x falls below the starting mean and stays below it; and no surviving form has
//!       more cells per edge than the limit allows for long.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{run, ShapeRules, ShapeWorld};
use medium_core::Rng;

fn rules() -> ShapeRules {
    let mut r = ShapeRules::new(ShapeEconomy::new(2.0, 1.0, 0.1).expect("economy"), 40.0)
        .expect("rules");
    r.max_population = 32;
    r
}

fn describe(world: &ShapeWorld) -> String {
    let mut sizes: Vec<usize> = world.forms.iter().map(|f| f.form.cells()).collect();
    sizes.sort_unstable();
    let xs: Vec<f64> = world.forms.iter().map(|f| f.form.x()).collect();
    let mean_x = if xs.is_empty() { 0.0 } else { xs.iter().sum::<f64>() / xs.len() as f64 };
    format!(
        "alive {:>3}  mean_cells {:>5.1}  mean_x {:.3}  sizes {:?}",
        world.alive(),
        world.mean_cells(),
        mean_x,
        if sizes.len() > 8 { sizes[..8].to_vec() } else { sizes.clone() }
    )
}

fn main() {
    let start: Vec<Form> = (2..=9).map(Form::square).chain([Form::strip(6), Form::strip(12)]).collect();
    let start_mean_x = {
        let xs: Vec<f64> = start.iter().map(|f| f.x()).collect();
        xs.iter().sum::<f64>() / xs.len() as f64
    };
    println!("start: {} forms, mean_x {:.3}", start.len(), start_mean_x);
    for (name, f) in start.iter().enumerate() {
        println!(
            "  {:>2}: cells {:>2}  perimeter {:>2}  x {:.3}  margin {:+.2}",
            name,
            f.cells(),
            f.perimeter(),
            f.x(),
            rules().economy.margin(f)
        );
    }
    println!();

    let mut world = run(rules(), start, 0, 5);
    let mut rng = Rng::new(5);
    println!("{:>5}  {}", "step", "state");
    for step in 1..=200 {
        world.step(&mut rng);
        if step % 20 == 0 || step <= 3 {
            println!("{step:>5}  {}", describe(&world));
        }
    }
    println!();
    println!(
        "births {}, deaths {}, mutations {}, final mean_x {:.3} (start {:.3})",
        world.births,
        world.deaths,
        world.mutations,
        world.mean_x(),
        start_mean_x
    );

    // the second experiment: does a compact form survive where the limit says it should not?
    println!();
    println!("survival of single squares, 40 steps, margin only:");
    for side in 2..=9u32 {
        let sq = Form::square(side);
        let w = run(rules(), vec![sq.clone()], 40, 11);
        println!(
            "  side {:>2}: x {:.3}  margin {:+.2}  alive after 40 {:>3}",
            side,
            sq.x(),
            rules().economy.margin(&sq),
            w.alive()
        );
    }

    // and the third: a strip of any length is viable, which is the prediction (a)
    println!();
    println!("survival of strips, 40 steps:");
    for len in [4u32, 8, 16, 32] {
        let s = Form::strip(len);
        let w = run(rules(), vec![s.clone()], 40, 13);
        println!(
            "  len {:>2}: x {:.3}  margin {:+.2}  alive after 40 {:>3}",
            len,
            s.x(),
            rules().economy.margin(&s),
            w.alive()
        );
    }
}
