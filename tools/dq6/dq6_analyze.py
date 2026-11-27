#!/usr/bin/env python3
"""D-Q6 candidate analysis and deterministic synthetic self-test.

Scientific inputs are the three candidate-driver summary CSVs and their exact
interval histograms.  Only the Python standard library is used.  The self-test
is in memory, is explicitly synthetic, and never writes scientific evidence.
"""
from __future__ import annotations

import argparse
import bisect
import copy
import csv
import hashlib
import io
import json
import math
import random
import re
import struct
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, TextIO

ANALYSIS_VERSION = "dq6-analysis-1.0.1"
TASK_ID = "EXP-2026-4103"
SEEDS = tuple(range(4301, 4313))
N = 100
STEPS = 800_000
SAMPLE_STEPS = (100_000, 200_000, 400_000, 800_000)
H_FIT = (0.99, 0.995, 0.998, 0.999, 0.9995)
H_REMOTE = (0.9, 0.95, 0.98, 0.99)
H_SILENT = (0.9, 0.95, 0.98, 0.99)
H_SPECIFIC = (0.995, 0.999)
CONTROLS = ("death-reset", "cap", "sham")
MATCHING_MODES = {
    "death-reset": "state-dependent",
    "cap": "state-dependent+cap",
    "sham": "yoked-step-count-value",
}
SUMMARY_HEADER = ["h", "seed", "sample_step", "Dbar", "events_so_far", "control"]
HISTOGRAM_HEADER = [
    "h", "seed", "control", "matching_mode", "record_type", "scope",
    "organism", "interval", "count", "reset_value_sum", "reset_value_sumsq",
    "reset_value_min", "reset_value_max", "reset_schedule_hash",
]
TARGETS = {"alpha_D": 0.5, "alpha_deriv": 1.5, "alpha_Tlife": 0.5}
TOLERANCE = 0.15
MIN_FIT_POINTS = 4
MIN_CONVERGED_SEEDS = 10
BOOTSTRAP_REPS = 10_000
BOOTSTRAP_SEED = 20_261_103
OUTPUT_BUDGET_BYTES = 268_435_456
FNV_OFFSET_A = 0xCBF29CE484222325
FNV_OFFSET_B = 0x84222325CBF29CE4
FNV_PRIME = 0x00000100000001B3
HASH_RE = re.compile(r"[0-9a-f]{32}\Z")
INT_RE = re.compile(r"(?:0|[1-9][0-9]*)\Z")


def derivative_step(h: float) -> float:
    return min(0.00025, (1.0 - h) / 4.0)


def derivative_neighbors(values: Iterable[float]) -> tuple[float, ...]:
    out = set(values)
    for h in values:
        if 0.0 < h < 1.0:
            step = derivative_step(h)
            lower, upper = h - step, h + step
            if lower >= 0.0 and upper <= 1.0:
                out.update((lower, upper))
    return tuple(sorted(out))


DEATH_H = derivative_neighbors((*H_REMOTE, *H_FIT, 1.0))
EXPECTED_H = {
    "death-reset": DEATH_H,
    "cap": (1.0,),
    "sham": H_SPECIFIC,
}
EXPECTED_SUMMARY_ROWS = {
    control: len(hs) * len(SEEDS) * len(SAMPLE_STEPS)
    for control, hs in EXPECTED_H.items()
}
EXPECTED_HIST_SUMMARIES = {
    control: len(hs) * len(SEEDS) for control, hs in EXPECTED_H.items()
}


def h_label(h: float) -> str:
    return format(h, ".15g")


def parse_float(value: str, context: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{context}: invalid float {value!r}") from error
    if not math.isfinite(result):
        raise ValueError(f"{context}: non-finite float")
    return result


def parse_int(value: str, context: str, maximum: int | None = None) -> int:
    if not isinstance(value, str) or not INT_RE.fullmatch(value):
        raise ValueError(f"{context}: invalid nonnegative integer {value!r}")
    result = int(value)
    if maximum is not None and result > maximum:
        raise ValueError(f"{context}: integer {result} exceeds {maximum}")
    return result


def canonical_h(value: float, allowed: Iterable[float], context: str) -> float:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{context}: h must be finite and in [0,1]")
    matches = [h for h in allowed if math.isclose(value, h, rel_tol=0.0, abs_tol=1e-12)]
    if len(matches) != 1:
        raise ValueError(f"{context}: h={value!r} is outside the strict registry")
    return matches[0]


def mean(values: Iterable[float]) -> float:
    values = list(values)
    if not values:
        raise ValueError("mean of empty values")
    return math.fsum(values) / len(values)


def median(values: Iterable[float]) -> float | None:
    values = sorted(values)
    if not values:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2.0


def nearest_rank(histogram: dict[int, int], probability: float) -> int | None:
    """Exact inverse empirical CDF; the smallest interval with CDF >= q."""
    total = sum(histogram.values())
    if total == 0:
        return None
    if not 0.0 <= probability <= 1.0:
        raise ValueError("quantile probability outside [0,1]")
    rank = max(1, math.ceil(probability * total))
    cumulative = 0
    for interval in sorted(histogram):
        cumulative += histogram[interval]
        if cumulative >= rank:
            return interval
    raise AssertionError("histogram CDF did not reach its total")


def percentile(values: Iterable[float], probability: float) -> float | None:
    """Linear (n-1)*p percentile used for bootstrap intervals."""
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def relative_convergence(d400: float, d800: float) -> float | None:
    if d800 <= 0.0:
        return None
    return abs(d800 - d400) / d800


def converged(d400: float, d800: float) -> bool:
    relative = relative_convergence(d400, d800)
    return relative is not None and relative <= 0.01


def ols_log_log(hs: Iterable[float], responses: Iterable[float]) -> dict:
    hs, responses = list(hs), list(responses)
    if len(hs) != len(responses) or len(hs) < 2:
        raise ValueError("log-log OLS needs at least two paired points")
    if any(not 0.0 < h < 1.0 for h in hs):
        raise ValueError("log-log OLS excludes h=1 and requires h in (0,1)")
    if any(not math.isfinite(v) or v <= 0.0 for v in responses):
        raise ValueError("log-log OLS requires finite positive responses")
    xs = [math.log(1.0 - h) for h in hs]
    ys = [math.log(v) for v in responses]
    xm, ym = mean(xs), mean(ys)
    sxx = math.fsum((x - xm) ** 2 for x in xs)
    if sxx <= 1e-15:
        raise ValueError("singular log-log OLS: h values do not span x")
    slope = math.fsum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / sxx
    intercept = ym - slope * xm
    sst = math.fsum((y - ym) ** 2 for y in ys)
    residual = math.fsum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    r_squared = 1.0 - residual / sst if sst > 0.0 else None
    return {
        "slope": slope,
        "intercept": intercept,
        "positive_exponent": -slope,
        "r_squared": r_squared,
        "n_h": len(hs),
    }


def fnv_update(hash_value: int, data: bytes) -> int:
    for byte in data:
        hash_value ^= byte
        hash_value = (hash_value * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return hash_value


def schedule_hash(events: Iterable[tuple[int, float]]) -> str:
    """Two FNV-1a 64-bit hashes; verification fingerprint, not cryptography."""
    a, b = FNV_OFFSET_A, FNV_OFFSET_B
    for step, value in events:
        payload = struct.pack("<Qd", step, value)
        a = fnv_update(a, payload)
        b = fnv_update(b, payload)
    return f"{a:016x}{b:016x}"


@dataclass
class SummaryRow:
    h: float
    seed: int
    sample_step: int
    dbar: float
    events_so_far: int
    control: str


@dataclass
class HistogramRun:
    h: float
    seed: int
    control: str
    matching_mode: str
    summary_seen: bool = False
    event_count: int = 0
    reset_sum: float = 0.0
    reset_sumsq: float = 0.0
    reset_min: float = 0.0
    reset_max: float = 0.0
    schedule_hash: str = ""
    global_intervals: dict[int, int] = field(default_factory=dict)
    organism_event_count: int = 0
    organism_bin_count: int = 0
    organisms_with_events: set[int] = field(default_factory=set)
    interval_record_count: int = 0
    histogram_detail: str = "organism"
    # Retained only by the in-memory synthetic fixture; production parsing
    # validates and discards organism bins to bound memory.
    organism_intervals: dict[int, dict[int, int]] | None = None

    @property
    def global_interval_mean(self) -> float | None:
        if self.event_count == 0:
            return None
        return math.fsum(interval * count for interval, count in self.global_intervals.items()) / self.event_count

    @property
    def reset_mean(self) -> float | None:
        return self.reset_sum / self.event_count if self.event_count else None

    @property
    def reset_second_moment(self) -> float | None:
        return self.reset_sumsq / self.event_count if self.event_count else None

    @property
    def reset_variance(self) -> float | None:
        if not self.event_count:
            return None
        variance = self.reset_second_moment - self.reset_mean ** 2
        scale = max(1.0, abs(self.reset_second_moment), abs(self.reset_mean ** 2))
        if variance < 0.0 and variance >= -1e-12 * scale:
            variance = 0.0
        return variance


@dataclass
class RawData:
    summaries: dict[str, dict[tuple[float, int, int], SummaryRow]]
    histograms: dict[str, dict[tuple[float, int], HistogramRun]]
    validation: dict


def read_csv_rows(handle: TextIO, expected_header: list[str], path: Path) -> Iterable[tuple[int, list[str]]]:
    reader = csv.reader(handle, strict=True)
    try:
        header = next(reader)
    except StopIteration as error:
        raise ValueError(f"{path}: empty CSV") from error
    if header != expected_header:
        raise ValueError(f"{path}: header mismatch; expected {expected_header}, got {header}")
    for line, row in enumerate(reader, 2):
        if len(row) != len(expected_header):
            raise ValueError(f"{path}:{line}: expected {len(expected_header)} columns, got {len(row)}")
        yield line, row


def parse_summary(path: Path, control: str) -> dict[tuple[float, int, int], SummaryRow]:
    rows: dict[tuple[float, int, int], SummaryRow] = {}
    allowed_h = EXPECTED_H[control]
    with path.open(newline="", encoding="utf-8") as handle:
        for line, raw in read_csv_rows(handle, SUMMARY_HEADER, path):
            context = f"{path}:{line}"
            h = canonical_h(parse_float(raw[0], context), allowed_h, context)
            seed = parse_int(raw[1], context)
            if seed not in SEEDS:
                raise ValueError(f"{context}: seed {seed} is outside 4301..4312")
            sample_step = parse_int(raw[2], context, STEPS)
            if sample_step not in SAMPLE_STEPS:
                raise ValueError(f"{context}: sample_step {sample_step} is outside the registry")
            dbar = parse_float(raw[3], context)
            if dbar < 0.0:
                raise ValueError(f"{context}: Dbar must be nonnegative")
            events = parse_int(raw[4], context, N * STEPS)
            if raw[5] != control:
                raise ValueError(f"{context}: expected control {control!r}, got {raw[5]!r}")
            key = (h, seed, sample_step)
            if key in rows:
                raise ValueError(f"{context}: duplicate summary key {key}")
            rows[key] = SummaryRow(h, seed, sample_step, dbar, events, control)
    expected = {(h, seed, step) for h in allowed_h for seed in SEEDS for step in SAMPLE_STEPS}
    actual = set(rows)
    if actual != expected or len(rows) != len(expected):
        missing, extra = sorted(expected - actual)[:5], sorted(actual - expected)[:5]
        raise ValueError(f"{path}: summary registry mismatch; missing={missing}, extra={extra}, rows={len(rows)}")
    return rows


class HistogramParser:
    """Streaming parser storing global bins, not every organism bin.

    The candidate writes contiguous run blocks.  Per-organism duplicate bins are
    checked in the current block and then discarded, bounding analyzer memory.
    """

    def __init__(self, control: str, path: Path):
        self.control = control
        self.path = path
        self.allowed_h = EXPECTED_H[control]
        self.runs: dict[tuple[float, int], HistogramRun] = {}
        self.finished: set[tuple[float, int]] = set()
        self.current_key: tuple[float, int] | None = None
        self.current: HistogramRun | None = None
        self.seen_organism_bins: set[tuple[int, int]] = set()

    def finish_current(self) -> None:
        if self.current is None:
            return
        run = self.current
        context = f"{self.path}: h={h_label(run.h)}, seed={run.seed}"
        if not run.summary_seen:
            raise ValueError(f"{context}: missing summary record")
        global_count = sum(run.global_intervals.values())
        if global_count != run.event_count:
            raise ValueError(f"{context}: global histogram count {global_count} != summary {run.event_count}")
        if run.organism_event_count != run.event_count and run.histogram_detail == "organism":
            raise ValueError(f"{context}: organism histogram count {run.organism_event_count} != summary {run.event_count}")
        if run.event_count == 0 and run.interval_record_count:
            raise ValueError(f"{context}: zero-event run contains interval records")
        if run.event_count:
            scale = max(1.0, abs(run.reset_sumsq), abs(run.reset_sum) ** 2 / run.event_count)
            lower = run.reset_min ** 2 * run.event_count
            upper = run.reset_max ** 2 * run.event_count
            if run.reset_sumsq < lower - 1e-9 * scale or run.reset_sumsq > upper + 1e-9 * scale:
                raise ValueError(f"{context}: reset moments violate min/max bounds")
            if run.reset_sumsq < run.reset_sum ** 2 / run.event_count - 1e-9 * scale:
                raise ValueError(f"{context}: reset sumsq is below sum^2/count")
        self.finished.add(self.current_key)
        self.current = None
        self.current_key = None
        self.seen_organism_bins.clear()

    def start(self, key: tuple[float, int], h: float, seed: int, mode: str) -> None:
        self.finish_current()
        if key in self.finished:
            raise ValueError(f"{self.path}: noncontiguous or repeated run block {key}")
        self.current_key = key
        self.current = HistogramRun(h, seed, self.control, mode)
        self.runs[key] = self.current

    def feed(self, line: int, raw: list[str]) -> None:
        context = f"{self.path}:{line}"
        h = canonical_h(parse_float(raw[0], context), self.allowed_h, context)
        seed = parse_int(raw[1], context)
        if seed not in SEEDS:
            raise ValueError(f"{context}: seed {seed} is outside 4301..4312")
        if raw[2] != self.control:
            raise ValueError(f"{context}: expected control {self.control!r}, got {raw[2]!r}")
        if raw[3] != MATCHING_MODES[self.control]:
            raise ValueError(f"{context}: incorrect matching_mode {raw[3]!r}")
        key = (h, seed)
        if key != self.current_key:
            self.start(key, h, seed, raw[3])
        run = self.current
        if raw[4] == "summary":
            if run.summary_seen:
                raise ValueError(f"{context}: duplicate summary record")
            if raw[5] not in ("", "global-only") or any(raw[i] != "" for i in (6, 7)):
                raise ValueError(f"{context}: summary scope must be blank or global-only; organism/interval must be blank")
            run.histogram_detail = "global-only" if raw[5] == "global-only" else "organism"
            count = parse_int(raw[8], context, N * STEPS)
            reset_sum = parse_float(raw[9], context)
            reset_sumsq = parse_float(raw[10], context)
            reset_min = parse_float(raw[11], context)
            reset_max = parse_float(raw[12], context)
            if min(reset_sum, reset_sumsq, reset_min, reset_max) < 0.0:
                raise ValueError(f"{context}: reset moments must be nonnegative")
            if count == 0:
                if any(v != 0.0 for v in (reset_sum, reset_sumsq, reset_min, reset_max)) or raw[13] != "":
                    raise ValueError(f"{context}: zero-event summary must have zero moments and blank hash")
            else:
                if reset_min > reset_max:
                    raise ValueError(f"{context}: reset minimum exceeds maximum")
                if not HASH_RE.fullmatch(raw[13]):
                    raise ValueError(f"{context}: schedule hash must be 32 lowercase hexadecimal digits")
            run.summary_seen = True
            run.event_count = count
            run.reset_sum = reset_sum
            run.reset_sumsq = reset_sumsq
            run.reset_min = reset_min
            run.reset_max = reset_max
            run.schedule_hash = raw[13]
            return
        if raw[4] != "interval":
            raise ValueError(f"{context}: unknown record_type {raw[4]!r}")
        if run.summary_seen and run.event_count == 0:
            raise ValueError(f"{context}: zero-event run contains interval records")
        if any(raw[i] != "" for i in (9, 10, 11, 12, 13)):
            raise ValueError(f"{context}: interval reset/hash fields must be blank")
        interval = parse_int(raw[7], context, STEPS)
        count = parse_int(raw[8], context, N * STEPS)
        # interval=0 (deaths in adjacent steps) is physical near the pole
        # (T_life ~ x^1/2 -> 0 as h -> 1) and is accepted; count stays positive.
        if interval < 0 or count <= 0:
            raise ValueError(f"{context}: interval must be non-negative and count positive")
        run.interval_record_count += 1
        if raw[5] == "global":
            if raw[6] != "":
                raise ValueError(f"{context}: global organism must be blank")
            if interval in run.global_intervals:
                raise ValueError(f"{context}: duplicate global interval {interval}")
            run.global_intervals[interval] = count
        elif raw[5] == "organism":
            if run.histogram_detail == "global-only":
                raise ValueError(f"{context}: global-only histogram contains organism bins")
            organism = parse_int(raw[6], context, N - 1)
            bin_key = (organism, interval)
            if bin_key in self.seen_organism_bins:
                raise ValueError(f"{context}: duplicate organism interval {bin_key}")
            self.seen_organism_bins.add(bin_key)
            run.organism_event_count += count
            run.organism_bin_count += 1
            run.organisms_with_events.add(organism)
        else:
            raise ValueError(f"{context}: unknown scope {raw[5]!r}")

    def parse(self, handle: TextIO) -> dict[tuple[float, int], HistogramRun]:
        for line, raw in read_csv_rows(handle, HISTOGRAM_HEADER, self.path):
            self.feed(line, raw)
        self.finish_current()
        expected = {(h, seed) for h in self.allowed_h for seed in SEEDS}
        actual = set(self.runs)
        if actual != expected:
            missing, extra = sorted(expected - actual)[:5], sorted(actual - expected)[:5]
            raise ValueError(f"{self.path}: histogram registry mismatch; missing={missing}, extra={extra}")
        return self.runs


def parse_histogram_stream(handle: TextIO, control: str, path: Path | str = "<histogram>") -> dict[tuple[float, int], HistogramRun]:
    parser = HistogramParser(control, Path(path))
    return parser.parse(handle)


def parse_histogram(path: Path, control: str) -> dict[tuple[float, int], HistogramRun]:
    with path.open(newline="", encoding="utf-8") as handle:
        return parse_histogram_stream(handle, control, path)


def float_bits_equal(a: float, b: float) -> bool:
    return struct.pack("<d", a) == struct.pack("<d", b)


def schedule_equal(a: HistogramRun, b: HistogramRun) -> bool:
    # The strict parser requires zero moments, no interval records and a blank
    # hash for zero-event runs. Equal empty schedules are therefore exact; the
    # old event_count > 0 guard incorrectly rejected that valid contract.
    return (
        a.event_count == b.event_count
        and a.schedule_hash == b.schedule_hash
        and float_bits_equal(a.reset_sum, b.reset_sum)
        and float_bits_equal(a.reset_sumsq, b.reset_sumsq)
        and float_bits_equal(a.reset_min, b.reset_min)
        and float_bits_equal(a.reset_max, b.reset_max)
    )


def load_inputs(
    death_summary: Path,
    cap_summary: Path,
    sham_summary: Path,
    death_histogram: Path,
    cap_histogram: Path,
    sham_histogram: Path,
) -> RawData:
    summary_paths = {
        "death-reset": death_summary,
        "cap": cap_summary,
        "sham": sham_summary,
    }
    histogram_paths = {
        "death-reset": death_histogram,
        "cap": cap_histogram,
        "sham": sham_histogram,
    }
    summaries = {control: parse_summary(path, control) for control, path in summary_paths.items()}
    histograms = {control: parse_histogram(path, control) for control, path in histogram_paths.items()}
    for control in CONTROLS:
        for h in EXPECTED_H[control]:
            for seed in SEEDS:
                counts = [summaries[control][(h, seed, step)].events_so_far for step in SAMPLE_STEPS]
                if any(a > b for a, b in zip(counts, counts[1:])):
                    raise ValueError(f"{control} h={h_label(h)} seed={seed}: cumulative event counts decrease")
                if counts[-1] != histograms[control][(h, seed)].event_count:
                    raise ValueError(
                        f"{control} h={h_label(h)} seed={seed}: final summary events {counts[-1]} "
                        f"!= histogram summary {histograms[control][(h, seed)].event_count}"
                    )
    yoked_counts_equal = all(
        summaries["death-reset"][(h, seed, step)].events_so_far
        == summaries["sham"][(h, seed, step)].events_so_far
        for h in H_SPECIFIC for seed in SEEDS for step in SAMPLE_STEPS
    )
    per_control = {}
    for control in CONTROLS:
        per_control[control] = {
            "expected_h": [h_label(h) for h in EXPECTED_H[control]],
            "summary_rows": len(summaries[control]),
            "expected_summary_rows": EXPECTED_SUMMARY_ROWS[control],
            "histogram_summary_records": len(histograms[control]),
            "expected_histogram_summary_records": EXPECTED_HIST_SUMMARIES[control],
            "histogram_interval_records": sum(run.interval_record_count for run in histograms[control].values()),
        }
    validation = {
        "status": "passed",
        "strict_registries": True,
        "cumulative_event_counts": "nondecreasing and final counts equal histogram summaries",
        "yoked_cumulative_counts_equal": yoked_counts_equal,
        "yoked_count_rule": "death-reset/sham equality is evaluated by the specific control, not used to discard a negative result",
        "hash_fields": "32 lowercase hex digits for nonempty summaries; blank on interval/empty records",
        "histogram_counts": "global totals equal the run summary; organism totals also equal it unless summary scope explicitly declares global-only",
        "per_control": per_control,
        "schedule_hash_algorithm": "two 64-bit FNV-1a hashes over little-endian u64 step then f64 reset-value bits; not cryptographic",
    }
    return RawData(summaries, histograms, validation)


def convergence_details(data: RawData) -> dict:
    per_h = []
    converged_fit_h = []
    for h in DEATH_H:
        seeds = []
        for seed in SEEDS:
            d400 = data.summaries["death-reset"][(h, seed, 400_000)].dbar
            d800 = data.summaries["death-reset"][(h, seed, 800_000)].dbar
            relative = relative_convergence(d400, d800)
            seeds.append({
                "seed": seed,
                "Dbar_400000": d400,
                "Dbar_800000": d800,
                "abs_D800_D400": abs(d800 - d400),
                "relative_D800_D400": relative,
                "converged": converged(d400, d800),
            })
        count = sum(item["converged"] for item in seeds)
        h_converged = count >= MIN_CONVERGED_SEEDS
        if h in H_FIT and h_converged:
            converged_fit_h.append(h)
        per_h.append({
            "h": h,
            "n_seeds": len(SEEDS),
            "converged_seed_count": count,
            "required_converged_seed_count": MIN_CONVERGED_SEEDS,
            "h_converged": h_converged,
            "asymptotic_fit_point": h in H_FIT,
            "included_in_asymptotic_fit": h in H_FIT and h_converged,
            "seeds": seeds,
        })
    return {
        "rule": "|Dbar(800000)-Dbar(400000)|/Dbar(800000) <= 0.01",
        "h_rule": f"at least {MIN_CONVERGED_SEEDS}/{len(SEEDS)} seeds converge",
        "minimum_fit_points": MIN_FIT_POINTS,
        "converged_fit_h": converged_fit_h,
        "converged_fit_point_count": len(converged_fit_h),
        "enough_converged_h": len(converged_fit_h) >= MIN_FIT_POINTS,
        "per_h": per_h,
    }


def seed_metrics(data: RawData) -> list[dict]:
    rows = []
    for control in CONTROLS:
        for h in EXPECTED_H[control]:
            for seed in SEEDS:
                histogram = data.histograms[control][(h, seed)]
                d400 = data.summaries[control][(h, seed, 400_000)].dbar
                d800 = data.summaries[control][(h, seed, 800_000)].dbar
                relative = relative_convergence(d400, d800)
                row = {
                    "h": h,
                    "seed": seed,
                    "control": control,
                    **{f"Dbar_{step}": data.summaries[control][(h, seed, step)].dbar for step in SAMPLE_STEPS},
                    **{f"events_so_far_{step}": data.summaries[control][(h, seed, step)].events_so_far for step in SAMPLE_STEPS},
                    "global_event_count": histogram.event_count,
                    "global_interval_mean": histogram.global_interval_mean,
                    "global_interval_q025": nearest_rank(histogram.global_intervals, 0.025),
                    "global_interval_q50": nearest_rank(histogram.global_intervals, 0.50),
                    "global_interval_q975": nearest_rank(histogram.global_intervals, 0.975),
                    "global_interval_min": min(histogram.global_intervals) if histogram.global_intervals else None,
                    "global_interval_max": max(histogram.global_intervals) if histogram.global_intervals else None,
                    "global_interval_bin_count": len(histogram.global_intervals),
                    "histogram_detail": histogram.histogram_detail,
                    "organism_interval_bin_count": histogram.organism_bin_count,
                    "organisms_with_events": len(histogram.organisms_with_events),
                    "reset_value_sum": histogram.reset_sum,
                    "reset_value_sumsq": histogram.reset_sumsq,
                    "reset_value_mean": histogram.reset_mean,
                    "reset_value_second_moment": histogram.reset_second_moment,
                    "reset_value_variance": histogram.reset_variance,
                    "reset_value_std": math.sqrt(histogram.reset_variance) if histogram.reset_variance is not None else None,
                    "reset_value_min": histogram.reset_min if histogram.event_count else None,
                    "reset_value_max": histogram.reset_max if histogram.event_count else None,
                    "reset_schedule_hash": histogram.schedule_hash,
                    "abs_D800_D400": abs(d800 - d400),
                    "relative_D800_D400": relative,
                    "converged": str(converged(d400, d800)).lower(),
                }
                rows.append(row)
    return rows


@dataclass
class FitSpec:
    key: str
    dataset: str
    endpoint: str
    horizon: int
    hs: tuple[float, ...]
    values: dict[float, tuple[Any, ...]]
    notes: str


def neighbor_pair(h: float) -> tuple[float, float]:
    step = derivative_step(h)
    return (
        canonical_h(h - step, DEATH_H, "lower derivative neighbor"),
        canonical_h(h + step, DEATH_H, "upper derivative neighbor"),
    )


def make_fit_specs(data: RawData, fit_hs: tuple[float, ...], include_horizons: bool = True) -> list[FitSpec]:
    specs: list[FitSpec] = []
    for endpoint in TARGETS:
        values = {}
        for h in fit_hs:
            per_seed = []
            for seed in SEEDS:
                if endpoint == "alpha_D":
                    value = data.summaries["death-reset"][(h, seed, 800_000)].dbar
                elif endpoint == "alpha_deriv":
                    lower, upper = neighbor_pair(h)
                    dl = data.summaries["death-reset"][(lower, seed, 800_000)].dbar
                    du = data.summaries["death-reset"][(upper, seed, 800_000)].dbar
                    value = (dl, du)
                else:
                    value = data.histograms["death-reset"][(h, seed)].global_interval_mean
                per_seed.append(value)
            values[h] = tuple(per_seed)
        notes = {
            "alpha_D": "OLS of log(mean seed Dbar at 800000) on log(1-h); h=1 excluded",
            "alpha_deriv": "central difference of seed-mean Dbar: |mean D(h+step)-mean D(h-step)|/(2*step), then log-log OLS; mean per-seed derivative is also reported",
            "alpha_Tlife": "OLS of log(mean seed exact global reset-interval mean) on log(1-h)",
        }[endpoint]
        specs.append(FitSpec(endpoint, "asymptotic", endpoint, 800_000, fit_hs, values, notes))
    if include_horizons:
        for horizon in SAMPLE_STEPS:
            for endpoint in ("alpha_D", "alpha_deriv"):
                key = f"{endpoint}_{horizon}"
                values = {}
                for h in fit_hs:
                    per_seed = []
                    for seed in SEEDS:
                        if endpoint == "alpha_D":
                            value = data.summaries["death-reset"][(h, seed, horizon)].dbar
                        else:
                            lower, upper = neighbor_pair(h)
                            dl = data.summaries["death-reset"][(lower, seed, horizon)].dbar
                            du = data.summaries["death-reset"][(upper, seed, horizon)].dbar
                            value = (dl, du)
                        per_seed.append(value)
                    values[h] = tuple(per_seed)
                specs.append(FitSpec(
                    key, "horizon_dependence", endpoint, horizon, fit_hs, values,
                    "exploratory horizon comparison on the fixed final-converged h_fit grid; not an additional decision endpoint",
                ))
    silent_values: dict[str, dict[float, tuple[float | None, ...]]] = {endpoint: {} for endpoint in TARGETS}
    for h in H_SILENT:
        lower, upper = neighbor_pair(h)
        for seed in SEEDS:
            silent_values["alpha_D"].setdefault(h, []).append(data.summaries["death-reset"][(h, seed, 800_000)].dbar)
            dl = data.summaries["death-reset"][(lower, seed, 800_000)].dbar
            du = data.summaries["death-reset"][(upper, seed, 800_000)].dbar
            silent_values["alpha_deriv"].setdefault(h, []).append((dl, du))
            silent_values["alpha_Tlife"].setdefault(h, []).append(data.histograms["death-reset"][(h, seed)].global_interval_mean)
    for endpoint in TARGETS:
        specs.append(FitSpec(
            f"silent_{endpoint}", "silent_remote", endpoint, 800_000, H_SILENT,
            {h: tuple(values) for h, values in silent_values[endpoint].items()},
            "remote-range instrument diagnostic on h=.9,.95,.98,.99; no convergence gating",
        ))
    return specs


def fit_powerlaw(spec: FitSpec, sample_indices: tuple[int, ...] | None = None) -> dict:
    target = TARGETS[spec.endpoint]
    points = []
    for h in spec.hs:
        values = spec.values.get(h, ())
        selected = values if sample_indices is None else [values[i] for i in sample_indices]
        mean_seed_derivative = None
        if spec.endpoint == "alpha_deriv":
            pairs = [
                v for v in selected
                if isinstance(v, tuple) and len(v) == 2
                and all(isinstance(x, (int, float)) and math.isfinite(x) and x >= 0.0 for x in v)
            ]
            response = (
                abs(mean([pair[1] for pair in pairs]) - mean([pair[0] for pair in pairs]))
                / (2.0 * derivative_step(h))
            ) if pairs else None
            if pairs:
                mean_seed_derivative = mean([
                    abs(pair[1] - pair[0]) / (2.0 * derivative_step(h)) for pair in pairs
                ])
            available_count = len(pairs)
        else:
            available = [v for v in selected if isinstance(v, (int, float)) and math.isfinite(v) and v > 0.0]
            response = mean(available) if available else None
            available_count = len(available)
        points.append({
            "h": h,
            "x": 1.0 - h,
            "log_x": math.log(1.0 - h),
            "response_mean": response,
            # Zero/non-positive responses are valid observations but cannot
            # enter a log-log fit. Report them as unestimable instead of
            # aborting the entire analysis before the five outputs are written.
            "log_response": math.log(response) if response is not None and response > 0.0 else None,
            "n_available_seeds": available_count,
            "mean_seed_central_derivative": mean_seed_derivative,
            "derivative_step": derivative_step(h) if spec.endpoint == "alpha_deriv" else None,
        })
        if spec.endpoint == "alpha_deriv":
            lower, upper = neighbor_pair(h)
            points[-1].update({"neighbor_lower": lower, "neighbor_upper": upper})
    fit = None
    status = "ok"
    if len(spec.hs) < MIN_FIT_POINTS:
        status = "insufficient_converged_h"
    elif any(point["log_response"] is None for point in points):
        status = "insufficient_positive_values"
    else:
        try:
            fit = ols_log_log(spec.hs, [point["response_mean"] for point in points])
        except (ValueError, ArithmeticError) as error:
            status = f"fit_error: {error}"
    result = {
        "key": spec.key,
        "dataset": spec.dataset,
        "endpoint": spec.endpoint,
        "horizon": spec.horizon,
        "target": target,
        "tolerance": TOLERANCE,
        "status": status,
        "point_estimate": (fit["slope"] if spec.endpoint == "alpha_Tlife" else fit["positive_exponent"]) if fit else None,
        "slope": fit["slope"] if fit else None,
        "intercept": fit["intercept"] if fit else None,
        "r_squared": fit["r_squared"] if fit else None,
        "n_h": len(spec.hs),
        "input_points": points,
        "notes": spec.notes,
    }
    if fit:
        for point in points:
            point["converged_seed_count"] = None
    return result


def bootstrap_seed_indices(reps: int = BOOTSTRAP_REPS) -> list[tuple[int, ...]]:
    rng = random.Random(BOOTSTRAP_SEED)
    return [tuple(rng.randrange(len(SEEDS)) for _ in SEEDS) for _ in range(reps)]


def bootstrap_fit_specs(specs: list[FitSpec], samples: list[tuple[int, ...]]) -> tuple[dict[str, dict], list[dict]]:
    distributions: dict[str, list[float]] = {spec.key: [] for spec in specs}
    rows = []
    for replicate, indices in enumerate(samples, 1):
        row = {
            "replicate": replicate,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "sampled_seeds": ";".join(str(SEEDS[i]) for i in indices),
        }
        for spec in specs:
            fitted = fit_powerlaw(spec, indices)
            value = fitted["point_estimate"]
            if value is not None and math.isfinite(value):
                distributions[spec.key].append(value)
                row[spec.key] = value
            else:
                row[spec.key] = None
        rows.append(row)
    results = {}
    for spec in specs:
        result = fit_powerlaw(spec)
        values = distributions[spec.key]
        result["bootstrap_replicates"] = len(samples)
        result["valid_bootstrap_replicates"] = len(values)
        result["ci_low"] = percentile(values, 0.025)
        result["ci_high"] = percentile(values, 0.975)
        result["ci_level"] = 0.95
        result["passes"] = bool(
            result["status"] == "ok"
            and len(values) == len(samples)
            and result["ci_low"] is not None
            and result["ci_low"] <= target_upper(spec.endpoint)
            and result["ci_high"] >= target_lower(spec.endpoint)
        )
        results[spec.key] = result
    return results, rows


def target_lower(endpoint: str) -> float:
    return TARGETS[endpoint] - TOLERANCE


def target_upper(endpoint: str) -> float:
    return TARGETS[endpoint] + TOLERANCE


FIT_FIELDS = [
    "record_type", "dataset", "key", "horizon", "endpoint", "h", "n_h",
    "n_available_seeds", "x", "derivative_step", "neighbor_lower", "neighbor_upper",
    "response_mean", "mean_seed_central_derivative", "log_x", "log_response", "slope", "intercept", "r_squared",
    "point_estimate", "positive_exponent", "target", "tolerance", "ci_low", "ci_high",
    "bootstrap_replicates", "valid_bootstrap_replicates", "passes", "status", "notes",
]


def flatten_fits(results: dict[str, dict]) -> list[dict]:
    rows = []
    for result in results.values():
        base = {key: result.get(key) for key in FIT_FIELDS}
        base.update({
            "record_type": "fit",
            "positive_exponent": result["point_estimate"],
            "passes": str(result["passes"]).lower(),
        })
        rows.append(base)
        for point in result["input_points"]:
            row = {key: None for key in FIT_FIELDS}
            row.update({
                "record_type": "input_point",
                "dataset": result["dataset"],
                "key": result["key"],
                "horizon": result["horizon"],
                "endpoint": result["endpoint"],
                "h": point["h"],
                "x": point["x"],
                "n_available_seeds": point["n_available_seeds"],
                "derivative_step": point.get("derivative_step"),
                "neighbor_lower": point.get("neighbor_lower"),
                "neighbor_upper": point.get("neighbor_upper"),
                "response_mean": point["response_mean"],
                "mean_seed_central_derivative": point.get("mean_seed_central_derivative"),
                "log_x": point["log_x"],
                "log_response": point["log_response"],
                "target": result["target"],
                "tolerance": result["tolerance"],
                "status": result["status"],
                "notes": result["notes"],
            })
            rows.append(row)
    return rows


def compact_fit(result: dict, include_points: bool = False) -> dict:
    keys = (
        "key", "dataset", "endpoint", "horizon", "status", "point_estimate", "slope",
        "intercept", "r_squared", "n_h", "target", "tolerance", "ci_low", "ci_high",
        "ci_level", "bootstrap_replicates", "valid_bootstrap_replicates", "passes", "notes",
    )
    compact = {key: result.get(key) for key in keys}
    if include_points:
        compact["input_points"] = result["input_points"]
    return compact


def horizon_dependence(data: RawData, fit_results: dict[str, dict]) -> dict:
    horizons = []
    for horizon in SAMPLE_STEPS:
        mean_d = {
            h_label(h): mean([data.summaries["death-reset"][(h, seed, horizon)].dbar for seed in SEEDS])
            for h in DEATH_H
        }
        event_rate = {
            h_label(h): mean([
                data.summaries["death-reset"][(h, seed, horizon)].events_so_far / horizon
                for seed in SEEDS
            ])
            for h in (*H_REMOTE, *H_FIT, 1.0)
        }
        if horizon == STEPS:
            life = {"available": True, **compact_fit(fit_results["alpha_Tlife"])}
        else:
            life = {
                "available": False,
                "status": "not_recoverable_from_prefix_histogram",
                "reason": "the histogram has intervals but no event steps, so exact prefix interval moments before 800000 cannot be reconstructed",
            }
        horizons.append({
            "sample_step": horizon,
            "mean_Dbar_by_h": mean_d,
            "mean_cumulative_event_rate_by_h": event_rate,
            "alpha_D": compact_fit(fit_results[f"alpha_D_{horizon}"]),
            "alpha_deriv": compact_fit(fit_results[f"alpha_deriv_{horizon}"]),
            "alpha_Tlife": life,
        })
    return {
        "method": "all four horizons use the same final-converged h_fit grid; early horizons are descriptive, not plateau-gated decision fits",
        "horizons": horizons,
        "note": "cumulative event rate is reported for context and is not substituted for the exact mean global reset interval",
    }


def evaluate_controls(data: RawData, fit_results: dict[str, dict]) -> dict:
    uncapped_seeds = []
    for seed in SEEDS:
        values = [data.summaries["death-reset"][(1.0, seed, step)].dbar for step in SAMPLE_STEPS]
        uncapped_seeds.append({
            "seed": seed,
            "Dbar_by_horizon": values,
            "strictly_increasing": all(a < b for a, b in zip(values, values[1:])),
            "net_growth": values[-1] > values[0],
        })
    uncapped_growth = all(item["strictly_increasing"] and item["net_growth"] for item in uncapped_seeds)
    capped_seeds = []
    for seed in SEEDS:
        values = [data.summaries["cap"][(1.0, seed, step)].dbar for step in SAMPLE_STEPS]
        capped_seeds.append({
            "seed": seed,
            "Dbar_by_horizon": values,
            "bounded_at_one": all(value <= 1.0 + 1e-6 for value in values),
            "relative_D800_D400": relative_convergence(values[2], values[3]),
            "converged": converged(values[2], values[3]),
        })
    capped_converged = sum(item["converged"] for item in capped_seeds)
    cap_bounded = all(item["bounded_at_one"] for item in capped_seeds)
    cap_plateau = capped_converged >= MIN_CONVERGED_SEEDS
    fires = {
        "passed": uncapped_growth and cap_bounded and cap_plateau,
        "uncapped_h1_growth": uncapped_growth,
        "uncapped_rule": "every seed increases strictly at all four horizons",
        "capped_h1_bounded": cap_bounded,
        "capped_h1_plateau": cap_plateau,
        "capped_converged_seed_count": capped_converged,
        "required_capped_converged_seed_count": MIN_CONVERGED_SEEDS,
        "cap_bound": 1.0,
        "uncapped_seeds": uncapped_seeds,
        "capped_seeds": capped_seeds,
    }
    silent_reproduced = {endpoint: fit_results[f"silent_{endpoint}"]["passes"] for endpoint in TARGETS}
    silent_estimable = all(fit_results[f"silent_{endpoint}"]["status"] == "ok" for endpoint in TARGETS)
    silent_all = silent_estimable and all(silent_reproduced.values())
    silent = {
        "passed": silent_estimable and not silent_all,
        "estimable": silent_estimable,
        "all_three_reproduced_within_tolerance": silent_all,
        "endpoint_ci_intersects_target_tolerance": silent_reproduced,
        "rule": "fit h=.9,.95,.98,.99; fail only when all three 95% seed-bootstrap CIs intersect target +/- 0.15",
        "fits": {endpoint: compact_fit(fit_results[f"silent_{endpoint}"], include_points=True) for endpoint in TARGETS},
    }
    per_h = []
    for h in H_SPECIFIC:
        per_seed = []
        for seed in SEEDS:
            death = data.histograms["death-reset"][(h, seed)]
            sham = data.histograms["sham"][(h, seed)]
            exact = schedule_equal(death, sham)
            counts_equal = all(
                data.summaries["death-reset"][(h, seed, step)].events_so_far
                == data.summaries["sham"][(h, seed, step)].events_so_far
                for step in SAMPLE_STEPS
            )
            relative = {}
            for horizon in (400_000, 800_000):
                d_death = data.summaries["death-reset"][(h, seed, horizon)].dbar
                d_sham = data.summaries["sham"][(h, seed, horizon)].dbar
                relative[horizon] = abs(d_death - d_sham) / d_death if d_death > 0.0 else None
            per_seed.append({
                "seed": seed,
                "schedule_exact": exact and counts_equal,
                "death_event_count": death.event_count,
                "sham_event_count": sham.event_count,
                "death_schedule_hash": death.schedule_hash,
                "sham_schedule_hash": sham.schedule_hash,
                "death_reset_sum": death.reset_sum,
                "sham_reset_sum": sham.reset_sum,
                "death_reset_sumsq": death.reset_sumsq,
                "sham_reset_sumsq": sham.reset_sumsq,
                "death_reset_min": death.reset_min,
                "sham_reset_min": sham.reset_min,
                "death_reset_max": death.reset_max,
                "sham_reset_max": sham.reset_max,
                "cumulative_counts_equal": counts_equal,
                "relative_Dbar_difference_400000": relative[400_000],
                "relative_Dbar_difference_800000": relative[800_000],
            })
        med400 = median([item["relative_Dbar_difference_400000"] for item in per_seed if item["relative_Dbar_difference_400000"] is not None])
        med800 = median([item["relative_Dbar_difference_800000"] for item in per_seed if item["relative_Dbar_difference_800000"] is not None])
        schedule_exact = all(item["schedule_exact"] for item in per_seed)
        comparison_defined = all(
            item["relative_Dbar_difference_400000"] is not None and item["relative_Dbar_difference_800000"] is not None
            for item in per_seed
        )
        reproduces = schedule_exact and comparison_defined and med400 <= 0.15 and med800 <= 0.15
        per_h.append({
            "h": h,
            "schedule_exact": schedule_exact,
            "comparison_defined": comparison_defined,
            "median_relative_Dbar_difference_400000": med400,
            "median_relative_Dbar_difference_800000": med800,
            "relative_difference_threshold": 0.15,
            "yoked_reproduces_pole": reproduces,
            "seeds": per_seed,
        })
    schedule_exact = all(item["schedule_exact"] for item in per_h)
    comparison_defined = all(item["comparison_defined"] for item in per_h)
    reproducing_h = [item["h"] for item in per_h if item["yoked_reproduces_pole"]]
    yoked_reproduction = bool(reproducing_h)
    specificity_supported = schedule_exact and comparison_defined and not yoked_reproduction
    specific = {
        "passed": specificity_supported,
        "specificity_supported": specificity_supported,
        "schedule_exact": schedule_exact,
        "comparison_defined": comparison_defined,
        "yoked_reproduces_pole": yoked_reproduction,
        "reproducing_h": reproducing_h,
        "rule": "exact death-reset/sham count, hash and reset moments at both h; reproduction if median |Ddeath-Dsham|/Ddeath <=15% at both 400000 and 800000",
        "per_h": per_h,
    }
    return {
        "fires": fires,
        "silent": silent,
        "specific": specific,
        "sham_schedule_exact": schedule_exact,
    }


def systematic_horizon_shift(horizons: dict, endpoint: str = "alpha_D") -> dict:
    fits = [horizon[endpoint] for horizon in horizons["horizons"]]
    estimates = [fit.get("point_estimate") for fit in fits]
    estimable = len(estimates) == 4 and all(
        value is not None and math.isfinite(value) and fit.get("status") == "ok"
        for value, fit in zip(estimates, fits)
    )
    changes = [b - a for a, b in zip(estimates, estimates[1:])] if estimable else []
    same_sign = (
        estimable and all(change > 0.0 for change in changes)
        or estimable and all(change < 0.0 for change in changes)
    )
    exceeding = [abs(change) > TOLERANCE for change in changes]
    systematic = bool(same_sign and sum(exceeding) >= 2)
    return {
        "endpoint": endpoint,
        "estimable": estimable,
        "estimates": estimates,
        "successive_changes": changes,
        "same_sign_all_three": same_sign,
        "exceeds_tolerance": exceeding,
        "systematic_shift": systematic,
        "rule": "same sign in all three successive changes and magnitude >0.15 in at least two changes",
    }


def classify(converged_fit_point_count: int, endpoint_fits: dict[str, dict], controls: dict,
             horizon_assessment: dict | None = None) -> dict:
    endpoint_pass = {endpoint: endpoint_fits[endpoint]["passes"] for endpoint in TARGETS}
    horizon_failure = bool(horizon_assessment and horizon_assessment["systematic_shift"])
    if not controls["fires"]["passed"] or not controls["silent"]["passed"]:
        outcome, classification = "void", "void"
        reason = "instrument control failed: fires and/or silent"
    elif horizon_failure:
        outcome, classification = "failed", "endpoint_failure"
        reason = "alpha_D changes systematically with horizon under the pre-run same-sign/two-transition rule"
    elif converged_fit_point_count < MIN_FIT_POINTS:
        outcome, classification = "failed", "horizon_limited"
        reason = f"only {converged_fit_point_count} converged h_fit points; at least {MIN_FIT_POINTS} required"
    elif controls["specific"]["yoked_reproduces_pole"]:
        outcome, classification = "failed", "yoked_reproduces_pole"
        reason = "yoked sham reproduces death-reset Dbar within 15% at both required horizons"
    elif not all(endpoint_pass.values()):
        outcome, classification = "failed", "endpoint_failure"
        reason = "one or more endpoint 95% bootstrap CIs do not intersect target +/-0.15"
    elif controls["specific"]["specificity_supported"]:
        outcome, classification = "passed", "passed"
        reason = "all endpoint CIs pass and the exact yoked control supports specificity"
    else:
        outcome, classification = "failed", "specificity_not_confirmed"
        reason = "endpoint CIs pass, but exact yoking or the non-reproduction comparison is not supported"
    return {
        "scientific_outcome": outcome,
        "reported_scientific_classification": classification,
        "reason": reason,
        "endpoint_pass": endpoint_pass,
        "horizon_alpha_D": horizon_assessment,
        "negative_results_are_valid": outcome in ("passed", "failed"),
    }


DECISION_RULES = {
    "convergence": "per seed |D800-D400|/D800<=0.01; h converged when >=10/12 seeds converge",
    "minimum_fit_points": "fewer than four converged h_fit points => failed/horizon_limited; no asymptotic slope decision",
    "alpha_D": "log-log OLS of mean seed Dbar(800000) vs log(1-h), h=1 excluded",
    "alpha_deriv": "|mean seed D(h+step)-mean seed D(h-step)|/(2*step), then log-log OLS; step=min(0.00025,(1-h)/4); mean per-seed derivative is a sensitivity diagnostic",
    "alpha_Tlife": "log-log OLS of mean seed exact global reset-interval mean vs log(1-h); alpha_Tlife=+slope because T_life~x^alpha, whereas alpha_D and alpha_deriv=-slope for x^-alpha",
    "bootstrap": "10000 replicates with random.Random(20261103), resampling 12 seed indices with replacement; the same indices are used for every h and endpoint",
    "endpoint_pass": "95% percentile bootstrap CI intersects target +/-0.15; all 10000 replicates must be valid",
    "fires": "uncapped h=1 strictly grows at every horizon for every seed; capped h=1 stays <=1 and >=10/12 seeds converge",
    "silent": "remote h=.9,.95,.98,.99 fit fails only if all three endpoint CIs reproduce their targets within +/-0.15",
    "specific": "exact yoked count/hash/reset moments; median relative Dbar difference <=15% at both 400000 and 800000 implies yoked_reproduces_pole",
    "priority": "fires/silent failure => void; else systematic alpha_D horizon shift => endpoint_failure; else <4 converged h => horizon_limited; else yoked reproduction => yoked_reproduces_pole; else endpoint failure => failed; else supported specificity => passed",
    "horizon_dependence": "alpha_D at all four horizons: same sign in all three successive changes and magnitude >0.15 in at least two changes => failed/endpoint_failure",
}

LIMITATIONS = [
    "This is a numerical check of an analytic result, not a new scientific result by itself.",
    "T_life is the death-reset interval, not Chao senescence time; no equality between the definitions is assumed.",
    "Points near h=1 may not plateau by 800000 steps; such runs are horizon_limited rather than confirmed.",
    "Comparison with Chao is blocked by the missing Q-024 parameter translation.",
    "The driver rounds Dbar to six decimals; finite differences of nearby h can amplify this numerical error.",
    "Only four summary horizons are available, not full trajectories; the pre-run alpha_D same-sign/two-transition rule is an additional decision gate.",
    "The interval histogram has no event-step field, so exact prefix T_life moments before 800000 are not recoverable; cumulative event rates are not substituted for them.",
    "The schedule hash is two non-cryptographic 64-bit FNV-1a hashes and cannot exclude collisions or replace an event journal for forensic audit.",
    "Bootstrap uncertainty conditions on the observed final-converged h set and resamples all 12 seeds at those h; it does not include model-selection or horizon-selection uncertainty.",
    "Missing zero-event T_life values are omitted from the relevant seed mean and their counts are reported; no interval is imputed.",
    "A zero or non-positive log-log response, including a zero central derivative, is unestimable and fails the preregistered endpoint gate; it is never imputed or replaced by a positive floor.",
    "Equal zero-event yoked schedules are exact only when both strict summaries have zero counts, zero reset moments, blank hashes and no interval records.",
    "The synthetic self-test validates implementation behavior only and is never scientific evidence.",
]


def analyze_data(data: RawData, input_hashes: dict | None = None) -> dict:
    convergence = convergence_details(data)
    fit_hs = tuple(convergence["converged_fit_h"])
    specs = make_fit_specs(data, fit_hs)
    samples = bootstrap_seed_indices()
    fit_results, bootstrap_rows = bootstrap_fit_specs(specs, samples)
    endpoint_fits = {endpoint: fit_results[endpoint] for endpoint in TARGETS}
    controls = evaluate_controls(data, fit_results)
    horizons = horizon_dependence(data, fit_results)
    horizon_assessment = systematic_horizon_shift(horizons)
    horizons["alpha_D_horizon_rule"] = horizon_assessment
    decision = classify(len(fit_hs), endpoint_fits, controls, horizon_assessment)
    configuration = {
        "task": TASK_ID,
        "N": N,
        "steps": STEPS,
        "seeds": list(SEEDS),
        "sample_steps": list(SAMPLE_STEPS),
        "h_fit": list(H_FIT),
        "h_remote": list(H_REMOTE),
        "h_silent": list(H_SILENT),
        "h_specific": list(H_SPECIFIC),
        "death_reset_h_registry_including_derivative_neighbors": list(DEATH_H),
        "cap_h_registry": [1.0],
        "sham_h_registry": list(H_SPECIFIC),
        "controls": list(CONTROLS),
        "derivative_step": "min(0.00025,(1-h)/4)",
        "minimum_fit_points": MIN_FIT_POINTS,
        "minimum_converged_seeds_per_h": MIN_CONVERGED_SEEDS,
        "convergence_threshold": 0.01,
        "bootstrap_replicates": BOOTSTRAP_REPS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_unit": "seed",
        "bootstrap_percentile": "linear (n-1)*p percentile",
        "histogram_quantiles": "nearest-rank inverse empirical CDF at .025,.50,.975",
        "exponent_sign_convention": "alpha_D=-slope; alpha_deriv=-slope; alpha_Tlife=+slope",
        "targets": TARGETS,
        "target_tolerance": TOLERANCE,
        "no_unseeded_random": True,
    }
    summary = {
        "analysis_version": ANALYSIS_VERSION,
        "task": TASK_ID,
        "input_hashes": input_hashes or {},
        "configuration": configuration,
        "validation": data.validation,
        "scientific_outcome": decision["scientific_outcome"],
        "reported_scientific_classification": decision["reported_scientific_classification"],
        "reason": decision["reason"],
        "negative_results_are_valid": decision["negative_results_are_valid"],
        "endpoint_pass": decision["endpoint_pass"],
        "horizon_alpha_D": decision["horizon_alpha_D"],
        "endpoints": {endpoint: compact_fit(result, include_points=True) for endpoint, result in endpoint_fits.items()},
        "convergence": convergence,
        "horizon_dependence": horizons,
        "controls": {
            "fires": controls["fires"]["passed"],
            "silent": controls["silent"]["passed"],
            "specific": controls["specific"]["passed"],
            "sham_schedule_exact": controls["sham_schedule_exact"],
        },
        "control_summary": {
            "fires": {key: controls["fires"][key] for key in (
                "passed", "uncapped_h1_growth", "capped_h1_bounded", "capped_h1_plateau", "capped_converged_seed_count"
            )},
            "silent": {key: controls["silent"][key] for key in (
                "passed", "estimable", "all_three_reproduced_within_tolerance", "endpoint_ci_intersects_target_tolerance"
            )},
            "specific": {key: controls["specific"][key] for key in (
                "passed", "specificity_supported", "schedule_exact", "comparison_defined", "yoked_reproduces_pole", "reproducing_h"
            )},
            "specific_per_h": [{key: item[key] for key in (
                "h", "schedule_exact", "median_relative_Dbar_difference_400000", "median_relative_Dbar_difference_800000", "yoked_reproduces_pole"
            )} for item in controls["specific"]["per_h"]],
        },
        "decision_rules": DECISION_RULES,
        "limitations": LIMITATIONS,
        "synthetic_data": bool(data.validation.get("synthetic", False)),
        "scientific_evidence": "none: deterministic synthetic self-test" if data.validation.get("synthetic", False) else "only the supplied candidate-driver artifacts; self-test data are excluded",
    }
    return {
        "summary": summary,
        "seed_metrics": seed_metrics(data),
        "fits": flatten_fits(fit_results),
        "bootstrap": bootstrap_rows,
        "controls": controls,
        "fit_results": fit_results,
        "convergence": convergence,
    }


SEED_METRIC_FIELDS = [
    "h", "seed", "control",
    *[f"Dbar_{step}" for step in SAMPLE_STEPS],
    *[f"events_so_far_{step}" for step in SAMPLE_STEPS],
    "global_event_count", "global_interval_mean", "global_interval_q025", "global_interval_q50", "global_interval_q975",
    "global_interval_min", "global_interval_max", "global_interval_bin_count", "histogram_detail", "organism_interval_bin_count", "organisms_with_events",
    "reset_value_sum", "reset_value_sumsq", "reset_value_mean", "reset_value_second_moment", "reset_value_variance", "reset_value_std",
    "reset_value_min", "reset_value_max", "reset_schedule_hash", "abs_D800_D400", "relative_D800_D400", "converged",
]
BOOTSTRAP_FIELDS = [
    "replicate", "bootstrap_seed", "sampled_seeds",
    "alpha_D", "alpha_deriv", "alpha_Tlife",
    *[f"alpha_D_{step}" for step in SAMPLE_STEPS],
    *[f"alpha_deriv_{step}" for step in SAMPLE_STEPS],
    *[f"silent_{endpoint}" for endpoint in TARGETS],
]
OUTPUT_NAMES = ("seed_metrics.csv", "fits.csv", "bootstrap.csv", "controls.json", "summary.json")


def sha256_file(path: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    return {"path": str(path.resolve()), "bytes": size, "sha256": digest.hexdigest()}


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def synthetic_histogram(h: float, seed: int, interval_mean: float, reset_value: float, events: int = 600) -> tuple[HistogramRun, list[int]]:
    low = max(1, math.floor(interval_mean))
    fraction = interval_mean - low
    high_count = int(round(fraction * events))
    low_count = events - high_count
    intervals = [low] * low_count
    if high_count:
        intervals.extend([low + 1] * high_count)
    global_bins = Counter(intervals)
    organism_bins: dict[int, dict[int, int]] = {}
    previous = [0] * N
    steps = []
    elapsed = 0
    reset_sum = 0.0
    reset_sumsq = 0.0
    for index, interval in enumerate(intervals):
        elapsed += interval
        if elapsed > STEPS:
            raise ValueError("synthetic schedule exceeds 800000 steps")
        steps.append(elapsed)
        organism = index % N
        organism_interval = elapsed - previous[organism]
        previous[organism] = elapsed
        bins = organism_bins.setdefault(organism, {})
        bins[organism_interval] = bins.get(organism_interval, 0) + 1
        reset_sum += reset_value
        reset_sumsq += reset_value * reset_value
    run = HistogramRun(
        h=h,
        seed=seed,
        control="death-reset",
        matching_mode="state-dependent",
        summary_seen=True,
        event_count=events,
        reset_sum=reset_sum,
        reset_sumsq=reset_sumsq,
        reset_min=reset_value,
        reset_max=reset_value,
        schedule_hash=schedule_hash((step, reset_value) for step in steps),
        global_intervals=dict(global_bins),
        organism_event_count=events,
        organism_bin_count=sum(len(bins) for bins in organism_bins.values()),
        organisms_with_events=set(organism_bins),
        interval_record_count=len(global_bins) + sum(len(bins) for bins in organism_bins.values()),
        organism_intervals=organism_bins,
    )
    return run, steps


def synthetic_data() -> RawData:
    summaries: dict[str, dict[tuple[float, int, int], SummaryRow]] = {control: {} for control in CONTROLS}
    histograms: dict[str, dict[tuple[float, int], HistogramRun]] = {control: {} for control in CONTROLS}
    death_values: dict[tuple[float, int], list[float]] = {}
    for h in DEATH_H:
        for seed in SEEDS:
            amplitude = 0.8 * (1.0 + 0.03 * math.sin(seed * 0.37))
            if h == 1.0:
                values = [amplitude * 0.001 * step for step in SAMPLE_STEPS]
                interval_mean = 400.0
            else:
                values = [amplitude * (1.0 - h) ** -0.5 * (1.0 + 0.04 * 100_000 / step) for step in SAMPLE_STEPS]
                interval_mean = 400.0 * math.sqrt(1.0 - h)
            death_values[(h, seed)] = values
            histogram, steps = synthetic_histogram(h, seed, interval_mean, h * values[-1])
            histograms["death-reset"][(h, seed)] = histogram
            for step, dbar in zip(SAMPLE_STEPS, values):
                summaries["death-reset"][(h, seed, step)] = SummaryRow(
                    h, seed, step, dbar, bisect.bisect_right(steps, step), "death-reset"
                )
    for seed in SEEDS:
        amplitude = death_values[(1.0, seed)][0] / 100.0
        histogram, steps = synthetic_histogram(1.0, seed, 400.0, 0.8 * amplitude)
        histograms["cap"][(1.0, seed)] = histogram
        for step in SAMPLE_STEPS:
            summaries["cap"][(1.0, seed, step)] = SummaryRow(
                1.0, seed, step, 0.8 * amplitude, bisect.bisect_right(steps, step), "cap"
            )
    for h in H_SPECIFIC:
        for seed in SEEDS:
            source = histograms["death-reset"][(h, seed)]
            histograms["sham"][(h, seed)] = replace(
                source,
                global_intervals=dict(source.global_intervals),
                organisms_with_events=set(source.organisms_with_events),
            )
            for step, value in zip(SAMPLE_STEPS, death_values[(h, seed)]):
                summaries["sham"][(h, seed, step)] = SummaryRow(h, seed, step, value, source.event_count, "sham")
    validation = {
        "status": "passed",
        "synthetic": True,
        "strict_registries": True,
        "summary_rows": {control: len(summaries[control]) for control in CONTROLS},
        "histogram_summary_records": {control: len(histograms[control]) for control in CONTROLS},
        "scientific_evidence": False,
    }
    return RawData(summaries, histograms, validation)


def serialize_summary(rows: dict[tuple[float, int, int], SummaryRow], control: str) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(SUMMARY_HEADER)
    for (h, seed, step), row in sorted(rows.items()):
        writer.writerow([h, seed, step, row.dbar, row.events_so_far, control])
    return output.getvalue()


def serialize_histogram(runs: dict[tuple[float, int], HistogramRun], control: str) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(HISTOGRAM_HEADER)
    for (h, seed), run in sorted(runs.items()):
        mode = MATCHING_MODES[control]
        writer.writerow([
            h, seed, control, mode, "summary", "", "", "", run.event_count,
            run.reset_sum, run.reset_sumsq, run.reset_min, run.reset_max, run.schedule_hash,
        ])
        for interval, count in sorted(run.global_intervals.items()):
            writer.writerow([h, seed, control, mode, "interval", "global", "", interval, count, "", "", "", "", ""])
        if run.organism_intervals is not None:
            for organism, bins in sorted(run.organism_intervals.items()):
                for interval, count in sorted(bins.items()):
                    writer.writerow([h, seed, control, mode, "interval", "organism", organism, interval, count, "", "", "", "", ""])
    return output.getvalue()


def self_test() -> None:
    checks = []
    histogram = {1: 1, 2: 2, 5: 1}
    assert nearest_rank(histogram, 0.5) == 2
    assert nearest_rank(histogram, 0.025) == 1
    assert nearest_rank(histogram, 0.975) == 5
    assert math.isclose(sum(k * v for k, v in histogram.items()) / 4, 2.5)
    assert converged(100.0, 101.0)
    assert not converged(100.0, 102.0)
    assert math.isclose(derivative_step(0.9995), 0.000125)
    checks.append("exact quantiles, convergence boundary, derivative step")

    zero_death = HistogramRun(0.995, 4301, "death-reset", MATCHING_MODES["death-reset"], summary_seen=True)
    zero_sham = HistogramRun(0.995, 4301, "sham", MATCHING_MODES["sham"], summary_seen=True)
    assert schedule_equal(zero_death, zero_sham)
    zero_sham.schedule_hash = "0" * 32
    assert not schedule_equal(zero_death, zero_sham)
    zero_derivative_spec = FitSpec(
        "zero_derivative", "zero_derivative_regression", "alpha_deriv", 800_000,
        H_SILENT, {h: tuple((0.25, 0.25) for _ in SEEDS) for h in H_SILENT},
        "zero central derivative must be reported as unestimable",
    )
    zero_derivative_fit = fit_powerlaw(zero_derivative_spec)
    assert zero_derivative_fit["status"] == "insufficient_positive_values"
    assert zero_derivative_fit["point_estimate"] is None
    assert all(point["log_response"] is None for point in zero_derivative_fit["input_points"])
    checks.append("exact zero-event yoking and zero central derivative without abort")

    data = synthetic_data()
    with tempfile.TemporaryDirectory(prefix="dq6-synthetic-self-test-") as temporary:
        temporary = Path(temporary)
        paths = {}
        for control in CONTROLS:
            summary_path = temporary / f"synthetic-{control}-summary.csv"
            histogram_path = temporary / f"synthetic-{control}-histogram.csv"
            summary_path.write_text(serialize_summary(data.summaries[control], control), encoding="utf-8")
            histogram_path.write_text(serialize_histogram(data.histograms[control], control), encoding="utf-8")
            paths[control] = (summary_path, histogram_path)
        loaded = load_inputs(
            paths["death-reset"][0], paths["cap"][0], paths["sham"][0],
            paths["death-reset"][1], paths["cap"][1], paths["sham"][1],
        )
        assert loaded.validation["status"] == "passed"
        assert loaded.validation["yoked_cumulative_counts_equal"]
    checks.append("full six-file synthetic registry and count validation")
    death_text = serialize_histogram(data.histograms["death-reset"], "death-reset")
    parsed = parse_histogram_stream(io.StringIO(death_text), "death-reset", "<synthetic>")
    first_key = (H_FIT[0], SEEDS[0])
    assert parsed[first_key].global_intervals == data.histograms["death-reset"][first_key].global_intervals
    assert parsed[first_key].schedule_hash == data.histograms["death-reset"][first_key].schedule_hash
    bad_lines = death_text.splitlines()
    summary_index = 1
    bad_fields = next(csv.reader([bad_lines[summary_index]]))
    bad_fields[8] = str(int(bad_fields[8]) + 1)
    bad_lines[summary_index] = ",".join(bad_fields)
    try:
        parse_histogram_stream(io.StringIO("\n".join(bad_lines) + "\n"), "death-reset", "<synthetic-bad-count>")
    except ValueError:
        pass
    else:
        raise AssertionError("histogram count mismatch was accepted")
    bad_fields[8] = "600"
    bad_fields[13] = "x" * 32
    bad_lines[summary_index] = ",".join(bad_fields)
    try:
        parse_histogram_stream(io.StringIO("\n".join(bad_lines) + "\n"), "death-reset", "<synthetic-bad-hash>")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid schedule hash was accepted")
    checks.append("histogram parsing, global counts, hash validation")

    compact_lines = []
    for line in death_text.splitlines():
        fields = next(csv.reader([line]))
        if fields[4] == "summary":
            fields[5] = "global-only"
        if fields[5] != "organism":
            compact_lines.append(",".join(fields))
    compact_runs = parse_histogram_stream(io.StringIO("\n".join(compact_lines) + "\n"), "death-reset", "<synthetic-compact>")
    assert all(run.histogram_detail == "global-only" for run in compact_runs.values())
    assert all(sum(run.global_intervals.values()) == run.event_count for run in compact_runs.values())
    assert all(run.organism_event_count == 0 for run in compact_runs.values())
    checks.append("explicit global-only compact histogram contract")

    result = analyze_data(data, {"synthetic_self_test": True})
    endpoints = result["summary"]["endpoints"]
    recovered = {endpoint: result["fit_results"][endpoint]["point_estimate"] for endpoint in TARGETS}
    # The prescribed finite central difference has a small known curvature
    # bias relative to the analytic derivative of x^-1/2.
    assert all(abs(recovered[endpoint] - TARGETS[endpoint]) < 0.02 for endpoint in TARGETS), recovered
    assert all(result["fit_results"][endpoint]["passes"] for endpoint in TARGETS)
    assert result["controls"]["fires"]["passed"]
    assert not result["controls"]["silent"]["passed"]
    assert result["controls"]["specific"]["yoked_reproduces_pole"]
    assert result["summary"]["scientific_outcome"] == "void"
    checks.append("power-law recovery and all endpoint bootstrap CIs")
    with tempfile.TemporaryDirectory(prefix="dq6-synthetic-output-self-test-") as temporary:
        temporary = Path(temporary)
        write_csv(temporary / "seed_metrics.csv", result["seed_metrics"], SEED_METRIC_FIELDS)
        write_csv(temporary / "fits.csv", result["fits"], FIT_FIELDS)
        write_csv(temporary / "bootstrap.csv", result["bootstrap"], BOOTSTRAP_FIELDS)
        write_json(temporary / "controls.json", {"synthetic_data": True, "scientific_evidence": False, **result["controls"]})
        write_json(temporary / "summary.json", result["summary"])
        assert len(result["seed_metrics"]) == 336
        assert len(result["bootstrap"]) == BOOTSTRAP_REPS
        assert json.loads((temporary / "summary.json").read_text(encoding="utf-8"))["synthetic_data"] is True
        assert all((temporary / name).is_file() for name in OUTPUT_NAMES)
    checks.append("all five output schemas in a temporary synthetic directory")

    # Break the remote power law while preserving the local asymptotic fixture.
    remote_factors = {0.9: 0.70, 0.95: 0.90, 0.98: 1.15, 0.99: 1.50}
    for center, factor in remote_factors.items():
        step = derivative_step(center)
        for h in (center - step, center, center + step):
            h = canonical_h(h, DEATH_H, "synthetic remote neighbor")
            for seed in SEEDS:
                for horizon in SAMPLE_STEPS:
                    data.summaries["death-reset"][(h, seed, horizon)].dbar *= factor
    convergence = convergence_details(data)
    remote_specs = [spec for spec in make_fit_specs(data, tuple(convergence["converged_fit_h"])) if spec.dataset == "silent_remote"]
    remote_results, _ = bootstrap_fit_specs(remote_specs, bootstrap_seed_indices())
    combined_results = dict(result["fit_results"])
    combined_results.update(remote_results)
    controls = evaluate_controls(data, combined_results)
    assert controls["fires"]["passed"] and controls["silent"]["passed"]
    assert controls["specific"]["yoked_reproduces_pole"]
    decision = classify(len(convergence["converged_fit_h"]), result["fit_results"], controls)
    assert decision["reported_scientific_classification"] == "yoked_reproduces_pole"
    checks.append("fires/silent controls and yoked-reproduction classification")

    for h in H_SPECIFIC:
        for seed in SEEDS:
            for horizon in SAMPLE_STEPS:
                data.summaries["sham"][(h, seed, horizon)].dbar *= 0.2
    controls = evaluate_controls(data, combined_results)
    assert controls["specific"]["specificity_supported"]
    decision = classify(len(convergence["converged_fit_h"]), result["fit_results"], controls)
    assert decision["scientific_outcome"] == "passed"
    checks.append("exact yoking with non-reproduction supports specificity")

    horizon_limited = copy.deepcopy(data)
    for h in H_FIT[-3:]:
        for seed in SEEDS:
            horizon_limited.summaries["death-reset"][(h, seed, 800_000)].dbar *= 1.2
    limited_convergence = convergence_details(horizon_limited)
    assert limited_convergence["converged_fit_point_count"] == 2
    decision = classify(limited_convergence["converged_fit_point_count"], result["fit_results"], controls)
    assert decision["reported_scientific_classification"] == "horizon_limited"
    checks.append("fewer-than-four converged h classification")

    bad_fires = copy.deepcopy(data)
    for seed in SEEDS:
        bad_fires.summaries["cap"][(1.0, seed, 800_000)].dbar *= 1.1
    bad_controls = evaluate_controls(bad_fires, combined_results)
    assert not bad_controls["fires"]["passed"]
    decision = classify(len(convergence["converged_fit_h"]), result["fit_results"], bad_controls)
    assert decision["scientific_outcome"] == "void"
    failed_endpoints = copy.deepcopy(result["fit_results"])
    failed_endpoints["alpha_Tlife"]["passes"] = False
    decision = classify(len(convergence["converged_fit_h"]), failed_endpoints, controls)
    assert decision["reported_scientific_classification"] == "endpoint_failure"
    checks.append("instrument void and endpoint-failure classifications")

    horizon_fixture = {"horizons": []}
    for value in (0.40, 0.25, 0.10, -0.05):
        horizon_fixture["horizons"].append({
            "alpha_D": {"status": "ok", "point_estimate": value},
            "alpha_deriv": {"status": "ok", "point_estimate": 1.5},
        })
    horizon_test = systematic_horizon_shift(horizon_fixture)
    assert horizon_test["systematic_shift"]
    horizon_decision = classify(len(convergence["converged_fit_h"]), result["fit_results"], controls, horizon_test)
    assert horizon_decision["reported_scientific_classification"] == "endpoint_failure"
    checks.append("systematic alpha_D horizon-shift classification")

    print(json.dumps({
        "self_test": "ok",
        "synthetic_data": True,
        "scientific_evidence": False,
        "bootstrap_replicates_per_fit": BOOTSTRAP_REPS,
        "power_law_recovery": recovered,
        "checks": checks,
        "scenario_classifications": ["void", "yoked_reproduces_pole", "passed", "horizon_limited", "void", "endpoint_failure"],
    }, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--death-reset", type=Path, help="death-reset summary CSV")
    parser.add_argument("--cap", type=Path, help="cap summary CSV")
    parser.add_argument("--sham", type=Path, help="sham summary CSV")
    parser.add_argument("--death-histogram", type=Path)
    parser.add_argument("--cap-histogram", type=Path)
    parser.add_argument("--sham-histogram", type=Path)
    parser.add_argument("--out", type=Path, help="new analysis output directory")
    parser.add_argument("--task", type=Path, help="optional task JSON to hash")
    parser.add_argument("--driver", type=Path, help="optional candidate binary to hash")
    parser.add_argument("--driver-source", type=Path, help="optional main-owned Rust source to hash")
    parser.add_argument("--candidate-source", type=Path, help="optional candidate Rust source to hash")
    parser.add_argument("--environment", type=Path, help="optional runner environment record to hash")
    parser.add_argument("--run-manifest", type=Path, help="optional runner manifest to hash")
    parser.add_argument("--self-test", action="store_true", help="run deterministic in-memory synthetic checks")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    required = (args.death_reset, args.cap, args.sham, args.death_histogram, args.cap_histogram, args.sham_histogram, args.out)
    if not all(required):
        parser.error("--death-reset, --cap, --sham, all three --*-histogram paths, and --out are required")
    try:
        if args.out.exists():
            existing = [name for name in OUTPUT_NAMES if (args.out / name).exists()]
            if existing:
                raise ValueError(f"refusing to overwrite analyzer outputs: {existing}")
        data = load_inputs(args.death_reset, args.cap, args.sham, args.death_histogram, args.cap_histogram, args.sham_histogram)
        hash_paths = {
            "death_reset_summary": args.death_reset,
            "cap_summary": args.cap,
            "sham_summary": args.sham,
            "death_reset_histogram": args.death_histogram,
            "cap_histogram": args.cap_histogram,
            "sham_histogram": args.sham_histogram,
            "analyzer": Path(__file__),
        }
        for name, path in (
            ("task", args.task), ("driver", args.driver), ("driver_source", args.driver_source),
            ("candidate_source", args.candidate_source), ("environment", args.environment),
            ("run_manifest", args.run_manifest),
        ):
            if path is not None:
                hash_paths[name] = path
        input_hashes = {name: sha256_file(path) for name, path in hash_paths.items()}
        result = analyze_data(data, input_hashes)
        args.out.mkdir(parents=True, exist_ok=True)
        write_csv(args.out / "seed_metrics.csv", result["seed_metrics"], SEED_METRIC_FIELDS)
        write_csv(args.out / "fits.csv", result["fits"], FIT_FIELDS)
        write_csv(args.out / "bootstrap.csv", result["bootstrap"], BOOTSTRAP_FIELDS)
        write_json(args.out / "controls.json", result["controls"])
        write_json(args.out / "summary.json", result["summary"])
    except (OSError, ValueError, csv.Error, ArithmeticError) as error:
        print(f"dq6_analyze: error: {error}", file=sys.stderr)
        return 2
    print(json.dumps({
        "out": str(args.out.resolve()),
        "scientific_outcome": result["summary"]["scientific_outcome"],
        "reported_scientific_classification": result["summary"]["reported_scientific_classification"],
        "controls": result["summary"]["controls"],
        "endpoint_pass": result["summary"]["endpoint_pass"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
