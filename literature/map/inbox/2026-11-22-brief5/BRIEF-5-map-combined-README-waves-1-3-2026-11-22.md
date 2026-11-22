# BRIEF-5 combined scientific map — waves 1–3

Date: 2026-11-22

This package combines the first and second batches with the third deepening wave. The source of truth is JSONL: one atomic claim per line, and edges are separate JSONL. Do not treat this package as having passed the complete BRIEF-5 acceptance gate.

## Files

- `BRIEF-5-map-combined-waves-1-3-2026-11-22.jsonl` — all atoms from waves 1–3.
- `BRIEF-5-map-combined-edges-waves-1-3-2026-11-22.jsonl` — all relations from waves 1–3.
- `BRIEF-5-map-combined-coverage-waves-1-3-2026-11-22.json` — counts, area distribution and verification status.
- `BRIEF-5-third-wave-2026-11-22.jsonl` — only new third-wave atoms.
- `BRIEF-5-third-wave-edges-2026-11-22.jsonl` — only new third-wave relations.
- `BRIEF-5-third-wave-coverage-2026-11-22.json` — per-area third-wave counts and confidence.
- `BRIEF-5-third-wave-notes-2026-11-22.md` — research notes, interpretation limits and DOI audit status.

## Important limits

- Third wave deepens four areas (information/error, genetics/epigenetics, membrane biophysics, morphogenesis/bioelectricity) with 12 atoms each: 10 positive high/medium claims and 2 gap candidates.
- This does not meet the brief's 1,000+ work target.
- Not every area in the full brief meets the 10-positive / 3-formula / 2-gap threshold.
- DOI/title matches were manually checked against PubMed/PMC or publisher records where retrieved; automated Crossref batch validation was not run. Quote snippets in the combined export are shortened exact excerpts, capped at 25 words per DOI.
- First- and second-wave rows were preserved verbatim. Their assertions and DOI matches were not re-verified in the third-wave pass.
- Gap entries have a bounded `searched` and `scope`; they are research gaps in the reviewed sample, not universal absence statements.
