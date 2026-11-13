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
