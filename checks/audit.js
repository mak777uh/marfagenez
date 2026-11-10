function gauss() {
  let u = 0, v = 0;
  while (!u) u = Math.random();
  while (!v) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(6.283185307 * v);
}

// SYSTEMATIC AUDIT of the numerical claims behind the theorems.
// For each claim, test it directly against simulation.

const results = [];
function check(name, ok, detail) {
  results.push({ name, ok, detail });
}

// ---- Claim 1: uniform spread = B/sqrt(3) ----
{
  const B = 3, N = 20000;
  let pop = Array.from({ length: N }, () => gauss() * 0.5);
  for (let s = 0; s < 6000; s++)
    for (let i = 0; i < N; i++) {
      const v = pop[i] + 0.3 * gauss();
      const Q = 4 * B;
      pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
    }
  const m = pop.reduce((a, b) => a + b, 0) / N;
  const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / N);
  const th = B / Math.sqrt(3);
  check('uniform spread = B/sqrt3', Math.abs(sd - th) / th < 0.03,
    `measured ${sd.toFixed(3)} vs theory ${th.toFixed(3)}`);
}

// ---- Claim 2: Var(X+c) = Var(X) ----
{
  const N = 50000;
  const base = Array.from({ length: N }, gauss);
  const shifted = base.map(x => x + 2.5);
  const v1 = (() => { const m = base.reduce((a, b) => a + b, 0) / N; return base.reduce((a, b) => a + (b - m) ** 2, 0) / N; })();
  const v2 = (() => { const m = shifted.reduce((a, b) => a + b, 0) / N; return shifted.reduce((a, b) => a + (b - m) ** 2, 0) / N; })();
  check('Var(X+c)=Var(X)', Math.abs(v1 - v2) / v1 < 0.01, `${v1.toFixed(4)} vs ${v2.toFixed(4)}`);
}

// ---- Claim 3: exponential tilt keeps variance 1 for N(0,1) ----
{
  const N = 200000;
  const base = Array.from({ length: N }, gauss);
  let ok = true, details = [];
  for (const k of [0.5, 1.0, 2.0]) {
    const w = base.map(x => Math.exp(k * x));
    const S = w.reduce((a, b) => a + b, 0);
    const m = base.reduce((a, x, i) => a + x * w[i], 0) / S;
    const m2 = base.reduce((a, x, i) => a + x * x * w[i], 0) / S;
    const v = m2 - m * m;
    details.push(`k=${k}: var=${v.toFixed(3)}`);
    if (Math.abs(v - 1) > 0.05) ok = false;
  }
  check('exp tilt Var=1', ok, details.join(', '));
}

// ---- Claim 4: growth density is exp(alpha x) ----
{
  const B = 3, SIG = 0.3, N = 40000;
  let ok = true, details = [];
  for (const mu of [0.03, 0.1]) {
    let pop = Array.from({ length: N }, () => gauss() * 0.5);
    for (let s = 0; s < 15000; s++)
      for (let i = 0; i < N; i++) {
        const v = pop[i] + mu + SIG * gauss();
        const Q = 4 * B;
        pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
      }
    const m = pop.reduce((a, b) => a + b, 0) / N;
    // theory mean for exp(alpha x)
    const alpha = 2 * mu / (SIG * SIG);
    const eB = Math.exp(alpha * B), emB = Math.exp(-alpha * B);
    const Z = (eB - emB) / alpha;
    const i1 = (eB * (B - 1 / alpha) - emB * (-B - 1 / alpha)) / alpha;
    const thMean = i1 / Z;
    details.push(`mu=${mu}: mean ${m.toFixed(3)} vs ${thMean.toFixed(3)}`);
    if (Math.abs(m - thMean) / Math.abs(thMean) > 0.06) ok = false;
  }
  check('growth density exp(alpha x)', ok, details.join(', '));
}

// ---- Claim 5: reflection is measure-preserving (1-Lipschitz) ----
{
  const B = 3;
  let worst = 0;
  for (let i = 0; i < 100000; i++) {
    const x = Math.random() * 40 - 20;
    const y = x + (Math.random() - 0.5) * 0.01;
    const d0 = Math.abs(x - y);
    const f = v => { const Q = 4 * B; return B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B); };
    if (d0 > 1e-12) worst = Math.max(worst, Math.abs(f(x) - f(y)) / d0);
  }
  check('reflection 1-Lipschitz', worst <= 1.001, `max ratio ${worst.toFixed(4)}`);
}

// ---- Claim 6: box keeps per-trait spread independent of d ----
{
  const B = 3, N = 8000;
  let ok = true, details = [];
  let first = null;
  for (const d of [1, 4, 8]) {
    let pop = Array.from({ length: N }, () => Array.from({ length: d }, () => gauss() * 0.5));
    for (let s = 0; s < 5000; s++)
      for (let i = 0; i < N; i++)
        for (let k = 0; k < d; k++) {
          const v = pop[i][k] + 0.3 * gauss();
          const Q = 4 * B;
          pop[i][k] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
        }
    let tot = 0;
    for (let k = 0; k < d; k++) {
      const m = pop.reduce((a, p) => a + p[k], 0) / N;
      tot += pop.reduce((a, p) => a + (p[k] - m) ** 2, 0) / N;
    }
    const sd = Math.sqrt(tot / d);
    if (first === null) first = sd;
    details.push(`d=${d}: ${sd.toFixed(3)}`);
    if (Math.abs(sd - first) / first > 0.05) ok = false;
  }
  check('box keeps spread for all d', ok, details.join(', '));
}

// ---- Claim 7: ball squeezes as d grows ----
{
  const B = 3, N = 8000;
  const vals = [];
  for (const d of [1, 4, 8]) {
    let pop = Array.from({ length: N }, () => Array.from({ length: d }, () => gauss() * 0.5));
    for (let s = 0; s < 5000; s++)
      for (let i = 0; i < N; i++) {
        for (let k = 0; k < d; k++) pop[i][k] += 0.3 * gauss();
        let r = 0;
        for (let k = 0; k < d; k++) r += pop[i][k] ** 2;
        r = Math.sqrt(r);
        if (r > B) { const sc = (2 * B - r) / r; for (let k = 0; k < d; k++) pop[i][k] *= sc; }
      }
    let tot = 0;
    for (let k = 0; k < d; k++) {
      const m = pop.reduce((a, p) => a + p[k], 0) / N;
      tot += pop.reduce((a, p) => a + (p[k] - m) ** 2, 0) / N;
    }
    vals.push(Math.sqrt(tot / d));
  }
  const ok = vals[0] > vals[1] && vals[1] > vals[2];
  check('ball squeezes as d grows', ok, vals.map((v, i) => `d=${[1,4,8][i]}: ${v.toFixed(3)}`).join(', '));
}

console.log('=== AUDIT OF NUMERICAL CLAIMS ===');
console.log();
let pass = 0;
for (const r of results) {
  console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}`);
  console.log(`      ${r.detail}`);
  if (r.ok) pass++;
}
console.log();
console.log(`${pass}/${results.length} claims verified`);
