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

struct Form {
    strain_a: bool,
    damage: f64,
}

fn main() {
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
                let inherit = if newcomer_a { 0.0 } else { 0.5 };
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

    println!("доля A: {:.3}, среднее повреждение A {a_damage:.3}, B {b_damage:.3}", a_share);
    println!("в начале: {:.3}, в конце: {:.3}", share_history[0], share_history[share_history.len() - 1]);

    println!();
    let mut bad = 0;

    let a = a_share > 0.5;
    println!("  {} (a) A gains above half: {a_share:.3}", if a { "ok   " } else { "WRONG" });
    if !a {
        bad += 1;
    }

    let ratio = a_share / (1.0 - a_share);
    let b = ratio > 1.05 && a_share < 0.95;
    println!(
        "  {} (b) the gain is moderate, not extinction: ratio {ratio:.2}",
        if b { "ok   " } else { "WRONG" }
    );
    if !b {
        bad += 1;
    }

    let c = (0.52..0.62).contains(&a_share);
    println!("  {} (c) the share lands in 52-62 %", if c { "ok   " } else { "WRONG" });
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
