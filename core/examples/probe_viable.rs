use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::World;

fn survives(world: &World, steps: usize) -> bool {
    let field = Field::new(1, 10.0, 1.0).expect("field");
    let mut life = match Life::spawn_even(*world, field, 1, world.capacity, 0.0, Policy::Stay, 1, 0)
    {
        Some(l) => l,
        None => return false,
    };
    for _ in 0..steps {
        life.advance();
    }
    life.census().alive > 0
}

/// The candidate condition: the step's surplus must cover one step's repair.
fn predicted(w: &World) -> bool {
    let surplus = w.income - w.maintenance_cost;
    let repair = w.damage_rate * w.repair_cost;
    surplus >= repair
}

fn main() {
    let mut agree = 0;
    let mut disagree = 0;
    let mut dis: Vec<String> = Vec::new();

    let incomes = [0.5, 1.0, 2.0, 5.0];
    let maints = [0.0, 0.3, 0.6, 0.9];
    let repairs = [1.0, 1.5, 5.0, 50.0];
    let damages = [0.0, 0.01, 0.05, 0.2];
    let caps = [0.5, 2.0, 10.0];

    for &income in &incomes {
        for &maint in &maints {
            for &repair in &repairs {
                for &damage in &damages {
                    for &cap in &caps {
                        let w = World {
                            income,
                            maintenance_cost: maint,
                            repair_cost: repair,
                            damage_rate: damage,
                            capacity: cap,
                            ..World::default()
                        };
                        let actual = survives(&w, 500);
                        let pred = predicted(&w);
                        if actual == pred {
                            agree += 1;
                        } else {
                            disagree += 1;
                            if dis.len() < 12 {
                                dis.push(format!(
                                    "income={} maint={} repair={} damage={} cap={} -> actual={} pred={} (surplus={:.4} repair_price={:.4})",
                                    income, maint, repair, damage, cap, actual, pred,
                                    income - maint, damage * repair
                                ));
                            }
                        }
                    }
                }
            }
        }
    }

    println!("agree={} disagree={}", agree, disagree);
    for d in dis {
        println!("  {}", d);
    }
}
