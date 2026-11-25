"""`F-023`: двойственная задача и смысл цены — что именно сохраняется.

Узел утверждает:
    прямая:   max cᵀv   при  S·v = 0,  l ≤ v ≤ u
    двойственная:  min uᵀy⁺ + lᵀy⁻   при  Sᵀ·y ≥ c
    инварианты: левое ядро S: {w : wᵀS = 0} → wᵀv постоянно        (L-064)

Проверяем ТРИ разные вещи, потому что «постоянно» можно понять трояко:
1. `wᵀv` на допустимых потоках (`Sv = 0`, но потоки разные) — так записано в узле;
2. `wᵀx` вдоль траектории `ẋ = S·v` — теорема о сохранении фрагментов (moiety conservation);
3. `Sᵀ(y + α·w) = Sᵀy` — сдвиг теневых цен вдоль `w` не меняет двойственную допустимость
   (и потому «химические потенциалы» определены с точностью до такого сдвига).

Опровергающее условие: если `wᵀv` окажется постоянным на разных допустимых потоках, запись узла верна
в буквальном смысле; если нет — запись говорит не о том векторе.

Запуск: python3 tools/duality_invariants.py
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import linprog

# Цикл A → B → C → A: три вещества, три реакции. Левое ядро S одномерно: w ∝ (1,1,1).
S = np.array([
    [-1.0, 1.0, 0.0],
    [0.0, -1.0, 1.0],
    [1.0, 0.0, -1.0],
])
c = np.array([3.0, 0.1, 0.1])
l = np.array([0.0, 0.0, 0.0])
u = np.array([5.0, 5.0, 5.0])


def main() -> int:
    rank = int(np.linalg.matrix_rank(S.T))
    _, _, vt = np.linalg.svd(S.T)
    null_basis = vt[rank:]
    w = null_basis[0]
    print(f"левое ядро S: размер {null_basis.shape[0]}; w = {np.round(w, 4)}; wᵀS ≈ 0: "
          f"{np.allclose(w @ S, 0, atol=1e-12)}")

    # 1) так, как записано в узле: wᵀv на разных допустимых потоках
    flows = [np.array([t, t, t]) for t in (0.5, 1.7, 4.2)]
    vals = [float(w @ v) for v in flows]
    print()
    print("1) wᵀv на допустимых потоках (Sv = 0):")
    for v, val in zip(flows, vals):
        print(f"   v = {np.round(v, 3)}  →  wᵀv = {val:.6f}")
    v_constant = np.allclose(vals, vals[0], atol=1e-10)
    print(f"   wᵀv постоянно: {v_constant}")
    if not v_constant:
        print(f"   разброс: от {min(vals):.3f} до {max(vals):.3f} — в {max(vals) / min(vals):.1f} раза")

    # 2) сохранение wᵀx на траектории ẋ = S·v, v = (1,1,1)
    v = np.array([1.0, 1.0, 1.0])
    x = np.array([2.0, 0.0, 0.0])
    dt = 0.001
    print()
    print("2) wᵀx вдоль траектории ẋ = S·v, v = (1,1,1):")
    marks = []
    for step in range(5001):
        if step % 1000 == 0:
            marks.append((step * dt, float(w @ x)))
        x = x + dt * (S @ v)
    for t, val in marks:
        print(f"   t = {t:5.1f}:  wᵀx = {val:.9f}   x = {np.round(x, 3) if t == 0 else ''}")
    x_constant = np.allclose([m[1] for m in marks], marks[0][1], atol=1e-9)
    print(f"   wᵀx постоянно: {x_constant}")

    # 3) сильная двойственность
    res = linprog(-c, A_eq=S, b_eq=np.zeros(S.shape[0]), bounds=list(zip(l, u)), method="highs")
    primal = -res.fun
    n, m = S.shape[1], S.shape[0]
    A_eq = np.hstack([S.T, np.eye(n), -np.eye(n)])
    cost = np.concatenate([np.zeros(m), u, -l])
    bounds = [(None, None)] * m + [(0, None)] * (2 * n)
    res_d = linprog(cost, A_eq=A_eq, b_eq=c, bounds=bounds, method="highs")
    dual = float(res_d.fun)
    y = res_d.x[:m]
    print()
    print(f"3) оптимум прямой {primal:.9f}; двойственной {dual:.9f}; "
          f"совпадение: {abs(primal - dual) < 1e-9}")
    print(f"   y = {np.round(y, 4)};  Sᵀy ≤ c: {np.all(S.T @ y <= c + 1e-9)}")

    # 4) сдвиг теневых цен вдоль w
    alpha = 2.5
    y2 = y + alpha * w
    print()
    print(f"4) сдвиг y на {alpha}·w: Sᵀy изменилось: {not np.allclose(S.T @ y2, S.T @ y, atol=1e-12)}")
    print("   → теневые цены определены с точностью до сдвига вдоль w (это и есть неоднозначность,")
    print("     которая в узле названа «химическими потенциалами»).")

    ok = (not v_constant) and x_constant and abs(primal - dual) < 1e-9
    print()
    if ok:
        print("ВЫВОД: постоянна величина wᵀx (состояние), а НЕ wᵀv (потоки).")
        print("        Запись узла «wᵀv постоянно» неверна в буквальном смысле: на разных допустимых")
        print("        потоках wᵀv меняется. Сильная двойственность подтверждена.")
        return 0
    print("ВЫВОД: проверка не подтвердила ожидаемое — см. строки выше.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
