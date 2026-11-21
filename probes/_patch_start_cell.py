import io, re, sys

p = '/root/marfagenez/core/src/bin/trace.rs'
s = io.open(p, encoding='utf-8').read()

# 1. new variable after `let mut even = false;`
s = s.replace(
    "    let mut even = false;\n",
    "    let mut even = false;\n    let mut start_cells: Option<Vec<usize>> = None;\n",
    1,
)

# 2. parse --start-cell
s = s.replace(
    '''            "--read-budget" => {''',
    '''            "--start-cell" => {
                i += 1;
                let raw = args.get(i).map(|s| s.as_str()).unwrap_or("");
                let mut v = Vec::new();
                for part in raw.split(',') {
                    let part = part.trim();
                    if part.is_empty() {
                        continue;
                    }
                    match part.parse::<usize>() {
                        Ok(c) => v.push(c),
                        Err(_) => {
                            eprintln!(
                                "refusing to run: --start-cell {} is not a list of cell indices.\\n             Pass e.g. --start-cell 0,2 to put organism 0 on cell 0 and\\n             organism 1 on cell 2. The list must have exactly --n entries.",
                                raw
                            );
                            std::process::exit(2);
                        }
                    }
                }
                start_cells = Some(v);
            }
            "--read-budget" => {''',
    1,
)

# 3. help line
s = s.replace(
    "[--rich X] [--poor X] [--regrow X] [--layout even]",
    "[--rich X] [--poor X] [--regrow X] [--layout even] [--start-cell 0,2]",
    1,
)

# 4. validation + use
old = '''    let spawned = if even {
        Life::spawn_even(world, field, n, energy, move_cost, policy, seed, memory_life)
    } else {
        Life::spawn(world, field, n, energy, move_cost, policy, seed, memory_life)
    };'''
new = '''    // `--start-cell` is the only way to ask a question about a particular
    // cell: `spawn` places organisms at random and `spawn_even` puts organism
    // `i` on cell `i % cells`, so without it a placement arm silently becomes
    // the even arm (EXP-83 D, EXP-84).
    if let Some(ref sc) = start_cells {
        if sc.len() != n {
            eprintln!(
                "refusing to run: --start-cell has {} entries but --n is {}.\\n             One index per organism, e.g. --n 2 --start-cell 0,2.",
                sc.len(),
                n
            );
            std::process::exit(2);
        }
        let cells_now = field.cells();
        for (i, c) in sc.iter().enumerate() {
            if *c >= cells_now {
                eprintln!(
                    "refusing to run: --start-cell puts organism {} on cell {} but the field has {} cells (0..{}).",
                    i,
                    c,
                    cells_now,
                    cells_now - 1
                );
                std::process::exit(2);
            }
        }
    }

    let spawned = if let Some(ref sc) = start_cells {
        Life::spawn_at(world, field, sc, energy, move_cost, policy, seed, memory_life)
    } else if even {
        Life::spawn_even(world, field, n, energy, move_cost, policy, seed, memory_life)
    } else {
        Life::spawn(world, field, n, energy, move_cost, policy, seed, memory_life)
    };'''
assert old in s
s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('trace.rs patched')

# 5. Life::spawn_at in life.rs
p2 = '/root/marfagenez/core/src/life.rs'
t = io.open(p2, encoding='utf-8').read()
anchor = "    pub fn spawn_even("
assert anchor in t
add = '''    /// Puts organism `i` on `cells[i]`.
    ///
    /// The command line needs this because neither `spawn` (random) nor
    /// `spawn_even` (cell `i % cells`) can ask a question about a chosen cell.
    pub fn spawn_at(
        world: World,
        field: Field,
        cells: &[usize],
        energy: f64,
        move_cost: f64,
        policy: Policy,
        seed: u64,
        memory_life: usize,
    ) -> Option<Self> {
        if cells.is_empty() {
            return None;
        }
        let n_cells = field.cells();
        let mut pop = Vec::with_capacity(cells.len());
        for &cell in cells {
            if cell >= n_cells {
                return None;
            }
            let o = Organism::healthy(energy)?;
            let mut r = Remembering::new(o, cell, 0.0, move_cost, memory_life)?;
            r.memory.best_level = 0.0;
            pop.push(r);
        }
        Self::new(world, field, pop, policy, seed, memory_life)
    }

'''
t = t.replace(anchor, add + anchor, 1)
io.open(p2, 'w', encoding='utf-8').write(t)
print('life.rs patched')
