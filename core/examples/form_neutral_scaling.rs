//! Эксперимент 1.2: зависит ли нейтральная точка мутации от длины прогона?
//!
//! `F-014` даёт `δ_c ≈ σ_g · √(2 ln N)` и сам называет различителем «зависимость δ_c от N».
//! Если измеренная нейтральная точка `p_grow* ≈ 0.27` (FINDING-221) и есть эта `δ_c`, то при смене
//! числа мутаций `N` она обязана сдвинуться на `σ_g·√(2 ln N)`.
//!
//! ПРЕДСКАЗАНИЕ (записано до прогона):
//!   F-014: `p*` растёт с `N` как `√(2 ln N)`; при `σ_g = 0.1` это 0.372 (N=10³) → 0.445 (N=2·10⁴),
//!          то есть сдвиг ≈ 0.07 вправо.
//!   баланс: `p*` — точка равновесия роста и удаления, свойство оператора мутации; от длины прогона
//!          не зависит, сдвиг ≈ 0 в пределах 0.01.
//!
//! Метод: без экономии, только `Form::mutate`; старт — квадрат 3×3; хвост — последние
//! `max(20, min(200, steps/10))` шагов; 8 сидов на точку; сетка 0.24…0.30 с шагом 0.005.

use medium_core::form::Form;
use medium_core::Rng;

fn run(p_grow: f64, seed: u64, steps: usize) -> f64 {
    let mut rng = Rng::new(seed);
    let mut f = Form::square(3);
    let tail_len = (steps / 10).clamp(20, 200);
    let mut tail = Vec::with_capacity(tail_len);
    for step in 0..steps {
        if let Some(next) = f.mutate(&mut rng, p_grow) {
            f = next;
        }
        if step >= steps - tail_len {
            tail.push(f.cells() as f64);
        }
    }
    tail.iter().sum::<f64>() / tail.len() as f64
}

fn mean(p_grow: f64, steps: usize, seeds: u64) -> f64 {
    (1..=seeds).map(|s| run(p_grow, s, steps)).sum::<f64>() / seeds as f64
}

/// Где средний размер пересекает старт (9 клеток): линейная интерполяция между узлами сетки.
fn crossing(steps: usize, seeds: u64) -> Option<(f64, Vec<(f64, f64)>)> {
    let mut rows = Vec::new();
    let mut p = 0.24_f64;
    while p <= 0.3001 {
        rows.push((p, mean(p, steps, seeds)));
        p += 0.005;
    }
    for w in rows.windows(2) {
        if w[0].1 <= 9.0 && w[1].1 > 9.0 {
            let (x0, y0) = w[0];
            let (x1, y1) = w[1];
            let t = (9.0 - y0) / (y1 - y0);
            return Some((x0 + t * (x1 - x0), rows));
        }
    }
    None
}

fn main() {
    println!("ЭКСПЕРИМЕНТ 1.2 · нейтральная точка против длины прогона");
    println!("{:<10} {:<12} {:<12}", "steps", "p*", "по F-014");
    let seeds = 8u64;
    let mut out = Vec::new();
    for steps in [200usize, 1000, 2000, 5000, 20000] {
        match crossing(steps, seeds) {
            Some((p_star, rows)) => {
                let pred = 0.1 * ((2.0 * (steps as f64).ln()).sqrt() - (2.0 * 1000.0_f64.ln()).sqrt()) + 0.372;
                println!("{steps:<10} {p_star:<12.3} {pred:<12.3}");
                out.push((steps, p_star));
                if steps == 2000 {
                    println!("   сетка при 2000 шагах:");
                    for (p, m) in &rows {
                        println!("     p_grow {p:.3}  средний размер {m:>6.2}");
                    }
                }
            }
            None => println!("{steps:<10} пересечения нет"),
        }
    }
    println!();
    if out.len() >= 2 {
        let (s0, p0) = out[0];
        let (s1, p1) = *out.last().unwrap();
        println!("сдвиг p* от {s0} к {s1} шагам: {:+.3}", p1 - p0);
        println!("предсказание F-014 (σ_g = 0.1): {:+.3}",
                 0.1 * ((2.0 * (s1 as f64).ln()).sqrt() - (2.0 * (s0 as f64).ln()).sqrt()));
    }
}
