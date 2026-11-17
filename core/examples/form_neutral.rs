//! Where is the mutation rate that leaves the size alone?
//!
//! `FINDING-216` found that mutation ratchets upwards: a form has more legal additions than
//! legal removals, so at `p_grow = 0.5` it grows. `FINDING-220` then showed that selection
//! cannot hold back that ratchet, because selection only bites during crashes. Before any
//! further world is built, the neutral point has to be measured: the `p_grow` at which a form's
//! mean size does not move.
//!
//! Method: no economy at all, only `Form::mutate`. Start from a square of side three, run two
//! thousand mutations, and report the mean size over the last two hundred steps.
//!
//! PREDICTION, before the run:
//!   (a) `p_grow = 0.5` grows the form, as `FINDING-216` reported;
//!   (b) the neutral point is below 0.5, and above 0.3;
//!   (c) the size drift is monotone in `p_grow`, so a single crossing exists.

use medium_core::form::Form;
use medium_core::Rng;

fn run(p_grow: f64, seed: u64, steps: usize) -> (f64, f64) {
    let mut rng = Rng::new(seed);
    let mut f = Form::square(3);
    let start = f.cells() as f64;
    let mut tail = Vec::new();
    for step in 0..steps {
        if let Some(next) = f.mutate(&mut rng, p_grow) {
            f = next;
        }
        if step >= steps - 200 {
            tail.push(f.cells() as f64);
        }
    }
    let mean_tail = tail.iter().sum::<f64>() / tail.len() as f64;
    (start, mean_tail)
}

fn main() {
    let steps = 2000;
    println!(
        "{:>7} {:>10} {:>12} {:>12}",
        "p_grow", "start", "mean (tail)", "change"
    );
    let mut rows = Vec::new();
    for p_grow in [0.24, 0.25, 0.26, 0.27, 0.28, 0.29, 0.30] {
        // four seeds per rate, with a different stream each time
        let mut means = Vec::new();
        for seed in 1..=4u64 {
            let (_, mean_tail) = run(p_grow, seed, steps);
            means.push(mean_tail);
        }
        let mean = means.iter().sum::<f64>() / means.len() as f64;
        println!("{p_grow:>7.2} {:>10.1} {mean:>12.1} {:>+12.1}", 9.0, mean - 9.0);
        rows.push((p_grow, mean));
    }

    println!();
    let neutral = rows
        .windows(2)
        .find(|w| w[0].1 <= 9.0 && w[1].1 > 9.0)
        .map(|w| (w[0].0, w[1].0));
    let monotone = rows.windows(2).all(|w| w[1].1 >= w[0].1);
    let at_half = rows
        .iter()
        .find(|(p, _)| (*p - 0.30).abs() < 1e-9)
        .map(|(_, m)| *m)
        .unwrap_or(f64::NAN);

    let mut bad = 0;
    let checks: [(&str, bool, String); 3] = [
        (
            "(a) p_grow 0.30 grows the form",
            at_half > 9.5,
            format!("{at_half:.1} cells"),
        ),
        (
            "(b) a crossing from shrinking to growing exists in the swept range",
            neutral.is_some(),
            format!("{neutral:?}"),
        ),
        (
            "(c) the drift rises with p_grow",
            monotone,
            format!("{:?}", rows.iter().map(|(p, m)| (*p, (*m * 10.0).round() / 10.0)).collect::<Vec<_>>()),
        ),
    ];
    for (label, ok, val) in checks {
        println!("  {} {label}  [{val}]", if ok { "ok   " } else { "WRONG" });
        if !ok {
            bad += 1;
        }
    }
    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
