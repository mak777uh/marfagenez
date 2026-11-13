use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::World;

fn main() {
    println!("=== AM) can a poor cell hold 2? push poor ceiling up ===");
    println!("{:>7} {:>8} {:>9} {:>8} {:>8}", "poor", "M*r", "pred_k", "poor_n", "alive");
    for poor in [1.40f64, 1.60, 1.80, 2.00, 2.60, 3.20] {
        let w = World { income: 1.05, maintenance_cost: 0.5, repair_cost: 1.5, damage_rate: 0.02, capacity: 10.0, read_budget: 3, share: Default::default() };
        let f = Field::alternating(40, 2.0, poor, 0.8).unwrap();
        let mut l = Life::spawn_even(w, f, 320, 10.0, 0.0, Policy::Stay, 1, 100000).unwrap();
        for _ in 0..5000 { l.advance(); }
        let s = l.samples();
        let pr = s.iter().filter(|x| x.alive && x.cell % 2 == 1).count();
        let mr = poor * 0.8; let need = 0.53;
        let ks = ((mr - need) / 1.05 + 1e-12).floor() as i64 + 1;
        let ku = (mr / 1.05 + 1e-12).floor() as i64;
        let kpred = if mr < need { 0 } else { ks.max(ku).max(0) };
        println!("{:>7.2} {:>8.4} {:>9} {:>8} {:>8}", poor, mr, kpred, pr/20, l.census().alive);
    }
    println!();
    println!("=== AN) uniform field, vary M, income=1.05 ===");
    println!("{:>7} {:>8} {:>9} {:>8} {:>8}", "M", "M*r", "pred_k", "crowd", "alive");
    for mm in [1.2f64, 1.6, 2.0, 2.4, 3.0, 4.0] {
        let w = World { income: 1.05, maintenance_cost: 0.5, repair_cost: 1.5, damage_rate: 0.02, capacity: 10.0, read_budget: 3, share: Default::default() };
        let f = Field::new(40, mm, 0.8).unwrap();
        let mut l = Life::spawn_even(w, f, 320, 10.0, 0.0, Policy::Stay, 1, 100000).unwrap();
        for _ in 0..5000 { l.advance(); }
        let mr = mm * 0.8; let need = 0.53;
        let ks = ((mr - need) / 1.05 + 1e-12).floor() as i64 + 1;
        let ku = (mr / 1.05 + 1e-12).floor() as i64;
        let kpred = if mr < need { 0 } else { ks.max(ku).max(0) };
        println!("{:>7.2} {:>8.4} {:>9} {:>8.2} {:>8}", mm, mr, kpred, l.census().alive as f64/40.0, l.census().alive);
    }
}
