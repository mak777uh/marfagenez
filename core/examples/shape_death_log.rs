//! What actually binds when a one-cell world dies? A step-by-step log, not another formula.
//!
//! `FINDING-242` measured the edge at `(6.5, 6.7)` and excluded both candidate arithmetics. The next
//! lawful step, named there, is an instrument: record `n`, `p`, `x`, the fill `f`, income, upkeep and the
//! form's energy on every step until it dies, at a price that survives and a price that does not.
//!
//! PREDICTION, before the run:
//!   (a) at `f0 = 6.7` the form dies on its second or third step, and the log shows the step's **margin**
//!       going negative there;
//!   (b) the binding quantity is either the fill (the stock has not recovered) or the form's own growth
//!       (n went up, so upkeep went up faster than income) - the log will say which;
//!   (c) at `f0 = 6.5` the same quantities stay positive, so the difference between the two prices is a
//!       single crossing and not a gradual decline.

use medium_core::form::{Form, ShapeEconomy};
use medium_core::shape_world::{Pool, ShapeRules, ShapeWorld};
use medium_core::Rng;

const CELLS: f64 = 100.0;
const INFLOW: f64 = 300.0;
const P_GROW: f64 = 0.27;
const BIRTH_PER_CELL: f64 = 4.0;

fn rules(f0: f64) -> ShapeRules {
    let economy = ShapeEconomy::new(2.0, 1.0, 0.1)
        .and_then(|e| e.with_fixed_cost(f0))
        .expect("valid economy");
    let mut r = ShapeRules::new(economy, 40.0).expect("rules");
    r.max_population = 64;
    r.pool = Pool::new(CELLS, INFLOW, CELLS);
    r.p_grow = P_GROW;
    r.birth_cost_per_cell = BIRTH_PER_CELL;
    r
}

fn log(f0: f64) {
    println!("\n=== f0 = {f0} (seed 1), every step until the world is empty ===");
    println!(
        "{:>4} {:>7} {:>3} {:>3} {:>6} {:>6} {:>8} {:>8} {:>8} {:>9}",
        "step", "forms", "n", "p", "x", "f", "income", "upkeep", "margin", "energy"
    );
    let mut world = ShapeWorld::new(rules(f0), vec![Form::square(1)]);
    let mut rng = Rng::new(1);
    for step in 1..=8 {
        world.step(&mut rng);
        let f = world.stock / CELLS;
        if world.forms.is_empty() {
            println!("{step:>4} {:>7} {:>3} {:>3} {:>6} {:>6} {:>8} {:>8} {:>8} {:>9}", 0, "-", "-", "-", f, "-", "-", "-", "-");
            break;
        }
        // report the first living form; with one starting cell there is usually one
        let fr = &world.forms[0];
        let n = fr.form.cells();
        let p = fr.form.perimeter();
        let x = fr.form.x();
        let income = world.rules.economy.income(&fr.form);
        let upkeep = world.rules.economy.upkeep(&fr.form);
        let margin = world.rules.economy.margin(&fr.form);
        println!(
            "{step:>4} {:>7} {n:>3} {p:>3} {x:>6.3} {f:>6.3} {income:>8.3} {upkeep:>8.3} {margin:>8.3} {:>9.3}",
            world.forms.len(),
            fr.energy
        );
    }
}

fn main() {
    log(6.5);
    log(6.7);
}
