from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

PIPELINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE))
import b_analyze as analyzer  # noqa: E402
import b_make_plan as make_plan  # noqa: E402
import b_run_leased as leased_runner  # noqa: E402
import b_submit as submit  # noqa: E402


def fnv1a64(data: bytes, value: int = 0xCBF29CE484222325) -> int:
    for byte in data:
        value ^= byte
        value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return value


def hash_u64(value: int, state: int) -> int:
    return fnv1a64(struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF), state)


def hash_f64(value: float, state: int) -> int:
    bits = struct.unpack("<Q", struct.pack("<d", value))[0]
    return hash_u64(bits, state)


def trajectory_hash(rows: list[dict]) -> str:
    state = 0xCBF29CE484222325
    for row in rows:
        state = hash_u64(row["n_t"], state)
        for field in ("cap_now", "d", "e", "s", "v", "f", "maint_e", "maint_short"):
            state = hash_f64(row[field], state)
    return f"{state:016x}"


def state_hash(n_t: int, d: float, e: float, s: float, debt: float,
               external: int, failed: int) -> str:
    state = hash_u64(n_t, 0xCBF29CE484222325)
    for value in (d, e, s, debt):
        state = hash_f64(value, state)
    state = hash_u64(external, state)
    state = hash_u64(failed, state)
    return f"{state:016x}"


def float_text(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    return repr(value)


def schedule(arm: str, step: int) -> tuple[str, int, int, int, int]:
    if arm == "B1-sham" and step == 5:
        return "sham", 0, 0, 0, 0
    ko1 = {"B2-ko1", "B3-ko2", "rescue", "A-B2-cost", "A-B3-cost", "A-rescue-cost", "ghost", "placebo-k1"}
    ko2 = {"B3-ko2", "rescue", "A-B3-cost", "A-rescue-cost", "ghost", "placebo-k1"}
    if arm in ko1 and step == 5:
        return "ko1", 0, 1, 1, 0
    if arm in ko2 and step == 10:
        return "ko2", 0, 1, 1, 0
    if arm in {"rescue", "A-rescue-cost"} and step == 15:
        return "rescue", 1, 0, 0, 1
    return "none", 0, 0, 0, 0


def capacity(arm: str, n_t: int) -> float:
    if arm in {"A-control", "A-B2-cost", "A-B3-cost", "A-rescue-cost", "ghost"}:
        return 0.1
    threshold = 1 if arm == "placebo-k1" else 2
    return min(0.1, 0.05 * n_t) if n_t >= threshold else 0.0


def generate(*, starve_control: bool = False, ghost_broken: bool = False,
             placebo_zero: bool = False, death_arm: str | None = None) -> tuple[list[dict], list[dict]]:
    raw_rows: list[dict] = []
    step_rows: list[dict] = []
    for arm in analyzer.ARMS:
        d0 = 0.25 if arm == "D-half" else (1.0 / 6.0 if arm == "D-third" else 0.5)
        d = d0
        e = 0.1
        s = 0.1
        n_t = 3
        debt = 0.0
        failed_stock = 0
        external_stock = 1 if arm in {"rescue", "A-rescue-cost"} else 0
        alive = True
        death_step = -1
        death_cause = "none"
        arm_steps: list[dict] = []
        aurd_sum = 0.0
        aurd_abs_sum = 0.0
        v_after_ko2 = 0.0
        v_after_rescue = 0.0
        maint_short_total = 0.0
        rescue_in_total = 0
        max_imbalance = 0.0
        t_reach95 = 0
        binary95 = 0
        f_at_ko2 = math.nan

        for step in range(40):
            if not alive:
                break
            event, module_in, module_out, failed_in, external_debit = schedule(arm, step)
            n_before = n_t
            failed_before = failed_stock
            external_before = external_stock
            debt_before = debt
            n_t += module_in - module_out
            failed_stock += failed_in
            external_stock -= external_debit
            rescue_in_total += module_in

            e_in = 0.05
            s_in = 0.04 if starve_control and arm == "A-control" else 0.05
            if death_arm == arm and step >= 10:
                e_in = 0.0
                s_in = 0.0
            e_add = min(e_in, max(0.0, 1.0 - e))
            s_add = min(s_in, max(0.0, 1.0 - s))
            e_unc = e_in - e_add
            s_unc = s_in - s_add
            maint_need = 0.03 if arm == "A-control" else 0.01 * n_t
            maint_e = min(max(e + e_add, 0.0), maint_need)
            maint_short = maint_need - maint_e
            debt += maint_short
            maint_short_total += maint_short
            d_before = d
            e_before = e + e_add - maint_e
            s_before = s + s_add
            cap_now = capacity(arm, n_t)
            if ghost_broken and arm == "ghost" and step >= 10:
                cap_now = 0.0
            if placebo_zero and arm == "placebo-k1" and step >= 10:
                cap_now = 0.0
            v = max(0.0, min(0.3 * d_before, cap_now, e_before / 0.2, s_before / 0.2, d_before))
            d = d_before - v
            e = e_before - 0.2 * v
            s = s_before - 0.2 * v
            f = (d0 - d) / d0
            energy_residual = e_before - 0.2 * v - e
            substrate_residual = s_before - 0.2 * v - s
            debt_residual = debt - (debt_before + maint_short)
            module_residual = n_before + module_in - module_out - n_t
            failed_residual = failed_before + failed_in - failed_stock
            rescue_residual = external_before - module_in - external_stock
            imbalance = max(abs(value) for value in (
                energy_residual, substrate_residual, debt_residual,
                module_residual, failed_residual, rescue_residual,
            ))
            max_imbalance = max(max_imbalance, imbalance)
            if e <= 0.0 or d >= 1.0:
                alive = False
                death_step = step
                death_cause = "energy" if e <= 0.0 else "damage"
            if step == 9:
                f_at_ko2 = f
            if step == 10:
                binary95 = int(alive and f >= 0.95)
            if t_reach95 == 0 and alive and f >= 0.95:
                t_reach95 = step
            aurd_sum += d / d0
            aurd_abs_sum += d
            if step >= 10:
                v_after_ko2 += v
            if step >= 15:
                v_after_rescue += v
            arm_steps.append({
                "arm": arm, "seed": 5401, "step": step, "n_t": n_t, "event": event,
                "u_e": 0.5, "u_s": 0.5, "e_in": e_in, "s_in": s_in,
                "e_unc": e_unc, "s_unc": s_unc, "maint_e": maint_e,
                "maint_short": maint_short, "v": v, "d": d, "e": e, "s": s,
                "cap_now": cap_now, "f": f, "imbalance": imbalance,
                "maint_debt": debt, "debt_imbalance": debt_residual,
                "module_in": module_in, "module_out": module_out,
                "module_imbalance": module_residual, "failed_module_in": failed_in,
                "failed_module_stock": failed_stock,
                "failed_module_imbalance": failed_residual,
                "external_rescue_stock": external_stock,
                "rescue_stock_imbalance": rescue_residual,
                "d_before": d_before, "e_before": e_before, "s_before": s_before,
                "alive": int(alive), "death_cause": death_cause,
            })
        step_rows.extend(arm_steps)
        observed = len(arm_steps)
        final = arm_steps[-1]
        k_eff = 1 if arm == "placebo-k1" else (-1 if arm in analyzer.FIXED_CAP_ARMS else 2)
        raw_rows.append({
            "arm": arm, "k_eff": k_eff, "d0": d0, "seed": 5401,
            "aurd": aurd_sum / 40 if alive else math.nan,
            "aurd_abs": aurd_abs_sum / 40 if alive else math.nan,
            "f_final": final["f"] if alive else math.nan,
            "f_at_ko2": f_at_ko2, "v_after_ko2": v_after_ko2,
            "v_after_rescue": v_after_rescue, "binary95_10": binary95,
            "t_reach95": t_reach95, "max_imbalance": max_imbalance,
            "v_first": arm_steps[0]["v"] if arm_steps else math.nan,
            "n_final": n_t,
            "aurd_observed": aurd_sum / observed if observed else math.nan,
            "aurd_abs_observed": aurd_abs_sum / observed if observed else math.nan,
            "f_at_death": final["f"] if not alive else math.nan,
            "maint_short_total": maint_short_total, "maint_debt": debt,
            "rescue_in_total": rescue_in_total, "external_rescue_stock": external_stock,
            "failed_module_stock": failed_stock, "observed_steps": observed,
            "alive": int(alive), "death_step": death_step,
            "death_cause": death_cause, "horizon_censored": int(alive),
            "state_hash": state_hash(n_t, d, e, s, debt, external_stock, failed_stock),
            "trajectory_hash": trajectory_hash(arm_steps),
        })
    return raw_rows, step_rows


def write_csv(path: Path, header: tuple[str, ...], rows: list[dict]) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: float_text(value) if isinstance(value, float) else value for key, value in row.items()})
    return path.read_bytes()


def file_record(path: Path, rel: str, rows: int) -> dict:
    data = path.read_bytes()
    return {"path": rel, "rows": rows, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class Fixture:
    def __init__(self, root: Path, **options):
        self.root = root
        self.raw_rows, self.step_rows = generate(**options)
        self.manifest_path = root / "raw-manifest.json"
        self.raw_path = root / "raw.csv"
        self.steps_path = root / "steps.csv"
        self.out = root / "analysis"
        self.sync()

    def sync(self) -> None:
        for directory in (self.root, self.root / "run1", self.root / "run2"):
            write_csv(directory / "raw.csv", analyzer.RAW_HEADER, self.raw_rows)
            write_csv(directory / "steps.csv", analyzer.STEPS_HEADER, self.step_rows)
        raw_record = file_record(self.raw_path, "raw.csv", len(self.raw_rows))
        steps_record = file_record(self.steps_path, "steps.csv", len(self.step_rows))
        self.manifest = {
            "schema": "raw-manifest/v2", "task_id": "EXP-2026-4107", "task_version": 7,
            "task_version_sha256": "a" * 64, "base_commit": "f" * 40,
            "driver_rc": 0, "run2_driver_rc": 0, "runner_rc": 0,
            "seeds": 1, "seed_base": 5401, "expected_arms": 12,
            "expected_raw_rows": 12, "expected_steps_rows": 480,
            "driver": {"sha256": "b" * 64, "source_sha256": "c" * 64},
            "environment": {
                "task_id": "EXP-2026-4107", "task_version": 7,
                "task_version_sha256": "a" * 64, "base_commit": "f" * 40,
                "seeds": 1, "seed_base": 5401,
            },
            "raw_csv": raw_record, "steps_csv": steps_record,
            "executions": {
                name: {
                    "returncode": 0,
                    "raw_csv": file_record(self.root / name / "raw.csv", f"{name}/raw.csv", len(self.raw_rows)),
                    "steps_csv": file_record(self.root / name / "steps.csv", f"{name}/steps.csv", len(self.step_rows)),
                    "driver_schedule_line": "schedule: t*=5;t**=10;t***=15;m=3;k=2;r0=R0/2",
                }
                for name in ("run1", "run2")
            },
            "repeat": {"byte_identical": True},
        }
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8")

    def analyze(self) -> dict:
        return analyzer.analyze(self.raw_path, self.steps_path, self.manifest_path, self.out)

    def make_sensitive(self) -> None:
        for directory in (self.root, self.root / "run1", self.root / "run2"):
            (directory / "raw.csv").write_bytes(
                b"INSENSITIVE_BY_CONSTRUCTION r0=0.05 need=0.01125 kD=0.3 need=0.000746\n")
            (directory / "steps.csv").write_bytes(b"")
        self.manifest["driver_rc"] = 3
        self.manifest["run2_driver_rc"] = 3
        self.manifest["runner_rc"] = 3
        self.manifest["raw_csv"] = file_record(self.raw_path, "raw.csv", 0)
        self.manifest["steps_csv"] = file_record(self.steps_path, "steps.csv", 0)
        for name in ("run1", "run2"):
            self.manifest["executions"][name]["returncode"] = 3
            self.manifest["executions"][name]["raw_csv"] = file_record(
                self.root / name / "raw.csv", f"{name}/raw.csv", 0)
            self.manifest["executions"][name]["steps_csv"] = file_record(
                self.root / name / "steps.csv", f"{name}/steps.csv", 0)
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8")


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_registered_headers_and_arms(self):
        self.assertEqual(f"{analyzer.fnv1a64(b'hello'):016x}", "a430d84680aabd0b")
        self.assertEqual(analyzer.ARMS, (
            "A-control", "B1-sham", "B2-ko1", "B3-ko2", "rescue",
            "A-B2-cost", "A-B3-cost", "A-rescue-cost", "D-half", "D-third",
            "ghost", "placebo-k1",
        ))
        self.assertEqual(",".join(analyzer.RAW_HEADER),
            "arm,k_eff,d0,seed,aurd,aurd_abs,f_final,f_at_ko2,v_after_ko2,v_after_rescue,binary95_10,t_reach95,max_imbalance,v_first,n_final,aurd_observed,aurd_abs_observed,f_at_death,maint_short_total,maint_debt,rescue_in_total,external_rescue_stock,failed_module_stock,observed_steps,alive,death_step,death_cause,horizon_censored,state_hash,trajectory_hash")
        self.assertEqual(",".join(analyzer.STEPS_HEADER),
            "arm,seed,step,n_t,event,u_e,u_s,e_in,s_in,e_unc,s_unc,maint_e,maint_short,v,d,e,s,cap_now,f,imbalance,maint_debt,debt_imbalance,module_in,module_out,module_imbalance,failed_module_in,failed_module_stock,failed_module_imbalance,external_rescue_stock,rescue_stock_imbalance,d_before,e_before,s_before,alive,death_cause")

    def test_pass(self):
        fixture = Fixture(self.root)
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "passed", summary["reason"])
        self.assertTrue(summary["all_controls_valid"])
        self.assertTrue(all(summary["predictions"].values()))

    def test_failed_scientific_prediction_with_valid_controls(self):
        fixture = Fixture(self.root, starve_control=True)
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "failed", summary["reason"])
        self.assertTrue(summary["all_controls_valid"])
        self.assertFalse(summary["predictions"]["P1_a_control_equals_b1_trajectory"])

    def test_void_ghost(self):
        fixture = Fixture(self.root, ghost_broken=True)
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void", summary["reason"])
        self.assertFalse(summary["controls"]["ghost_control_valid"])

    def test_void_placebo(self):
        fixture = Fixture(self.root, placebo_zero=True)
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void", summary["reason"])
        self.assertFalse(summary["controls"]["placebo_control_valid"])

    def test_void_ledger(self):
        fixture = Fixture(self.root)
        fixture.step_rows[0]["e"] += 1e-6
        fixture.sync()
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void", summary["reason"])
        self.assertFalse(summary["controls"]["ledger_closed"])

    def test_death_and_nan_are_explicit_void(self):
        fixture = Fixture(self.root, death_arm="B3-ko2")
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void", summary["reason"])
        self.assertFalse(summary["controls"]["registered_arms_alive"])
        self.assertTrue(any("B3-ko2/5401/aurd" in item for item in summary["non_finite_metrics"]))
        json.loads((fixture.out / "summary.json").read_text(encoding="utf-8"),
                   parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))

    def test_repeat_mismatch_is_void(self):
        fixture = Fixture(self.root)
        run2_raw = fixture.root / "run2" / "raw.csv"
        data = run2_raw.read_text(encoding="utf-8")
        first_hash = fixture.raw_rows[0]["trajectory_hash"]
        replacement = "0" if first_hash[0] != "0" else "1"
        run2_raw.write_text(data.replace(first_hash, replacement + first_hash[1:], 1), encoding="utf-8")
        record = fixture.manifest["executions"]["run2"]["raw_csv"]
        record.update(file_record(run2_raw, "run2/raw.csv", len(fixture.raw_rows)))
        fixture.manifest["repeat"]["byte_identical"] = False
        fixture.manifest_path.write_text(json.dumps(fixture.manifest, indent=2) + "\n", encoding="utf-8")
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void", summary["reason"])
        self.assertFalse(summary["controls"]["repeat_byte_identical"])

    def test_other_driver_failure_is_void(self):
        fixture = Fixture(self.root)
        fixture.manifest["driver_rc"] = 2
        fixture.manifest["run2_driver_rc"] = 2
        fixture.manifest_path.write_text(json.dumps(fixture.manifest, indent=2) + "\n", encoding="utf-8")
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void")
        self.assertFalse(summary["controls"]["driver_exit_codes_valid"])

    def test_sensitivity_exit_3(self):
        fixture = Fixture(self.root)
        fixture.make_sensitive()
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "insensitive_by_construction")
        self.assertTrue(summary["controls"]["sensitivity_exit_3"])

    def test_sensitivity_still_requires_valid_provenance(self):
        fixture = Fixture(self.root)
        fixture.make_sensitive()
        fixture.manifest["driver"]["source_sha256"] = None
        fixture.manifest_path.write_text(json.dumps(fixture.manifest, indent=2) + "\n", encoding="utf-8")
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void")
        self.assertFalse(summary["controls"]["artifact_hashes_valid"])

    def test_mixed_exit_3_is_not_insensitive(self):
        fixture = Fixture(self.root)
        fixture.make_sensitive()
        fixture.manifest["run2_driver_rc"] = 0
        fixture.manifest["executions"]["run2"]["returncode"] = 0
        fixture.manifest_path.write_text(json.dumps(fixture.manifest, indent=2) + "\n", encoding="utf-8")
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void")
        self.assertFalse(summary["controls"]["driver_exit_codes_valid"])

    def test_raw_bit_hashes_are_recomputed(self):
        fixture = Fixture(self.root)
        for row in fixture.raw_rows:
            if row["arm"] in {"A-control", "B1-sham"}:
                row["trajectory_hash"] = "0" * 16
        fixture.sync()
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void")
        self.assertFalse(summary["controls"]["state_trajectory_hashes_exact"])

    def test_draft_task_payload_cannot_be_submitted(self):
        document = {
            "draft_only": True,
            "payload": {"schema": "task/v1", "id": analyzer.TASK_ID, "version": 3,
                        "task_version_sha256": "a" * 64, "base_commit": "b" * 40},
        }
        with self.assertRaises(ValueError):
            submit.unwrap_task_payload(document)

    def test_leased_runner_enforces_spec_seed_grid_and_short_zero_base(self):
        task = {
            "schema": "task/v1", "id": analyzer.TASK_ID, "version": 3,
            "task_version_sha256": "a" * 64, "base_commit": "f" * 40,
            "spec": {"seeds": [5401], "parameters": {
                "seeds": 1, "seed_base": 5401,
                "schedule_fingerprint": analyzer.SCHEDULE_FINGERPRINT,
            }},
        }
        self.assertEqual(leased_runner.task_identity(task)["task_version"], 3)
        wrong_grid = json.loads(json.dumps(task))
        wrong_grid["spec"]["seeds"] = [5402]
        with self.assertRaisesRegex(ValueError, "spec.seeds"):
            leased_runner.task_identity(wrong_grid)
        short_zero = dict(task, base_commit="0000000")
        with self.assertRaisesRegex(ValueError, "base_commit placeholder"):
            leased_runner.task_identity(short_zero)

    @unittest.skipUnless(os.name != "nt" and shutil.which("bash"), "requires POSIX bash")
    def test_runner_rejects_draft_before_creating_output(self):
        draft = self.root / "draft.json"
        draft.write_text(json.dumps({
            "draft_only": True,
            "payload": {"schema": "task/v1", "id": analyzer.TASK_ID, "version": 3,
                        "task_version_sha256": "a" * 64, "base_commit": "b" * 40},
        }), encoding="utf-8")
        out = self.root / "out"
        result = subprocess.run(
            ["bash", str(PIPELINE / "b_run.sh"), sys.executable, str(out), str(draft)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("draft task payload", result.stderr)
        self.assertFalse(out.exists(), "rejected draft must not create run artifacts")

    @unittest.skipUnless(os.name != "nt" and shutil.which("bash"), "requires POSIX bash")
    def test_runner_rejects_seed_override_before_creating_output(self):
        task = self.root / "task.json"
        task.write_text(json.dumps({
            "schema": "task/v1", "id": analyzer.TASK_ID, "version": 3,
            "task_version_sha256": "a" * 64, "base_commit": "f" * 40,
            "spec": {"seeds": [5401], "parameters": {
                "seeds": 1, "seed_base": 5401,
                "schedule_fingerprint": analyzer.SCHEDULE_FINGERPRINT,
            }},
        }), encoding="utf-8")
        out = self.root / "out"
        environment = dict(os.environ, B_UNIT_SEEDS="2")
        result = subprocess.run(
            ["bash", str(PIPELINE / "b_run.sh"), sys.executable, str(out), str(task)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30,
            env=environment)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly 1", result.stderr)
        self.assertFalse(out.exists())

    def test_placeholder_identity_is_void(self):
        fixture = Fixture(self.root)
        fixture.manifest["task_version_sha256"] = "0" * 64
        fixture.manifest["environment"]["task_version_sha256"] = "0" * 64
        fixture.manifest_path.write_text(json.dumps(fixture.manifest, indent=2) + "\n", encoding="utf-8")
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void")
        self.assertFalse(summary["controls"]["task_manifest_valid"])

    def test_live_raw_cannot_hide_dead_final_step(self):
        fixture = Fixture(self.root)
        fixture.step_rows[-1]["alive"] = 0
        fixture.step_rows[-1]["death_cause"] = "energy"
        fixture.sync()
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void")
        self.assertFalse(summary["controls"]["death_censoring_explicit"])
        self.assertFalse(summary["controls"]["registered_arms_alive"])

    def test_seed_grid_mismatch_is_void(self):
        fixture = Fixture(self.root)
        fixture.manifest["seeds"] = 2
        fixture.manifest["environment"]["seeds"] = 2
        fixture.manifest_path.write_text(json.dumps(fixture.manifest, indent=2) + "\n", encoding="utf-8")
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void")
        self.assertFalse(summary["controls"]["task_manifest_valid"])

    def test_plan_hash_pins_every_staged_artifact(self):
        task = {"write_scope": [f"results/experiments/{analyzer.TASK_ID}/**", analyzer.FINDING_PATH]}
        for relative, _media in make_plan.ARTIFACTS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"fixture:{relative}\n".encode("utf-8"))
        entries, by_staged = make_plan.build_artifact_entries(self.root, task)
        self.assertEqual(len(entries), len(make_plan.ARTIFACTS))
        for entry in entries:
            data = (self.root / entry["staged_path"]).read_bytes()
            self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(entry["bytes"], len(data))
            self.assertTrue(submit.path_in_write_scope(entry["path"], task["write_scope"]))
        self.assertEqual(by_staged[f"FINDING-{analyzer.TASK_ID}.md"]["path"], analyzer.FINDING_PATH)
        plan = {"artifacts": entries}
        validated, _pending, _staged = submit.validate_planned_artifacts(plan, self.root, task)
        self.assertEqual(len(validated), len(entries))
        entries[0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "planned artifact hash mismatch"):
            submit.validate_planned_artifacts(plan, self.root, task)

    def test_plan_rejects_paths_outside_write_scope(self):
        task = {"write_scope": []}
        for relative, _media in make_plan.ARTIFACTS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture\n")
        with self.assertRaisesRegex(ValueError, "outside task.write_scope"):
            make_plan.build_artifact_entries(self.root, task)

    def test_staged_evidence_rejects_summary_and_manifest_tampering(self):
        task = {
            "schema": "task/v1", "id": analyzer.TASK_ID, "version": 3,
            "task_version_sha256": "a" * 64, "base_commit": "f" * 40,
            "write_scope": [
                f"results/experiments/{analyzer.TASK_ID}/**", analyzer.FINDING_PATH],
            "spec": {"seeds": [5401], "parameters": {
                "seeds": 1, "seed_base": 5401,
                "schedule_fingerprint": analyzer.SCHEDULE_FINGERPRINT,
            }},
        }
        task_path = self.root / "supplied-task.json"
        task_path.write_text(json.dumps(task) + "\n", encoding="utf-8")
        environment = {
            "task_id": analyzer.TASK_ID, "task_version": 3,
            "task_version_sha256": "a" * 64, "base_commit": "f" * 40,
            "seeds": 1, "seed_base": 5401,
        }
        toolchain = {"rust": "fixture", "python": "fixture"}
        summary = {
            "task_id": analyzer.TASK_ID, "task_version": 3,
            "task_version_sha256": "a" * 64, "base_commit": "f" * 40,
            "seeds": 1, "seed_base": 5401, "scientific_outcome": "passed",
            "raw_sha256": "1" * 64, "steps_sha256": "2" * 64,
        }
        manifest = {
            "seeds": 1, "seed_base": 5401,
            "driver": {"source_sha256": "3" * 64},
            "raw_csv": {}, "steps_csv": {}, "executions": {
                "run1": {"raw_csv": {}, "steps_csv": {}},
                "run2": {"raw_csv": {}, "steps_csv": {}},
            },
        }
        for relative, _media in make_plan.ARTIFACTS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture\n")
        (self.root / "task.json").write_bytes(task_path.read_bytes())
        (self.root / "run/environment.json").write_text(json.dumps(environment), encoding="utf-8")
        (self.root / "run/toolchain.json").write_text(json.dumps(toolchain), encoding="utf-8")
        (self.root / "run/analysis/summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (self.root / "run/raw-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.root / f"FINDING-{analyzer.TASK_ID}.md").write_text(
            f"{analyzer.TASK_ID}\n`passed`\n## Воспроизведение\n", encoding="utf-8")
        plan = {"environment": environment, "toolchain": toolchain}
        entries, by_staged = make_plan.build_artifact_entries(self.root, task)
        plan["artifacts"] = entries
        _validated, _pending, pinned = submit.validate_planned_artifacts(
            plan, self.root, task)
        for relative, field in (("run/raw.csv", "raw_sha256"),
                                ("run/steps.csv", "steps_sha256")):
            record = manifest["raw_csv" if field == "raw_sha256" else "steps_csv"]
            record.update(sha256=pinned[relative]["sha256"], bytes=pinned[relative]["bytes"])
            for run in ("run1", "run2"):
                run_relative = f"run/{run}/{relative.rsplit('/', 1)[1]}"
                record = manifest["executions"][run][relative.rsplit('/', 1)[1].replace(".csv", "_csv")]
                record.update(sha256=pinned[run_relative]["sha256"], bytes=pinned[run_relative]["bytes"])
        manifest["driver"]["source_sha256"] = pinned["driver.rs"]["sha256"]
        environment["driver_source_sha256"] = pinned["driver.rs"]["sha256"]
        (self.root / "run/environment.json").write_text(json.dumps(environment), encoding="utf-8")
        (self.root / "run/raw-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        summary["raw_sha256"] = pinned["run/raw.csv"]["sha256"]
        summary["steps_sha256"] = pinned["run/steps.csv"]["sha256"]
        (self.root / "run/analysis/summary.json").write_text(json.dumps(summary), encoding="utf-8")
        entries, by_staged = make_plan.build_artifact_entries(self.root, task)
        plan["artifacts"] = entries
        _validated, _pending, pinned = submit.validate_planned_artifacts(plan, self.root, task)
        _task, identity = submit.unwrap_task_payload(task)
        submit.validate_staged_evidence(
            self.root, pinned, task_path, identity, plan, summary, manifest)

        changed_summary = dict(summary, raw_sha256="0" * 64)
        staged_summary = self.root / "run/analysis/summary.json"
        staged_summary.write_text(json.dumps(changed_summary), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "summary/staged raw_sha256 mismatch"):
            submit.validate_staged_evidence(
                self.root, pinned, task_path, identity, plan, changed_summary, manifest)

        staged_summary.write_text(json.dumps(changed_summary), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "summary.json differs"):
            submit.validate_staged_evidence(
                self.root, pinned, task_path, identity, plan, summary, manifest)
        staged_summary.write_text(json.dumps(summary), encoding="utf-8")

        staged_manifest = self.root / "run/raw-manifest.json"
        staged_manifest.write_text(json.dumps(dict(manifest, seeds=2)), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "raw-manifest.json differs"):
            submit.validate_staged_evidence(
                self.root, pinned, task_path, identity, plan, summary, manifest)

    def test_passed_summary_requires_exact_registered_controls(self):
        fixture = Fixture(self.root)
        summary = fixture.analyze()
        del summary["controls"]["death_censoring_explicit"]
        summary["all_controls_valid"] = all(summary["controls"].values())
        with self.assertRaisesRegex(ValueError, "exact registered control set"):
            submit.validate_outcome(summary, fixture.manifest)

    def test_invalid_base_commit_is_void(self):
        fixture = Fixture(self.root)
        fixture.manifest["base_commit"] = "fixture-base"
        fixture.manifest["environment"]["base_commit"] = "fixture-base"
        fixture.manifest_path.write_text(json.dumps(fixture.manifest, indent=2) + "\n", encoding="utf-8")
        summary = fixture.analyze()
        self.assertEqual(summary["scientific_outcome"], "void")
        self.assertFalse(summary["controls"]["task_manifest_valid"])


if __name__ == "__main__":
    unittest.main()
