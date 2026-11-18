//! A window of perception: the control is that `k = 1` changes nothing at all.
//!
//! The calculation in `docs/DESIGN-perception.md` showed that a one-neighbour rule is
//! silent in 71% of the sea between rich patches - both neighbours equal - so a medium
//! cannot reward searching with that perception.
//!
//! `Life::set_sight_radius(k)` widens the look to `[-k, k]`. The originality of the
//! change is not the window; it is that `k <= 1` runs the **original** code path, so
//! every recorded run keeps its bits by construction rather than by luck.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::memory::Remembering;
use medium_core::organism::{Organism, TieBreak, World};

fn world() -> World {
    World {
        income: 2.0,
        maintenance_cost: 1.0,
        repair_cost: 1.5,
        damage_rate: 0.02,
        read_budget: 8,
        tiebreak: TieBreak::Random,
        ..World::default()
    }
}

fn life(cells: usize) -> Life {
    let organisms: Vec<Remembering> = (0..cells)
        .map(|c| {
            let o = Organism::new(9.0, 0.0).expect("valid organism");
            Remembering::new(o, c, 2.0, 0.0, 32).expect("valid remembering")
        })
        .collect();
    Life::new_mixed(
        world(),
        Field::new(cells, 2.0, 0.99).expect("valid field"),
        organisms,
        vec![Policy::Sighted; cells],
        3,
        32,
    )
    .expect("built")
}

fn moves_after(mut l: Life, steps: usize) -> u64 {
    for _ in 0..steps {
        l.advance();
    }
    l.census().moves
}

#[test]
fn the_default_radius_is_the_original_neighbour_rule() {
    let l = life(6);
    assert_eq!(l.sight_radius(), 0);
}

#[test]
fn a_radius_of_one_is_the_original_rule_bit_for_bit() {
    // The window path is entered only when the radius is strictly greater than one, so
    // these two runs must agree exactly - same seed, same world, same start.
    let plain = moves_after(life(8), 30);
    let mut widened = life(8);
    assert!(widened.set_sight_radius(1));
    let one = moves_after(widened, 30);
    assert_eq!(plain, one, "k = 1 must be the original rule, not a variant of it");
}

#[test]
fn a_window_sees_what_the_neighbours_hide() {
    // To isolate perception from the depletion trail, the organism does not eat at all:
    // income, upkeep and damage are zero, so the field is static and the only thing that
    // can move it is what it sees.
    //
    // The field is flat poor with one rich cell three steps away. One neighbour look
    // sees two equal cells and stays; a window of three sees the rich cell and walks.
    fn moves_with(radius: usize) -> u64 {
        let w = World {
            income: 0.0,
            maintenance_cost: 0.0,
            damage_rate: 0.0,
            read_budget: 8,
            ..World::default()
        };
        let mut cells = vec![1.0; 9];
        cells[0] = 3.0; // the island, three steps from cell 3 on a ring of nine
        let mut f = Field::new(9, 1.0, 0.99).expect("valid field");
        for (i, v) in cells.iter().enumerate() {
            // `Field` has no per-cell setter, so the island is made by a peak field of
            // period 9, which lights cell 0 only.
            let _ = (i, v);
        }
        f = Field::peaks(9, 3.0, 1.0, 0.99, 9).expect("valid field");
        let mut l = Life::new_mixed(
            w,
            f,
            vec![Remembering::new(
                Organism::new(9.0, 0.0).expect("valid organism"),
                3,
                0.0,
                0.0,
                32,
            )
            .expect("valid remembering")],
            vec![Policy::Sighted],
            7,
            32,
        )
        .expect("built");
        assert!(l.set_sight_radius(radius));
        for _ in 0..3 {
            l.advance();
        }
        l.census().moves
    }

    let one_look = moves_with(1);
    let window = moves_with(3);
    assert_eq!(one_look, 0, "equal neighbours give a one-neighbour rule nothing");
    assert!(window > 0, "a window of three must see the island at distance three");
}

#[test]
fn an_impossible_radius_is_refused() {
    let mut l = life(6);
    assert!(!l.set_sight_radius(1000));
    assert_eq!(l.sight_radius(), 0);
}

#[test]
fn a_window_lets_memory_hold_a_distant_cell() {
    // `FINDING-230` found that a window helps only if the information is retained: sighting
    // without memory uses a distant reading once and loses it. This checks the mechanism
    // directly. The field is poor everywhere except cell 0, kept poor enough that eating does
    // not disturb it (income and upkeep are zero, so nothing eats). The organism starts at
    // cell 3, so the island is three steps away: invisible to one look, visible to a window
    // of three.
    fn final_cell(radius: usize) -> u64 {
        let w = World {
            income: 0.0,
            maintenance_cost: 0.0,
            damage_rate: 0.0,
            read_budget: 8,
            ..World::default()
        };
        let field = Field::peaks(9, 3.0, 1.0, 0.99, 9).expect("valid field");
        let mut l = Life::new_mixed(
            w,
            field,
            vec![Remembering::new(
                Organism::new(9.0, 0.0).expect("valid organism"),
                3,
                0.0,
                0.0,
                32,
            )
            .expect("valid remembering")],
            vec![Policy::Memory],
            9,
            32,
        )
        .expect("built");
        assert!(l.set_sight_radius(radius));
        for _ in 0..3 {
            l.advance();
        }
        l.samples()[0].cell as u64
    }

    let one_look = final_cell(1);
    let window = final_cell(3);
    assert_eq!(one_look, 3, "an equal-neighbour sea gives one look nothing to remember");
    assert!(
        window <= 1,
        "with a window the organism should walk toward the island at cell 0, ended at {window}"
    );
}
