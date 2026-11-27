### Цикл 1 — 2026-11-28 — gate correctness / preflight / pinned DAG

**Задача.** Устранить ложный зелёный статус KG, отсеивать дешёвые детерминированные красные до тяжёлого прогона и сократить время ожидания за счёт точного тайминга и DAG.

**Изменения.**
- `run.sh`: fail-closed агрегация четырёх KG проверок; ранний preflight; build bins/examples в pin; полный pinned worktree; DAG `reach <- lean`, `exp <- build`; собственные rc/duration markers секций; per-check exp timing; параллельный default Rust test suite.
- Добавлен `checks/gate_kg_fail_closed.py` с контролируемыми негативными сценариями; обновлены dispatcher/runtime regressions.
- CI очищен от повторных default Rust / Lean build / examples шагов, добавлены Rust/Lean caches и ShellCheck; обновлены README/AGENTS и состояние агента.
- Исправление `kg/kg.py` не делалось: проверка показала, что `kg/regress.py` уже возвращает ненулевой rc; ошибка была в потере rc в shell-обёртке.

**Коммиты, покрытые этой записью.**
- `111218b` основной патч run.sh: KG, preflight, pin, DAG, timings.
- `57d8bb3` dispatcher test fixtures для build/pin/preflight.
- `9bc4ab6` обновление runtime section-count regression.
- `b5162d8` KG fail-closed regression harness.
- `56e61be` CI caches и устранение дублирующих этапов.
- `4f7e09b` контракт проверки CI.
- `507a2bc` ShellCheck в dispatcher.
- `810cf29` README: команды preflight и default test threads.
- `30c4077` AGENTS: команды preflight и pinned DAG.
- `c6f60ac` получение Lean prebuilt cache внутри pinned build.
- `096ac8d` синхронизация AGENT_STATE.md с реализацией.

**Валидация.** Проведена статическая сверка remote-файлов и структуры изменений. В этой среде не запускались `bash -n`, ShellCheck, Python selftests, `run.sh preflight` и полный WSL gate. Нужна независимая валидация основным агентом на точном HEAD PR; до неё не мержить и не пушить master.

**Отложено.** P5 section cache; P6 parallel claims/audit и бит-в-бит RNG equivalence; P7 background gate service/coalescing; P9 sparse pin, scratch cleanup и counter generator; решение по LTO только после отдельного benchmark.
