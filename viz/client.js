window.__ModuleLoader__.load({
  id: '@local/medium-viz',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useRef, useEffect, useState, useCallback } = React;

    // ---------- helpers ----------
    const gauss = () => {
      let u = 0, v = 0;
      while (!u) u = Math.random();
      while (!v) v = Math.random();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(6.283185307 * v);
    };
    const stats = (a) => {
      const n = a.length;
      if (!n) return { m: 0, v: 0, sd: 0 };
      let m = 0;
      for (const v of a) m += v;
      m /= n;
      let s = 0;
      for (const v of a) s += (v - m) * (v - m);
      return { m, v: s / n, sd: Math.sqrt(s / n) };
    };
    const refl = (v, B) => {
      const P = 4 * B;
      const u = ((v + B) % P + P) % P;
      return B - Math.abs(u - 2 * B);
    };

    function useCanvas(draw, deps, ms) {
      const ref = useRef(null);
      useEffect(() => {
        const c = ref.current;
        if (!c) return;
        let timer = 0;
        let dim = { ctx: null, w: 0, h: 0 };

        const setup = () => {
          const r = window.devicePixelRatio || 1;
          const w = Math.max(80, c.clientWidth || 300);
          const hgt = Math.max(60, c.clientHeight || 120);
          c.width = Math.round(w * r);
          c.height = Math.round(hgt * r);
          const ctx = c.getContext('2d');
          ctx.setTransform(r, 0, 0, r, 0, 0);
          dim = { ctx, w, h: hgt };
        };

        setup();

        // The card stretches with the grid, so track the real box.
        let ro = null;
        if (typeof ResizeObserver !== 'undefined') {
          ro = new ResizeObserver(() => { setup(); });
          ro.observe(c);
        } else {
          window.addEventListener('resize', setup);
        }

        const tick = () => {
          if (!dim.ctx || dim.w < 10 || dim.h < 10) return;
          try { draw(dim.ctx, dim.w, dim.h); } catch (e) { /* keep alive */ }
        };
        tick();
        timer = setInterval(tick, ms || 70);

        return () => {
          clearInterval(timer);
          if (ro) ro.disconnect();
          else window.removeEventListener('resize', setup);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, deps || []);
      return ref;
    }

    const axis = (ctx, p, w, hgt) => {
      ctx.strokeStyle = '#30363d';
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(p, hgt - 20); ctx.lineTo(w - p, hgt - 20); ctx.stroke();
    };
    const label = (ctx, text, x, y, color) => {
      ctx.fillStyle = color || '#8b949e';
      ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
      ctx.fillText(text, x, y);
    };

    // ---------- panel 1 ----------
    function Panel1() {
      const st = useRef({ pop: Array.from({ length: 120 }, gauss), sd: 0, at: 0 });
      const [ui, setUi] = useState({ sd: 0, at: 0 });
      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        for (let i = 0; i < s.pop.length; i++) s.pop[i] = Math.min(s.pop[i] + 0.5, 5);
        const t = stats(s.pop);
        s.sd = t.sd;
        s.at = s.pop.filter((v) => Math.abs(v - 5) < 1e-9).length / s.pop.length * 100;
        setUi({ sd: s.sd, at: s.at });

        ctx.clearRect(0, 0, w, hgt);
        const p = 24, W = w - p * 2, lo = -4, hi = 6;
        const X = (v) => p + (v - lo) / (hi - lo) * W;
        ctx.strokeStyle = '#f85149'; ctx.setLineDash([4, 4]);
        ctx.beginPath(); ctx.moveTo(X(5), 10); ctx.lineTo(X(5), hgt - 20); ctx.stroke();
        ctx.setLineDash([]);
        axis(ctx, p, w, hgt);
        const cnt = {};
        for (const v of s.pop) { const k = v.toFixed(1); cnt[k] = (cnt[k] || 0) + 1; }
        for (const k of Object.keys(cnt)) {
          ctx.fillStyle = '#58a6ff';
          for (let i = 0; i < cnt[k]; i++) {
            ctx.beginPath(); ctx.arc(X(+k), hgt - 30 - i * 1.6, 1.4, 0, 7); ctx.fill();
          }
        }
        label(ctx, 'потолок', X(5) + 4, 18, '#f85149');
      }, [], 70);

      return h('div', null,
        h('div', { style: S.stats },
          h('span', { style: S.bad }, 'sd ', h('b', null, ui.sd.toFixed(2))),
          h('span', { style: S.bad }, 'на потолке ', h('b', null, ui.at.toFixed(0) + '%'))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 21: the trace ----------
    // Records what the cycle did, frame by frame. Not a summary: every organism,
    // every step. Krishnamurti P204: watch ten minutes without judging.
    // Krishnamurti P283: looking with a direction is not looking.
    function Panel21() {
      const [pol, setPol] = useState('remember');
      const [at, setAt] = useState(0);
      const [playing, setPlaying] = useState(true);
      const traces = (DATA && DATA.traces) || [];
      const tr = traces.find((t) => t.policy === pol) || traces[0];

      const ref = useCanvas((ctx, w, hgt) => {
        ctx.clearRect(0, 0, w, hgt);
        if (!tr || !tr.frames || !tr.frames.length) {
          label(ctx, 'нет трассировок — запустите cargo run --bin trace', 20, hgt / 2, '#8b949e');
          return;
        }
        const f = tr.frames[Math.min(at, tr.frames.length - 1)];
        const cells = f.field.length;
        const p = 20, W = w - p * 2, H = hgt - 60;

        // The field: a strip, richer = brighter.
        const cw = W / cells;
        for (let i = 0; i < cells; i++) {
          const v = f.field[i];
          const g = Math.min(1, v / 2.0);
          ctx.fillStyle = 'rgba(63,185,80,' + (0.08 + g * 0.30) + ')';
          ctx.fillRect(p + i * cw, 20, cw - 1, H * 0.35);
        }
        label(ctx, 'поле', p, 14, '#3fb950');

        // The organisms: one dot each, at its cell.
        const rowY = 20 + H * 0.35 + 16;
        for (const s of f.samples) {
          const x = p + (s.cell + 0.5) * cw;
          const y = rowY + (1 - Math.min(1, s.energy / 10)) * (H * 0.5);
          ctx.fillStyle = s.alive ? '#58a6ff' : '#30363d';
          ctx.beginPath();
          ctx.arc(x, y, s.alive ? 2.6 : 1.6, 0, 7);
          ctx.fill();
          // The memory: a faint line to the cell it remembers.
          if (s.alive && s.memory_level > 0) {
            const mx = p + (s.memory_cell + 0.5) * cw;
            ctx.strokeStyle = 'rgba(210,153,34,0.10)';
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(mx, rowY + H * 0.5);
            ctx.stroke();
          }
        }
        label(ctx, 'организмы (высота = энергия)', p, rowY - 6, '#58a6ff');

        // The census of this frame.
        const alive = f.samples.filter((s) => s.alive).length;
        const meanE = f.samples.reduce((a, s) => a + (s.alive ? s.energy : 0), 0) / (alive || 1);
        label(
          ctx,
          'шаг ' + f.step + ' / ' + tr.frames[tr.frames.length - 1].step +
            '   живых ' + alive + ' / ' + f.samples.length +
            '   средняя энергия ' + meanE.toFixed(2),
          p, hgt - 10, '#e6edf3'
        );
      }, [pol, at], 70);

      useEffect(() => {
        if (!playing) return;
        const id = setInterval(() => {
          setAt((a) => (a + 1) % Math.max(1, (tr && tr.frames.length) || 1));
        }, 120);
        return () => clearInterval(id);
      }, [playing, tr]);

      const btn = (id, lbl) =>
        h('button', {
          key: id,
          onClick: () => { setPol(id); setAt(0); },
          style: Object.assign({}, S.tab, pol === id ? S.tabOn : null),
        }, lbl);

      return h('div', null,
        h('div', { style: Object.assign({}, S.stats, { gap: '6px' }) },
          btn('stay', 'стоит'),
          btn('random', 'случайно'),
          btn('remember', 'помнит'),
          h('button', {
            onClick: () => setPlaying((p) => !p),
            style: Object.assign({}, S.tab, { marginLeft: '8px' }),
          }, playing ? 'пауза' : 'идёт'),
          h('span', { style: { marginLeft: '10px', fontSize: '10px', color: '#8b949e' } },
            tr ? ('hash ' + tr.hash) : '')),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 22: the field segregates ----------
    // Measured (exp21, seed 1, 8 cells, 8 organisms, r = 0.5, t = 1):
    //   k = 0 cells settle at M,   k = 1 at M - t/r,   k = 2 at max(M - 2t/r, 0).
    // With feed=true the cell regrows first, then is eaten: c* = M - k*t/r.
    // With feed=false the cell is eaten first, then regrows from what is left:
    //   c* = M + k*t - k*t/r while c after eating stays positive, else M*r.
    function Panel22() {
      const [feed, setFeed] = useState(true);
      const [M, setM] = useState(2.0);
      const r = 0.5, t = 1.0;
      const cells = [0, 3, 1, 2, 4, 5, 6, 7];
      const load = [0, 0, 1, 1, 1, 1, 2, 2];   // how many organisms sit on each cell
      const kOf = (i) => load[i];

      // The equilibrium of one cell with k organisms on it.
      const eq = (k) => {
        if (feed) return Math.max(M - (k * t) / r, 0);
        const afterEating = M - k * t;
        if (afterEating > 0) return M + k * t - (k * t) / r;
        return M * r;
      };

      const ref = useCanvas((ctx, w, hgt) => {
        ctx.clearRect(0, 0, w, hgt);
        const p = 26, W = w - p * 2, H = hgt - 74;
        const hi = Math.max(M, 4) * 1.05;
        const Y = (v) => 20 + H - (v / hi) * H;

        // The empty-cell line: M. A cell that nobody eats stands here.
        ctx.strokeStyle = '#3fb950'; ctx.setLineDash([4, 4]);
        ctx.beginPath(); ctx.moveTo(p, Y(M)); ctx.lineTo(p + W, Y(M)); ctx.stroke();
        ctx.setLineDash([]);
        label(ctx, 'M = ' + M.toFixed(1), p + W - 62, Y(M) - 5, '#3fb950');

        const cw = W / cells.length;
        let sum = 0;
        for (let i = 0; i < cells.length; i++) {
          const k = kOf(i);
          const v = eq(k);
          sum += v;
          const x = p + i * cw;
          // The bar: what the cell holds once it settles.
          const col = k === 0 ? '#3fb950' : k === 1 ? '#d29922' : '#f85149';
          ctx.fillStyle = col + '55';
          ctx.fillRect(x + 3, Y(v), cw - 6, 20 + H - Y(v));
          ctx.strokeStyle = col;
          ctx.strokeRect(x + 3, Y(v), cw - 6, 20 + H - Y(v));
          // The organisms on it: one dot per organism, above the bar.
          for (let j = 0; j < k; j++) {
            ctx.fillStyle = '#58a6ff';
            ctx.beginPath();
            ctx.arc(x + cw / 2, Y(v) - 8 - j * 9, 2.6, 0, 7);
            ctx.fill();
          }
          label(ctx, 'k=' + k, x + cw / 2 - 10, 20 + H + 14, col);
          label(ctx, v.toFixed(2), x + cw / 2 - 12, Y(v) - 6 - k * 9 - 10, '#8b949e');
        }

        const mean = sum / cells.length;
        label(ctx,
          'среднее по полю ' + mean.toFixed(3) +
            '   (измерено: ' + (feed ? (M === 2 ? '0.500' : '2.000') : '1.250') + ')',
          p, hgt - 8, '#e6edf3');
      }, [feed, M], 40);

      const btn = (id, lbl, on) =>
        h('button', {
          key: id,
          onClick: on,
          style: Object.assign({}, S.tab, id === (feed ? 'f' : 'n') ? S.tabOn : null),
        }, lbl);

      return h('div', null,
        h('div', { style: Object.assign({}, S.stats, { gap: '6px' }) },
          btn('f', 'сначала растёт, потом едят', () => setFeed(true)),
          btn('n', 'сначала едят, потом растёт', () => setFeed(false)),
          h('button', {
            onClick: () => setM(M === 2.0 ? 4.0 : 2.0),
            style: Object.assign({}, S.tab, { marginLeft: '8px' }),
          }, 'M = ' + M.toFixed(1))),
        h('canvas', { ref, style: S.canvas }));
    }

// ---------- panel 23: the capacity law ----------
// Numbers are copied verbatim from
//   results/EXP-22/run-2026-11-12T12-46-12.json  (k_max is a count)
//   results/EXP-23/run-2026-11-12T12-55-33.json  (capacity is set by seating)
//   docs/LAW-capacity.md                          (the law, 12/12 + 12/12 + 6/6)
// and the law itself is proved in laws/Medium/Capacity.lean.
// The panel does not recompute anything: it draws what the runs recorded.
function Panel23() {
  // EXP-22: 40 cells, M=2, even seating of k per cell.
  const kmax = [
    { key: 'k1', n: 40, alive: 40, occupied: 40, crowding: 1.0 },
    { key: 'k2', n: 80, alive: 80, occupied: 40, crowding: 2.0 },
    { key: 'k3', n: 120, alive: 80, occupied: 40, crowding: 2.0 },
    { key: 'k4', n: 160, alive: 80, occupied: 40, crowding: 2.0 },
  ];

  // EXP-23: 160 organisms on 40 cells, random vs even seating.
  const seating = [
    { key: 'random M=4.0', M: 4.0, kmax: 4, alive: 126, predicted: 126 },
    { key: 'even M=4.0', M: 4.0, kmax: 4, alive: 160, predicted: 160 },
    { key: 'random M=2.25', M: 2.25, kmax: 2, alive: 77, predicted: 77 },
    { key: 'even M=2.25', M: 2.25, kmax: 2, alive: 80, predicted: 80 },
  ];

  // The step-1 occupancy histogram from EXP-23, random seating, seed 1:
  // 160 organisms on 40 cells, and nine cells carry more than k_max.
  const hist = [
    [1, 3], [2, 9], [3, 7], [4, 5],
    [5, 8], [6, 2], [7, 3], [8, 2], [9, 1],
  ];

  // The law, checked 12/12 on a rich cell (docs/LAW-capacity.md, check 1).
  // M=2.0, r=0.8, m=0.5, bill=0.03 -> need=0.53, M*r=1.60.
  //   unsaturated:  k_max = floor(M*r/t)
  //   saturated:    k_max = floor((M*r - need)/t) + 1
  // The measured column is what cap.rs recorded after 5000 steps.
  const rich = [
    { t: 0.55, k: 2 }, { t: 0.60, k: 2 }, { t: 0.70, k: 2 },
    { t: 0.80, k: 2 }, { t: 0.90, k: 2 }, { t: 1.00, k: 2 },
    { t: 1.05, k: 2 }, { t: 1.10, k: 1 }, { t: 1.20, k: 1 },
    { t: 1.40, k: 1 }, { t: 1.60, k: 1 }, { t: 2.00, k: 1 },
  ];
  const Mr = 1.60, need = 0.53;
  const lawK = (t) => {
    if (t <= need) return 0;
    const unsat = Math.floor(Mr / t);
    const sat = Math.floor((Mr - need) / t) + 1;
    // Take the larger branch that is self-consistent.
    let best = 0;
    if (unsat * t <= Mr) best = Math.max(best, unsat);
    if (sat * t >= Mr) best = Math.max(best, sat);
    return best;
  };

  // The cell walk at M=2, r=0.8, income=0.8: the corrected step is
  // take first, then regrow, so the level is
  //   cellLevel = max(M - k*t*(1-r)/r, M*r)
  const M = 2.0, r = 0.8, income = 0.8, maint = 0.6;
  const cellLevel = (k) => Math.max(M - k * income * (1 - r) / r, M * r);
  const walk = [];
  let left = cellLevel(0);
  for (let i = 1; i <= 4; i++) {
    const got = Math.min(income, left);
    walk.push({ k: i, before: left, got: got, fed: got >= maint - 1e-12 });
    left -= got;
  }

  return h('div', null,
    h('div', { className: 'muted', style: { marginBottom: 8 } },
      'Клетка отдаёт min(income, остаток) по очереди, поэтому ёмкость — это счёт ' +
      'едоков, а не запас ресурса. Закон выведен из трёх фактов в коде и проверен ' +
      '12/12 на богатой клетке, 12/12 на бедной, 6/6 на однородном поле.'),

    h('div', { style: { display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 12 } },
      h('div', { className: 'card', style: { padding: '8px 12px' } },
        h('div', { className: 'muted' }, 'EXP-22'),
        h('div', { style: { fontWeight: 600, color: '#2e7d32' } }, 'passed')),
      h('div', { className: 'card', style: { padding: '8px 12px' } },
        h('div', { className: 'muted' }, 'EXP-23'),
        h('div', { style: { fontWeight: 600, color: '#2e7d32' } }, 'passed')),
      h('div', { className: 'card', style: { padding: '8px 12px' } },
        h('div', { className: 'muted' }, 'k_max при M=2'),
        h('div', { style: { fontWeight: 600 } }, '2')),
      h('div', { className: 'card', style: { padding: '8px 12px' } },
        h('div', { className: 'muted' }, 'ёмкость поля'),
        h('div', { style: { fontWeight: 600 } }, '40 × 2 = 80'))),

    // ---- the law ----
    h('div', { className: 'muted', style: { margin: '12px 0 4px' } },
      'Закон: k_max(t) = max( floor(M·r/t) , floor((M·r − need)/t) + 1 ), ' +
      'взят по самосогласованным ветвям. M·r = 1.60, need = m + bill = 0.53.'),
    h('table', { className: 'table' },
      h('thead', null, h('tr', null,
        h('th', null, 'income t'), h('th', null, 'формула'),
        h('th', null, 'измерено'), h('th', null, ''))),
      h('tbody', null, rich.map((row) => {
        const f = lawK(row.t);
        const ok = f === row.k;
        return h('tr', { key: 'r' + row.t },
          h('td', null, row.t.toFixed(2)),
          h('td', null, String(f)),
          h('td', null, String(row.k)),
          h('td', { style: { color: ok ? '#2e7d32' : '#c62828' } },
            ok ? '✓' : '✗'));
      }))),
    h('div', { className: 'muted', style: { marginTop: 4, fontSize: 12 } },
      'Граница 2→1: t = M·r − m − bill = 1.60 − 0.50 − 0.03 = 1.0700. ' +
      'Бисекцией измерено 1.0733 — разница 0.0033 есть смещение бисекции, не физика.'),

    // ---- the cell walk ----
    h('div', { className: 'muted', style: { margin: '12px 0 4px' } },
      'Что остаётся на клетке после каждого едока. Уровень: ' +
      'max(M − k·t·(1−r)/r, M·r), M = ' + M + ', r = ' + r +
      ', income = ' + income + ', maintenance = ' + maint),
    h('table', { className: 'table' },
      h('thead', null, h('tr', null,
        h('th', null, 'k'), h('th', null, 'было'), h('th', null, 'взял'),
        h('th', null, 'съеден'))),
      h('tbody', null, walk.map((w) =>
        h('tr', { key: w.k },
          h('td', null, String(w.k)),
          h('td', null, w.before.toFixed(2)),
          h('td', null, w.got.toFixed(2)),
          h('td', { style: { color: w.fed ? '#2e7d32' : '#c62828' } },
            w.fed ? 'да' : 'нет — меньше ' + maint))))),

    // ---- EXP-22 ----
    h('div', { className: 'muted', style: { margin: '12px 0 4px' } },
      'EXP-22: 40 клеток, ровная посадка k на клетку (--layout even)'),
    h('table', { className: 'table' },
      h('thead', null, h('tr', null,
        h('th', null, 'плечо'), h('th', null, 'организмов'),
        h('th', null, 'выжило'), h('th', null, 'занято'), h('th', null, 'давка'))),
      h('tbody', null, kmax.map((row) =>
        h('tr', { key: row.key },
          h('td', null, row.key),
          h('td', null, String(row.n)),
          h('td', null, String(row.alive)),
          h('td', null, String(row.occupied)),
          h('td', null, row.crowding.toFixed(2)))))),

    // ---- EXP-23 ----
    h('div', { className: 'muted', style: { margin: '12px 0 4px' } },
      'EXP-23: 160 организмов на 40 клетках, случайная и ровная посадка'),
    h('table', { className: 'table' },
      h('thead', null, h('tr', null,
        h('th', null, 'посадка'), h('th', null, 'M'), h('th', null, 'k_max'),
        h('th', null, 'предсказано'), h('th', null, 'измерено'))),
      h('tbody', null, seating.map((row) =>
        h('tr', { key: row.key },
          h('td', null, row.key),
          h('td', null, row.M.toFixed(2)),
          h('td', null, String(row.kmax)),
          h('td', null, String(row.predicted)),
          h('td', { style: { color: row.alive === row.predicted ? '#2e7d32' : '#c62828' } },
            String(row.alive)))))),

    // ---- histogram ----
    h('div', { className: 'muted', style: { margin: '12px 0 4px' } },
      'Занятость при случайной посадке (160 на 40 клетках, seed 1): ' +
      'девять клеток несут больше k_max'),
    h('div', { style: { display: 'flex', alignItems: 'flex-end', gap: 4, height: 90 } },
      hist.map(([occ, count]) =>
        h('div', { key: 'h' + occ, style: { textAlign: 'center', width: 34 } },
          h('div', {
            style: {
              height: count * 8,
              background: occ > 4 ? '#c62828' : '#90a4ae',
              borderRadius: '2px 2px 0 0',
            },
          }),
          h('div', { className: 'muted', style: { fontSize: 10 } }, String(occ)),
          h('div', { className: 'muted', style: { fontSize: 10 } }, count + 'кл')))),

    h('div', { className: 'muted', style: { marginTop: 10, fontSize: 12 } },
      'Выживает sum min(занятость, k_max). При M=4.0 это 126 из 160, при M=2.25 — ' +
      '77 из 160; ровная посадка даёт 160 и 80. Запас, выраженный в порциях, дал бы ' +
      '2.25 и ёмкость 90 — это и было ошибкой старой заметки.'),

    // ---- what the proof caught ----
    h('div', { className: 'muted', style: { margin: '12px 0 4px' } },
      'Что поймала формализация (laws/Medium/Capacity.lean, 9 теорем, 0 sorry)'),
    h('div', { style: { fontSize: 13, lineHeight: 1.5 } },
      h('div', null,
        'Закон сначала был записан со строгим «<» на насыщенной ветви: ',
        h('code', null, 'need < M·r − floor((M·r − need)/t)·t'),
        '. Это ложь. Контрпример: M·r = 10, need = 4, t = 2 → floor(6/2) = 3 → ',
        h('code', null, '10 − 3·2 = 4 = need'),
        ', значит 4 < 4 неверно.'),
      h('div', { style: { marginTop: 6 } },
        'Строгость живёт на шаг дальше — в ',
        h('code', null, 'capacity_law_strict'),
        ': 0 < M·r − (floor((M·r − need)/t) − 1)·t. Она требует 0 ≤ need.'),
      h('div', { style: { marginTop: 6, color: '#6d4c41' } },
        'Без Lean эта теорема ушла бы в заметки как доказанная.')),
  );
}
    // ---------- panel 2 ----------
    function Panel2() {
      const B = 5, SG = 0.3;
      const st = useRef({ pop: Array.from({ length: 120 }, gauss), sd: 0 });
      const [ui, setUi] = useState({ sd: 0 });
      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        for (let k = 0; k < 3; k++)
          for (let i = 0; i < s.pop.length; i++) s.pop[i] = refl(s.pop[i] + SG * gauss(), B);
        s.sd = stats(s.pop).sd;
        setUi({ sd: s.sd });

        ctx.clearRect(0, 0, w, hgt);
        const p = 24, W = w - p * 2, lo = -6, hi = 6;
        const X = (v) => p + (v - lo) / (hi - lo) * W;
        ctx.strokeStyle = '#3fb950'; ctx.setLineDash([4, 4]);
        for (const b of [-B, B]) { ctx.beginPath(); ctx.moveTo(X(b), 10); ctx.lineTo(X(b), hgt - 20); ctx.stroke(); }
        ctx.setLineDash([]);
        axis(ctx, p, w, hgt);
        const bn = 36, c = new Array(bn).fill(0);
        for (const v of s.pop) {
          let i = Math.floor((v - lo) / (hi - lo) * bn);
          i = Math.max(0, Math.min(bn - 1, i)); c[i]++;
        }
        const mx = Math.max(...c, 1), bw = W / bn;
        for (let i = 0; i < bn; i++) {
          const bh = c[i] / mx * (hgt - 42);
          ctx.fillStyle = 'rgba(63,185,80,' + (0.25 + 0.6 * c[i] / mx) + ')';
          ctx.fillRect(p + i * bw, hgt - 21 - bh, bw - 1, bh);
        }
        label(ctx, '−B', X(-B) - 12, 18, '#3fb950');
        label(ctx, '+B', X(B) + 3, 18, '#3fb950');
      }, [], 55);

      return h('div', null,
        h('div', { style: S.stats },
          h('span', { style: S.good }, 'sd ', h('b', null, ui.sd.toFixed(2))),
          h('span', { style: S.good }, 'теория ', h('b', null, (5 / Math.sqrt(3)).toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 3 ----------
    function Panel3() {
      const N = 4000;
      const st = useRef({ base: Array.from({ length: N }, gauss), k: 0, dir: 1 });
      const [ui, setUi] = useState({ k: 0, m: 0, v: 1, neff: N });
      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        s.k += 0.05 * s.dir;
        if (s.k > 2.2) { s.k = 2.2; s.dir = -1; }
        if (s.k < -1.5) { s.k = -1.5; s.dir = 1; }
        const wt = s.base.map((v) => Math.exp(s.k * v));
        let S = 0, S2 = 0;
        for (const x of wt) { S += x; S2 += x * x; }
        let m = 0, m2 = 0;
        for (let i = 0; i < N; i++) { m += s.base[i] * wt[i]; m2 += s.base[i] * s.base[i] * wt[i]; }
        m /= S; m2 /= S;
        setUi({ k: s.k, m, v: m2 - m * m, neff: S * S / S2 });

        ctx.clearRect(0, 0, w, hgt);
        const p = 24, W = w - p * 2, H = hgt - 42, lo = -4, hi = 6;
        const X = (v) => p + (v - lo) / (hi - lo) * W;
        axis(ctx, p, w, hgt);
        const bn = 40, hb = new Array(bn).fill(0), hw = new Array(bn).fill(0);
        for (let i = 0; i < N; i++) {
          let b = Math.floor((s.base[i] - lo) / (hi - lo) * bn);
          b = Math.max(0, Math.min(bn - 1, b));
          hb[b]++; hw[b] += wt[i];
        }
        const bw = W / bn, mB = Math.max(...hb, 1), mW = Math.max(...hw, 1);
        for (let i = 0; i < bn; i++) {
          ctx.fillStyle = 'rgba(139,148,158,0.25)';
          ctx.fillRect(p + i * bw, hgt - 21 - hb[i] / mB * H * 0.45, bw - 1, hb[i] / mB * H * 0.45);
          ctx.fillStyle = 'rgba(88,166,255,0.75)';
          ctx.fillRect(p + i * bw, hgt - 21 - hw[i] / mW * H * 0.85, bw - 1, hw[i] / mW * H * 0.85);
        }
        ctx.strokeStyle = '#d29922'; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(X(m), 12); ctx.lineTo(X(m), hgt - 21); ctx.stroke();
      }, [], 65);

      return h('div', null,
        h('div', { style: S.stats },
          h('span', { style: S.dim }, 'k ', h('b', null, ui.k.toFixed(1))),
          h('span', { style: S.warn }, 'среднее ', h('b', null, ui.m.toFixed(2))),
          h('span', { style: S.good }, 'дисперсия ', h('b', null, ui.v.toFixed(2))),
          h('span', { style: S.dim }, 'N ', h('b', null, Math.round(ui.neff)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 4 ----------
    function Panel4() {
      const N = 3000;
      const st = useRef({ base: Array.from({ length: N }, gauss), a: 3, dir: -1 });
      const [ui, setUi] = useState({ w: 6, r: 0 });
      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        s.a += 0.04 * s.dir;
        if (s.a < 0.15) { s.a = 0.15; s.dir = 1; }
        if (s.a > 3) { s.a = 3; s.dir = -1; }
        const a = s.a;
        const sub = s.base.filter((v) => v >= -a && v <= a);
        const t = stats(sub);
        setUi({ w: 2 * a, r: t.v / (4 * a * a) });

        ctx.clearRect(0, 0, w, hgt);
        const p = 24, W = w - p * 2, H = hgt - 42, lo = -4, hi = 4;
        axis(ctx, p, w, hgt);
        const bn = 36, hb = new Array(bn).fill(0), hs = new Array(bn).fill(0);
        for (const v of s.base) { let b = Math.floor((v - lo) / (hi - lo) * bn); if (b >= 0 && b < bn) hb[b]++; }
        for (const v of sub) { let b = Math.floor((v - lo) / (hi - lo) * bn); if (b >= 0 && b < bn) hs[b]++; }
        const bw = W / bn, mB = Math.max(...hb, 1), mS = Math.max(...hs, 1);
        for (let i = 0; i < bn; i++) {
          ctx.fillStyle = 'rgba(139,148,158,0.2)';
          ctx.fillRect(p + i * bw, hgt - 21 - hb[i] / mB * H * 0.5, bw - 1, hb[i] / mB * H * 0.5);
          ctx.fillStyle = 'rgba(210,153,34,0.8)';
          ctx.fillRect(p + i * bw, hgt - 21 - hs[i] / mS * H * 0.85, bw - 1, hs[i] / mS * H * 0.85);
        }
        ctx.strokeStyle = '#f85149'; ctx.setLineDash([3, 3]);
        for (const b of [-a, a]) {
          const X = p + (b - lo) / (hi - lo) * W;
          ctx.beginPath(); ctx.moveTo(X, 10); ctx.lineTo(X, hgt - 21); ctx.stroke();
        }
        ctx.setLineDash([]);
      }, [], 65);

      return h('div', null,
        h('div', { style: S.stats },
          h('span', { style: S.dim }, 'ширина ', h('b', null, ui.w.toFixed(1))),
          h('span', { style: S.warn }, 'Var/w² ', h('b', null, ui.r.toFixed(3))),
          h('span', { style: S.dim }, '→ 1/12 = 0.083')),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 5 ----------
    function Panel5() {
      const [mode, setMode] = useState('const');
      const st = useRef({ pop: Array.from({ length: 120 }, () => gauss() * 0.5 + 1), hist: [], sd: 0, B: 5 });
      const [ui, setUi] = useState({ sd: 0, B: 5 });
      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: 120 }, () => gauss() * 0.5 + 1);
        st.current.hist = [];
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current, K = 3;
        let B;
        if (mode === 'const') B = 5;
        else {
          const t = stats(s.pop);
          B = Math.max(0.001, mode === 'std' ? K * t.sd : K * Math.abs(t.m));
        }
        s.B = B;
        for (let i = 0; i < s.pop.length; i++) s.pop[i] = refl(s.pop[i] + 0.3 * gauss(), B);
        s.sd = stats(s.pop).sd;
        s.hist.push(s.sd);
        if (s.hist.length > 200) s.hist.shift();
        setUi({ sd: s.sd, B });

        ctx.clearRect(0, 0, w, hgt);
        const p = 24, W = w - p * 2, H = hgt - 42;
        const mx = Math.max(4, ...s.hist, 1);
        ctx.strokeStyle = mode === 'const' ? '#3fb950' : mode === 'mean' ? '#f85149' : '#d29922';
        ctx.lineWidth = 2; ctx.beginPath();
        s.hist.forEach((v, i) => {
          const px = p + i / 200 * W, py = hgt - 21 - v / mx * H;
          i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
        });
        ctx.stroke();
        axis(ctx, p, w, hgt);
        if (mode === 'const') {
          const ty = hgt - 21 - (5 / Math.sqrt(3)) / mx * H;
          ctx.strokeStyle = '#3fb950'; ctx.setLineDash([4, 4]); ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(p, ty); ctx.lineTo(w - p, ty); ctx.stroke();
          ctx.setLineDash([]);
          label(ctx, 'B/√3', w - p - 30, ty - 4, '#3fb950');
        }
      }, [mode], 45);

      const btn = (m, text) => h('button', {
        key: m,
        onClick: () => { setMode(m); reset(); },
        style: Object.assign({}, S.btn, mode === m ? S.btnOn : null),
      }, text);

      return h('div', null,
        h('div', { style: S.btns },
          btn('const', 'const'), btn('mean', 'k·mean'), btn('std', 'k·std')),
        h('div', { style: S.stats },
          h('span', { style: S.dim }, 'sd ', h('b', null, ui.sd.toFixed(3))),
          h('span', { style: S.dim }, 'стена ', h('b', null, ui.B.toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 6: symmetry is what preserves diversity ----------
    function Panel6() {
      // Four walls, same noise. Only the symmetric reflection reaches uniform.
      const walls = [
        { id: 'reflect', label: 'отражение', sym: true, col: '#3fb950' },
        { id: 'clamp', label: 'обрезка', sym: false, col: '#8b949e' },
        { id: 'foldtop', label: 'складка', sym: false, col: '#d29922' },
        { id: 'biased', label: 'сжатие', sym: false, col: '#f85149' },
      ];
      const N = 900;
      const st = useRef({
        pops: walls.map(() => Array.from({ length: N }, () => gauss() * 2.5)),
        chi: walls.map(() => 0),
      });
      const [ui, setUi] = useState({ chi: walls.map(() => 0), sd: walls.map(() => 0) });

      const applyWall = (id, x, B) => {
        if (id === 'reflect') {
          const Q = 4 * B;
          return B - Math.abs((((x + B) % Q + Q) % Q) - 2 * B);
        }
        if (id === 'clamp') return Math.min(Math.max(x, -B), B);
        if (id === 'foldtop') {
          if (x > B) return 2 * B - x;
          if (x < -B) return -B;
          return x;
        }
        // biased: squeeze and shift
        const Q = 4 * B;
        const f = B - Math.abs((((x + B) % Q + Q) % Q) - 2 * B);
        return f * 0.85 - 0.4;
      };

      const ref = useCanvas((ctx, w, hgt) => {
        const B = 5;
        const s = st.current;
        for (let k = 0; k < 2; k++) {
          for (let wi = 0; wi < walls.length; wi++) {
            const pop = s.pops[wi];
            for (let i = 0; i < pop.length; i++) {
              pop[i] = applyWall(walls[wi].id, pop[i] + 0.3 * gauss(), B);
            }
          }
        }
        // chi2 per bin count (normalised by N)
        const bins = 16;
        const chis = [], sds = [];
        for (let wi = 0; wi < walls.length; wi++) {
          const pop = s.pops[wi];
          const h = new Array(bins).fill(0);
          for (const v of pop) {
            let i = Math.floor((v + B) / (2 * B) * bins);
            i = Math.max(0, Math.min(bins - 1, i));
            h[i]++;
          }
          const e = pop.length / bins;
          chis.push(h.reduce((a, x) => a + (x - e) ** 2 / e, 0) / pop.length);
          const m = pop.reduce((a, b) => a + b, 0) / pop.length;
          sds.push(Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / pop.length));
        }
        setUi({ chi: chis, sd: sds });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26;
        const plotW = w - pad * 2;
        const plotH = hgt - 60;
        const lo = -B, hi = B;

        // four mini histograms side by side
        const cellW = plotW / walls.length;
        for (let wi = 0; wi < walls.length; wi++) {
          const pop = s.pops[wi];
          const x0 = pad + wi * cellW;
          const bins2 = 18;
          const h = new Array(bins2).fill(0);
          for (const v of pop) {
            let i = Math.floor((v - lo) / (hi - lo) * bins2);
            i = Math.max(0, Math.min(bins2 - 1, i));
            h[i]++;
          }
          const mx = Math.max(...h, 1);
          const bw = (cellW - 10) / bins2;
          for (let i = 0; i < bins2; i++) {
            const bh = h[i] / mx * plotH;
            ctx.fillStyle = walls[wi].col;
            ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
            ctx.fillRect(x0 + 5 + i * bw, hgt - 32 - bh, Math.max(1, bw - 1), bh);
          }
          ctx.globalAlpha = 1;
          // label
          ctx.fillStyle = walls[wi].col;
          ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
          ctx.fillText(walls[wi].label, x0 + 5, 14);
          // chi2/N
          ctx.fillStyle = '#8b949e';
          ctx.font = '9px ui-monospace,SFMono-Regular,Consolas,monospace';
          const c = chis[wi];
          const txt = c < 1e-2 ? c.toExponential(1) : c.toFixed(2);
          ctx.fillText('χ²/N ' + txt, x0 + 5, 26);
        }
        // baseline
        ctx.strokeStyle = '#30363d';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 32);
        ctx.lineTo(w - pad, hgt - 32);
        ctx.stroke();
      }, [], 60);

      return h('div', null,
        h('div', { style: S.stats },
          h('span', { style: S.good }, 'отражение ', h('b', null, ui.chi[0] < 1e-2 ? ui.chi[0].toExponential(1) : ui.chi[0].toFixed(2))),
          h('span', { style: S.dim }, 'обрезка ', h('b', null, ui.chi[1].toFixed(2))),
          h('span', { style: S.warn }, 'складка ', h('b', null, ui.chi[2].toFixed(2))),
          h('span', { style: S.bad }, 'сжатие ', h('b', null, ui.chi[3].toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 7: symmetry pins the centre, not the width ----------
    function Panel7() {
      const B = 5;
      const rules = [
        { id: 'uniform', label: 'w=1', col: '#3fb950' },
        { id: 'tilt', label: 'exp(0.5x)', col: '#d29922' },
        { id: 'tent', label: 'симметр.', col: '#58a6ff' },
      ];
      const N = 700;
      const st = useRef({
        pops: rules.map(() => Array.from({ length: N }, () => gauss() * 2.5)),
      });
      const [ui, setUi] = useState({ mean: [0, 0, 0], sd: [0, 0, 0] });

      const weight = (id, x) => {
        if (id === 'uniform') return 1;
        if (id === 'tilt') return Math.exp(0.5 * x);
        // symmetric tent: peaks at the centre, symmetric about 0
        return 1 + 0.9 * (1 - Math.abs(x) / B);
      };

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        for (let wi = 0; wi < rules.length; wi++) {
          const pop = s.pops[wi];
          const id = rules[wi].id;
          // one generation: select, then repopulate with noise + reflection
          const kept = [];
          for (const x of pop) {
            const wgt = weight(id, x);
            if (Math.random() < wgt / 2.2) kept.push(x);
          }
          if (kept.length > 20) {
            for (let i = 0; i < pop.length; i++) {
              const p = kept[Math.floor(Math.random() * kept.length)];
              const Q = 4 * B;
              const v = p + 0.3 * gauss();
              pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
            }
          }
        }

        const means = [], sds = [];
        for (const pop of s.pops) {
          const m = pop.reduce((a, b) => a + b, 0) / pop.length;
          means.push(m);
          sds.push(Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / pop.length));
        }
        setUi({ mean: means, sd: sds });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 58;
        const lo = -B, hi = B;
        const cellW = plotW / rules.length;

        for (let wi = 0; wi < rules.length; wi++) {
          const pop = s.pops[wi];
          const x0 = pad + wi * cellW;
          const bins = 18;
          const h = new Array(bins).fill(0);
          for (const v of pop) {
            let i = Math.floor((v - lo) / (hi - lo) * bins);
            i = Math.max(0, Math.min(bins - 1, i));
            h[i]++;
          }
          const mx = Math.max(...h, 1);
          const bw = (cellW - 10) / bins;
          for (let i = 0; i < bins; i++) {
            const bh = h[i] / mx * plotH;
            ctx.fillStyle = rules[wi].col;
            ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
            ctx.fillRect(x0 + 5 + i * bw, hgt - 30 - bh, Math.max(1, bw - 1), bh);
          }
          ctx.globalAlpha = 1;
          ctx.fillStyle = rules[wi].col;
          ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
          ctx.fillText(rules[wi].label, x0 + 5, 14);
          ctx.fillStyle = '#8b949e';
          ctx.font = '9px ui-monospace,SFMono-Regular,Consolas,monospace';
          ctx.fillText('m ' + means[wi].toFixed(2) + '  sd ' + sds[wi].toFixed(2), x0 + 5, 26);
        }
        ctx.strokeStyle = '#30363d';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 30);
        ctx.lineTo(w - pad, hgt - 30);
        ctx.stroke();
      }, [], 55);

      return h('div', null,
        h('div', { style: S.stats },
          h('span', { style: S.good }, 'w=1 sd ', h('b', null, ui.sd[0].toFixed(2))),
          h('span', { style: S.warn }, 'tilt sd ', h('b', null, ui.sd[1].toFixed(2))),
          h('span', { style: S.accent || S.dim }, 'симметр. sd ', h('b', null, ui.sd[2].toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 8: the room law ----------
    function Panel8() {
      const [B, setB] = useState(2.0);
      const [narrow, setNarrow] = useState(false);

      // Two rooms side by side: the current B and a doubled one.
      const N = 600;
      const st = useRef({
        a: Array.from({ length: N }, () => gauss() * 0.5),
        b: Array.from({ length: N }, () => gauss() * 0.5),
      });
      const [ui, setUi] = useState({ sdA: 0, sdB: 0 });

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const B2 = B * 2;
        for (let k = 0; k < 3; k++) {
          for (let i = 0; i < N; i++) {
            const qa = 4 * B;
            const va = s.a[i] + 0.3 * gauss();
            s.a[i] = B - Math.abs((((va + B) % qa + qa) % qa) - 2 * B);
            const qb = 4 * B2;
            const vb = s.b[i] + 0.3 * gauss();
            s.b[i] = B2 - Math.abs((((vb + B2) % qb + qb) % qb) - 2 * B2);
          }
        }
        const mean = (p) => p.reduce((x, y) => x + y, 0) / p.length;
        const sd = (p) => {
          const m = mean(p);
          return Math.sqrt(p.reduce((x, y) => x + (y - m) ** 2, 0) / p.length);
        };
        setUi({ sdA: sd(s.a), sdB: sd(s.b) });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 58;
        const half = plotW / 2 - 8;

        // left: room B
        const drawRoom = (x0, pop, room, col, label) => {
          const bins = 16;
          const h = new Array(bins).fill(0);
          for (const v of pop) {
            let i = Math.floor((v + room) / (2 * room) * bins);
            i = Math.max(0, Math.min(bins - 1, i));
            h[i]++;
          }
          const mx = Math.max(...h, 1);
          const bw = (half - 10) / bins;
          for (let i = 0; i < bins; i++) {
            const bh = h[i] / mx * plotH;
            ctx.fillStyle = col;
            ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
            ctx.fillRect(x0 + 5 + i * bw, hgt - 30 - bh, Math.max(1, bw - 1), bh);
          }
          ctx.globalAlpha = 1;
          // walls
          ctx.strokeStyle = '#f85149';
          ctx.setLineDash([3, 3]);
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(x0 + 5, hgt - 30 - plotH);
          ctx.lineTo(x0 + 5, hgt - 30);
          ctx.moveTo(x0 + 5 + half - 10, hgt - 30 - plotH);
          ctx.lineTo(x0 + 5 + half - 10, hgt - 30);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.fillStyle = col;
          ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
          ctx.fillText(label, x0 + 5, 14);
          ctx.fillStyle = '#8b949e';
          ctx.font = '9px ui-monospace,SFMono-Regular,Consolas,monospace';
          ctx.fillText('sd ' + sd(pop).toFixed(2), x0 + 5, 26);
        };

        drawRoom(pad, s.a, B, '#58a6ff', 'комната B');
        drawRoom(pad + half + 16, s.b, B2, '#3fb950', 'комната 2B');

        ctx.strokeStyle = '#30363d';
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 30);
        ctx.lineTo(w - pad, hgt - 30);
        ctx.stroke();
      }, [B], 55);

      return h('div', null,
        h('div', { style: S.btns },
          h('button', {
            key: 'narrow',
            onClick: () => setB(1.0),
            style: Object.assign({}, S.btn, B === 1.0 ? S.btnOn : null),
          }, 'узкая B=1'),
          h('button', {
            key: 'mid',
            onClick: () => setB(2.0),
            style: Object.assign({}, S.btn, B === 2.0 ? S.btnOn : null),
          }, 'B=2'),
          h('button', {
            key: 'wide',
            onClick: () => setB(4.0),
            style: Object.assign({}, S.btn, B === 4.0 ? S.btnOn : null),
          }, 'широкая B=4')),
        h('div', { style: S.stats },
          h('span', { style: S.dim }, 'sd в B ', h('b', null, ui.sdA.toFixed(2))),
          h('span', { style: S.good }, 'sd в 2B ', h('b', null, ui.sdB.toFixed(2))),
          h('span', { style: S.dim }, '≈ ×√2 = 1.41')),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 9: a responding space destroys ----------
    function Panel9() {
      const [mode, setMode] = useState('fixed');
      const N = 500;
      const st = useRef({
        pop: Array.from({ length: N }, () => gauss() * 0.8),
        B: 3,
        hist: [],
      });
      const [ui, setUi] = useState({ sd: 0, B: 3 });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () => gauss() * 0.8);
        st.current.B = 3;
        st.current.hist = [];
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        const m = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / pop.length);

        if (mode === 'fixed') s.B = 3;
        else if (mode === 'mean') s.B = Math.max(0.05, 2.5 * Math.abs(m));
        else s.B = Math.max(0.05, 2.5 * sd);

        const B = s.B;
        for (let i = 0; i < pop.length; i++) {
          const v = pop[i] + 0.3 * gauss();
          const Q = 4 * B;
          pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
        }
        const m2 = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd2 = Math.sqrt(pop.reduce((a, b) => a + (b - m2) ** 2, 0) / pop.length);
        s.hist.push(sd2);
        if (s.hist.length > 200) s.hist.shift();
        setUi({ sd: sd2, B });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 52;

        // spread over time
        const mx = Math.max(4, ...s.hist, 1);
        ctx.strokeStyle = mode === 'fixed' ? '#3fb950' : mode === 'mean' ? '#f85149' : '#d29922';
        ctx.lineWidth = 2;
        ctx.beginPath();
        s.hist.forEach((v, i) => {
          const px = pad + i / 200 * plotW;
          const py = hgt - 26 - v / mx * plotH;
          i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
        });
        ctx.stroke();

        // theory line for fixed
        if (mode === 'fixed') {
          const ty = hgt - 26 - (3 / Math.sqrt(3)) / mx * plotH;
          ctx.strokeStyle = '#3fb950';
          ctx.setLineDash([4, 4]);
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(pad, ty);
          ctx.lineTo(w - pad, ty);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.fillStyle = '#3fb950';
          ctx.font = '9px ui-monospace,SFMono-Regular,Consolas,monospace';
          ctx.fillText('B/√3', w - pad - 28, ty - 4);
        }

        ctx.strokeStyle = '#30363d';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 26);
        ctx.lineTo(w - pad, hgt - 26);
        ctx.stroke();

        ctx.fillStyle = '#8b949e';
        ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
        ctx.fillText('разброс', 6, 16);
      }, [mode], 45);

      const btn = (m, text) => h('button', {
        key: m,
        onClick: () => { setMode(m); reset(); },
        style: Object.assign({}, S.btn, mode === m ? S.btnOn : null),
      }, text);

      return h('div', null,
        h('div', { style: S.btns },
          btn('fixed', 'фиксированная'),
          btn('mean', 'вокруг среднего'),
          btn('spread', 'вокруг разброса')),
        h('div', { style: S.stats },
          h('span', { style: S.dim }, 'sd ', h('b', null, ui.sd.toFixed(3))),
          h('span', { style: S.dim }, 'комната B ', h('b', null, ui.B.toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 10: bounded response holds ----------
    function Panel10() {
      const [Bmax, setBmax] = useState(3.0);
      const N = 500;
      const st = useRef({
        pop: Array.from({ length: N }, () => gauss() * 0.8),
        B: 3,
        hist: [],
      });
      const [ui, setUi] = useState({ sd: 0, B: 3 });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () => gauss() * 0.8);
        st.current.B = 3;
        st.current.hist = [];
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        const m0 = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd0 = Math.sqrt(pop.reduce((a, b) => a + (b - m0) ** 2, 0) / pop.length);

        // responds to spread, but bounded above by Bmax
        const Bmin = 0.3;
        s.B = Math.min(Bmax, Math.max(Bmin, 2.5 * sd0));

        const B = s.B;
        for (let i = 0; i < pop.length; i++) {
          const v = pop[i] + 0.3 * gauss();
          const Q = 4 * B;
          pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
        }
        const m = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / pop.length);
        s.hist.push(sd);
        if (s.hist.length > 200) s.hist.shift();
        setUi({ sd, B });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 52;
        const mx = Math.max(4, ...s.hist, 1);

        ctx.strokeStyle = '#3fb950';
        ctx.lineWidth = 2;
        ctx.beginPath();
        s.hist.forEach((v, i) => {
          const px = pad + i / 200 * plotW;
          const py = hgt - 26 - v / mx * plotH;
          i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
        });
        ctx.stroke();

        // theory: Bmax/sqrt(3)
        const ty = hgt - 26 - (Bmax / Math.sqrt(3)) / mx * plotH;
        ctx.strokeStyle = '#58a6ff';
        ctx.setLineDash([4, 4]);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pad, ty);
        ctx.lineTo(w - pad, ty);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = '#58a6ff';
        ctx.font = '9px ui-monospace,SFMono-Regular,Consolas,monospace';
        ctx.fillText('Bmax/√3 = ' + (Bmax / Math.sqrt(3)).toFixed(2), w - pad - 96, ty - 4);

        ctx.strokeStyle = '#30363d';
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 26);
        ctx.lineTo(w - pad, hgt - 26);
        ctx.stroke();

        ctx.fillStyle = '#8b949e';
        ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
        ctx.fillText('разброс', 6, 16);
      }, [Bmax], 45);

      const btn = (v, text) => h('button', {
        key: String(v),
        onClick: () => { setBmax(v); reset(); },
        style: Object.assign({}, S.btn, Bmax === v ? S.btnOn : null),
      }, text);

      return h('div', null,
        h('div', { style: S.btns },
          btn(1.0, 'Bmax=1'),
          btn(3.0, 'Bmax=3'),
          btn(6.0, 'Bmax=6')),
        h('div', { style: S.stats },
          h('span', { style: S.good }, 'sd ', h('b', null, ui.sd.toFixed(3))),
          h('span', { style: S.dim }, 'комната B ', h('b', null, ui.B.toFixed(2))),
          h('span', { style: S.dim }, 'Bmax/√3 ', h('b', null, (Bmax / Math.sqrt(3)).toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 11: growth vs range trade-off ----------
    function Panel11() {
      const [push, setPush] = useState(0.05);
      const B = 3, SIG = 0.3;
      const N = 700;
      const st = useRef({ pop: Array.from({ length: N }, () => gauss() * 0.5) });
      const [ui, setUi] = useState({ m: 0, sd: 0 });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () => gauss() * 0.5);
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        for (let k = 0; k < 2; k++) {
          for (let i = 0; i < pop.length; i++) {
            const v = pop[i] + push + SIG * gauss();
            const Q = 4 * B;
            pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
          }
        }
        const m = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / pop.length);
        setUi({ m, sd });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 56;
        const lo = -B, hi = B;

        // histogram
        const bins = 22;
        const h = new Array(bins).fill(0);
        for (const v of pop) {
          let i = Math.floor((v - lo) / (hi - lo) * bins);
          i = Math.max(0, Math.min(bins - 1, i));
          h[i]++;
        }
        const mx = Math.max(...h, 1);
        const bw = plotW / bins;
        for (let i = 0; i < bins; i++) {
          const bh = h[i] / mx * plotH;
          ctx.fillStyle = '#58a6ff';
          ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
          ctx.fillRect(pad + i * bw, hgt - 28 - bh, Math.max(1, bw - 1), bh);
        }
        ctx.globalAlpha = 1;

        // theory: exp(alpha x)
        const alpha = 2 * push / (SIG * SIG);
        if (Math.abs(alpha) > 1e-6) {
          const eB = Math.exp(alpha * B), emB = Math.exp(-alpha * B);
          const Z = (eB - emB) / alpha;
          ctx.strokeStyle = '#d29922';
          ctx.lineWidth = 2;
          ctx.beginPath();
          let first = true;
          let maxD = 0;
          const dens = [];
          for (let i = 0; i <= 100; i++) {
            const x = lo + i / 100 * (hi - lo);
            const d = Math.exp(alpha * x) / Z;
            dens.push(d);
            if (d > maxD) maxD = d;
          }
          for (let i = 0; i <= 100; i++) {
            const x = lo + i / 100 * (hi - lo);
            const px = pad + i / 100 * plotW;
            const py = hgt - 28 - (dens[i] / maxD) * plotH * 0.95;
            first ? (ctx.moveTo(px, py), first = false) : ctx.lineTo(px, py);
          }
          ctx.stroke();
        }

        // mean marker
        const px = pad + (m - lo) / (hi - lo) * plotW;
        ctx.strokeStyle = '#f85149';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(px, 14);
        ctx.lineTo(px, hgt - 28);
        ctx.stroke();

        // walls
        ctx.strokeStyle = '#f85149';
        ctx.setLineDash([3, 3]);
        ctx.lineWidth = 1;
        for (const b of [lo, hi]) {
          const wx = pad + (b - lo) / (hi - lo) * plotW;
          ctx.beginPath();
          ctx.moveTo(wx, 14);
          ctx.lineTo(wx, hgt - 28);
          ctx.stroke();
        }
        ctx.setLineDash([]);

        ctx.strokeStyle = '#30363d';
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 28);
        ctx.lineTo(w - pad, hgt - 28);
        ctx.stroke();

        ctx.fillStyle = '#8b949e';
        ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
        ctx.fillText('рост ' + push.toFixed(2), 6, 16);
      }, [push], 45);

      const btn = (v, text) => h('button', {
        key: String(v),
        onClick: () => { setPush(v); reset(); },
        style: Object.assign({}, S.btn, push === v ? S.btnOn : null),
      }, text);

      return h('div', null,
        h('div', { style: S.btns },
          btn(0.0, 'нет роста'),
          btn(0.03, 'слабый'),
          btn(0.05, 'средний'),
          btn(0.2, 'сильный')),
        h('div', { style: S.stats },
          h('span', { style: S.warn }, 'среднее ', h('b', null, ui.m.toFixed(2))),
          h('span', { style: S.good }, 'разброс ', h('b', null, ui.sd.toFixed(2))),
          h('span', { style: S.dim }, 'α ', h('b', null, (2 * push / 0.09).toFixed(1)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 12: the noise optimum ----------
    function Panel12() {
      const [sigma, setSigma] = useState(0.4);
      const B = 3, MU = 0.05;
      const N = 600;
      const st = useRef({ pop: Array.from({ length: N }, () => gauss() * 0.5) });
      const [ui, setUi] = useState({ m: 0, sd: 0 });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () => gauss() * 0.5);
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        for (let k = 0; k < 2; k++) {
          for (let i = 0; i < pop.length; i++) {
            const v = pop[i] + MU + sigma * gauss();
            const Q = 4 * B;
            pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
          }
        }
        const m = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / pop.length);
        setUi({ m, sd });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 56;
        const lo = -B, hi = B;

        // histogram
        const bins = 22;
        const h = new Array(bins).fill(0);
        for (const v of pop) {
          let i = Math.floor((v - lo) / (hi - lo) * bins);
          i = Math.max(0, Math.min(bins - 1, i));
          h[i]++;
        }
        const mx = Math.max(...h, 1);
        const bw = plotW / bins;
        for (let i = 0; i < bins; i++) {
          const bh = h[i] / mx * plotH;
          ctx.fillStyle = '#bc8cff';
          ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
          ctx.fillRect(pad + i * bw, hgt - 28 - bh, Math.max(1, bw - 1), bh);
        }
        ctx.globalAlpha = 1;

        // mean
        const px = pad + (m - lo) / (hi - lo) * plotW;
        ctx.strokeStyle = '#f85149';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(px, 14);
        ctx.lineTo(px, hgt - 28);
        ctx.stroke();

        // walls
        ctx.strokeStyle = '#f85149';
        ctx.setLineDash([3, 3]);
        ctx.lineWidth = 1;
        for (const b of [lo, hi]) {
          const wx = pad + (b - lo) / (hi - lo) * plotW;
          ctx.beginPath();
          ctx.moveTo(wx, 14);
          ctx.lineTo(wx, hgt - 28);
          ctx.stroke();
        }
        ctx.setLineDash([]);

        ctx.strokeStyle = '#30363d';
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 28);
        ctx.lineTo(w - pad, hgt - 28);
        ctx.stroke();

        ctx.fillStyle = '#8b949e';
        ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
        ctx.fillText('шум ' + sigma.toFixed(2), 6, 16);
      }, [sigma], 45);

      const btn = (v, text) => h('button', {
        key: String(v),
        onClick: () => { setSigma(v); reset(); },
        style: Object.assign({}, S.btn, sigma === v ? S.btnOn : null),
      }, text);

      const base = B / Math.sqrt(3);
      const growth = ui.m / B;
      const range = ui.sd / base;

      return h('div', null,
        h('div', { style: S.btns },
          btn(0.1, 'тихо'),
          btn(0.25, 'мало'),
          btn(0.4, 'оптимум'),
          btn(0.8, 'много'),
          btn(1.2, 'хаос')),
        h('div', { style: S.stats },
          h('span', { style: S.warn }, 'рост ', h('b', null, growth.toFixed(2))),
          h('span', { style: S.good }, 'диапазон ', h('b', null, range.toFixed(2))),
          h('span', { style: S.dim }, 'произв. ', h('b', null, (growth * range).toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 13: the matching law ----------
    function Panel13() {
      // Measured optima: (mu, best sigma, alpha)
      const data = [
        { mu: 0.02, sigma: 0.25, alpha: 0.64 },
        { mu: 0.05, sigma: 0.40, alpha: 0.62 },
        { mu: 0.10, sigma: 0.50, alpha: 0.80 },
        { mu: 0.20, sigma: 0.80, alpha: 0.62 },
      ];
      const [sel, setSel] = useState(0);
      const d = data[sel];

      const B = 3, N = 500;
      const st = useRef({ pop: Array.from({ length: N }, () => gauss() * 0.5) });
      const [ui, setUi] = useState({ m: 0, sd: 0 });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () => gauss() * 0.5);
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        for (let k = 0; k < 2; k++) {
          for (let i = 0; i < pop.length; i++) {
            const v = pop[i] + d.mu + d.sigma * gauss();
            const Q = 4 * B;
            pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
          }
        }
        const m = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / pop.length);
        setUi({ m, sd });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 56;
        const lo = -B, hi = B;

        const bins = 22;
        const h = new Array(bins).fill(0);
        for (const v of pop) {
          let i = Math.floor((v - lo) / (hi - lo) * bins);
          i = Math.max(0, Math.min(bins - 1, i));
          h[i]++;
        }
        const mx = Math.max(...h, 1);
        const bw = plotW / bins;
        for (let i = 0; i < bins; i++) {
          const bh = h[i] / mx * plotH;
          ctx.fillStyle = '#3fb950';
          ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
          ctx.fillRect(pad + i * bw, hgt - 28 - bh, Math.max(1, bw - 1), bh);
        }
        ctx.globalAlpha = 1;

        const px = pad + (m - lo) / (hi - lo) * plotW;
        ctx.strokeStyle = '#f85149';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(px, 14);
        ctx.lineTo(px, hgt - 28);
        ctx.stroke();

        ctx.strokeStyle = '#f85149';
        ctx.setLineDash([3, 3]);
        ctx.lineWidth = 1;
        for (const b of [lo, hi]) {
          const wx = pad + (b - lo) / (hi - lo) * plotW;
          ctx.beginPath();
          ctx.moveTo(wx, 14);
          ctx.lineTo(wx, hgt - 28);
          ctx.stroke();
        }
        ctx.setLineDash([]);

        ctx.strokeStyle = '#30363d';
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 28);
        ctx.lineTo(w - pad, hgt - 28);
        ctx.stroke();

        ctx.fillStyle = '#8b949e';
        ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
        ctx.fillText('рост ' + d.mu.toFixed(2) + '  шум ' + d.sigma.toFixed(2) + '  α ' + d.alpha.toFixed(2), 6, 16);
      }, [sel], 45);

      const base = B / Math.sqrt(3);
      const growth = ui.m / B;
      const range = ui.sd / base;

      return h('div', null,
        h('div', { style: S.btns },
          data.map((dd, i) => h('button', {
            key: String(dd.mu),
            onClick: () => { setSel(i); reset(); },
            style: Object.assign({}, S.btn, sel === i ? S.btnOn : null),
          }, 'μ=' + dd.mu.toFixed(2)))),
        h('div', { style: S.stats },
          h('span', { style: S.dim }, 'σ ', h('b', null, d.sigma.toFixed(2))),
          h('span', { style: S.warn }, 'рост ', h('b', null, growth.toFixed(2))),
          h('span', { style: S.good }, 'диапазон ', h('b', null, range.toFixed(2))),
          h('span', { style: S.dim }, 'α ', h('b', null, d.alpha.toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 14: a growing child needs a tracking room ----------
    function Panel14() {
      const [tracking, setTracking] = useState(true);
      const B = 3, N = 500;
      const MU0 = 0.02, MU1 = 0.20, ALPHA = 0.65;
      const sigmaFor = (mu) => Math.sqrt(2 * mu / ALPHA);

      const st = useRef({
        pop: Array.from({ length: N }, () => gauss() * 0.5),
        t: 0,
        sigma: sigmaFor(MU0),
      });
      const [ui, setUi] = useState({ m: 0, sd: 0, mu: MU0, sigma: 0 });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () => gauss() * 0.5);
        st.current.t = 0;
        st.current.sigma = sigmaFor(MU0);
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        s.t += 1;
        const frac = (s.t % 400) / 400;
        const mu = MU0 + (MU1 - MU0) * frac;

        if (tracking) {
          const target = sigmaFor(mu);
          s.sigma = s.sigma + (target - s.sigma) / 20;
        } else {
          s.sigma = sigmaFor(MU0);
        }
        const sigma = s.sigma;

        for (let i = 0; i < pop.length; i++) {
          const v = pop[i] + mu + sigma * gauss();
          const Q = 4 * B;
          pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
        }
        const m = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / pop.length);
        setUi({ m, sd, mu, sigma });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 56;
        const lo = -B, hi = B;

        const bins = 22;
        const h = new Array(bins).fill(0);
        for (const v of pop) {
          let i = Math.floor((v - lo) / (hi - lo) * bins);
          i = Math.max(0, Math.min(bins - 1, i));
          h[i]++;
        }
        const mx = Math.max(...h, 1);
        const bw = plotW / bins;
        for (let i = 0; i < bins; i++) {
          const bh = h[i] / mx * plotH;
          ctx.fillStyle = tracking ? '#3fb950' : '#f85149';
          ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
          ctx.fillRect(pad + i * bw, hgt - 28 - bh, Math.max(1, bw - 1), bh);
        }
        ctx.globalAlpha = 1;

        const px = pad + (m - lo) / (hi - lo) * plotW;
        ctx.strokeStyle = '#d29922';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(px, 14);
        ctx.lineTo(px, hgt - 28);
        ctx.stroke();

        ctx.strokeStyle = '#f85149';
        ctx.setLineDash([3, 3]);
        ctx.lineWidth = 1;
        for (const b of [lo, hi]) {
          const wx = pad + (b - lo) / (hi - lo) * plotW;
          ctx.beginPath();
          ctx.moveTo(wx, 14);
          ctx.lineTo(wx, hgt - 28);
          ctx.stroke();
        }
        ctx.setLineDash([]);

        ctx.strokeStyle = '#30363d';
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 28);
        ctx.lineTo(w - pad, hgt - 28);
        ctx.stroke();

        ctx.fillStyle = '#8b949e';
        ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
        ctx.fillText((tracking ? 'следит' : 'застыла') + '  μ ' + mu.toFixed(3) + '  σ ' + sigma.toFixed(2), 6, 16);
      }, [tracking], 45);

      const base = B / Math.sqrt(3);
      const growth = ui.m / B;
      const range = ui.sd / base;

      return h('div', null,
        h('div', { style: S.btns },
          h('button', {
            key: 'track',
            onClick: () => { setTracking(true); reset(); },
            style: Object.assign({}, S.btn, tracking ? S.btnOn : null),
          }, 'комната следит'),
          h('button', {
            key: 'frozen',
            onClick: () => { setTracking(false); reset(); },
            style: Object.assign({}, S.btn, !tracking ? S.btnOn : null),
          }, 'комната застыла')),
        h('div', { style: S.stats },
          h('span', { style: S.warn }, 'рост ', h('b', null, growth.toFixed(2))),
          h('span', { style: S.good }, 'диапазон ', h('b', null, range.toFixed(2))),
          h('span', { style: S.dim }, 'произв. ', h('b', null, (growth * range).toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 15: box vs ball, the shape of the room ----------
    function Panel15() {
      const [shape, setShape] = useState('box');
      const [d, setD] = useState(4);
      const B = 3, MU = 0.05, SIG = 0.4, N = 400;

      const st = useRef({
        pop: Array.from({ length: N }, () =>
          Array.from({ length: 8 }, () => gauss() * 0.5)),
      });
      const [ui, setUi] = useState({ sd: 0 });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () =>
          Array.from({ length: 8 }, () => gauss() * 0.5));
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        for (let k = 0; k < 2; k++) {
          for (let i = 0; i < pop.length; i++) {
            const p = pop[i];
            if (shape === 'box') {
              for (let j = 0; j < d; j++) {
                const v = p[j] + MU + SIG * gauss();
                const Q = 4 * B;
                p[j] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
              }
            } else {
              for (let j = 0; j < d; j++) p[j] += MU + SIG * gauss();
              let r = 0;
              for (let j = 0; j < d; j++) r += p[j] * p[j];
              r = Math.sqrt(r);
              if (r > B) {
                const sc = (2 * B - r) / r;
                for (let j = 0; j < d; j++) p[j] *= sc;
              }
            }
          }
        }
        // per-trait spread over d traits
        let tot = 0;
        for (let j = 0; j < d; j++) {
          const m = pop.reduce((a, p) => a + p[j], 0) / pop.length;
          tot += pop.reduce((a, p) => a + (p[j] - m) ** 2, 0) / pop.length;
        }
        const sd = Math.sqrt(tot / d);
        setUi({ sd });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 56;
        const lo = -B, hi = B;

        // show first two traits as a scatter
        const cx = pad + plotW / 2, cy = 14 + plotH / 2;
        const R = Math.min(plotW, plotH) / 2 - 6;
        const sc = R / B;

        // room outline
        ctx.strokeStyle = '#f85149';
        ctx.setLineDash([4, 3]);
        ctx.lineWidth = 1.5;
        if (shape === 'box') {
          ctx.strokeRect(cx - R, cy - R, 2 * R, 2 * R);
        } else {
          ctx.beginPath();
          ctx.arc(cx, cy, R, 0, 7);
          ctx.stroke();
        }
        ctx.setLineDash([]);

        // points (first two traits)
        for (const p of pop) {
          ctx.fillStyle = shape === 'box' ? '#3fb950' : '#d29922';
          ctx.globalAlpha = 0.5;
          ctx.beginPath();
          ctx.arc(cx + p[0] * sc, cy - p[1] * sc, 1.6, 0, 7);
          ctx.fill();
        }
        ctx.globalAlpha = 1;

        ctx.fillStyle = '#8b949e';
        ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
        ctx.fillText((shape === 'box' ? 'куб' : 'шар') + '  d=' + d, 6, 16);
      }, [shape, d], 45);

      const btn = (v, text) => h('button', {
        key: String(v),
        onClick: () => { setD(v); reset(); },
        style: Object.assign({}, S.btn, d === v ? S.btnOn : null),
      }, text);

      const base = B / Math.sqrt(3);

      return h('div', null,
        h('div', { style: S.btns },
          h('button', {
            key: 'box',
            onClick: () => { setShape('box'); reset(); },
            style: Object.assign({}, S.btn, shape === 'box' ? S.btnOn : null),
          }, 'куб (по черте)'),
          h('button', {
            key: 'ball',
            onClick: () => { setShape('ball'); reset(); },
            style: Object.assign({}, S.btn, shape === 'ball' ? S.btnOn : null),
          }, 'шар (весь ребёнок)')),
        h('div', { style: S.btns }, btn(1, 'd=1'), btn(2, 'd=2'), btn(4, 'd=4'), btn(8, 'd=8')),
        h('div', { style: S.stats },
          h('span', { style: shape === 'box' ? S.good : S.bad }, 'разброс черты ', h('b', null, ui.sd.toFixed(3))),
          h('span', { style: S.dim }, 'полный ', h('b', null, base.toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 16: the budget law ----------
    function Panel16() {
      const [alloc, setAlloc] = useState([3, 3, 3, 3]);
      const TOTAL = 12, MU = 0.05, SIG = 0.4, N = 400;
      const d = 4;

      const st = useRef({
        pop: Array.from({ length: N }, () =>
          Array.from({ length: d }, () => gauss() * 0.5)),
      });
      const [ui, setUi] = useState({ tot: 0, sds: [0, 0, 0, 0] });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () =>
          Array.from({ length: d }, () => gauss() * 0.5));
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        for (let k = 0; k < 2; k++) {
          for (let i = 0; i < pop.length; i++) {
            const p = pop[i];
            for (let j = 0; j < d; j++) {
              const B = Math.max(0.02, alloc[j]);
              const v = p[j] + MU + SIG * gauss();
              const Q = 4 * B;
              p[j] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
            }
          }
        }
        let tot = 0;
        const sds = [];
        for (let j = 0; j < d; j++) {
          const m = pop.reduce((a, p) => a + p[j], 0) / pop.length;
          const v = pop.reduce((a, p) => a + (p[j] - m) ** 2, 0) / pop.length;
          tot += v;
          sds.push(Math.sqrt(v));
        }
        setUi({ tot, sds });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 50;

        // four mini histograms, one per trait
        const cellW = plotW / d;
        for (let j = 0; j < d; j++) {
          const B = Math.max(0.02, alloc[j]);
          const x0 = pad + j * cellW;
          const bins = 14;
          const h = new Array(bins).fill(0);
          for (const p of pop) {
            let i = Math.floor((p[j] + B) / (2 * B) * bins);
            i = Math.max(0, Math.min(bins - 1, i));
            h[i]++;
          }
          const mx = Math.max(...h, 1);
          const bw = (cellW - 8) / bins;
          for (let i = 0; i < bins; i++) {
            const bh = h[i] / mx * plotH;
            ctx.fillStyle = alloc[j] >= 3 ? '#3fb950' : '#f85149';
            ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
            ctx.fillRect(x0 + 4 + i * bw, hgt - 26 - bh, Math.max(1, bw - 1), bh);
          }
          ctx.globalAlpha = 1;
          ctx.fillStyle = '#8b949e';
          ctx.font = '9px ui-monospace,SFMono-Regular,Consolas,monospace';
          ctx.fillText('B=' + B.toFixed(1), x0 + 4, 14);
          ctx.fillText('sd ' + sds[j].toFixed(2), x0 + 4, 26);
        }

        ctx.strokeStyle = '#30363d';
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 26);
        ctx.lineTo(w - pad, hgt - 26);
        ctx.stroke();
      }, [alloc], 45);

      const presets = [
        ['равно', [3, 3, 3, 3]],
        ['скос', [6, 3, 2, 1]],
        ['сильно', [9, 1, 1, 1]],
        ['одна', [12, 0.02, 0.02, 0.02]],
      ];

      return h('div', null,
        h('div', { style: S.btns },
          presets.map(([label, a]) => h('button', {
            key: label,
            onClick: () => { setAlloc(a); reset(); },
            style: Object.assign({}, S.btn,
              JSON.stringify(alloc) === JSON.stringify(a) ? S.btnOn : null),
          }, label))),
        h('div', { style: S.stats },
          h('span', { style: S.dim }, 'сумма ', h('b', null, '12')),
          h('span', { style: S.good }, 'общий разброс ', h('b', null, ui.tot.toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 17: effort trade-off ----------
    function Panel17() {
      const [conc, setConc] = useState(0);
      const d = 4, SIG = 0.4, B = 3, N = 400;

      // effort split from concentration
      const raw = Array.from({ length: d }, (_, k) => Math.exp(-conc * k * 2));
      const tot = raw.reduce((a, b) => a + b, 0);
      const effort = raw.map(x => x / tot);
      const mu = effort.map(e => 0.2 * e);

      const st = useRef({
        pop: Array.from({ length: N }, () =>
          Array.from({ length: d }, () => gauss() * 0.5)),
      });
      const [ui, setUi] = useState({ g: 0, s: 0 });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () =>
          Array.from({ length: d }, () => gauss() * 0.5));
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        for (let k = 0; k < 2; k++) {
          for (let i = 0; i < pop.length; i++) {
            const p = pop[i];
            for (let j = 0; j < d; j++) {
              const v = p[j] + mu[j] + SIG * gauss();
              const Q = 4 * B;
              p[j] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
            }
          }
        }
        let sumMean = 0, sumVar = 0;
        const sds = [];
        for (let j = 0; j < d; j++) {
          const m = pop.reduce((a, p) => a + p[j], 0) / pop.length;
          const v = pop.reduce((a, p) => a + (p[j] - m) ** 2, 0) / pop.length;
          sumMean += m;
          sumVar += v;
          sds.push(Math.sqrt(v));
        }
        setUi({ g: sumMean, s: sumVar });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 50;

        const cellW = plotW / d;
        for (let j = 0; j < d; j++) {
          const x0 = pad + j * cellW;
          const bins = 14;
          const h = new Array(bins).fill(0);
          for (const p of pop) {
            let i = Math.floor((p[j] + B) / (2 * B) * bins);
            i = Math.max(0, Math.min(bins - 1, i));
            h[i]++;
          }
          const mx = Math.max(...h, 1);
          const bw = (cellW - 8) / bins;
          for (let i = 0; i < bins; i++) {
            const bh = h[i] / mx * plotH;
            ctx.fillStyle = effort[j] > 0.2 ? '#3fb950' : '#8b949e';
            ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
            ctx.fillRect(x0 + 4 + i * bw, hgt - 26 - bh, Math.max(1, bw - 1), bh);
          }
          ctx.globalAlpha = 1;
          ctx.fillStyle = '#8b949e';
          ctx.font = '9px ui-monospace,SFMono-Regular,Consolas,monospace';
          ctx.fillText('e=' + effort[j].toFixed(2), x0 + 4, 14);
          ctx.fillText('sd ' + sds[j].toFixed(2), x0 + 4, 26);
        }

        ctx.strokeStyle = '#30363d';
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 26);
        ctx.lineTo(w - pad, hgt - 26);
        ctx.stroke();
      }, [conc], 45);

      const btn = (v, text) => h('button', {
        key: String(v),
        onClick: () => { setConc(v); reset(); },
        style: Object.assign({}, S.btn, conc === v ? S.btnOn : null),
      }, text);

      return h('div', null,
        h('div', { style: S.btns },
          btn(0, 'равно'),
          btn(0.3, 'скос'),
          btn(0.8, 'сильно'),
          btn(2.0, 'одна')),
        h('div', { style: S.stats },
          h('span', { style: S.warn }, 'рост ', h('b', null, ui.g.toFixed(2))),
          h('span', { style: S.good }, 'разброс ', h('b', null, ui.s.toFixed(2))),
          h('span', { style: S.dim }, 'произв. ', h('b', null, (ui.g * ui.s).toFixed(1)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 18: the child as chooser ----------
    function Panel18() {
      const [mode, setMode] = useState('passive');
      const B = 3, SIG = 0.4, N = 500;
      const base = B / Math.sqrt(3);

      const st = useRef({ pop: Array.from({ length: N }, () => gauss() * 0.5) });
      const [ui, setUi] = useState({ m: 0, sd: 0 });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () => gauss() * 0.5);
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        const m0 = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd0 = Math.sqrt(pop.reduce((a, b) => a + (b - m0) ** 2, 0) / pop.length);

        let mu;
        if (mode === 'passive') mu = 0.05;
        else if (mode === 'grower') mu = m0 > B - 2 * sd0 ? 0.01 : 0.08;
        else if (mode === 'balancer') mu = sd0 > 0.3 * base ? 0.06 : 0.02;
        else mu = m0 > 0 ? -0.02 : 0.02;

        for (let i = 0; i < pop.length; i++) {
          const v = pop[i] + mu + SIG * gauss();
          const Q = 4 * B;
          pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
        }
        const m = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / pop.length);
        setUi({ m, sd });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 56;
        const lo = -B, hi = B;

        const bins = 22;
        const h = new Array(bins).fill(0);
        for (const v of pop) {
          let i = Math.floor((v - lo) / (hi - lo) * bins);
          i = Math.max(0, Math.min(bins - 1, i));
          h[i]++;
        }
        const mx = Math.max(...h, 1);
        const bw = plotW / bins;
        const col = mode === 'balancer' ? '#3fb950' :
                    mode === 'grower' ? '#d29922' :
                    mode === 'avoider' ? '#8b949e' : '#58a6ff';
        for (let i = 0; i < bins; i++) {
          const bh = h[i] / mx * plotH;
          ctx.fillStyle = col;
          ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
          ctx.fillRect(pad + i * bw, hgt - 28 - bh, Math.max(1, bw - 1), bh);
        }
        ctx.globalAlpha = 1;

        const px = pad + (m - lo) / (hi - lo) * plotW;
        ctx.strokeStyle = '#f85149';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(px, 14);
        ctx.lineTo(px, hgt - 28);
        ctx.stroke();

        ctx.strokeStyle = '#f85149';
        ctx.setLineDash([3, 3]);
        ctx.lineWidth = 1;
        for (const b of [lo, hi]) {
          const wx = pad + (b - lo) / (hi - lo) * plotW;
          ctx.beginPath();
          ctx.moveTo(wx, 14);
          ctx.lineTo(wx, hgt - 28);
          ctx.stroke();
        }
        ctx.setLineDash([]);

        ctx.strokeStyle = '#30363d';
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 28);
        ctx.lineTo(w - pad, hgt - 28);
        ctx.stroke();

        ctx.fillStyle = '#8b949e';
        ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
        ctx.fillText(mode + '  μ=' + mu.toFixed(2), 6, 16);
      }, [mode], 45);

      const btn = (m, text) => h('button', {
        key: m,
        onClick: () => { setMode(m); reset(); },
        style: Object.assign({}, S.btn, mode === m ? S.btnOn : null),
      }, text);

      const growth = ui.m / B;
      const range = ui.sd / base;

      return h('div', null,
        h('div', { style: S.btns },
          btn('passive', 'только толкают'),
          btn('balancer', 'балансирует'),
          btn('grower', 'растёт'),
          btn('avoider', 'избегает')),
        h('div', { style: S.stats },
          h('span', { style: S.warn }, 'рост ', h('b', null, growth.toFixed(2))),
          h('span', { style: S.good }, 'диапазон ', h('b', null, range.toFixed(2))),
          h('span', { style: S.dim }, 'произв. ', h('b', null, (growth * range).toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 19: other children ----------
    function Panel19() {
      const [kappa, setKappa] = useState(0);
      const B = 3, SIG = 0.4, MU = 0.05, N = 400;
      const base = B / Math.sqrt(3);

      const st = useRef({ pop: Array.from({ length: N }, () => gauss() * 0.5) });
      const [ui, setUi] = useState({ m: 0, sd: 0 });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () => gauss() * 0.5);
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        const mean = pop.reduce((a, b) => a + b, 0) / pop.length;

        for (let i = 0; i < pop.length; i++) {
          const pull = kappa * (mean - pop[i]);
          const v = pop[i] + MU + pull + SIG * gauss();
          const Q = 4 * B;
          pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
        }
        const m = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / pop.length);
        setUi({ m, sd });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 56;
        const lo = -B, hi = B;

        const bins = 24;
        const h = new Array(bins).fill(0);
        for (const v of pop) {
          let i = Math.floor((v - lo) / (hi - lo) * bins);
          i = Math.max(0, Math.min(bins - 1, i));
          h[i]++;
        }
        const mx = Math.max(...h, 1);
        const bw = plotW / bins;
        const col = kappa < 0 ? '#d29922' : kappa > 0 ? '#f85149' : '#3fb950';
        for (let i = 0; i < bins; i++) {
          const bh = h[i] / mx * plotH;
          ctx.fillStyle = col;
          ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
          ctx.fillRect(pad + i * bw, hgt - 28 - bh, Math.max(1, bw - 1), bh);
        }
        ctx.globalAlpha = 1;

        const px = pad + (m - lo) / (hi - lo) * plotW;
        ctx.strokeStyle = '#58a6ff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(px, 14);
        ctx.lineTo(px, hgt - 28);
        ctx.stroke();

        ctx.strokeStyle = '#f85149';
        ctx.setLineDash([3, 3]);
        ctx.lineWidth = 1;
        for (const b of [lo, hi]) {
          const wx = pad + (b - lo) / (hi - lo) * plotW;
          ctx.beginPath();
          ctx.moveTo(wx, 14);
          ctx.lineTo(wx, hgt - 28);
          ctx.stroke();
        }
        ctx.setLineDash([]);

        ctx.strokeStyle = '#30363d';
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 28);
        ctx.lineTo(w - pad, hgt - 28);
        ctx.stroke();

        ctx.fillStyle = '#8b949e';
        ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
        const lbl = kappa < 0 ? 'отталкивание' : kappa > 0 ? 'подражание' : 'независимость';
        ctx.fillText(lbl + '  κ=' + kappa.toFixed(1), 6, 16);
      }, [kappa], 45);

      const btn = (v, text) => h('button', {
        key: String(v),
        onClick: () => { setKappa(v); reset(); },
        style: Object.assign({}, S.btn, kappa === v ? S.btnOn : null),
      }, text);

      const growth = ui.m / B;
      const range = ui.sd / base;

      return h('div', null,
        h('div', { style: S.btns },
          btn(-0.2, 'отталкивание'),
          btn(0, 'независимость'),
          btn(0.1, 'слабое'),
          btn(0.3, 'среднее'),
          btn(0.9, 'сильное')),
        h('div', { style: S.stats },
          h('span', { style: S.warn }, 'рост ', h('b', null, growth.toFixed(2))),
          h('span', { style: S.good }, 'диапазон ', h('b', null, range.toFixed(2))),
          h('span', { style: S.dim }, 'произв. ', h('b', null, (growth * range).toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- panel 20: every help narrows ----------
    function Panel20() {
      const [mode, setMode] = useState('none');
      const B = 3, MU = 0.05, N = 400;
      const base = B / Math.sqrt(3);

      const st = useRef({
        pop: Array.from({ length: N }, () => gauss() * 0.5),
        K: 0,
      });
      const [ui, setUi] = useState({ m: 0, sd: 0 });

      const reset = useCallback(() => {
        st.current.pop = Array.from({ length: N }, () => gauss() * 0.5);
        st.current.K = 0;
      }, []);

      const ref = useCanvas((ctx, w, hgt) => {
        const s = st.current;
        const pop = s.pop;
        const mean = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd0 = Math.sqrt(pop.reduce((a, b) => a + (b - mean) ** 2, 0) / pop.length);

        s.K = s.K * 0.999 + (mode === 'none' ? 0 : 1) * sd0 * 0.001;

        let sigma = 0.4;
        let mu = MU;
        if (mode === 'copy') {
          // copying: pull toward the mean
          for (let i = 0; i < pop.length; i++) {
            pop[i] = pop[i] + 0.1 * (mean - pop[i]);
          }
        } else if (mode === 'teach-noise') {
          sigma = 0.4 * Math.exp(-s.K);
        } else if (mode === 'teach-drift') {
          mu = MU + s.K * 0.5;
        }

        for (let i = 0; i < pop.length; i++) {
          const v = pop[i] + mu + sigma * gauss();
          const Q = 4 * B;
          pop[i] = B - Math.abs((((v + B) % Q + Q) % Q) - 2 * B);
        }
        const m = pop.reduce((a, b) => a + b, 0) / pop.length;
        const sd = Math.sqrt(pop.reduce((a, b) => a + (b - m) ** 2, 0) / pop.length);
        setUi({ m, sd });

        ctx.clearRect(0, 0, w, hgt);
        const pad = 26, plotW = w - pad * 2, plotH = hgt - 56;
        const lo = -B, hi = B;

        const bins = 24;
        const h = new Array(bins).fill(0);
        for (const v of pop) {
          let i = Math.floor((v - lo) / (hi - lo) * bins);
          i = Math.max(0, Math.min(bins - 1, i));
          h[i]++;
        }
        const mx = Math.max(...h, 1);
        const bw = plotW / bins;
        const col = mode === 'none' ? '#3fb950' : '#f85149';
        for (let i = 0; i < bins; i++) {
          const bh = h[i] / mx * plotH;
          ctx.fillStyle = col;
          ctx.globalAlpha = 0.35 + 0.6 * (h[i] / mx);
          ctx.fillRect(pad + i * bw, hgt - 28 - bh, Math.max(1, bw - 1), bh);
        }
        ctx.globalAlpha = 1;

        const px = pad + (m - lo) / (hi - lo) * plotW;
        ctx.strokeStyle = '#58a6ff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(px, 14);
        ctx.lineTo(px, hgt - 28);
        ctx.stroke();

        ctx.strokeStyle = '#f85149';
        ctx.setLineDash([3, 3]);
        ctx.lineWidth = 1;
        for (const b of [lo, hi]) {
          const wx = pad + (b - lo) / (hi - lo) * plotW;
          ctx.beginPath();
          ctx.moveTo(wx, 14);
          ctx.lineTo(wx, hgt - 28);
          ctx.stroke();
        }
        ctx.setLineDash([]);

        ctx.strokeStyle = '#30363d';
        ctx.beginPath();
        ctx.moveTo(pad, hgt - 28);
        ctx.lineTo(w - pad, hgt - 28);
        ctx.stroke();

        ctx.fillStyle = '#8b949e';
        ctx.font = '10px ui-monospace,SFMono-Regular,Consolas,monospace';
        const labels = {
          none: 'никто не помогает',
          copy: 'копирование',
          'teach-noise': 'обучение (снижает шум)',
          'teach-drift': 'обучение (поднимает)',
        };
        ctx.fillText(labels[mode], 6, 16);
      }, [mode], 45);

      const btn = (m, text) => h('button', {
        key: m,
        onClick: () => { setMode(m); reset(); },
        style: Object.assign({}, S.btn, mode === m ? S.btnOn : null),
      }, text);

      const growth = ui.m / B;
      const range = ui.sd / base;

      return h('div', null,
        h('div', { style: S.btns },
          btn('none', 'никто'),
          btn('copy', 'копирование'),
          btn('teach-noise', 'обучение'),
          btn('teach-drift', 'подъём')),
        h('div', { style: S.stats },
          h('span', { style: S.warn }, 'рост ', h('b', null, growth.toFixed(2))),
          h('span', { style: S.good }, 'диапазон ', h('b', null, range.toFixed(2))),
          h('span', { style: S.dim }, 'произв. ', h('b', null, (growth * range).toFixed(2)))),
        h('canvas', { ref, style: S.canvas }));
    }

    // ---------- styles ----------
    const S = {
      root: {
        height: 'calc(100vh - 190px)',
        width: '100%',
        maxWidth: '100%',
        boxSizing: 'border-box',
        padding: '8px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        overflow: 'hidden',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        background: 'var(--dsh-bg, #0d1117)',
        color: 'var(--dsh-text, #e6edf3)',
      },
      tabs: {
        display: 'flex',
        gap: '4px',
        flex: '0 0 auto',
        flexWrap: 'nowrap',
        overflowX: 'auto',
      },
      tab: {
        background: 'transparent',
        border: '1px solid var(--dsh-border, #30363d)',
        borderRadius: '6px',
        color: 'var(--dsh-text-dim, #8b949e)',
        fontSize: '11px',
        padding: '4px 10px',
        cursor: 'pointer',
        whiteSpace: 'nowrap',
        fontFamily: 'inherit',
      },
      tabOn: {
        background: 'var(--dsh-accent, #58a6ff)',
        color: '#0d1117',
        borderColor: 'var(--dsh-accent, #58a6ff)',
        fontWeight: 600,
      },
      pair: {
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '10px',
        flex: '1 1 auto',
        minHeight: 0,
      },
      intro: {
        flex: '0 0 auto',
        fontSize: '11px', color: 'var(--dsh-text-dim, #8b949e)',
        lineHeight: 1.5, marginBottom: '12px',
        paddingBottom: '10px',
        borderBottom: '1px solid var(--dsh-border, #30363d)',
      },
      card: {
        border: '1px solid var(--dsh-border, #30363d)',
        borderRadius: '8px',
        padding: '10px 12px',
        background: 'var(--dsh-surface, #161b22)',
        minWidth: 0,
        minHeight: 0,
        overflow: 'hidden',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
      },
      cardTitle: {
        fontSize: '12px', fontWeight: 600,
        color: 'var(--dsh-accent, #58a6ff)', marginBottom: '3px',
      },
      cardText: {
        fontSize: '11px', color: 'var(--dsh-text-dim, #8b949e)',
        lineHeight: 1.45, marginBottom: '4px',
      },
      cardGive: {
        fontSize: '11px', color: '#3fb950',
        lineHeight: 1.45, marginBottom: '7px',
        paddingLeft: '8px', borderLeft: '2px solid #3fb950',
      },
      canvas: { display: 'block', width: '100%', maxWidth: '100%', flex: '1 1 auto', minHeight: 0, borderRadius: '5px', background: '#0a0e14' },
      stats: { display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '5px', alignItems: 'baseline' },
      btns: { display: 'flex', gap: '5px', marginBottom: '6px' },
      dim: { fontSize: '10px', color: 'var(--dsh-text-dim, #8b949e)' },
      good: { fontSize: '10px', color: '#3fb950' },
      bad: { fontSize: '10px', color: '#f85149' },
      warn: { fontSize: '10px', color: '#d29922' },
      btn: {
        background: '#21262d', color: '#e6edf3',
        border: '1px solid var(--dsh-border, #30363d)',
        borderRadius: '5px', padding: '2px 8px', fontSize: '10px', cursor: 'pointer',
      },
      btnOn: { background: '#58a6ff', color: '#0d1117', fontWeight: 600 },
    };

    const Card = (title, what, give, body) => h('div', { style: S.card, key: title },
      h('div', { style: S.cardTitle }, title),
      h('div', { style: S.cardText }, what),
      h('div', { style: S.cardGive }, give),
      body);

    // ---------- the tab body ----------
    function MediumViz() {
      const [tab, setTab] = useState(0);

      const groups = [
        {
          name: 'Модель',
          items: [
            ['1. Модель обнуляет себя',
              'Детерминированная мутация двигает всех вместе, потолок ловит всех в одной точке.',
              'Если клетки не могут стать разными — отбирать нечего. Жизнь требует различия.',
              h(Panel1)],
            ['2. Исправленная модель',
              'Независимый шум у каждой клетки + отражение от стены. Разброс выходит на B/√3.',
              'Разнообразие держится, только если вариация независима.',
              h(Panel2)],
          ],
        },
        {
          name: 'Отбор',
          items: [
            ['3. Отбор не сжимает разброс',
              'Взвешивание exp(k·x) на нормальной базе: среднее едет, дисперсия стоит.',
              'Отбор двигает среднее, но не сужает популяцию.',
              h(Panel3)],
            ['4. Стены стирают форму',
              'Окно сужается — Var/w² → 1/12 независимо от исходной формы.',
              'Среда, которая сужается, не отбирает — она обнуляет.',
              h(Panel4)],
          ],
        },
        {
          name: 'Совпадение',
          items: [
            ['5. Ребёнок не пассивен — он выбирает',
              'Тот, кто балансирует, обгоняет того, кого только толкают: рост 0.55 против 0.51.',
              'Выбор помогает — но немного. Комната задаёт границы, выбор двигает по ним.',
              h(Panel18)],
            ['6. Форма комнаты, а не размер',
              'Куб ограничивает каждую черту. Шар ограничивает всего ребёнка — и душит каждую черту с ростом d.',
              'Ребёнку с многими сторонами нельзя дать один общий бюджет. Нужен бюджет на каждую сторону.',
              h(Panel15)],
          ],
        },
        {
          name: 'Ребёнок',
          items: [
            ['7. Растущему ребёнку нужна меняющаяся комната',
              'Драйв растёт со временем. Застывшая комната даёт либо рост, либо диапазон.',
              'Требование не «постоянство» и не «отзывчивость», а совпадение во времени.',
              h(Panel14)],
            ['8. Рост и диапазон — враги',
              'Устойчивый рост прижимает к потолку. Плотность становится экспоненциальной: exp(αx), α = 2μ/σ².',
              'Чтобы расти, ребёнок тратит диапазон. Курс обмена задаёт α — отношение роста к шуму.',
              h(Panel11)],
          ],
        },
        {
          name: 'Другие',
          items: [
            ['9. Ребёнок не один',
              'Подражание поднимает рост, но уничтожает диапазон. Отталкивание — наоборот.',
              'Другие дети не нейтральны. В модели, где они только образец для копирования, они сужают ребёнка.',
              h(Panel19)],
            ['10. Любая помощь сужает',
              'Копирование, обучение, подъём — все снижают шум. А шум и есть источник диапазона.',
              'В этой модели быть облагодетельствованным = быть суженным. Ограничение модели, не жизни.',
              h(Panel20)],
          ],
        },
        {
          name: 'Среда',
          items: [
            ['11. Что происходит на самом деле',
              'Трассировка: каждый организм, каждый шаг. Где он, сколько у него, что он помнит, куда идёт.',
              'Сводка говорит «средняя энергия 0.7». Трассировка говорит, кто именно где. Это наблюдение, а не оценка.',
              h(Panel21)],
            ['12. Поле не рушится — расслаивается',
              'Клетка с k организмами приходит к c* = M - k*t/r. Пустая стоит на M, с одним — на M - t/r, с двумя — на нуле.',
              'Голод не распространяется по полю. Он остаётся там, где живут. Рядом может стоять полная клетка.',
              h(Panel22),
              h(Panel23)],
          ],
        },
        {
          name: 'Потолок',
          items: [
            ['9. Шум — не дефект, а инструмент',
              'Больше шума — меньше наклон α. Ребёнок растёт, сохраняя диапазон. Но среднее падает.',
              'Есть оптимум шума: слишком тихо — прижат к стене, слишком шумно — не растёт.',
              h(Panel12)],
            ['10. Шум — не дефект, а инструмент',
              'Больше шума — меньше наклон α. Ребёнок растёт, сохраняя диапазон. Но среднее падает.',
              'Есть оптимум шума: слишком тихо — прижат к стене, слишком шумно — не растёт.',
              h(Panel12)],
          ],
        },
      ];

      const g = groups[tab];

      return h('div', { style: S.root },
        h('div', { style: S.tabs },
          groups.map((grp, i) => h('button', {
            key: grp.name,
            onClick: () => setTab(i),
            style: Object.assign({}, S.tab, tab === i ? S.tabOn : null),
          }, grp.name))),
        h('div', { style: S.pair },
          g.items.map(([title, what, give, body]) =>
            h('div', { style: S.card, key: title },
              h('div', { style: S.cardTitle }, title),
              h('div', { style: S.cardText }, what),
              h('div', { style: S.cardGive }, give),
              body))));
    }

    return {
      inject: ['slots'],
      apply(ctx) {
        ctx.slots.inject('conversation.view', () => ctx.slots.register({
          name: 'conversation.view',
          id: 'medium-viz',
          order: 20,
          label: () => '\u0421\u0440\u0435\u0434\u0430 \u0436\u0438\u0437\u043d\u0438',
        }, MediumViz));
      },
    };
  },
});

// rev 2: force bundle revision change
