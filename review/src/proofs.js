// ---------- Proofs: every claim as equations -> variables -> sources, re-run by analysis/validation/proofs.py ----------
// Data: #proofData (proofs.json: per claim the variables with the file each value was read from, the steps with their
// results, the comparison with the claim, upstream/downstream links and external SRC ids), #validData (status and
// reasons), #meshAudit (analysis/cfd3d/mesh_audit.py, with the build_mesh.py lines each sizing rule comes from).
// This file draws; it computes no reported number. Equations are a small TeX subset rendered to MathML.
const Proofs = (() => {
  const $ = s => document.querySelector(s), esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  const CHIP = { 'Verified': 'met', 'Partially Verified': 'risk', 'Unverified': 'open', 'Failed': 'fail' };
  const SRCST = { confirmed: ['met', 'Confirmed'], partially_confirmed: ['risk', 'Partly confirmed'], mismatch: ['fail', 'Mismatch'], unreachable: ['open', 'Site blocked'],
    not_found_on_page: ['open', 'Not found on page'], not_fetchable: ['open', 'Book or standard'] };
  let P = null, V = null, C = {}, tip = null;
  function load() { if (P) return true; const pe = document.getElementById('proofData'), ve = document.getElementById('validData'); if (!pe || !ve) return false;
    P = JSON.parse(pe.textContent); V = JSON.parse(ve.textContent); V.claims.forEach(c => { C[c.id] = c; }); return true; }

  // ---- numbers ----
  const sig = (x, n = 4) => { if (typeof x !== 'number' || !isFinite(x)) return esc(x); if (x === 0) return '0'; const a = Math.abs(x);
    if (a >= 1e5 || a < 1e-3) { const e = Math.floor(Math.log10(a)), m = x / 10 ** e; return `${+m.toPrecision(3)}×10<sup>${e}</sup>`; }
    return String(+x.toPrecision(n)); };
  const mn = x => { if (typeof x !== 'number' || !isFinite(x)) return '<mi>…</mi>'; const a = Math.abs(x);
    if (x !== 0 && (a >= 1e5 || a < 1e-3)) { const e = Math.floor(Math.log10(a)), m = x / 10 ** e; return `<mrow><mn>${+m.toPrecision(3)}</mn><mo>×</mo><msup><mn>10</mn><mn>${e}</mn></msup></mrow>`; }
    const s = String(+x.toPrecision(4)); return x < 0 ? `<mrow><mo>(</mo><mn>${s.replace('-', '−')}</mn><mo>)</mo></mrow>` : `<mn>${s}</mn>`; };

  // ---- TeX subset -> MathML. Variables are swapped for placeholders first (longest first, on symbol boundaries), so a
  // variable written as "L/D" or "C_{L,\max}" is one hoverable unit, or its number in the substituted line ----
  const GREEK = { rho: 'ρ', mu: 'μ', eta: 'η', pi: 'π', sigma: 'σ', delta: 'δ', Delta: 'Δ', omega: 'ω', alpha: 'α', tau: 'τ', theta: 'θ', lambda: 'λ', epsilon: 'ε', nu: 'ν', phi: 'φ', beta: 'β', gamma: 'γ', kappa: 'κ' };
  const OPS = { int: '∫', iint: '∬', le: '≤', ge: '≥', approx: '≈', to: '→', infty: '∞', cdot: '·', times: '×', sum: '∑' };   // rev 2026-11-03: claim equations
  const FN = ['max', 'min', 'ln', 'exp', 'cos', 'sin', 'log'];
  function bounded(s, t, rep) { let out = '', i = 0;
    while (i < s.length) { const k = s.indexOf(t, i); if (k < 0) { out += s.slice(i); break; }
      const b = k ? s[k - 1] : ' ', a = s[k + t.length] || ' ';
      const ok = !/[A-Za-z\\_]/.test(b) && !/[A-Za-z0-9_{]/.test(a) && !(b === '{' && s.slice(Math.max(0, k - 5), k).match(/\\v\{$/));
      out += s.slice(i, k) + (ok ? rep : t); i = k + t.length; }
    return out; }
  function mml(tex, ctx) {
    let s = tex;
    if (ctx) ctx.vars.map((v, i) => [v.tex, i]).filter(x => x[0]).sort((a, b) => b[0].length - a[0].length).forEach(([t, i]) => { s = bounded(s, t, `\\v{${i}}`); });
    let i = 0;
    const isNum = a => /^(<msup>|<msub>|<msubsup>)?(<mrow class="pf-n"|<mn)/.test(a);
    const seq = (stop, toRight) => { let out = '', last = false; while (i < s.length && !(stop && s[i] === '}') && !(toRight && s.startsWith('\\right', i))) { if (!stop && s[i] === '}') { i++; continue; } const a = atom(); if (!a) continue;
        if (a.startsWith('<mspace')) { out += a; continue; } const num = isNum(a); if (num && last) out += '<mo>×</mo>'; out += a; last = num || a === '<mo>)</mo>'; }
      return out; };
    const group = () => seq(true);
    const raw = () => { while (s[i] === ' ') i++; if (s[i] !== '{') return s[i++]; i++; let r = ''; while (i < s.length && s[i] !== '}') r += s[i++]; i++; return r; };
    const arg = () => { while (s[i] === ' ') i++; if (s[i] === '{') { i++; const g = group(); i++; return `<mrow>${g}</mrow>`; } return base(); };
    function atom() { let b = base(); if (!b) return '';
      for (;;) { if (s[i] === '_') { i++; const sub = arg(); if (s[i] === '^') { i++; b = `<msubsup>${b}${sub}${arg()}</msubsup>`; } else b = `<msub>${b}${sub}</msub>`; }
        else if (s[i] === '^') { i++; b = `<msup>${b}${arg()}</msup>`; } else return b; } }
    function base() { const c = s[i];
      if (c === undefined) return '';
      if (c === ' ') { i++; return ''; }
      if (c === '{') { i++; const g = group(); i++; return `<mrow>${g}</mrow>`; }
      if (c === '\\') { i++; let n = ''; while (i < s.length && /[A-Za-z]/.test(s[i])) n += s[i++];
        if (!n) { const ch = s[i++]; return ch === ',' || ch === ';' ? '<mspace width="0.18em"/>' : ch === ' ' ? '<mspace width="0.3em"/>' : `<mo>${esc(ch)}</mo>`; }
        if (n === 'frac' || n === 'tfrac') { const a = arg(); return `<mfrac>${a}${arg()}</mfrac>`; }
        if (n === 'sqrt') return `<msqrt>${arg()}</msqrt>`;
        if (n === 'left') { const d = s[i++], inner = seq(false, true); i += 6; const e = s[i++] || '';   // own mrow, so the delimiters stretch to the content
          return `<mrow><mo fence="true" stretchy="true">${esc(d)}</mo>${inner}<mo fence="true" stretchy="true">${esc(e)}</mo></mrow>`; }
        if (n === 'quad') return '<mspace width="1em"/>';
        if (n === 'text') return `<mtext>${esc(raw()).replace(/^ | $/g, ' ')}</mtext>`;
        if (n === 'mathrm') return `<mi mathvariant="normal">${esc(raw())}</mi>`;
        if (n === 'bar') return `<mover accent="true">${arg()}<mo>¯</mo></mover>`;
        if (n === 'v') { const k = +raw(), v = ctx.vars[k];
          return ctx.mode === 'num' && typeof v.value === 'number' ? `<mrow class="pf-n" data-i="${k}">${mn(v.value)}</mrow>` : `<mrow class="pf-v" data-i="${k}">${mml(v.tex)}</mrow>`; }
        if (GREEK[n]) return `<mi>${GREEK[n]}</mi>`;
        if (FN.includes(n)) return `<mi mathvariant="normal">${n}</mi>`;
        if (OPS[n]) return `<mo>${OPS[n]}</mo>`;
        return '';   // \left, \right and unknown commands draw nothing
      }
      if (/[0-9.]/.test(c)) { let n = ''; while (i < s.length && /[0-9.]/.test(s[i])) n += s[i++]; return `<mn>${n}</mn>`; }
      if (/[A-Za-z]/.test(c)) { i++; return `<mi>${c}</mi>`; }
      i++; return `<mo>${c === '-' ? '−' : esc(c)}</mo>`;
    }
    return seq(false); }
  const pct = (d, k = 2) => { const t = (+d).toFixed(k); return (/^-0\.0*$/.test(t) ? t.slice(1) : (d > 0 ? '+' : '') + t).replace('-', '−'); };
  const math = (inner, block) => `<math${block ? ' display="block"' : ''}>${inner}</math>`;
  // a claim's equation list: typeset where equations_tex.json has a form (proofs.json equation_tex), else the plain text
  const eqList = list => { if (!list || !list.length) return ''; load(); const T = (P && P.equation_tex) || {};
    return `<ul class="vm-eq">${list.map(e => { const t = T[e];
      if (!t) return `<li><code>${esc(e)}</code></li>`;
      return t.tex ? `<li>${math(mml(t.tex), true)}${t.note ? `<span class="pf-mute">${esc(t.note)}</span>` : ''}</li>` : `<li class="vm-eqt">${esc(t.note)}</li>`; }).join('')}</ul>`; };

  // ---- where a value comes from ----
  function origin(v) { const s = v.src || {}, bits = [];
    if (v.from_claim) { const l = v.link || {}, st = l.state === 'consistent' ? 'ok' : l.state === 'stale' ? 'bad' : 'n';
      bits.push(`<button type="button" class="pf-chip pf-${st}" data-claim="${esc(v.from_claim)}" title="${l.state === 'stale' ? `Stale: this input is ${sig(v.value)} but ${v.from_claim} now says ${sig(l.claim_value)}` : 'Result of ' + v.from_claim}">${esc(v.from_claim)}${l.state === 'stale' ? ' ≠' : ''}</button>`); }
    if (s.kind === 'file') bits.push(`<code>${esc(s.ref)}</code>`);
    else if (s.kind === 'checker') bits.push(`<code>${esc(s.ref.split(' ')[0])}</code> <span class="pf-mute">(read by the checker)</span>`);
    else if (s.kind === 'constant') bits.push(`<span class="pf-mute">${esc(s.ref)}</span>`);
    if (s.src_id) { const so = P.sources[s.src_id] || {}, k = SRCST[so.status] || ['open', so.status];
      bits.push(`<span class="pf-src" title="${esc(so.title || '')}"><span class="chip ${k[0]}">${esc(s.src_id)}</span></span>`); }
    return bits.join(' '); }

  // ---- "check it yourself": the proof as steps a student can follow with the repo open and a calculator ----
  function where(src) { if (!src) return '';
    if (src.kind === 'file') { const [f, path] = src.ref.split('#'); if (path) return `open <code>${esc(f)}</code> and follow ${path.split('.').map(k => `<b>${esc(k)}</b>`).join(' → ')}`;
      const m = /^(.*):(\d+)$/.exec(src.ref); return m ? `open <code>${esc(m[1])}</code> at line ${m[2]}` : `open <code>${esc(src.ref)}</code>`; }
    if (src.kind === 'checker') { const [f, k] = src.ref.split(' '); return `open <code>${esc(f)}</code>, claim ${esc((k || '').split('.inputs.')[0])}, input <b>${esc((k || '').split('.inputs.')[1] || '')}</b> (the checker read it from the evidence file)`; }
    if (src.kind === 'constant') return `a fixed value: ${esc(src.ref)}`;
    return ''; }
  function calcLine(expr, vals) {   // the step's own expression with the numbers put in, as you would type it into a calculator
    let e = expr; Object.keys(vals).sort((a, b) => b.length - a.length).forEach(k => { e = e.replace(new RegExp('(?<![A-Za-z_.])' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![A-Za-z0-9_])', 'g'), '(' + (+vals[k].toPrecision(6)) + ')'); });
    return e.replace(/math\.sqrt/g, 'sqrt').replace(/math\.pi/g, 'π').replace(/\*\*/g, '^').replace(/\(\((-?[\d.e+-]+)\)\)/g, '($1)').replace(/\((\d[\d.e+]*)\)/g, '$1'); }
  function guideHtml(id, p, c) {
    const run = `<code>py tools/vtol.py trace ${esc(id)}</code> (or option 3 in <code>VTOL.bat</code>) prints all of this in a terminal; <code>py tools/vtol.py prove ${esc(id)}</code> writes it as a one-page sheet.`;
    const ic = p.check || {}, icLine = ic.method ? `<li><b>Independent check.</b> ${esc(ic.method)}${ic.script ? `: run <code>py ${esc(ic.script.split('#')[0])}</code> and find <b>${esc(ic.script.split('#')[1] || id)}</b> in its printout` : ''}${ic.delta_pct != null ? `; it should differ from the claim by about ${(+ic.delta_pct).toFixed(1)} %` : ''}.</li>` : '';
    if (p.kind !== 'computed') {
      const ev = (p.evidence || []).map(e => `<li>Open <code>${esc(e.file)}</code> and look for: ${esc(e.what)}.</li>`).join('');
      return `<details class="pf-guide"><summary>Check it yourself</summary><ol>${ev}${icLine}<li>Compare what you found with the claim above and the reason for its status.</li></ol><p class="pf-mute">${run}</p></details>`; }
    const vals = {}; (p.vars || []).forEach(v => { if (typeof v.value === 'number') vals[v.sym] = v.value; });
    const inputs = (p.vars || []).map(v => `<li>${esc(v.desc)} (${math(mml(v.tex))}): ${where(v.src)}. You should read <b>${Array.isArray(v.value) ? v.value.length + ' items' : sig(v.value)}</b>${v.unit && v.unit !== '-' ? ' ' + esc(v.unit) : ''}${v.src && v.src.scaled ? ` (×${v.src.scaled} to convert units)` : ''}.</li>`).join('');
    const steps = (p.steps || []).map(st => { const line = calcLine(st.expr, vals); vals[st.out] = st.value;
      const how = /_vars|for/.test(st.expr) ? 'add up the input values listed above' : `type <code>${esc(line)}</code> into a calculator`;
      return `<li>${esc(st.desc || 'Compute')}: ${how}. You should get <b>${sig(st.value)}</b>${st.unit && st.unit !== '-' ? ' ' + esc(st.unit) : ''}.</li>`; }).join('');
    const r = p.result, rel = r.relation === 'ge' ? 'at least' : r.relation === 'le' ? 'at most' : `within ±${r.tol_pct} % of`;
    return `<details class="pf-guide"><summary>Check it yourself (about 5 minutes)</summary>
      <p><b>1. Read the inputs</b> from the repository:</p><ol>${inputs}</ol>
      <p><b>2. Do the arithmetic.</b></p><ol>${steps}</ol>
      <p><b>3. Compare.</b> The claim says <b>${sig(r.claim_value)}</b> ${esc(r.claim_units || '')}; your result should be ${rel} that number. ${r.reproduced === false ? 'It is not, which is why this claim is marked as it is.' : ''}</p>
      ${icLine ? `<p><b>4. The independent check</b> uses a different method on the same question:</p><ol>${icLine}</ol>` : ''}
      <p class="pf-mute">${run}</p></details>`; }

  // ---- the proof card ----
  function card(id) { if (!load()) return ''; const c = C[id], p = P.claims[id]; if (!c || !p) return `<p>No record for ${esc(id)}.</p>`;
    const ch = CHIP[c.status]; let body = '';
    if (p.kind === 'computed') { const r = p.result, vars = p.vars, prev = [];
      const steps = p.steps.map(st => { const lhs = st.tex.split('=')[0].trim(), rhs = st.tex.slice(st.tex.indexOf('=') + 1);
        const ctx = { vars: vars.concat(prev) }; const sym = mml(lhs) + '<mo>=</mo>' + mml(rhs, { ...ctx, mode: 'sym' });
        const num = '<mo>=</mo>' + mml(rhs, { ...ctx, mode: 'num' }) + `<mo>=</mo><mn class="pf-res">${sig(st.value)}</mn>` + (st.unit && st.unit !== '-' ? `<mspace width="0.3em"/><mi mathvariant="normal">${esc(st.unit)}</mi>` : '');
        prev.push({ tex: lhs, value: st.value, unit: st.unit, desc: st.desc, src: { kind: 'step' } });
        return `<div class="pf-step"><div class="pf-desc">${esc(st.desc || '')}</div>${math(sym, true)}${math(num, true)}</div>`; }).join('');
      const ok = r.reproduced, rel = r.relation === 'ge' ? 'must be at least the claim' : r.relation === 'le' ? 'must not exceed the claim' : `within ${r.tol_pct} %`;
      const verdict = ok === true ? `<span class="pf-ok">✓ Re-runs to ${sig(r.value)} ${esc(r.unit)}</span> against the claim's ${sig(r.claim_value)} ${esc(r.claim_units || '')} (Δ ${pct(r.delta_pct)} %, ${rel})`
        : ok === false ? `<span class="pf-bad">✗ Re-runs to ${sig(r.value)} ${esc(r.unit)}</span>, not the claim's ${sig(r.claim_value)} ${esc(r.claim_units || '')} (Δ ${pct(r.delta_pct, 1)} %, ${rel})` : `Result ${sig(r.value)} ${esc(r.unit)}`;
      const rows = vars.map((v, i) => `<tr data-i="${i}"><td>${math(mml(v.tex))}</td><td class="n">${Array.isArray(v.value) ? v.value.length + ' items' : sig(v.value)} ${esc(v.unit === '-' ? '' : v.unit)}</td><td>${esc(v.desc)}</td><td>${origin(v)}</td></tr>`).join('');
      body = `<div class="pf-verdict">${verdict}</div><div class="pf-steps">${steps}</div>
        <div class="tbl pf-vt"><table><thead><tr><th>Symbol</th><th class="n">Value</th><th>Meaning</th><th>Comes from</th></tr></thead><tbody>${rows}</tbody></table></div>${p.note ? `<p class="pf-note">${esc(p.note)}</p>` : ''}`;
    } else {
      body = `<div class="pf-verdict pf-ev">No closed-form arithmetic to re-run. The proof is the evidence and the independent check below.</div>`
        + eqList(p.equations);
    }
    const chips = (h, a) => a && a.length ? `<span class="pf-lk">${h}</span> ${a.map(x => `<button type="button" class="pf-chip" data-claim="${esc(x)}">${esc(x)}</button>`).join(' ')}` : '';
    const ext = (p.external || []).map(s => { const so = P.sources[s] || {}, k = SRCST[so.status] || ['open', so.status]; return `<button type="button" class="pf-chip pf-srcb" data-src="${esc(s)}" title="${esc(so.title || '')}"><span class="chip ${k[0]}">${esc(s)}</span> ${esc((so.title || '').split(/[,(]/)[0].slice(0, 36))}</button>`; }).join(' ');
    const ic = p.check || {};
    return `<article class="pf-card vm-${ch}" id="pf-${esc(id)}" data-id="${esc(id)}">
      <header><span class="vm-id">${esc(id)}</span><span class="chip ${ch}">${esc(c.status)}</span><span class="vm-disc">${esc(c.discipline)}</span></header>
      <p class="vm-claim">${esc(c.claim)}</p>${body}
      <div class="pf-links">${chips('Uses', p.upstream)} ${chips('Used by', p.downstream)} ${ext ? `<span class="pf-lk">Sources</span> ${ext}` : ''}</div>
      <p class="vm-why"><b>Why ${esc(c.status.toLowerCase())}:</b> ${esc(c.status_reason)}</p>
      ${guideHtml(id, p, c)}
      <details><summary>Independent check, evidence files, assumptions</summary>
        <h5>Independent check</h5><p>${esc(ic.method || '—')}${ic.delta_pct != null ? ` (Δ ${(+ic.delta_pct).toFixed(1)} %)` : ''}${ic.script ? ` <code>${esc(ic.script)}</code>` : ''}</p>
        ${(p.evidence || []).length ? `<h5>Evidence files</h5><ul class="vm-ev">${p.evidence.map(e => `<li><code>${esc(e.file)}</code> ${esc(e.what)}</li>`).join('')}</ul>` : ''}
        ${(c.assumptions || []).length ? `<h5>Assumptions</h5><ul>${c.assumptions.map(a => `<li>${esc(a)}</li>`).join('')}</ul>` : ''}
        ${(c.limitations || []).length ? `<h5>Limitations</h5><ul>${c.limitations.map(a => `<li>${esc(a)}</li>`).join('')}</ul>` : ''}
        ${c.next_step && c.next_step !== '—' ? `<h5>Next step</h5><p>${esc(c.next_step)}</p>` : ''}
        <p class="src">${esc(c.source_file)} · analysis/validation/proofs.json</p></details></article>`; }

  // ---- interaction: hover a symbol for its value and source; chips open other claims or sources in the same panel ----
  function srcCard(sid) { const s = P.sources[sid] || {}, k = SRCST[s.status] || ['open', s.status];
    const used = Object.entries(P.claims).filter(([, p]) => (p.external || []).includes(sid)).map(([id]) => id);
    return `<article class="pf-card" id="pfs-${esc(sid)}"><header><span class="vm-id">${esc(sid)}</span><span class="chip ${k[0]}">${esc(k[1])}</span><span class="vm-disc">${esc(s.kind || '')}</span></header>
      <p class="vm-claim">${esc(s.title)}</p>${s.url ? `<p><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.url)}</a> <span class="pf-mute">checked ${esc(s.checked || '—')}</span></p>` : ''}
      <div class="tbl"><table><thead><tr><th>Quantity</th><th class="n">Repo uses</th><th class="n">Source says</th><th>Where</th><th></th></tr></thead><tbody>${(s.values || []).map(v => `<tr><td>${esc(v.quantity)}</td><td class="n">${esc(v.repo_value)}</td><td class="n">${esc(v.source_value == null ? '—' : v.source_value)}</td><td>${esc(v.where || '')}</td><td>${v.match === true ? '<span class="pf-ok">✓</span>' : v.match === false ? '<span class="pf-bad">✗</span>' : '—'}</td></tr>`).join('')}</tbody></table></div>
      ${s.note ? `<p class="pf-note">${esc(s.note)}</p>` : ''}<div class="pf-links"><span class="pf-lk">Used by</span> ${used.map(x => `<button type="button" class="pf-chip" data-claim="${esc(x)}">${esc(x)}</button>`).join(' ')}</div></article>`; }
  function open(id, panel, isSrc) { if (!panel || !load()) return; panel.innerHTML = isSrc ? srcCard(id) : card(id); wire(panel);
    const a = panel.firstElementChild; if (a) a.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
  function wire(panel, onClaim) { if (panel.dataset.wired) return; panel.dataset.wired = 1;   // onClaim: the panel's own way to show a claim (the claims map keeps its list)
    panel.addEventListener('click', e => { const b = e.target.closest('[data-claim],[data-src]'); if (!b) return; e.preventDefault();
      if (b.dataset.claim) (onClaim ? onClaim(b.dataset.claim) : open(b.dataset.claim, panel)); else open(b.dataset.src, panel, true); });
    panel.addEventListener('mouseover', e => { const m = e.target.closest('.pf-v,.pf-n'); const art = e.target.closest('.pf-card'); if (!art) return;
      art.querySelectorAll('.pf-vt tr.on').forEach(r => r.classList.remove('on')); if (!m) { if (tip) tip.hidden = true; return; }
      const p = P.claims[art.dataset.id]; if (!p || !p.vars) return; const k = +m.dataset.i, v = p.vars[k];
      if (!v) return; const row = art.querySelector(`.pf-vt tr[data-i="${k}"]`); if (row) row.classList.add('on');
      if (!tip) { tip = document.createElement('div'); tip.className = 'pf-tip'; document.body.appendChild(tip); }
      tip.innerHTML = `<b>${esc(v.desc)}</b><br>${Array.isArray(v.value) ? v.value.length + ' items' : sig(v.value)} ${esc(v.unit === '-' ? '' : v.unit)}<br><span>${origin(v)}</span>`; tip.hidden = false;
      const r = m.getBoundingClientRect(); tip.style.left = Math.max(8, Math.min(innerWidth - 300, r.left)) + 'px'; tip.style.top = (r.bottom + 6 + scrollY) + 'px'; });
    panel.addEventListener('mouseleave', () => { if (tip) tip.hidden = true; }); }

  // ---- proof chains: sources -> claims -> claims, layered left to right ----
  function graph() { const svg = $('#pfGraph'); if (!svg || svg.dataset.done) return; svg.dataset.done = 1;
    const ids = Object.keys(P.claims).filter(id => P.claims[id].kind === 'computed'), nodes = {}, edges = [];
    ids.forEach(id => { nodes[id] = { id, kind: 'claim' }; });
    ids.forEach(id => { const p = P.claims[id]; (p.vars || []).forEach(v => {
      if (v.from_claim && nodes[v.from_claim]) edges.push({ a: v.from_claim, b: id, state: (v.link || {}).state });
      if (v.src && v.src.src_id) { const s = v.src.src_id; nodes[s] = nodes[s] || { id: s, kind: 'src' }; edges.push({ a: s, b: id, state: 'src' }); } }); });
    const uniq = new Map(); edges.forEach(e => uniq.set(e.a + '>' + e.b, e)); const E = [...uniq.values()];
    const layer = {}; const L = id => { if (layer[id] != null) return layer[id]; if (nodes[id].kind === 'src') return (layer[id] = 0); layer[id] = 1;
      const ins = E.filter(e => e.b === id && nodes[e.a].kind === 'claim'); return (layer[id] = ins.length ? 1 + Math.max(...ins.map(e => L(e.a))) : 1); };
    Object.keys(nodes).forEach(L);
    const cols = []; Object.values(nodes).forEach(n => { (cols[layer[n.id]] = cols[layer[n.id]] || []).push(n); });
    for (let pass = 0; pass < 4; pass++) cols.forEach((col, li) => { if (!li) return; col.forEach(n => { const ins = E.filter(e => e.b === n.id).map(e => cols[layer[e.a]].indexOf(nodes[e.a]));
      n.bc = ins.length ? ins.reduce((a, b) => a + b, 0) / ins.length : col.indexOf(n); }); col.sort((x, y) => x.bc - y.bc); });
    const W = 168, H = 40, GX = 64, GY = 12, top = 26, maxN = Math.max(...cols.map(c => c.length));
    const w = cols.length * (W + GX), h = top + maxN * (H + GY);
    cols.forEach((col, li) => col.forEach((n, k) => { n.x = li * (W + GX) + 4; n.y = top + k * (H + GY) + (maxN - col.length) * (H + GY) / 2; }));
    const name = n => { if (n.kind === 'src') return (P.sources[n.id] || {}).title || n.id; const p = P.claims[n.id]; return (p.steps[p.steps.length - 1] || {}).desc || C[n.id].claim; };
    const short = t => t.length > 26 ? t.slice(0, 25).replace(/\s+\S*$/, '') + '…' : t;
    let g = cols.map((c, li) => `<text x="${li * (W + GX) + 4}" y="14" class="tick">${li === 0 ? 'External sources' : li === 1 ? 'Computed from inputs' : 'Built on level ' + (li - 1) + ' results'}</text>`).join('');
    g += E.map(e => { const a = nodes[e.a], b = nodes[e.b], x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2, mx = (x1 + x2) / 2;
      return `<path class="pf-e pf-e-${e.state === 'stale' ? 'bad' : e.state === 'src' ? 'src' : 'ok'}" data-a="${e.a}" data-b="${e.b}" d="M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}"/>`; }).join('');
    g += Object.values(nodes).map(n => { const st = n.kind === 'src' ? (SRCST[(P.sources[n.id] || {}).status] || ['open'])[0] : CHIP[C[n.id].status];
      const r = n.kind === 'claim' ? P.claims[n.id].result.reproduced : null;
      return `<g class="pf-node pf-${n.kind}" data-id="${n.id}" tabindex="0" role="button" aria-label="${esc(n.id + ': ' + name(n))}"><rect x="${n.x}" y="${n.y}" width="${W}" height="${H}" rx="6" class="st-${st}"/>
        <text x="${n.x + 9}" y="${n.y + 16}" class="pf-nid">${esc(n.id)}${r === false ? ' ✗' : ''}</text><text x="${n.x + 9}" y="${n.y + 31}" class="pf-nt">${esc(short(name(n)))}</text></g>`; }).join('');
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`); svg.style.minWidth = w + 'px'; svg.innerHTML = g;
    const hl = id => { const up = new Set([id]), dn = new Set([id]); let ch = true; while (ch) { ch = false; E.forEach(e => { if (dn.has(e.a) && !dn.has(e.b)) { dn.add(e.b); ch = true; } if (up.has(e.b) && !up.has(e.a)) { up.add(e.a); ch = true; } }); }
      svg.classList.toggle('pf-hl', !!id); svg.querySelectorAll('.pf-node').forEach(x => x.classList.toggle('on', !!id && (up.has(x.dataset.id) || dn.has(x.dataset.id))));
      svg.querySelectorAll('.pf-e').forEach(x => x.classList.toggle('on', !!id && ((up.has(x.dataset.a) && up.has(x.dataset.b)) || (dn.has(x.dataset.a) && dn.has(x.dataset.b))))); };
    svg.addEventListener('mouseover', e => { const n = e.target.closest('.pf-node'); hl(n ? n.dataset.id : null); });
    svg.addEventListener('mouseleave', () => hl(null));
    const go = n => { const isSrc = n.classList.contains('pf-src'); open(n.dataset.id, $('#pfPanel'), isSrc); };
    svg.addEventListener('click', e => { const n = e.target.closest('.pf-node'); if (n) go(n); });
    svg.addEventListener('keydown', e => { const n = e.target.closest('.pf-node'); if (n && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); go(n); } });
    if (!$('#pfPanel').children.length) open('AERO-14', $('#pfPanel')); }

  // ---- sources ----
  function sources() { const tb = $('#srcTable tbody'); if (!tb || tb.dataset.done) return; tb.dataset.done = 1;
    const S = P.sources, cnt = {}; Object.values(S).forEach(s => { cnt[s.status] = (cnt[s.status] || 0) + 1; });
    const lc = P.link_check || null;
    $('#srcKpis').innerHTML = Object.entries(SRCST).filter(([k]) => cnt[k]).map(([k, [c, l]]) => `<div class="kpi"><div class="l"><span class="chip ${c}">${l}</span></div><div class="v">${cnt[k]}</div></div>`).join('')
      + (lc ? `<div class="kpi"><div class="l">Every URL in the docs</div><div class="v">${lc.ok} / ${lc.n}</div><div class="s">load; ${lc.dead} dead, ${lc.blocked} block automated checks</div></div>` : '');
    tb.innerHTML = Object.entries(S).map(([id, s]) => { const k = SRCST[s.status] || ['open', s.status], used = Object.entries(P.claims).filter(([, p]) => (p.external || []).includes(id)).map(([c]) => c);
      const vals = (s.values || []).map(v => `${esc(v.quantity)}: ${esc(v.repo_value)}${v.match === true ? ' <span class="pf-ok">✓</span>' : v.match === false ? ` <span class="pf-bad">✗ source ${esc(v.source_value)}</span>` : ''}`).join('<br>');
      return `<tr><td><button type="button" class="pf-chip" data-src="${id}">${id}</button> ${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>` : esc(s.title)}</td><td><span class="chip ${k[0]}">${esc(k[1])}</span></td><td class="pf-vals">${vals}</td><td>${used.map(c => `<button type="button" class="pf-chip" data-claim="${c}">${c}</button>`).join(' ')}</td></tr>`; }).join('');
    const panel = $('#srcPanel'); wire(panel); $('#srcTable').addEventListener('click', e => { const b = e.target.closest('[data-claim],[data-src]'); if (!b) return; e.preventDefault(); b.dataset.claim ? open(b.dataset.claim, panel) : open(b.dataset.src, panel, true); });
    $('#srcNote').textContent = 'analysis/validation/source_audit.json (value-by-value check, ' + Object.values(S).map(s => s.checked).filter(Boolean).sort().pop() + ')' + (lc ? `; analysis/validation/link_check.py → link_check.json (${lc.n} unique URLs)` : ''); }

  // ---- mesh audit (3-D CFD tab) ----
  function meshAudit() { const tb = $('#maTable tbody'), el = document.getElementById('meshAudit'); if (!tb || !el || tb.dataset.done) return; tb.dataset.done = 1;
    const A = JSON.parse(el.textContent), std = {}; A.standards.forEach(s => { std[s.id] = s; }); const S = A.summary;
    $('#maVerdict').innerHTML = `<b>${S.fails} of ${S.passes + S.fails} applicable checks fail.</b> ` + esc(S.verdict);
    $('#maKpis').innerHTML = [['met', 'Pass', S.passes], ['fail', 'Fail', S.fails], ['open', 'Does not apply', S.not_applicable]].map(([c, l, n]) => `<div class="kpi"><div class="l"><span class="chip ${c}">${l}</span></div><div class="v">${n}</div></div>`).join('');
    const cell = x => { if (!x) return '<td class="n">—</td>'; const v = x.value, r = x.result, k = r === 'pass' ? 'ok' : r === 'fail' ? 'bad' : 'na';
      return `<td class="n ma-${k}">${v == null ? '—' : typeof v === 'number' ? +v.toPrecision(3) : esc(v)}</td>`; };
    tb.innerHTML = A.scorecard.map(r => { const s = std[r.standard] || {}; return `<tr><td>${esc(s.criterion || r.metric)}</td><td>${s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.source)}</a>` : esc(s.source || '')}: ${esc(r.threshold_text)}</td>${cell(r.L1)}${cell(r.L2)}${cell(r.L3)}<td>${esc(r.note || '')}</td></tr>`; }).join('');
    $('#maNeed').innerHTML = (S.what_a_passing_mesh_needs || []).map(x => `<li>${esc(x)}</li>`).join('');
    $('#maStrategy').innerHTML = A.strategy.map(st => `<div class="ma-rule"><h5>${esc(st.name)}</h5><p>${esc(st.what)}</p>${st.parameters ? `<p class="pf-mute">${Object.entries(st.parameters).map(([k, v]) => `${esc(k)} = ${esc(v)}`).join(' · ')}</p>` : ''}
      ${st.code ? `<pre class="ma-code"><code>${st.code.lines.map((l, i) => `<span class="ln">${st.code.from + i}</span>${esc(l)}`).join('\n')}</code></pre><p class="src">${esc(st.code.file)}:${st.code.from}</p>` : `<p class="src">${esc(st.code_ref || '')}</p>`}</div>`).join('');
    $('#maSrc').textContent = `analysis/cfd3d/mesh_audit.py → out/mesh_audit.json (${A.generated}); standards: ` + A.standards.map(s => s.source).filter((x, i, a) => a.indexOf(x) === i).join('; '); }

  // ---- chapter verdict (Proof and validation) ----
  function verdict() { const v = $('#vmVerdict'); if (!v || v.dataset.done) return; v.dataset.done = 1; const c = V.counts, s = P.summary;
    const so = Object.values(P.sources), conf = so.filter(x => x.status === 'confirmed').length, bad = so.filter(x => x.status === 'mismatch').length;
    v.innerHTML = `<b>${V.claims.length} claims: ${c['Verified'] || 0} verified, ${c['Partially Verified'] || 0} partly verified, ${c['Unverified'] || 0} unverified, ${c['Failed'] || 0} failed.</b> `
      + `${s.reproduced} of the ${s.computed} claims with arithmetic re-run to the same number from their cited files${s.not_reproduced ? ` (${s.not_reproduced} does not: ${Object.entries(P.claims).filter(([, p]) => p.result && p.result.reproduced === false).map(([id]) => id).join(', ')})` : ''}; `
      + `${s.links_consistent} of ${s.links} hand-offs between claims carry the same number${s.links_stale ? ` (${s.links_stale} stale: ${Object.entries(P.claims).filter(([, p]) => (p.vars || []).some(x => x.link && x.link.state === 'stale')).map(([id]) => id).join(', ')})` : ''}. `
      + `Of ${so.length} external sources, ${conf} were confirmed value by value and ${bad} contradict the repo; the rest are books, standards or sites that block automated reading.`; }

  return {
    card, open, wire, load, eqList,
    redraw(sec) { if (!load()) return; const vis = id => { const e = document.getElementById(id); return e && !e.closest('[hidden]'); };
      if (vis('vmVerdict')) verdict(); if (vis('pfGraph')) graph(); if (vis('srcTable')) sources(); if (vis('maTable')) meshAudit(); }
  };
})();
