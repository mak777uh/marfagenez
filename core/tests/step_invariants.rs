//! Property-style invariants for the one-step energy ledger and trace JSON.
//!
//! No new dependency is used: deterministic xoshiro RNG2 streams generate
//! seeds and resources, and a small parser round-trips the project's own JSON.

use medium_core::field::Field;
use medium_core::life::{Life, Policy};
use medium_core::organism::{Organism, RepairPolicy, World};
use medium_core::trace::{record, Frame, Sample, Trace};
use medium_core::{Rng2, RngVersion};

fn close_to_zero(value: f64, scale: f64) {
    let tolerance = 64.0 * f64::EPSILON * scale.abs().max(1.0);
    assert!(
        value.abs() <= tolerance,
        "ledger residual {value:.17e} exceeds tolerance {tolerance:.17e}"
    );
}

#[test]
fn income_spending_energy_delta_and_spill_balance_on_rng2_traces() {
    // Every generated resource is greater than maintenance, so this test
    // exercises the conservation ledger rather than starvation/negative debt.
    for seed in 0..64_u64 {
        let mut rng = Rng2::new(0xBA1A_ACE0_0000_0000_u64.wrapping_add(seed));
        let world = World {
            income: 2.0,
            maintenance_cost: 0.1,
            repair_cost: 1.5,
            damage_rate: 0.005,
            capacity: 12.0,
            ..World::default()
        };
        let mut organism = Organism::healthy(5.0).expect("valid starting organism");

        for step in 0..512 {
            let resource = 0.3 + 1.7 * rng.uniform();
            let energy_before = organism.energy();
            let damage_before = organism.damage();
            let taken = resource.max(0.0).min(world.income);

            // Reconstruct the exact step order in organism.rs. Repair is
            // all-or-nothing and is charged only when the strict affordability
            // condition in the implementation is true.
            let after_maintenance = energy_before + taken - world.maintenance_cost;
            let damage_after = (damage_before + world.damage_rate).min(1.0);
            let repair_spent = if damage_after > 0.0 {
                let price = damage_after * world.repair_cost;
                if price < after_maintenance { price } else { 0.0 }
            } else {
                0.0
            };
            let spent = world.maintenance_cost + repair_spent;
            let energy_before_cap = energy_before + taken - spent;
            assert!(
                energy_before_cap >= 0.0,
                "generated a debt state at seed={seed}, step={step}"
            );
            let expected_spill = (energy_before_cap - world.capacity).max(0.0);

            let alive = organism.step_with(&world, resource, RepairPolicy::AllOrNothing);
            let energy_after = organism.energy();
            let delta_energy = energy_after - energy_before;

            // taken - spent - ΔE - spill = 0
            close_to_zero(
                taken - spent - delta_energy - expected_spill,
                energy_before.abs() + taken + spent + world.capacity,
            );
            close_to_zero(
                energy_after - energy_before_cap.min(world.capacity),
                world.capacity + energy_before_cap,
            );
            if !alive {
                // In this fixture, only damage can kill; the reserve is kept
                // positive by construction.
                assert!(organism.damage() >= 1.0);
                break;
            }
        }
    }
}

#[test]
fn spill_is_zero_at_capacity_and_exactly_the_excess_above_it() {
    let world = World {
        income: 4.0,
        maintenance_cost: 1.0,
        repair_cost: 0.0,
        damage_rate: 0.0,
        capacity: 10.0,
        ..World::default()
    };

    let mut at_boundary = Organism::healthy(7.0).unwrap();
    assert!(at_boundary.step(&world, 4.0));
    assert_eq!(at_boundary.energy(), 10.0); // 7 + 4 - 1 = cap; spill = 0

    let mut above_boundary = Organism::healthy(9.0).unwrap();
    assert!(above_boundary.step(&world, 4.0));
    assert_eq!(above_boundary.energy(), 10.0); // 9 + 4 - 1 = 12; spill = 2
}

#[derive(Debug, PartialEq)]
enum Json {
    Object(Vec<(String, Json)>),
    Array(Vec<Json>),
    String(String),
    Number(String),
    Bool(bool),
    Null,
}

struct Parser<'a> {
    bytes: &'a [u8],
    at: usize,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        Self { bytes: input.as_bytes(), at: 0 }
    }

    fn whitespace(&mut self) {
        while self.at < self.bytes.len() && self.bytes[self.at].is_ascii_whitespace() {
            self.at += 1;
        }
    }

    fn take(&mut self, expected: u8) {
        self.whitespace();
        assert_eq!(self.bytes.get(self.at), Some(&expected), "expected byte {:?}", expected as char);
        self.at += 1;
    }

    fn string(&mut self) -> String {
        self.take(b'"');
        let mut out = String::new();
        while self.at < self.bytes.len() {
            let byte = self.bytes[self.at];
            self.at += 1;
            match byte {
                b'"' => return out,
                b'\\' => {
                    let escaped = *self.bytes.get(self.at).expect("truncated escape");
                    self.at += 1;
                    match escaped {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{0008}'),
                        b'f' => out.push('\u{000c}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        other => panic!("unsupported escape in trace JSON: {other:?}"),
                    }
                }
                0x00..=0x7f => out.push(byte as char),
                _ => {
                    self.at -= 1;
                    let rest = std::str::from_utf8(&self.bytes[self.at..]).expect("trace JSON utf-8");
                    let ch = rest.chars().next().expect("unicode scalar");
                    out.push(ch);
                    self.at += ch.len_utf8();
                }
            }
        }
        panic!("unterminated JSON string")
    }

    fn value(&mut self) -> Json {
        self.whitespace();
        match self.bytes.get(self.at).copied().expect("unexpected end of JSON") {
            b'{' => {
                self.at += 1;
                self.whitespace();
                let mut entries = Vec::new();
                if self.bytes.get(self.at) == Some(&b'}') {
                    self.at += 1;
                    return Json::Object(entries);
                }
                loop {
                    let key = self.string();
                    self.take(b':');
                    entries.push((key, self.value()));
                    self.whitespace();
                    match self.bytes.get(self.at) {
                        Some(b',') => self.at += 1,
                        Some(b'}') => { self.at += 1; break; }
                        other => panic!("expected comma or object end, got {other:?}"),
                    }
                }
                Json::Object(entries)
            }
            b'[' => {
                self.at += 1;
                self.whitespace();
                let mut values = Vec::new();
                if self.bytes.get(self.at) == Some(&b']') {
                    self.at += 1;
                    return Json::Array(values);
                }
                loop {
                    values.push(self.value());
                    self.whitespace();
                    match self.bytes.get(self.at) {
                        Some(b',') => self.at += 1,
                        Some(b']') => { self.at += 1; break; }
                        other => panic!("expected comma or array end, got {other:?}"),
                    }
                }
                Json::Array(values)
            }
            b'"' => Json::String(self.string()),
            b't' if self.bytes.get(self.at..self.at + 4) == Some(b"true") => {
                self.at += 4;
                Json::Bool(true)
            }
            b'f' if self.bytes.get(self.at..self.at + 5) == Some(b"false") => {
                self.at += 5;
                Json::Bool(false)
            }
            b'n' if self.bytes.get(self.at..self.at + 4) == Some(b"null") => {
                self.at += 4;
                Json::Null
            }
            _ => {
                let start = self.at;
                while self.at < self.bytes.len()
                    && matches!(self.bytes[self.at], b'-' | b'+' | b'.' | b'e' | b'E' | b'0'..=b'9')
                {
                    self.at += 1;
                }
                assert!(self.at > start, "invalid JSON token at byte {}", self.at);
                Json::Number(
                    std::str::from_utf8(&self.bytes[start..self.at])
                        .unwrap()
                        .to_string(),
                )
            }
        }
    }

    fn parse(mut self) -> Json {
        let value = self.value();
        self.whitespace();
        assert_eq!(self.at, self.bytes.len(), "trailing JSON bytes");
        value
    }
}

impl Json {
    fn get(&self, key: &str) -> &Json {
        match self {
            Json::Object(entries) => &entries.iter().find(|(k, _)| k == key)
                .unwrap_or_else(|| panic!("missing JSON key {key}")).1,
            _ => panic!("expected JSON object for key {key}"),
        }
    }

    fn array(&self) -> &[Json] {
        match self { Json::Array(values) => values, _ => panic!("expected JSON array") }
    }

    fn string(&self) -> &str {
        match self { Json::String(value) => value, _ => panic!("expected JSON string") }
    }

    fn usize(&self) -> usize {
        match self {
            Json::Number(value) => value.parse().expect("usize JSON number"),
            _ => panic!("expected JSON integer"),
        }
    }

    fn i32(&self) -> i32 {
        match self {
            Json::Number(value) => value.parse().expect("i32 JSON number"),
            _ => panic!("expected JSON integer"),
        }
    }

    fn f64(&self) -> f64 {
        match self {
            Json::Number(value) => value.parse().expect("f64 JSON number"),
            Json::String(value) if value == "infinity" => f64::INFINITY,
            Json::String(value) if value == "-infinity" => f64::NEG_INFINITY,
            Json::String(value) if value == "nan" => f64::NAN,
            _ => panic!("expected JSON float"),
        }
    }

    fn boolean(&self) -> bool {
        match self { Json::Bool(value) => *value, _ => panic!("expected JSON bool") }
    }

    fn static_str(&self) -> &'static str {
        Box::leak(self.string().to_owned().into_boxed_str())
    }
}

fn trace_from_json(input: &str) -> Trace {
    let root = Parser::new(input).parse();
    let frames = root.get("frames").array().iter().map(|frame| {
        let field = frame.get("field").array().iter().map(Json::f64).collect();
        let samples = frame.get("samples").array().iter().map(|sample| Sample {
            slot: sample.get("slot").usize(),
            cell: sample.get("cell").usize(),
            energy: sample.get("energy").f64(),
            damage: sample.get("damage").f64(),
            alive: sample.get("alive").boolean(),
            memory_cell: sample.get("memory_cell").usize(),
            memory_level: sample.get("memory_level").f64(),
            direction: sample.get("direction").i32(),
            taken: sample.get("taken").f64(),
            prev_cell: sample.get("prev_cell").usize(),
        }).collect();
        Frame { step: frame.get("step").usize(), field, samples }
    }).collect();
    Trace {
        frames,
        hash: u64::from_str_radix(root.get("hash").string(), 16).unwrap(),
        policy: root.get("policy").static_str(),
        seed: root.get("seed").usize() as u64,
        rng_version: root.get("rng_version").static_str(),
        read_budget: root.get("read_budget").usize(),
        share: root.get("share").static_str(),
        tiebreak: root.get("tiebreak").static_str(),
        look_order: root.get("look_order").static_str(),
        birth_threshold: root.get("birth_threshold").f64(),
        birth_cost: root.get("birth_cost").f64(),
        max_population: root.get("max_population").usize(),
        read_cost: root.get("read_cost").f64(),
        read_period: root.get("read_period").usize(),
        look_on_shortfall: root.get("look_on_shortfall").boolean(),
    }
}

#[test]
fn trace_json_parse_and_serialize_is_byte_for_byte_stable() {
    let world = World {
        income: 1.0,
        maintenance_cost: 0.1,
        damage_rate: 0.001,
        repair_cost: 1.5,
        capacity: 10.0,
        ..World::default()
    };
    let field = Field::alternating(8, 2.0, 0.2, 0.8).unwrap();
    let mut life = Life::spawn_even_with_rng_version(
        world,
        field,
        8,
        5.0,
        0.0,
        Policy::Stay,
        0x51_7E,
        0,
        RngVersion::Xoshiro256PlusPlusV1,
    ).unwrap();
    let trace = record(&mut life, 12, 1);
    let json = trace.to_json();
    let parsed = trace_from_json(&json);
    assert_eq!(parsed.to_json().as_bytes(), json.as_bytes());
}
