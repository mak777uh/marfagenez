//! F3 из `DESIGN-fading.md`: возвращает ли избыток смысл, если починка идёт «насколько хватит запаса»?
//!
//! `FINDING-293` показал: при правиле «ровно `1.5·need`» плечи `yield = 2` и 3 совпадают по хэшу, потому что починка
//! упирается в предел, и избыток **пропадает**. Здесь починка просит сколько можно, а смерть — угасание
//! `μ(q) = rate·(1−q)²`.
//!
//! PREDICTION, before the run (`rate = 0.01`, `p = 2`, `d = 0.05`, горизонт 200 000, 300 сидов на плечо):
//!   (a) при `yield = 2` и `3` установившиеся `q` **разойдутся** (в 293 они совпадали);
//!   (b) средняя жизнь при `yield = 3` **больше**, чем при 2, примерно на треть;
//!   (c) при `yield = 1` форма по-прежнему быстро гибнет — избытка нет.

use medium_core::organ::{mortality, Flow, Part, RepairMode};
use medium_core::Rng;

const Q_MIN: f64 = 0.2;
const D: f64 = 0.05;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const STEPS: usize = 200_000;
const SEEDS: usize = 300;

fn hash_of(values: &[f64]) -> String {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for v in values {
        h ^= v.to_bits();
        h = h.wrapping_mul(0x100_0000_01b3);
    }
    format!("{h:016x}")
}

/// One sampled life with fading mortality, driven by the settled `q` of the two parts.
fn mean_life(yield_rate: f64) -> (f64, f64, f64, String) {
    // first settle the deterministic economy, with no death at all
    let mut f = Flow::new(Part::new(1.0, D, 1.0), Part::new(1.0, D, 1.0), Q_MIN, 10.0);
    f.yield_rate = yield_rate;
    f.repair_mode = RepairMode::Fill;
    let mut trace = Vec::with_capacity(200);
    for step in 1..=STEPS {
        // keep the pair alive while settling: fading is applied separately below
        if !f.step() {
            return (0.0, f.a.q, f.b.q, hash_of(&trace));
        }
        if step % 1000 == 0 {
            trace.push(f.a.q);
            trace.push(f.b.q);
        }
    }
    let q = f.a.q.min(f.b.q);
    let mu = mortality(q, RATE, P);

    // then the lifetime at that settled state
    let mut total = 0.0;
    let mut counted = 0;
    for seed in 0..SEEDS {
        let mut rng = Rng::new(seed as u64 + 1);
        if let Some(steps) = medium_core::organ::sample_life(&mut rng, q, RATE, P, 2_000_000) {
            total += steps as f64;
            counted += 1;
        }
    }
    let life = if counted > 0 { total / counted as f64 } else { f64::NAN };
    let _ = mu;
    (life, f.a.q, f.b.q, hash_of(&trace))
}

fn main() {
    println!("{:>7} {:>8} {:>8} {:>10} {:>14} {:>10}", "yield", "q_a", "q_b", "mu", "mean life", "hash");
    let mut rows = Vec::new();
    for y in [1.0, 2.0, 3.0] {
        let (life, qa, qb, hash) = mean_life(y);
        let mu = mortality(qa.min(qb), RATE, P);
        println!("{y:>7.1} {qa:>8.4} {qb:>8.4} {mu:>10.6} {life:>14.0} {:>10}", &hash[..8]);
        rows.push((y, life, qa, qb, hash));
    }

    println!();
    let mut bad = 0;

    let a = rows[1].4 != rows[2].4;
    println!(
        "  {} (a) the two arms now diverge (their hashes differ): {} vs {}",
        if a { "ok   " } else { "WRONG" },
        &rows[1].4[..8],
        &rows[2].4[..8]
    );
    if !a {
        bad += 1;
    }

    let ratio = rows[2].1 / rows[1].1;
    let b = ratio > 1.1;
    println!(
        "  {} (b) a bigger surplus buys more life: {:.0} against {:.0} (ratio {ratio:.2})",
        if b { "ok   " } else { "WRONG" },
        rows[2].1,
        rows[1].1
    );
    if !b {
        bad += 1;
    }

    let c = rows[0].1 < rows[1].1;
    println!(
        "  {} (c) without a surplus life is shorter: {:.0} against {:.0}",
        if c { "ok   " } else { "WRONG" },
        rows[0].1,
        rows[1].1
    );
    if !c {
        bad += 1;
    }

    println!();
    if bad > 0 {
        println!("РАСХОЖДЕНИЙ: {bad}");
        std::process::exit(1);
    }
    println!("Проверка пройдена.");
}
