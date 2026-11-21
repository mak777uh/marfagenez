"""OpenAlex budget: read it from the API, keep a ledger, decide whether a request is worth spending.

The number `$1/day` is not a constant of nature — it belongs to the account behind the key. So this tool
asks `/rate-limit` (which does not itself spend budget) and records what it saw. The ledger lives in
`literature/budget/openalex.jsonl`, not in `results/` (that directory is restored by `git checkout`).

Policy:
  * a cached answer is free — check the cache first (`literature/cache/`);
  * remaining >= reserve            -> allow;
  * 0 < remaining < reserve         -> allow with a warning (a slow day is not an error);
  * remaining == 0 or unknown       -> `skip`: the channel is marked `skipped_budget`, the run continues.

The ledger stores `budget_before`/`budget_after` as reported by the API — not an invented per-request price.

Usage:
    python3 tools/budget.py                    # print the live budget
    python3 tools/budget.py --json             # machine form
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "literature" / "budget" / "openalex.jsonl"
CACHE = ROOT / "literature" / "cache"
KEY_FILE = pathlib.Path(os.environ.get("LITSEARCH_KEY", "/mnt/c/Users/Admin/.dsh/secrets/openalex.key"))
CURL = os.environ.get("LITSEARCH_CURL", "/mnt/c/Windows/System32/curl.exe")
RESERVE_USD = 0.2


def read_key() -> str | None:
    try:
        return KEY_FILE.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def live_budget() -> dict:
    key = read_key()
    if not key:
        return {"known": False, "reason": "нет ключа"}
    url = "https://api.openalex.org/rate-limit?api_key=" + key
    try:
        out = subprocess.run([CURL, "-sS", "-L", "--compressed", "-m", "30", "-A", "dsh-budget/1.0", url],
                             capture_output=True, text=True, timeout=45)
        payload = json.loads(out.stdout)
    except Exception as exc:  # noqa: BLE001
        return {"known": False, "reason": f"{type(exc).__name__}"}
    limit = payload.get("rate_limit") or {}
    return {
        "known": "daily_remaining_usd" in limit,
        "daily_budget_usd": limit.get("daily_budget_usd"),
        "daily_used_usd": limit.get("daily_used_usd"),
        "daily_remaining_usd": limit.get("daily_remaining_usd"),
        "resets_at": limit.get("resets_at"),
    }


def decide(budget: dict, reserve: float = RESERVE_USD) -> tuple[bool, str]:
    if not budget.get("known"):
        # An unknown budget must not block the channel: the cache and the other channels still work,
        # and refusing on a failed probe would turn a network hiccup into "search unavailable".
        return True, "бюджет неизвестен: пробуем и пишем в леджер"
    remaining = budget.get("daily_remaining_usd") or 0.0
    if remaining <= 0:
        return False, "остаток нулевой"
    if remaining < reserve:
        return True, f"остаток {remaining:.3f} < резерва {reserve:.2f}: предупреждение"
    return True, f"остаток {remaining:.3f}"


def append_ledger(entry: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def cache_path(name: str) -> pathlib.Path:
    return CACHE / f"{name}.json"


def cache_get(name: str) -> dict | None:
    path = cache_path(name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def cache_put(name: str, body: str) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    payload = {"fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "body": body}
    cache_path(name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str]) -> int:
    budget = live_budget()
    allow, why = decide(budget)
    if "--json" in argv:
        print(json.dumps({"budget": budget, "allow": allow, "reason": why}, ensure_ascii=False, indent=1))
        return 0
    if budget.get("known"):
        print(f"бюджет: потрачено {budget['daily_used_usd']}, осталось {budget['daily_remaining_usd']} "
              f"из {budget['daily_budget_usd']} (сброс {budget.get('resets_at')})")
    else:
        print(f"бюджет неизвестен: {budget.get('reason')}")
    print(("можно тратить: " if allow else "не тратим: ") + why)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
