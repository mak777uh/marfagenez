//! # Probes for the boundary
//!
//! A gate that cannot fail is a slogan. These probes plant the violation the boundary
//! is supposed to catch, and assert that the violation is **visible**.
//!
//! | probe | planted defect | what it shows |
//! |---|---|---|
//! | `probe_a_measuring_medium_is_visible` | a medium that answers the population | it narrows the child |
//! | `probe_the_absence_is_real` | adding `score()` would be a change | the API has no such method |
//! | `probe_outside_experiment_is_named` | acting on a child | the type says so |

#[cfg(test)]
mod probes {
    use crate::boundary::{MediumAction, OutsideExperiment};
    use crate::child::{Child, Medium};
    use crate::room::{Room, Shape};
    use crate::HalfWidth;

    fn spread_of(pop: &[Child]) -> f64 {
        let n = pop.len();
        let mean: f64 = pop.iter().map(|c| c.position()[0]).sum::<f64>() / n as f64;
        (pop.iter()
            .map(|c| {
                let x = c.position()[0] - mean;
                x * x
            })
            .sum::<f64>()
            / n as f64)
            .sqrt()
    }

    #[test]
    fn probe_a_measuring_medium_is_visible() {
        // The planted defect: a medium that reads the population and answers it.
        // This is exactly what principle 3 forbids. The probe asserts that the
        // violation **shows up in the result** — a gate that could not see it would
        // be useless.
        let b = 3.0;
        let law = b / 3.0_f64.sqrt();

        // A silent medium.
        let room = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
        let mut silent = Medium::new(room, 9001);
        let mut pop: Vec<Child> = (0..1500)
            .map(|i| {
                let mut c = Child::born(1, 0.0, 0.3).unwrap();
                c.set_position(vec![((i as f64) * 0.001) - 0.75]).unwrap();
                c
            })
            .collect();
        for c in pop.iter_mut() {
            silent.run(c, 12000).unwrap();
        }
        let silent_spread = spread_of(&pop);

        // A measuring medium, built outside the medium with an explicit name.
        let experiment = OutsideExperiment::declare();
        let room2 = Room::new(Shape::Box, HalfWidth::new(b).unwrap(), 1).unwrap();
        let mut measuring = Medium::new(room2, 9001);
        let mut pop2: Vec<Child> = (0..1500)
            .map(|i| {
                let mut c = Child::born(1, 0.0, 0.3).unwrap();
                c.set_position(vec![((i as f64) * 0.001) - 0.75]).unwrap();
                c
            })
            .collect();
        for _ in 0..12000 {
            let mean: f64 = pop2.iter().map(|c| c.position()[0]).sum::<f64>() / pop2.len() as f64;
            let s = spread_of(&pop2);
            // The violation: the room answers the population.
            let new_b = (2.5 * s).clamp(0.05, 50.0);
            let room3 = Room::new(Shape::Box, HalfWidth::new(new_b).unwrap(), 1).unwrap();
            measuring.set_room(room3);
            let _ = mean;
            for c in pop2.iter_mut() {
                measuring.step(c).unwrap();
            }
        }
        let measuring_spread = spread_of(&pop2);

        // The silent medium reaches the law.
        assert!(
            (silent_spread - law).abs() / law < 0.15,
            "the silent medium should reach the law: {} vs {}",
            silent_spread,
            law
        );
        // The measuring medium does not: the violation is visible.
        assert!(
            (measuring_spread - law).abs() / law > 0.15,
            "GATE FAILED: the measuring medium gave the same spread as the silent one, \
             so the violation is invisible (silent {} measuring {} law {})",
            silent_spread,
            measuring_spread,
            law
        );
    }

    #[test]
    fn probe_the_absence_is_real() {
        // The planted defect: assuming the medium has a scoring method.
        // The probe cannot call one, because there is none. This test documents the
        // absence by listing the whole API.
        let actions = MediumAction::ALL;
        assert_eq!(actions.len(), 2, "the medium should have exactly two actions");
        assert!(actions.contains(&MediumAction::DriftAndNoise));
        assert!(actions.contains(&MediumAction::Fold));
        // There is no MediumAction::Score, ::Evaluate, ::Suggest, ::Goal.
        // If one were added, this count would change and the test would fail.
    }

    #[test]
    fn probe_outside_experiment_is_named() {
        // The planted defect: acting on a child without admitting it.
        // The probe shows that the only way to act is through a type that says
        // "outside experiment" in its name.
        let room = Room::new(Shape::Box, HalfWidth::new(3.0).unwrap(), 1).unwrap();
        let mut medium = Medium::new(room, 9002);
        let mut child = Child::born(1, 0.0, 0.3).unwrap();

        let experiment = OutsideExperiment::declare();
        experiment
            .step_and_act(&mut medium, &mut child, |p| vec![p[0] + 1.0])
            .unwrap();

        // The child moved by the medium plus the experiment, and stayed inside.
        assert!(medium.room().contains(child.position()));
    }
}
