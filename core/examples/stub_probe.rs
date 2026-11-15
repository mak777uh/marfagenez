//! Prints whether the Lean bridge is real or a stub.
//!
//! `checks/stub_links.sh` runs this in a copy of the crate with `lean` hidden
//! from PATH. The stub returns 0 for every input, so `bridge::available()` is
//! `false` there; if it ever prints `true` on a stub, the stub is lying about
//! itself and every bridge test would be comparing zeros with zeros.
//!
//! Run: `cargo run --release --example stub_probe`

fn main() {
    println!("{}", medium_core::bridge::available());
}
