# KG reachability audit

## Baseline (master before this change)

Snapshot commit: 4efd39d6aac8e80ca0692f5d1e6c4ceb4ec18b66. The generated graph contained 580 nodes and 101 edges. Degree counting on both endpoints found 511 isolated nodes. The baseline IDs are frozen in kg/legacy-isolated.json; this prevents an existing orphan from blocking migration while stopping a newly added established node from silently becoming another orphan.

## New artifact chain

The current migration already turns evidence[] and relations[] into graph edges, and resolves a result-file reference to its experiment node. This change adds the missing measurable middle of the route:

conclusion -> experiment measurement -> DATA result JSON -> CODE source/commit.

An experiment receives has_data to a data-artifact node whose path and SHA-256 are computed from the actual result JSON. That node receives generated_by to a code locator. The locator pairs the recorded command path (when present) with the explicit model_commit field. The migration does not hash the current checkout as if it were the historical executed bytes; this would be false provenance when the file has changed since the run. The code node is a locator, not copied source. No script path is guessed from an experiment name. If neither source is present, the run remains visibly unlinked.

The new relations carry no epistemic weight. They describe where the measurement came from, not whether its conclusion is true. Literature nodes continue to link through their separately recorded section and artifact references; this does not merge the literature map with the experiment KG.

## Reachability categories

- reachable: a directed path reaches a result-data artifact and then a code locator
- isolated: a baseline conclusion node with no incident edge
- new-isolated: a new conclusion node with no edge
- no-source: a node has incident edges but has no evidence/source locator
- no-link: a source is recorded but the full directed chain is absent

## Rebuild and report

Run python3 kg/migrate.py, then the existing kg/kg.py build, then:

    python3 tools/kg_reach.py --write
    python3 checks/kg_edges.py
    python3 -m unittest checks.test_kg_reach

The generated report includes the before/after isolated counts and per-conclusion paths. The before count is fixed here at 511. The after count is computed from the rebuilt graph rather than predicted from code that has not run.
