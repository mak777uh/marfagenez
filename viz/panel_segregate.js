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

