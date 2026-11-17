//! Why did the mutation test see only growth? Print the sequence.

use medium_core::form::Form;
use medium_core::Rng;

fn main() {
    let mut rng = Rng::new(7);
    let mut f = Form::square(3);
    let mut sizes = String::new();
    let mut grew = 0;
    let mut shrank = 0;
    let mut refused = 0;
    for _ in 0..60 {
        match f.mutate(&mut rng, 0.55) {
            Some(next) => {
                if next.cells() > f.cells() {
                    grew += 1;
                } else {
                    shrank += 1;
                }
                f = next;
            }
            None => refused += 1,
        }
        sizes.push_str(&format!("{} ", f.cells()));
    }
    println!("sizes: {sizes}");
    println!("grew {grew}, shrank {shrank}, refused {refused}");

    // and directly: can a 3x3 corner be removed?
    let square = Form::square(3);
    println!("shrink corner: {:?}", square.shrink(0, 0).map(|f| f.cells()));
    println!("shrink centre: {:?}", square.shrink(1, 1).map(|f| f.cells()));
}
