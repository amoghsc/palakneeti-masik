/* After Paged.js has paginated, walk every page and emit a flat list of
   positioned shapes (line-groups of text, images, filled rectangles) so the
   layout can be rebuilt as editable boxes in PowerPoint / Canva.          */
window.__extractLayout = function () {

  const PAGE_SEL = '.pagedjs_page';
  /* any filled element, rather than a hand-maintained list — otherwise new
     design elements (cover panels, rules, bars) silently vanish on export */
  const TEXT_SEL = 'p, h1, h2, h3, h4, li, b, .mail, .role, .bio, .logo-cap,'
                 + ' .url, .no, .pg, .folio, .toc-by, .runfoot, .bar, .foot';

  const isBold = el => {
    const w = getComputedStyle(el).fontWeight;
    return (+w >= 600) || w === 'bold';
  };

  /* flatten an element's text into characters, carrying style flags */
  function chars(el) {
    const out = [];
    const walk = (n, b, i, href) => {
      for (const c of n.childNodes) {
        if (c.nodeType === 3) {
          for (let k = 0; k < c.data.length; k++)
            out.push({ node: c, off: k, ch: c.data[k], b, i, href });
        } else if (c.nodeType === 1) {
          if (getComputedStyle(c).display === 'none') continue;
          const nb = b || c.tagName === 'STRONG' || c.tagName === 'B' || isBold(c);
          const ni = i || c.tagName === 'EM' || c.tagName === 'I';
          const nh = c.tagName === 'A' ? (c.getAttribute('href') || href) : href;
          walk(c, nb, ni, nh);
        }
      }
    };
    walk(el, isBold(el), false, null);
    return out;
  }

  /* split an element's characters into visual lines, then merge consecutive
     lines that share a left edge and width into one editable box           */
  function lineGroups(el) {
    const cs = chars(el);
    if (!cs.length) return [];
    const r = document.createRange();
    const lines = [];
    let cur = null;
    for (const c of cs) {
      let rect;
      try {
        r.setStart(c.node, c.off);
        r.setEnd(c.node, c.off + 1);
        rect = r.getBoundingClientRect();
      } catch (e) { continue; }
      if (!rect || (rect.width === 0 && rect.height === 0)) {
        if (cur) cur.cs.push(c);
        continue;
      }
      if (!cur || Math.abs(rect.top - cur.top) > 3) {
        cur = { top: rect.top, bottom: rect.bottom, left: rect.left,
                right: rect.right, cs: [c] };
        lines.push(cur);
      } else {
        cur.left = Math.min(cur.left, rect.left);
        cur.right = Math.max(cur.right, rect.right);
        cur.bottom = Math.max(cur.bottom, rect.bottom);
        cur.cs.push(c);
      }
    }
    if (!lines.length) return [];

    /* the usable measure of each line = the containing block's box, so that a
       paragraph flowing around a float splits into a narrow part and a wide
       part rather than one overlapping rectangle                            */
    const groups = [];
    let g = null;
    for (const ln of lines) {
      const L = Math.round(ln.left), R = Math.round(ln.right);
      /* a new box starts only when the left edge moves, or when the measure
         gets WIDER (i.e. we have flowed past the bottom of a float).  A short
         final line must not split off into a box of its own.               */
      if (g && Math.abs(L - g.L) <= 2
          && (ln.top - g.bottom) < (ln.bottom - ln.top) * 1.6
          && R <= g.Rmax + 40) {
        g.top = Math.min(g.top, ln.top);
        g.bottom = Math.max(g.bottom, ln.bottom);
        g.Rmax = Math.max(g.Rmax, R);
        g.cs = g.cs.concat(ln.cs);
        g.n++;
      } else {
        g = { L, top: ln.top, bottom: ln.bottom, Rmax: R, cs: ln.cs.slice(), n: 1 };
        groups.push(g);
      }
    }
    return groups;
  }

  function runsOf(cs) {
    const runs = [];
    for (const c of cs) {
      const last = runs[runs.length - 1];
      if (last && last.b === c.b && last.i === c.i && last.href === c.href)
        last.t += c.ch;
      else runs.push({ t: c.ch, b: c.b, i: c.i, href: c.href });
    }
    return runs.filter(r => r.t.trim() !== '' || runs.length === 1);
  }

  const out = [];
  document.querySelectorAll(PAGE_SEL).forEach((pg, pi) => {
    const pb = pg.getBoundingClientRect();
    const shapes = [];
    const rel = r => ({ x: r.left - pb.left, y: r.top - pb.top,
                        w: r.width, h: r.height });

    /* filled panels first, in DOM order, so they sit behind the text */
    pg.querySelectorAll('*').forEach(el => {
      const cn = typeof el.className === 'string' ? el.className : '';
      if (cn.indexOf('pagedjs') === 0) return;
      const st = getComputedStyle(el);
      const bg = st.backgroundColor;
      const filled = bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent';
      const bordered = ['Top', 'Bottom', 'Left', 'Right'].some(
        d => (parseFloat(st['border' + d + 'Width']) || 0) > 0);
      if (!filled && !bordered) return;
      if (st.display === 'none' || st.visibility === 'hidden') return;
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) return;
      if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
        shapes.push({ kind: 'rect', ...rel(r), fill: bg,
                      radius: parseFloat(st.borderTopLeftRadius) || 0,
                      round: st.borderRadius.includes('50%'),
                      opacity: parseFloat(st.opacity) });
      }
      const B = rel(r);
      const edges = [
        [parseFloat(st.borderTopWidth),    st.borderTopColor,
         B.x, B.y, B.w, parseFloat(st.borderTopWidth)],
        [parseFloat(st.borderBottomWidth), st.borderBottomColor,
         B.x, B.y + B.h - parseFloat(st.borderBottomWidth), B.w,
         parseFloat(st.borderBottomWidth)],
        [parseFloat(st.borderLeftWidth),   st.borderLeftColor,
         B.x, B.y, parseFloat(st.borderLeftWidth), B.h],
        [parseFloat(st.borderRightWidth),  st.borderRightColor,
         B.x + B.w - parseFloat(st.borderRightWidth), B.y,
         parseFloat(st.borderRightWidth), B.h],
      ];
      for (const [w, col, x, y, ew, eh] of edges) {
        if (!w || w <= 0 || !col || col === 'rgba(0, 0, 0, 0)') continue;
        shapes.push({ kind: 'rect', x: x, y: y, w: ew, h: eh,
                      fill: col, radius: 0, round: false, opacity: 1 });
      }
    });

    pg.querySelectorAll('img').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width < 1) return;
      const st = getComputedStyle(el);
      /* a rotated element's client rect is the axis-aligned bounding box, so
         take the laid-out size and centre it on that box instead */
      let deg = 0;
      const m = st.transform && st.transform.match(/^matrix\(([^)]+)\)/);
      if (m) {
        const [a, b] = m[1].split(',').map(parseFloat);
        deg = Math.round(Math.atan2(b, a) * 180 / Math.PI);
      }
      let box = rel(r);
      if (deg % 360 !== 0) {
        const w = el.offsetWidth || r.width, h = el.offsetHeight || r.height;
        box = { x: box.x + box.w / 2 - w / 2, y: box.y + box.h / 2 - h / 2,
                w: w, h: h };
      }
      const bw = parseFloat(st.borderTopWidth) || 0;
      shapes.push({ kind: 'img', ...box,
                    src: el.getAttribute('src'),
                    radius: parseFloat(st.borderTopLeftRadius) || 0,
                    circle: (st.borderRadius || '').includes('50%'),
                    edgeW: bw, edgeColor: bw ? st.borderTopColor : null,
                    rot: deg, opacity: parseFloat(st.opacity) });
    });

    pg.querySelectorAll(TEXT_SEL).forEach(el => {
      /* only leaf-ish text holders, to avoid emitting the same words twice */
      if (el.querySelector(TEXT_SEL)) return;
      if (!el.textContent.trim()) return;
      const st = getComputedStyle(el);
      if ((st.writingMode || '').startsWith('vertical')) {
        const r = el.getBoundingClientRect();
        shapes.push({
          kind: 'text', vert: true,
          x: r.left - pb.left, y: r.top - pb.top, w: r.width, h: r.height,
          runs: runsOf(chars(el)),
          size: parseFloat(st.fontSize),
          lh: parseFloat(st.lineHeight) || parseFloat(st.fontSize) * 1.2,
          color: st.color, align: 'left', lines: 1,
          spacing: parseFloat(st.letterSpacing) || 0,
          underline: (st.textDecorationLine || '').includes('underline'),
        });
        return;                       // forEach callback: return, not continue
      }
      for (const g of lineGroups(el)) {
        const runs = runsOf(g.cs);
        if (!runs.length) continue;
        shapes.push({
          kind: 'text',
          x: g.L - pb.left, y: g.top - pb.top,
          w: g.Rmax - g.L, h: g.bottom - g.top,
          runs,
          size: parseFloat(st.fontSize),
          lh: parseFloat(st.lineHeight) || parseFloat(st.fontSize) * 1.2,
          color: st.color, align: st.textAlign, lines: g.n,
          spacing: parseFloat(st.letterSpacing) || 0,
          underline: (st.textDecorationLine || '').includes('underline'),
        });
      }
    });

    /* guard against a text element that no selector happens to match:
       compare the words on the page with the words actually captured */
    const norm = t => (t || '').replace(/\s+/g, ' ').trim();
    const bag = t => norm(t).split(' ').filter(Boolean);
    const got = new Set();
    let all = '';
    for (const sh of shapes) {
      if (sh.kind !== 'text') continue;
      const t = sh.runs.map(r => r.t).join('');
      all += t + ' ';
      for (const w of bag(t)) got.add(w);
    }
    /* a word may legitimately be captured while joined to its neighbour, so
       fall back to a substring test with zero-width characters normalised */
    const squash = t => t.replace(/[\s\u200b\u200c\u200d\ufeff]+/g, '');
    const allSquashed = squash(all);
    const missing = [];
    /* innerText, not textContent: it separates block boxes and omits
       anything that is not actually rendered */
    for (const w of bag(pg.innerText)) {
      if (got.has(w) || allSquashed.includes(squash(w))) continue;
      if (!missing.includes(w)) missing.push(w);
    }
    out.push({ page: pi + 1, w: pb.width, h: pb.height, shapes,
               missing: missing.slice(0, 12) });
  });

  const pre = document.createElement('pre');
  pre.id = 'LAYOUT';
  pre.style.display = 'none';
  pre.textContent = 'LAYOUT' + JSON.stringify(out);
  document.body.appendChild(pre);
  document.title = 'EXTRACT_DONE';
};
