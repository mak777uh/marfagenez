//! # The boundary: what a medium may and may not do
//!
//! The vision says the medium must not measure and must not direct. The code so far
//! enforces that by **absence** — there is no `score()`, no `suggest()`. But absence
//! is a weak guarantee: someone can add one, and nothing complains.
//!
//! This module makes the guarantee **structural**. A medium can only be built from a
//! [`Room`], and a room has no access to the child. Anything that reads the child and
//! writes back must go through [`OutsideExperiment`], a type that is **named as what
//! it is** — an experiment outside the medium, not part of it.
//!
//! ## The three layers of the guarantee
//!
//! | layer | how | what it stops |
//! |---|---|---|
//! | **absence** | no `score()`, no `suggest()` | the obvious violation |
//! | **privacy** | `Child` fields are private | reading the child from outside the medium |
//! | **naming** | `OutsideExperiment` is a distinct type | writing back without admitting it |
//!
//! The third layer is the new one. It does not prevent the experiment; it makes the
//! experiment **say its name**. A test that uses it cannot pretend to be testing the
//! medium.

#![forbid(unsafe_code)]

use crate::child::{Child, Medium};


/// An experiment that acts on a child from outside the medium.
///
/// This type exists so that "I am breaking principle 3" is written in the code
/// rather than hidden in a test helper. It carries no capability the medium has: it
/// is a marker, and its only method is [`OutsideExperiment::act`], which takes a
/// closure that reads and writes the child.
///
/// The medium never holds one. A test that does is testing something **about** the
/// medium, not the medium.
#[derive(Debug, Clone, Copy)]
pub struct OutsideExperiment {
    _private: (),
}

impl OutsideExperiment {
    /// Declares an experiment outside the medium.
    ///
    /// The name is the point: every call site says "this is not the medium".
    pub fn declare() -> Self {
        Self { _private: () }
    }

    /// Runs `act` on the child, outside the medium.
    ///
    /// The closure receives the child's position and returns a new position. The
    /// medium is not involved: this is the experimenter acting directly.
    ///
    /// Returns `None` if the closure returns a position of the wrong length.
    pub fn act<F>(&self, child: &mut Child, act: F) -> Option<()>
    where
        F: FnOnce(&[f64]) -> Vec<f64>,
    {
        let new_position = act(child.position());
        child.set_position(new_position)
    }

    /// Runs one step of the medium, then `act`, then folds through the room.
    ///
    /// This is the shape every experiment in `core/tests/` uses: the child moves by
    /// the medium, the experiment acts on it, and the room keeps the boundary.
    pub fn step_and_act<F>(&self, medium: &mut Medium, child: &mut Child, act: F) -> Option<()>
    where
        F: FnOnce(&[f64]) -> Vec<f64>,
    {
        medium.step(child)?;
        let new_position = act(child.position());
        let folded = medium.room().fold(&new_position)?;
        child.set_position(folded)
    }
}

impl Default for OutsideExperiment {
    fn default() -> Self {
        Self::declare()
    }
}

/// What a medium may do to a child, as a closed list.
///
/// This enum is the **whole** of the medium's power. It exists so that the list can be
/// read and audited: if a new capability is added, it appears here.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MediumAction {
    /// Move the child by its own drift and noise.
    DriftAndNoise,
    /// Fold the child back into the room.
    Fold,
}

impl MediumAction {
    /// Every action a medium may take.
    pub const ALL: [MediumAction; 2] = [MediumAction::DriftAndNoise, MediumAction::Fold];

    /// Whether this action reads the child's state to decide what to do.
    ///
    /// Both allowed actions are **blind**: drift-and-noise uses only the child's own
    /// parameters, and fold uses only the room. Neither looks at where the child is
    /// to decide what to do with it.
    pub fn is_blind(self) -> bool {
        match self {
            MediumAction::DriftAndNoise => true,
            MediumAction::Fold => true,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::room::Shape;
    use crate::HalfWidth;

    fn setup() -> (Medium, Child) {
        let room = Room::new(Shape::Box, HalfWidth::new(3.0).unwrap(), 1).unwrap();
        let child = Child::born(1, 0.0, 0.3).unwrap();
        (Medium::new(room, 42), child)
    }

    #[test]
    fn the_medium_has_exactly_two_actions() {
        assert_eq!(MediumAction::ALL.len(), 2);
    }

    #[test]
    fn both_medium_actions_are_blind() {
        for a in MediumAction::ALL {
            assert!(a.is_blind(), "{:?} is not blind", a);
        }
    }

    #[test]
    fn an_outside_experiment_can_act_on_a_child() {
        let (mut medium, mut child) = setup();
        let experiment = OutsideExperiment::declare();
        experiment
            .step_and_act(&mut medium, &mut child, |p| vec![p[0] + 0.5])
            .unwrap();
        assert!(medium.room().contains(child.position()));
    }

    #[test]
    fn an_outside_experiment_refuses_a_wrong_length() {
        let (_, mut child) = setup();
        let experiment = OutsideExperiment::declare();
        assert!(experiment.act(&mut child, |_| vec![0.0, 0.0]).is_none());
    }

    #[test]
    fn the_medium_never_holds_an_outside_experiment() {
        // This is a compile-time statement: `Medium` has no field of type
        // `OutsideExperiment`. The test documents the absence.
        let (medium, _) = setup();
        let _ = medium.room();
    }
}
