//! Gate probes for the multi-dimensional room.
//!
//! Each probe plants a defect and asserts the corresponding gate catches it.
//!
//! | probe | planted defect | the real error it mirrors |
//! |---|---|---|
//! | `probe_single_reflection_ball` | one reflection instead of a periodic fold | the bug found while writing `room.rs` |
//! | `probe_box_as_ball` | a box used where a ball is meant | E2: two rooms confused |
//! | `probe_wrong_dims` | a point with the wrong number of traits | a silent shape mismatch |

#[cfg(test)]
mod probes {
    use crate::room::{Room, Shape};
    use crate::HalfWidth;

    fn room(shape: Shape, b: f64, d: usize) -> Room {
        Room::new(shape, HalfWidth::new(b).unwrap(), d).unwrap()
    }

    /// The buggy ball fold: a single reflection `2B - r`.
    fn buggy_ball_fold(point: &[f64], b: f64) -> Vec<f64> {
        let r = point.iter().map(|x| x * x).sum::<f64>().sqrt();
        if r <= b {
            return point.to_vec();
        }
        let scale = (2.0 * b - r) / r;
        point.iter().map(|x| x * scale).collect()
    }

    #[test]
    fn probe_single_reflection_ball() {
        // The planted defect: a point far outside the ball.
        // A single reflection gives a negative radius and throws the point out.
        let b = 3.0;
        let far = vec![12.0; 4]; // radius 24, well beyond 2B = 6
        let bad = buggy_ball_fold(&far, b);
        let bad_norm = bad.iter().map(|x| x * x).sum::<f64>().sqrt();

        assert!(
            bad_norm > b,
            "GATE FAILED: the buggy fold produced a point inside the ball, \
             so the single-reflection defect is undetectable (norm {})",
            bad_norm
        );

        // The correct fold keeps it inside.
        let r = room(Shape::Ball, b, 4);
        let good = r.fold(&far).unwrap();
        assert!(
            r.contains(&good),
            "the correct fold must keep a far point inside, got {:?}",
            good
        );
    }

    #[test]
    fn probe_box_as_ball() {
        // The planted defect: treating a box as a ball.
        // A corner of the box is far outside the ball of the same radius.
        let b = 3.0;
        let corner = vec![2.9; 8];
        let bx = room(Shape::Box, b, 8);
        let bl = room(Shape::Ball, b, 8);

        let in_box = bx.contains(&corner);
        let in_ball = bl.contains(&corner);
        assert!(
            in_box && !in_ball,
            "GATE FAILED: the corner is (in box {}, in ball {}), so the two rooms \
             are indistinguishable",
            in_box,
            in_ball
        );
    }

    #[test]
    fn probe_wrong_dims() {
        // The planted defect: a point whose length does not match the room.
        let r = room(Shape::Box, 3.0, 4);
        assert!(
            r.fold(&[1.0, 2.0]).is_none(),
            "GATE FAILED: a point with the wrong number of traits was accepted"
        );
        assert!(
            r.fold(&[1.0, 2.0, 3.0, 4.0]).is_some(),
            "a point with the right number of traits must be accepted"
        );
    }

    #[test]
    fn probe_box_and_ball_diverge_with_dims() {
        // The planted defect: assuming the shape does not matter.
        // At d = 1 the two rooms agree; at d = 8 they do not.
        let b = 3.0;
        let d1 = vec![2.9];
        let r1b = room(Shape::Box, b, 1);
        let r1l = room(Shape::Ball, b, 1);
        let fb = r1b.fold(&d1).unwrap();
        let fl = r1l.fold(&d1).unwrap();
        assert!(
            (fb[0] - fl[0]).abs() < 1e-9,
            "at d=1 a box and a ball are the same room ({} vs {})",
            fb[0],
            fl[0]
        );

        let d8 = vec![2.9; 8];
        let r8b = room(Shape::Box, b, 8);
        let r8l = room(Shape::Ball, b, 8);
        assert_ne!(
            r8b.fold(&d8).unwrap(),
            r8l.fold(&d8).unwrap(),
            "GATE FAILED: at d=8 a box and a ball gave the same answer, so the \
             shape distinction is undetectable"
        );
    }
}
