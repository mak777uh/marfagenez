# KG reachability audit

Conclusion nodes checked: 157.

| Graph measure | Count |
|---|---:|
| Nodes after rebuild | 1191 |
| Edges after rebuild | 907 |
| Isolated before (frozen baseline) | 511 |
| Isolated after rebuild | 110 |
| Baseline isolates still isolated | 110 |
| New isolates | 0 |
| Change vs baseline | -401 |

| Conclusion-path status | Nodes |
|---|---:|
| isolated | 15 |
| no-link | 125 |
| no-source | 11 |
| reachable | 6 |

A node is reachable only if a directed path reaches an experiment, its result-data
artifact, and then a code source/commit locator. Literature-only evidence does not
count as an experimental code path. Isolated is a baseline orphan; new-isolated is
a new conclusion node with no incident edge; no-source and no-link identify separate
repair jobs. The audit never treats a mechanically linked artifact as scientific support.

Reproduce after python3 kg/migrate.py and python3 kg/kg.py build:

    python3 tools/kg_reach.py --write
    python3 checks/kg_edges.py
    python3 -m unittest checks.test_kg_reach
