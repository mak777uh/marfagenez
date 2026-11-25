"""Числовая проверка единиц и границ режимов для F-001, F-003, F-029."""
import math

print("== F-003: граница режимов h* = 1 - lambda*delta/(2*mu0^2)")
for mu0, lam, delta in ((1.0, 1.0, 1.0), (0.5, 1.0, 1.0), (1.0, 2.0, 1.0)):
    h_star = 1 - lam * delta / (2 * mu0**2)
    D = math.sqrt(delta / (lam * 1e-9)) if h_star < 1 else 0  # заглушка
    print(f"  mu0={mu0} lambda={lam} delta={delta}: h*={h_star:.4f}")
    # в точке h* члены равны: lambda*D^2 = mu0*D
    # из lambda D^2 + mu0 D = delta/(1-h*) при h*: левая часть = 2*mu0*D
    D_eq = mu0 / lam
    lhs = lam * D_eq**2 + mu0 * D_eq
    rhs = delta / (1 - h_star)
    print(f"    D_eq={D_eq:.4f}; lambda D^2+mu0 D={lhs:.6f}; delta/(1-h*)={rhs:.6f}; "
          f"разница={abs(lhs-rhs):.2e}")

print("\n== F-003: где лежат наши точки (h = 0.90/0.95/0.98/0.99) при mu0=lambda=delta=1")
for h in (0.90, 0.95, 0.98, 0.99):
    eta = 1 * 1 / (1**2 * (1 - h))
    regime = "линейный (eta<<1)" if eta < 1 else ("корневой (eta>>1)" if eta > 1 else "граница")
    D = (-1 + math.sqrt(1 + 4 * 1 * 1 / (1 - h))) / (2 * 1)
    D_lin = 1 / (1 * (1 - h))
    print(f"  h={h}: eta={eta:.1f} -> {regime}; D*={D:.4f}; линейная аппроксимация={D_lin:.4f}; "
          f"отношение={D/D_lin:.3f}")

print("\n== F-029: ширина складки по параметру r для ẋ = r·x − x³ + ε")
for eps in (1e-1, 1e-2, 1e-3, 1e-6):
    r_fold = 3 * (eps / 2) ** (2 / 3)
    print(f"  eps={eps:g}: r_fold={r_fold:.6f}; r_fold/eps^(2/3)="
          f"{r_fold / eps**(2/3):.4f}; x в складке=sqrt(r/3)={math.sqrt(r_fold/3):.6f}")
print("  ожидание: r_fold/eps^(2/3) = 3/2^(2/3) =", 3 / 2 ** (2 / 3))

print("\n== F-029: сдвиг по состоянию при статическом несовершенстве r + x^2 + eps = 0")
for eps in (1e-1, 1e-2, 1e-3):
    print(f"  eps={eps:g}: сдвиг x = sqrt(eps) = {math.sqrt(eps):.6f} ~ eps^(1/2), не 2/3")

print("\n== F-001: проверка решения H(T)=1 при mu0=0.01, lambda=delta=0.001")
mu0, lam, delta = 0.01, 0.001, 0.001
a = lam * delta / 2
b = mu0
c = -1
T = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)
print(f"  T={T:.2f} с; H(T)={mu0*T + a*T*T:.6f} (должно 1)")
print(f"  размерности: mu0*T = {mu0}*{T:.1f} -> 1; lambda*delta*T^2 = "
      f"{lam}*{delta}*{T**2:.1f} -> безразмерно")
