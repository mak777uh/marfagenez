// What is actually verified vs what is only stated?
// This checks every numerical claim in the Lean theorems against simulation.
// If a claim fails, it must not be ported to Rust/C.

function gauss() {
  let u = 0, v = 0;
  while (!u) u = Math.random();
  while (!v) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(6.283185307 * v);
}

const results = [];
const check = (name, ok, detail) => results.push({ name, ok, detail });

// 1. uniform spread = B/sqrt(3)
{
  const B = 3, N = 30000;
  let pop = Array.from({ length: N }, () => gauss() * 0.5);
  for (let s = 0; s < 8000; s++)
    for (let i = 0; i < N; i++) {
      const v = pop[i] + 0.3 * gauss();
      const Q = 4 * B;
      pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
    }
  const m = pop.reduce((a, b) => a + b, 0) / N;
  const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / N);
  const th = B / Math.sqrt(3);
  check('spread = B/sqrt3', Math.abs(sd - th) / th < 0.03, `${sd.toFixed(3)} vs ${th.toFixed(3)}`);
}

// 2. Var(X+c) = Var(X)
{
  const N = 100000;
  const a = Array.from({ length: N }, gauss);
  const b = a.map(x => x + 3);
  const va = (() => { const m = a.reduce((s, x) => s + x, 0) / N; return a.reduce((s, x) => s + (x - m) ** 2, 0) / N; })();
  const vb = (() => { const m = b.reduce((s, x) => s + x, 0) / N; return b.reduce((s, x) => s + (x - m) ** 2, 0) / N; })();
  check('Var(X+c)=Var(X)', Math.abs(va - vb) / va < 0.01, `${va.toFixed(5)} vs ${vb.toFixed(5)}`);
}

// 3. exp tilt on N(0,1) keeps Var = 1
{
  const N = 300000;
  const base = Array.from({ length: N }, gauss);
  let worst = 0;
  for (const k of [0.5, 1, 2]) {
    const w = base.map(x => Math.exp(k * x));
    const S = w.reduce((a, b) => a + b, 0);
    const m = base.reduce((a, x, i) => a + x * w[i], 0) / S;
    const m2 = base.reduce((a, x, i) => a + x * x * w[i], 0) / S;
    worst = Math.max(worst, Math.abs(m2 - m * m - 1));
  }
  check('exp tilt Var=1', worst < 0.06, `max deviation ${worst.toFixed(3)}`);
}

// 4. growth density exp(alpha x)
{
  const B = 3, SIG = 0.3, N = 50000;
  let worst = 0;
  for (const mu of [0.03, 0.1]) {
    let pop = Array.from({ length: N }, () => gauss() * 0.5);
    for (let s = 0; s < 20000; s++)
      for (let i = 0; i < N; i++) {
        const v = pop[i] + mu + SIG * gauss();
        const Q = 4 * B;
        pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
      }
    const m = pop.reduce((a, b) => a + b, 0) / N;
    const alpha = 2 * mu / (SIG * SIG);
    const eB = Math.exp(alpha * B), emB = Math.exp(-alpha * B);
    const Z = (eB - emB) / alpha;
    const i1 = (eB * (B - 1 / alpha) - emB * (-B - 1 / alpha)) / alpha;
    const thMean = i1 / Z;
    worst = Math.max(worst, Math.abs(m - thMean) / Math.abs(thMean));
  }
  check('growth density exp(alpha x)', worst < 0.06, `max rel error ${(worst * 100).toFixed(1)}%`);
}

// 5. reflection is 1-Lipschitz
{
  const B = 3;
  let worst = 0;
  const f = v => { const Q = 4 * B; return B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B); };
  for (let i = 0; i < 200000; i++) {
    const x = Math.random() * 40 - 20;
    const y = x + (Math.random() - 0.5) * 0.01;
    const d0 = Math.abs(x - y);
    if (d0 > 1e-12) worst = Math.max(worst, Math.abs(f(x) - f(y)) / d0);
  }
  check('reflection 1-Lipschitz', worst <= 1.001, `max ratio ${worst.toFixed(4)}`);
}

// 6. box keeps spread for all d
{
  const B = 3, N = 10000;
  const vals = [];
  for (const d of [1, 4, 8]) {
    let pop = Array.from({ length: N }, () => Array.from({ length: d }, () => gauss() * 0.5));
    for (let s = 0; s < 6000; s++)
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
    vals.push(Math.sqrt(tot / d));
  }
  const ok = Math.abs(vals[0] - vals[2]) / vals[0] < 0.05;
  check('box keeps spread for all d', ok, vals.map(v => v.toFixed(3)).join(', '));
}

// 7. ball squeezes as d grows
{
  const B = 3, N = 10000;
  const vals = [];
  for (const d of [1, 4, 8]) {
    let pop = Array.from({ length: N }, () => Array.from({ length: d }, () => gauss() * 0.5));
    for (let s = 0; s < 6000; s++)
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
  check('ball squeezes as d grows', vals[0] > vals[1] && vals[1] > vals[2], vals.map(v => v.toFixed(3)).join(' > '));
}

// 8. imitation raises growth, destroys range
{
  const N = 6000, B = 3, MU = 0.05, SIG = 0.4;
  const base = B / Math.sqrt(3);
  const run = (kappa) => {
    let pop = Array.from({ length: N }, () => gauss() * 0.5);
    for (let s = 0; s < 6000; s++) {
      const mean = pop.reduce((a, b) => a + b, 0) / N;
      for (let i = 0; i < N; i++) {
        const v = pop[i] + MU + kappa * (mean - pop[i]) + SIG * gauss();
        const Q = 4 * B;
        pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
      }
    }
    const m = pop.reduce((a, b) => a + b, 0) / N;
    const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / N);
    return { g: m / B, r: sd / base };
  };
  const a = run(0), b = run(0.9);
  check('imitation raises growth', b.g > a.g, `${a.g.toFixed(3)} -> ${b.g.toFixed(3)}`);
  check('imitation destroys range', b.r < a.r, `${a.r.toFixed(3)} -> ${b.r.toFixed(3)}`);
}

// 9. independence maximises product
{
  const N = 6000, B = 3, MU = 0.05, SIG = 0.4;
  const base = B / Math.sqrt(3);
  const run = (kappa) => {
    let pop = Array.from({ length: N }, () => gauss() * 0.5);
    for (let s = 0; s < 6000; s++) {
      const mean = pop.reduce((a, b) => a + b, 0) / N;
      for (let i = 0; i < N; i++) {
        const v = pop[i] + MU + kappa * (mean - pop[i]) + SIG * gauss();
        const Q = 4 * B;
        pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
      }
    }
    const m = pop.reduce((a, b) => a + b, 0) / N;
    const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / N);
    return (m / B) * (sd / base);
  };
  const p0 = run(0), p3 = run(0.3);
  check('independence maximises product', p0 > p3, `${p0.toFixed(3)} vs ${p3.toFixed(3)}`);
}

console.log('=== VERIFICATION BEFORE PORTING TO RUST/C ===');
console.log();
let pass = 0;
for (const r of results) {
  console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name.padEnd(34)} ${r.detail}`);
  if (r.ok) pass++;
}
console.log();
console.log(`${pass}/${results.length} verified`);
console.log();
if (pass === results.length) {
  console.log('ALL CLAIMS VERIFIED — safe to port.');
} else {
  console.log('SOME CLAIMS FAILED — do NOT port until fixed.');
  // Exit non-zero so CI sees the failure. The earlier version printed FAIL and
  // returned success, which made a red result look green.
  process.exit(1);
}
