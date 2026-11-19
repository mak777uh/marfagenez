//! Наследование повреждения: вытесняют ли молодые старых?
//!
//! `FINDING-297` дал форме прошлое. Здесь два штамма в одном мире различаются только тем, **сколько повреждения
//! передаётся потомку**: A сбрасывает (`inherit = 0`), B несёт половину (`inherit = 0.5`).
//!
//! PREDICTION, before the run (`q = 0.5` у всех, `rate = 0.01`, `p = 2`, `floor = 0.0002`, `λ = 0.001`,
//! `δ = 0.001`, 200 форм, 200 000 шагов):
//!   (a) доля A **вырастет** выше 50 %, доля B упадёт — молодость даёт преимущество;
//!   (b) преимущество **умеренное**, а не полное вытеснение: отношение долей ≈ отношению жизней 339/258 ≈ 1.31;
//!   (c) средняя доля A окажется в диапазоне **52–62 %**.

use medium_core::organ::aging_mortality;
use medium_core::Rng;

const Q: f64 = 0.5;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const FLOOR: f64 = 0.0002;
const LAMBDA: f64 = 0.001;
const DELTA: f64 = 0.001;
const N: usize = 200;
const STEPS: usize = 200_000;

const INHERIT_B: f64 = 0.5;

struct Form {
    strain_a: bool,
    damage: f64,
}

fn run(inherit_b: f64) -> (f64, f64, f64) {
    let mut rng = Rng::new(20261119);
    let mut pop: Vec<Form> = (0..N)
        .map(|i| Form { strain_a: i % 2 == 0, damage: 0.0 })
        .collect();
    let mut share_history = Vec::new();

    for step in 1..=STEPS {
        // how fit is each strain right now: its expected remaining life at its mean damage
        let mean_damage = |a: bool| {
            let mut total = 0.0;
            let mut n = 0;
            for f in &pop {
                if f.strain_a == a {
                    total += f.damage;
                    n += 1;
                }
            }
            if n > 0 { total / n as f64 } else { 1e9 }
        };
        let life = |a: bool| {
            let mu = aging_mortality(Q, RATE, P, FLOOR, LAMBDA, mean_damage(a));
            1.0 / mu
        };
        let (la, lb) = (life(true), life(false));
        let total_life = la + lb;

        for i in 0..pop.len() {
            let mu = aging_mortality(Q, RATE, P, FLOOR, LAMBDA, pop[i].damage);
            let survive = (-mu).exp();
            let u = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
            if u > survive {
                // A death frees a place. The newcomer takes it with a probability set by the two strains' fitness, so
                // the strains COMPETE for places - without this the share cannot move at all, which is what the first
                // version of this example got wrong.
                let pick = (rng.next_u64() >> 11) as f64 / (1u64 << 53) as f64;
                let newcomer_a = pick * total_life < la;
                // the newborn carries a share of a random parent's damage of its own strain
                let parent_damage = {
                    let mut total = 0.0;
                    let mut n = 0;
                    for f in &pop {
                        if f.strain_a == newcomer_a {
                            total += f.damage;
                            n += 1;
                        }
                    }
                    if n > 0 { total / n as f64 } else { 0.0 }
                };
                let inherit = if newcomer_a { 0.0 } else { inherit_b };
                pop[i].strain_a = newcomer_a;
                pop[i].damage = inherit * parent_damage;
            } else {
                pop[i].damage += DELTA;
            }
        }
        if step % 1000 == 0 {
            let a = pop.iter().filter(|f| f.strain_a).count() as f64 / pop.len() as f64;
            share_history.push(a);
        }
    }

    let a_share = pop.iter().filter(|f| f.strain_a).count() as f64 / pop.len() as f64;
    let a_damage: f64 = pop.iter().filter(|f| f.strain_a).map(|f| f.damage).sum::<f64>()
        / pop.iter().filter(|f| f.strain_a).count().max(1) as f64;
    let b_damage: f64 = pop.iter().filter(|f| !f.strain_a).map(|f| f.damage).sum::<f64>()
        / pop.iter().filter(|f| !f.strain_a).count().max(1) as f64;

    (a_share, a_damage, b_damage)
}

fn main() {
    println!("{:>9} {:>9} {:>12} {:>12}", "inherit B", "share A", "damage A", "damage B");
    let mut rows = Vec::new();
    for inherit in [0.5, 0.8, 0.95] {
        let (a_share, a_dmg, b_dmg) = run(inherit);
        println!("{inherit:>9.2} {a_share:>9.3} {a_dmg:>12.3} {b_dmg:>12.3}");
        rows.push((inherit, a_share));
    }

    println!();
    let mut bad = 0;

    let a = rows.iter().all(|r| r.1 > 0.5) && rows.windows(2).all(|w| w[1].1 >= w[0].1);
    println!("  {} (a) A gains above half in every arm, and more with a bigger inherit", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    let b = rows.iter().all(|r| r.1 < 0.95);
    println!(
        "  {} (b) no arm goes extinct: {:?}",
        if b { "ok   " } else { "WRONG" },
        rows.iter().map(|r| (r.0, (r.1 * 1000.0).round() / 1000.0)).collect::<Vec<_>>()
    );
    if !b {
        bad += 1;
    }

    let c = (0.6..0.9).contains(&rows[2].1);
    println!("  {} (c) at inherit 0.95 the share is still below 0.9: {:.3}", if c { "ok   " } else { "WRONG" }, rows[2].1);
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
