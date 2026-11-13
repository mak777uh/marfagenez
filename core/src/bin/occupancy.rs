//! EXP-28: once the population is at capacity, how many empty cells are there,
//! and does anything ever fill them?
//!
//! EXP-26 measured 77 alive on 40 cells at n = 160, with 0-3 cells empty, and
//! the number varied with the seed. EXP-27 showed that a sighted organism will
//! not step into an empty cell, because an empty cell is not *richer* than the
//! cell it stands on.
//!
//! That leaves a question the two experiments together do not answer: if a cell
//! empties, can anything fill it again? This program answers it by watching the
//! occupancy of every cell, step by step, and reporting every change.
//!
//! Arithmetic first (PROTOCOL.md §1)
//! ---------------------------------
//! `Life::advance` walks the organism vector and skips the dead:
//!
//!     for slot in self.organisms.iter_mut() {
//!         let Some(r) = slot.as_mut() else { continue };
//!         if !r.organism.is_alive() { continue; }
//!         ...
//!     }
//!
//! There is no birth, no respawn, and no removal. The vector is built once by
//! the spawner and its length never changes. So the number of living organisms
//! is a **non-increasing** function of the step count, and a cell that loses its
//! last occupant can only be refilled by a living organism **moving in**.
//!
//! Two predictions follow, both falsifiable:
//!
//!   P1  alive(step) never increases.
//!   P2  the number of empty cells never decreases.
//!
//! If either fails, something in the cycle creates or destroys organisms and
//! the model is not what the code says it is.
//!
//! The interesting measurement is not whether P1 and P2 hold -- they follow from
//! the loop -- but **how many empty cells there are at the end**, and whether
//! they are the cells that were empty at the start. A cell that empties late is
//! a cell nothing can refill.

use std::env;

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::World;

/// Occupancy of each cell: how many living organisms stand on it.
fn occupancy(life: &Life) -> Vec<usize> {
    let cells = life.field().cells();
    let mut occ = vec![0usize; cells];
    for s in life.samples() {
        if s.alive && s.cell < cells {
            occ[s.cell] += 1;
        }
    }
    occ
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let n: usize = args
        .get(1)
        .and_then(|s| s.parse().ok())
        .unwrap_or(160);
    let cells: usize = args
        .get(2)
        .and_then(|s| s.parse().ok())
        .unwrap_or(40);
    let steps: usize = args
        .get(3)
        .and_then(|s| s.parse().ok())
        .unwrap_or(1200);
    let seed: u64 = args
        .get(4)
        .and_then(|s| s.parse().ok())
        .unwrap_or(7);

    let capacity = 2.0;
    let regrow = 0.8;
    let income = 0.8;
    let maintenance = 0.6;
    let damage_rate = 0.02;
    let energy = 5.0;
    let move_cost = 0.02;
    let repair_cost = 0.05;

    let world = World {
        income,
        maintenance_cost: maintenance,
        repair_cost,
        damage_rate,
        capacity: 10.0,
        read_budget: 3,
        share: Default::default(),
    };
    let field = Field::new(cells, capacity, regrow).expect("field");
    let spawner = if args.iter().any(|a| a == "--random") {
        "random"
    } else {
        "even"
    };
    let mut life = if spawner == "random" {
        Life::spawn(world, field, n, energy, move_cost, Policy::Sighted, seed, 300)
    } else {
        Life::spawn_even(world, field, n, energy, move_cost, Policy::Sighted, seed, 300)
    }
    .expect("population");

    println!(
        "n={} cells={} steps={} seed={} spawn={} M={} r={} income={} maintenance={} damage={}",
        n, cells, steps, seed, spawner, capacity, regrow, income, maintenance, damage_rate
    );
    println!();
    println!(
        "{:>6} {:>6} {:>8} {:>7} {:>8}  {}",
        "step", "alive", "empty", "maxocc", "field", "event"
    );

    let mut prev_alive = life.census().alive;
    let mut prev_empty = cells - occupancy(&life).iter().filter(|&&c| c > 0).count();
    let mut prev_occ = occupancy(&life);

    let mut alive_rose = false;
    let mut empty_fell = false;
    let mut deaths_at: Vec<usize> = Vec::new();
    let mut refills_at: Vec<usize> = Vec::new();

    for s in 0..steps {
        life.advance().expect("step");
        let occ = occupancy(&life);
        let census = life.census();
        let alive = census.alive;
        let empty = cells - occ.iter().filter(|&&c| c > 0).count();
        let maxocc = occ.iter().copied().max().unwrap_or(0);

        let mut event = String::new();
        if alive > prev_alive {
            alive_rose = true;
            event.push_str("ALIVE ROSE ");
        }
        if empty < prev_empty {
            empty_fell = true;
            event.push_str("EMPTY FELL ");
        }
        if alive < prev_alive {
            deaths_at.push(s + 1);
            event.push_str(&format!("deaths +{} ", prev_alive - alive));
        }
        // A cell that was empty and now has someone: a refill.
        let mut refilled = 0;
        for c in 0..cells {
            if prev_occ[c] == 0 && occ[c] > 0 {
                refilled += 1;
            }
        }
        if refilled > 0 {
            refills_at.push(s + 1);
            event.push_str(&format!("refilled {} ", refilled));
        }

        let show = s < 20 || s % 100 == 99 || !event.is_empty();
        if show {
            println!(
                "{:>6} {:>6} {:>8} {:>7} {:>8.3}  {}",
                s + 1,
                alive,
                empty,
                maxocc,
                census.mean_energy,
                event.trim_end()
            );
        }

        prev_alive = alive;
        prev_empty = empty;
        prev_occ = occ;
    }

    let occ = occupancy(&life);
    let census = life.census();
    let empty_cells: Vec<usize> = (0..cells).filter(|&c| occ[c] == 0).collect();
    let empty = empty_cells.len();
    let maxocc = occ.iter().copied().max().unwrap_or(0);

    println!();
    println!("--- summary ---");
    println!("alive            {}", census.alive);
    println!("empty cells      {}", empty);
    if !empty_cells.is_empty() {
        println!("empty cell ids   {:?}", empty_cells);
    }
    println!("max per cell     {}", maxocc);
    println!("crowding alive/cells   {:.4}", census.alive as f64 / cells as f64);
    println!(
        "crowding alive/occupied {:.4}",
        census.alive as f64 / (cells - empty) as f64
    );
    println!("mean energy      {:.4}", census.mean_energy);
    println!();
    println!("P1 alive never rose:      {}", !alive_rose);
    println!("P2 empty never fell:      {}", !empty_fell);
    println!("steps with deaths:        {:?}", deaths_at);
    println!("steps with refills:       {:?}", refills_at);
}
