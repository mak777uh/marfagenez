"""`F-025`: ITI — разложение временной информации. Аддитивность не выполняется сама собой.

Узел:
    временная целостность:   I(X_t ; X_{t+1})
    разложение (схема):      I(X_t ; X_{t+1}) = I_env + I_ind + I_col
      I_env — вклад среды (детерминизм извне),
      I_ind — «индивидуальная» память/инерция (система предсказывает себя),
      I_col — коллективная компонента (части предсказывают целое)

Проверяем на числах, определена ли такая сумма. Берём систему X_{t+1} = f(X_t, E) с известным механизмом
и считаем три кандидата:
    I(X_t ; X_{t+1})            — полная временная информация,
    I(E ; X_{t+1})              — «вклад среды»,
    I(X_t ; X_{t+1} | E)        — «вклад самой системы при фиксированной среде».
Если сумма двух последних НЕ равна полной, значит аддитивное разложение требует отдельного определения,
а не следует из определений условной/взаимной информации.

Опровергающее условие: если сумма всегда равна полной на всех проверенных системах, схема безопасна
как арифметика. Если есть система, где не равна, — «I_env + I_ind + I_col» есть ОПРЕДЕЛЕНИЕ, и его надо
задавать явно (и оно не обязано быть неотрицательным).

Запуск: python3 tools/iti_decomposition.py
"""

from __future__ import annotations

import numpy as np


def entropy(p: np.ndarray) -> float:
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def mutual(joint: np.ndarray) -> float:
    """I(A;B) по совместному распределению (матрица)."""
    pa = joint.sum(axis=1)
    pb = joint.sum(axis=0)
    outer = np.outer(pa, pb)
    mask = joint > 0
    return float((joint[mask] * np.log2(joint[mask] / outer[mask])).sum())


def system(p_flip_env: float) -> dict:
    """X_t ∈ {0,1}, E ∈ {0,1}, X_{t+1} = X_t, если E = 0; X_{t+1} = 1 − X_t, если E = 1 (с шумом)."""
    p_x = np.array([0.5, 0.5])
    p_e = np.array([0.5, 0.5])
    # p(x_next | x, e)
    p_next = np.zeros((2, 2, 2))  # [x_next][x][e]
    for x in (0, 1):
        for e in (0, 1):
            flip = p_flip_env if e == 1 else 0.0
            p_next[x, x, e] = 1.0 - flip
            p_next[1 - x, x, e] = flip
    # совместное (x, x_next)
    j_xx = np.zeros((2, 2))
    for x in (0, 1):
        for e in (0, 1):
            for xn in (0, 1):
                j_xx[x, xn] += p_x[x] * p_e[e] * p_next[xn, x, e]
    # совместное (x, x_next, e) сворачиваем до (x, x_next) уже сделано; для условной энтропии нужен (x,xn,e)
    j3 = np.zeros((2, 2, 2))
    for x in (0, 1):
        for xn in (0, 1):
            for e in (0, 1):
                j3[x, xn, e] = p_x[x] * p_e[e] * p_next[xn, x, e]
    # I(X_t; X_{t+1})
    full = mutual(j_xx)
    # H(X_{t+1} | E)
    p_xn_e = j3.sum(axis=0)  # [xn][e]
    h_xn_given_e = sum(entropy(p_xn_e[:, e] / p_xn_e[:, e].sum()) * p_xn_e[:, e].sum() for e in (0, 1))
    h_xn = entropy(j_xx.sum(axis=0))
    i_env = h_xn - h_xn_given_e           # I(E; X_{t+1})
    # H(X_{t+1} | X_t, E)
    p_x_e = j3.sum(axis=1)                # [x][e]
    h_cond = 0.0
    for x in (0, 1):
        for e in (0, 1):
            w = p_x_e[x, e]
            if w > 0:
                cond = j3[x, :, e] / w
                h_cond += w * entropy(cond)
    i_ind = h_xn - h_cond                 # I(X_t; X_{t+1} | E)
    return {"full": full, "i_env": i_env, "i_ind": i_ind, "sum": i_env + i_ind,
            "h_xn": h_xn, "h_cond": h_cond}


def main() -> int:
    print(f"{'система':38} {'I(Xt;Xt+1)':>11} {'I_env':>8} {'I_ind':>8} {'сумма':>8} {'разница':>9}")
    worst = 0.0
    rows = []
    for name, flip in (("среда выключает память (flip=1)", 1.0),
                       ("среда иногда переворачивает (0,5)", 0.5),
                       ("среда переворачивает редко (0,1)", 0.1),
                       ("среда не влияет (0,0)", 0.0)):
        r = system(flip)
        diff = r["sum"] - r["full"]
        worst = max(worst, abs(diff))
        rows.append((name, r, diff))
        print(f"{name:38} {r['full']:11.6f} {r['i_env']:8.6f} {r['i_ind']:8.6f} "
              f"{r['sum']:8.6f} {diff:9.6f}")

    print()
    print("ЧТО ЭТО ЗНАЧИТ:")
    print("  1. I_env = 0 во всех системах, хотя X_{t+1} ЗАВИСИТ от E: среда не несёт отдельной информации")
    print("     о следующем состоянии (X_{t+1} маргинально не зависит от E при равномерных X и E).")
    print("  2. I_env + I_ind БОЛЬШЕ полной информации: компоненты перекрываются, а не дополняют друг друга.")
    print("  3. Крайний случай: при flip=1 полная информация 0, а «индивидуальная» 1 — то есть часть")
    print("     больше целого. Неотрицательное разбиение с такими частями невозможно.")
    print(f"  максимальное расхождение суммы и полной: {max(r['sum'] - r['full'] for _, r, _ in rows):.6f} бит")
    print()
    print("  Значит запись «I = I_env + I_ind + I_col» — это ОПРЕДЕЛЕНИЕ разбиения, а не следствие")
    print("  теории информации. Чтобы им пользоваться, нужно задать правило разбиения (как в PID:")
    print("  уникальность / избыточность / синергия) и проверить неотрицательность частей.")
    print("  Для третьей компоненты I_col нужен ещё и способ делить систему на части — в узле он не задан.")

    ok = worst > 1e-6
    print()
    if ok:
        print("ВЫВОД: аддитивность нарушается на проверенных системах — схема требует явного определения.")
        return 0
    print("ВЫВОД: аддитивность выполнилась на всех системах — схема безопасна как арифметика (проверить шире).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
