// ---------- Claims map: every engineering claim tied to the part it is about ----------
// Data: #validData (analysis/validation/build_matrix.py -> validation_matrix.json; claims from check_aero.py, check_struct.py and
// analysis/cfd3d/verify_cfd.py) and the SOLIDWORKS assembly mesh #meshData (review/mesh.mjs, the CAD viewer's data, parsed lazily
// into the shared MESH). Each part is coloured by the worst status among the claims about its component; clicking a part (or a
// component chip) lists those claims as proof cards (proofs.js). Equation pointers: labels anchored on the part each key
// equation acts on (centre of that part's mesh), projected every frame, each opening its claim's proof.
const ClaimsMap = (() => {
  const $ = s => document.querySelector(s);
  let V = null, gl, cv, prog, buf = {}, A = null, cam, raf = 0, started = false, sel = null, pickFb = null, hoverComp = null, mfgDone = false;
  // claim -> the part (and which copy of it) its equation acts on; label = what the equation gives
  const PTRS = [['AERO-09', /^Wing_Panel_R$/, 0, 'cruise CL'], ['AERO-07', /^Wing_Panel_L$/, 0, 'stall speed'], ['STR-07', /^Wing_Joiner$/, 0, 'joiner stress'],
    ['STR-01', /^Boom_Clamp_F_Upper$/, 1, 'boom root stress'], ['STR-03', /^Motor_Mount_Upper$/, 1, 'boom tip deflection'], ['STR-05', /^Motor_Mount_Cap$/, 3, 'lift-unit mass'],
    ['THM-01', /^Lift_Motor$/, 0, 'motor temperature'], ['AERO-16', /^Lift_Prop$/, 2, 'hover power'], ['AERO-26', /^Fuselage_Pod$/, 0, 'static margin'],
    ['AERO-27', /^H_Tail$/, 0, 'tail volume'], ['AERO-20', /^Battery_6S_LiPo$/, 0, 'cruise time'], ['AERO-14', /^Pusher_Prop_14in$/, 0, 'cruise power']];
  // rev 2026-11-03: with a component selected, one label per claim of that component: [part, copy, label, position along the
  // part's longest side 0-1 (centre if omitted)]. A claim missing here is anchored on its component's first part.
  const BAL = {
    // wing
    'AERO-01': [/^Wing_Panel_R$/, 0, 'cruise Re', 0.3], 'AERO-02': [/^Wing_Panel_R$/, 0, 'section lift slope', 0.55], 'AERO-03': [/^Wing_Panel_R$/, 0, 'section drag', 0.8],
    'AERO-04': [/^Aileron_R$/, 0, '2-D mesh GCI'], 'AERO-05': [/^Wing_Panel_L$/, 0, '2-D CL max', 0.8], 'AERO-06': [/^Wing_Panel_L$/, 0, '3-D CL max', 0.55],
    'AERO-07': [/^Wing_Panel_L$/, 0, 'stall speed', 0.3], 'AERO-08': [/^Aileron_L$/, 0, 'wing area'], 'AERO-09': [/^Wing_Panel_L$/, 0, 'cruise CL', 0.08],
    'AERO-23': [/^Wing_Panel_R$/, 0, 'wing mass', 0.08], 'CFD-09': [/^Wing_Panel_R$/, 0, 'CFD Reynolds', 0.97], 'CFD-12': [/^Wing_Panel_L$/, 0, '2-D scheme check', 0.97],
    'MFG-05': [/^Wing_Joiner$/, 0, 'joiner fit', 0.25], 'MFG-06': [/^Spar_Tube$/, 0, 'socket tilt', 0.7], 'MFG-09': [/^Bolt_Pillar$/, 0, 'wing-bolt protrusion'],
    'STR-06': [/^Wing_Saddle$/, 0, 'root moment'], 'STR-07': [/^Wing_Joiner$/, 0, 'joiner stress', 0.6], 'STR-08': [/^Spar_Tube$/, 1, 'spar stress (FEA)', 0.3],
    'STR-09': [/^Spar_Tube$/, 1, 'spar tip deflection', 0.9], 'STR-13': [/^Bolt_Pillar$/, 1, 'wing-bolt load'],
    // tail
    'AERO-27': [/^H_Tail$/, 0, 'tail volume'], 'AERO-28': [/^Elevator$/, 0, 'cruise trim'], 'CFD-07': [/^Fin$/, 0, 'CFD neutral point'],
    // booms
    'STR-01': [/^Boom_Clamp_F_Upper$/, 1, 'boom root stress'], 'STR-02': [/^Boom_Front$/, 0, 'FEA vs beam', 0.35], 'STR-03': [/^Boom_Front$/, 1, 'tip deflection', 0.95],
    'STR-04': [/^Boom_Front$/, 1, 'first bending mode', 0.6], 'XT-01': [/^Boom_Front$/, 0, 'independent FEA', 0.8], 'STR-10': [/^Boom_Clamp_F_Lower$/, 0, 'clamp load'],
    'STR-14': [/^Boom_Clamp_R_Upper$/, 0, 'clamp slip torque'], 'MFG-07': [/^Boom_Clamp_R_Lower$/, 1, 'clamp grip'], 'STR-12': [/^Splice_Plug$/, 0, 'splice bolt load'],
    'MFG-08': [/^Splice_Plug$/, 1, 'splice plug fit'],
    // lift propulsion
    'AERO-16': [/^Lift_Prop$/, 2, 'hover power'], 'AERO-18': [/^Lift_Prop$/, 0, 'hover T/W'], 'AERO-32': [/^Lift_Motor$/, 1, 'T/W under load'],
    'THM-01': [/^Lift_Motor$/, 0, 'motor steady temp'], 'THM-02': [/^Lift_Motor$/, 2, 'film coefficient'], 'THM-03': [/^Lift_Motor$/, 3, 'motor heat'],
    'THM-04': [/^Motor_Mount_Upper$/, 0, 'motor temp, hover'], 'THM-05': [/^Motor_Mount_Cap$/, 1, 'ESC temperature'], 'STR-05': [/^Motor_Mount_Cap$/, 3, 'lift-unit mass'],
    // cruise propulsion, battery, gear, avionics
    'AERO-14': [/^Pusher_Prop_14in$/, 0, 'cruise power'], 'AERO-15': [/^Pusher_Motor$/, 0, 'prop efficiency'], 'THM-08': [/^Pusher_Cup$/, 0, 'pusher motor temp'],
    'AERO-17': [/^Battery_6S_LiPo$/, 0, 'hover current', 0.15], 'AERO-20': [/^Battery_6S_LiPo$/, 0, 'cruise time', 0.5], 'AERO-21': [/^Battery_6S_LiPo$/, 0, 'pack energy', 0.85],
    'THM-06': [/^Battery_Tray$/, 0, 'pack temperature'], 'STR-11': [/^Landing_Leg$/, 0, 'landing stress'], 'THM-07': [/^Flight_Controller$/, 0, 'FC temperature'],
    // whole aircraft
    'AERO-12': [/^Fuselage_Pod$/, 0, 'zero-lift drag', 0.15], 'AERO-22': [/^Fuselage_Pod$/, 0, 'MTOW', 0.45], 'MFG-12': [/^Fuselage_Pod$/, 0, 'bottom-up mass', 0.3],
    'AERO-26': [/^Fuselage_Pod$/, 0, 'static margin', 0.65], 'AERO-25': [/^Fuselage_Pod$/, 0, 'neutral point', 0.8], 'CFD-10': [/^Fuselage_Pod$/, 0, 'surface CD', 0.97],
    'CFD-04': [/^Fuselage_Pod$/, 0, 'boundary conditions', 0.02], 'AERO-19': [/^Battery_6S_LiPo$/, 0, 'transition current', 0.5], 'AERO-24': [/^Battery_6S_LiPo$/, 0, 'CG position', 0.1],
    'AERO-13': [/^Wing_Panel_R$/, 0, 'cruise L/D', 0.4], 'AERO-10': [/^Wing_Panel_R$/, 0, 'lift-curve slope', 0.7], 'AERO-11': [/^Wing_Panel_R$/, 0, 'Oswald e', 0.95],
    'CFD-01': [/^Wing_Panel_R$/, 0, 'CFD runs', 0.15], 'CFD-05': [/^Wing_Panel_R$/, 0, 'CFD lift slope', 0.55], 'CFD-02': [/^Wing_Panel_L$/, 0, 'grid uncertainty', 0.3],
    'CFD-03': [/^Wing_Panel_L$/, 0, 'force integration', 0.45], 'AERO-29': [/^Wing_Panel_L$/, 0, 'best-L/D speed', 0.6], 'CFD-06': [/^Wing_Panel_L$/, 0, 'CFD CL', 0.75],
    'CFD-08': [/^Wing_Panel_L$/, 0, 'induced drag (CFD)', 0.9], 'CFD-11': [/^H_Tail$/, 0, 'Cp overshoot'], 'AERO-30': [/^Fin$/, 0, 'doc numbers match'],
    'AERO-31': [/^Canopy$/, 0, 'budget'], 'MFG-02': [/^Canopy$/, 0, 'interferences'], 'MFG-03': [/^Elevator$/, 0, 'drawings'], 'MFG-01': [/^Spar_Tube$/, 0, 'CAD = sizing', 0.4],
    'MFG-04': [/^Bolt_Pillar$/, 0, 'fastener order'], 'MFG-10': [/^Boom_Clamp_F_Upper$/, 0, 'fastener torques'], 'MFG-11': [/^Horn_Hardpoint$/, 0, 'bond adhesive'] };
  const ORDER = ['Failed', 'Unverified', 'Partially Verified', 'Verified'];
  const CHIP = { 'Verified': 'met', 'Partially Verified': 'risk', 'Unverified': 'open', 'Failed': 'fail' };
  const COL = { 'Failed': [0.86, 0.33, 0.33], 'Unverified': [0.6, 0.53, 0.95], 'Partially Verified': [0.92, 0.72, 0.3], 'Verified': [0.33, 0.78, 0.55], none: [0.55, 0.58, 0.62] };
  // SOLIDWORKS part name -> claim component (analysis/validation/build_matrix.py COMPONENTS)
  const MAP = [[/^(Wing_Panel|Aileron|Wing_Saddle|Spar_Tube|Wing_Joiner|Joiner_Stop|Root_Tongue|Bolt_Pillar|Spar_Collar|Rear_Hardpoint|Horn_Hardpoint)/, 'wing'],
    [/^(H_Tail|Elevator|Fin|Rudder|Tail_Clamp|Crush_Sleeve)/, 'tail'], [/^(Fuselage_Pod|Canopy)/, 'fuselage'],
    [/^(Boom_|Splice_Plug)/, 'booms'], [/^(Lift_Motor|Lift_Prop|Motor_Mount|Prop_Plate)/, 'lift_propulsion'],
    [/^(Pusher_|Prop_Washer|N04)/, 'cruise_propulsion'], [/^(Battery_)/, 'battery'], [/^(Landing_Leg|Gear_)/, 'landing_gear'],
    [/^(Flight_Controller|FC_Tray|Servo|Pitot|Control_Horn|Horn_Backplate|Pushrod)/, 'avionics']];
  const compOf = n => { for (const [re, c] of MAP) if (re.test(n)) return c; return null; };
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  let PRC = null; const PROOF = () => PRC || (PRC = document.getElementById('proofData') && JSON.parse(document.getElementById('proofData').textContent).claims);
  const worst = comp => { const st = V.claims.filter(c => c.component === comp).map(c => c.status); return ORDER.find(s => st.includes(s)) || 'none'; };

  // ---------------------------------------------------------------- panels
  function kpis() { const c = V.counts, n = V.claims.length;
    $('#vmKpis').innerHTML = ORDER.slice().reverse().map(s => `<div class="kpi"><div class="l"><span class="chip ${CHIP[s]}">${s}</span></div><div class="v">${c[s] || 0}</div><div class="s">${esc(V.status_definitions[s])}</div></div>`).join('')
      + `<div class="kpi"><div class="l">Claims checked</div><div class="v">${n}</div><div class="s">${Object.entries(V.sources).map(([f, s]) => `${f} (${s.n})`).join(', ')}</div></div>`; }
  function chips() { const comps = Object.keys(V.component_labels);
    $('#vmChips').innerHTML = comps.map(k => { const n = V.claims.filter(c => c.component === k).length, w = worst(k);
      return `<button type="button" data-comp="${k}" aria-pressed="${k === sel}"><span class="vm-dot" style="background:rgb(${COL[w].map(x => Math.round(x * 255)).join(',')})"></span>${esc(V.component_labels[k])} <span class="vm-n">${n}</span></button>`; }).join(''); }
  function cardOld(c) { const ic = c.independent_check || {}, d = ic.delta_pct;
    const val = c.value == null ? '—' : (typeof c.value === 'number' ? (Math.abs(c.value) >= 1000 ? c.value.toLocaleString(undefined, { maximumFractionDigits: 0 }) : +c.value.toPrecision(4)) : esc(c.value));
    const list = (h, a) => a && a.length ? `<h5>${h}</h5><ul>${a.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : '';
    const inputs = c.inputs && Object.keys(c.inputs).length ? `<h5>Inputs</h5><dl class="vm-in">${Object.entries(c.inputs).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(typeof v === 'object' ? JSON.stringify(v) : v)}</dd>`).join('')}</dl>` : '';
    return `<article class="vm-card vm-${CHIP[c.status]}" id="claim-${esc(c.id)}">
      <header><span class="vm-id">${esc(c.id)}</span><span class="chip ${CHIP[c.status]}">${esc(c.status)}</span><span class="vm-disc">${esc(c.discipline)}</span></header>
      <p class="vm-claim">${esc(c.claim)}</p>
      <div class="vm-num"><span>Claimed <b>${val}</b> ${esc(c.units || '')}</span>${ic.value != null ? `<span>Independent <b>${typeof ic.value === 'number' ? +ic.value.toPrecision(4) : esc(ic.value)}</b></span>` : ''}${d != null ? `<span>Δ <b class="${Math.abs(d) > 10 ? 'bad-t' : Math.abs(d) > 5 ? 'warn-t' : 'ok-t'}">${d >= 0 ? '+' : ''}${(+d).toFixed(1)} %</b></span>` : ''}</div>
      <p class="vm-why"><b>Why this status:</b> ${esc(c.status_reason)}</p>
      <details><summary>Equations, inputs, assumptions and evidence</summary>
        ${c.equations && c.equations.length ? `<h5>Equations</h5>${Proofs.eqList(c.equations)}` : ''}
        ${inputs}${list('Assumptions', c.assumptions)}
        <h5>Tool</h5><p>${esc(c.tool)}</p>
        <h5>Did the computation run?</h5><p>${esc(c.ran_evidence)}</p>
        ${c.reproduced ? `<h5>Reproduced</h5><p>${c.reproduced.done ? 'Yes' : 'No'}${c.reproduced.how ? ': ' + esc(c.reproduced.how) : ''}${c.reproduced.matches === true ? ' (matches)' : c.reproduced.matches === false ? ' (does not match)' : ''}</p>` : ''}
        <h5>Independent check</h5><p>${esc(ic.method || '—')}${ic.script ? ` <span class="src-i">${esc(ic.script)}</span>` : ''}</p>
        ${c.evidence && c.evidence.length ? `<h5>Evidence files</h5><ul class="vm-ev">${c.evidence.map(e => `<li><code>${esc(e.file)}</code> ${esc(e.what)}</li>`).join('')}</ul>` : ''}
        ${list('Limitations', c.limitations)}
        ${c.next_step && c.next_step !== '—' ? `<h5>Next step</h5><p>${esc(c.next_step)}</p>` : ''}
        <p class="src">${esc(c.source_file)}</p>
      </details></article>`; }
  function show(comp) { sel = comp; chips(); const list = V.claims.filter(c => !comp || c.component === comp);
    const lab = comp ? V.component_labels[comp] : 'All components', ch = comp && V.component_chapter[comp];
    const cnt = ORDER.map(s => [s, list.filter(c => c.status === s).length]).filter(([, n]) => n).map(([s, n]) => `<span class="chip ${CHIP[s]}">${n} ${s}</span>`).join(' ');
    // compact: nothing listed until a part is chosen; then one row per claim, and one proof card open at a time
    const PR = document.getElementById('proofData') && (show.pr = show.pr || JSON.parse(document.getElementById('proofData').textContent).claims);
    const mark = id => { const r = PR && PR[id] && PR[id].result; return !r ? '' : r.reproduced === true ? '<span class="pf-ok" title="Re-runs to the same number">✓</span>' : r.reproduced === false ? '<span class="pf-bad" title="Re-runs to a different number">✗</span>' : ''; };
    $('#vmPanel').innerHTML = !comp ? `<p class="vm-empty">Click a part, a component above or an equation label to see its claims. ${cnt}</p>`
      : `<div class="vm-ph"><h4>${esc(lab)}</h4><div>${cnt}</div>${ch ? `<a class="xref" href="#${ch}">Evidence chapter</a>` : ''}</div>`
        + (list.length ? `<ul class="vm-rows">${list.map(c => `<li data-id="${esc(c.id)}"><button type="button" class="vm-row" aria-expanded="false"><span class="vm-id">${esc(c.id)}</span><span class="chip ${CHIP[c.status]}">${esc(c.status)}</span><span class="vm-rt">${esc(c.claim)}</span>${mark(c.id)}</button></li>`).join('')}</ul>` : '<p>No claims recorded for this component.</p>');
    draw(); }
  function expand(id, scroll) { const li = document.querySelector(`#vmPanel li[data-id="${id}"]`); if (!li) return;
    document.querySelectorAll('#vmPanel li.on').forEach(x => { if (x !== li) { x.classList.remove('on'); x.querySelector('.vm-row').setAttribute('aria-expanded', 'false'); const c = x.querySelector('.pf-card'); if (c) c.remove(); } });
    const open = !li.classList.contains('on'); li.classList.toggle('on', open); li.querySelector('.vm-row').setAttribute('aria-expanded', String(open));
    const c = li.querySelector('.pf-card'); if (c) c.remove();
    if (open) { li.insertAdjacentHTML('beforeend', Proofs.card(id)); if (scroll) li.scrollIntoView({ behavior: 'smooth', block: 'start' }); } }
  function goClaim(id) { const c = V.claims.find(x => x.id === id); if (!c) return; if (sel !== c.component) show(c.component); expand(id, true); }
  function table() {
    const f = { st: $('#vmFStatus').value, di: $('#vmFDisc').value, q: $('#vmFText').value.toLowerCase() };
    const rows = V.claims.filter(c => (!f.st || c.status === f.st) && (!f.di || c.discipline === f.di) && (!f.q || (c.id + ' ' + c.claim + ' ' + c.status_reason).toLowerCase().includes(f.q)));
    const PR = Proofs.load() && JSON.parse(document.getElementById('proofData').textContent).claims;
    $('#vmTable tbody').innerHTML = rows.map(c => { const r = PR && PR[c.id] && PR[c.id].result, rr = !r ? '<span class="pf-mute">evidence</span>' : r.reproduced === true ? '<span class="pf-ok">✓ same number</span>' : r.reproduced === false ? '<span class="pf-bad">✗ differs</span>' : '—';
      return `<tr><td><a href="#pf-${esc(c.id)}" data-id="${esc(c.id)}" class="vm-go">${esc(c.id)}</a></td><td>${esc(c.claim)}</td><td><span class="chip ${CHIP[c.status]}">${esc(c.status)}</span></td><td>${rr}</td><td>${esc(c.status_reason)}</td></tr>`; }).join('');
    $('#vmCount').textContent = `${rows.length} of ${V.claims.length} claims`; }
  function mfg() { if (mfgDone || !document.getElementById('vmMfg')) return; mfgDone = true; const M = V.manufacturing, LV = { 'Ready': 'met', 'Needs minor specification': 'risk', 'Not ready': 'fail' };
    $('#vmMfg tbody').innerHTML = M.subsystems.map(s => `<tr><td>${esc(s.name)}</td><td><span class="chip ${LV[s.level] || 'open'}">${esc(s.level)}</span></td><td><ul class="vm-ul">${s.blocking_items.map(b => `<li>${esc(b)}</li>`).join('')}</ul></td></tr>`).join('');
    $('#vmStacks tbody').innerHTML = (M.tolerance_stacks || []).map(t => `<tr><td>${esc(t.name)}</td><td class="n">${esc(t.worst_case)}</td><td class="n">${esc(t.rss)}</td><td>${esc(t.requirement)}</td><td>${esc(t.verdict)}</td></tr>`).join(''); }

  // ---------------------------------------------------------------- 3-D aircraft
  const VS = 'attribute vec3 p; attribute vec3 c; uniform mat4 M, P; varying vec3 vc; varying vec3 ve; void main(){ vec4 e = M * vec4(p,1.0); ve = e.xyz; vc = c; gl_Position = P * e; }';
  const FS = '#extension GL_OES_standard_derivatives : enable\nprecision mediump float; varying vec3 vc; varying vec3 ve; uniform float pick; void main(){ if (pick > 0.5) { gl_FragColor = vec4(vc, 1.0); return; } vec3 n = normalize(cross(dFdx(ve), dFdy(ve))); float d = abs(dot(n, normalize(vec3(0.3,0.6,1.0)))); gl_FragColor = vec4(vc * (0.42 + 0.62 * d), 1.0); }';
  function aircraft() {
    if (typeof MESH !== 'undefined' && !MESH) MESH = JSON.parse(document.getElementById('meshData').textContent);
    const M = MESH, dec = (s, T) => { const b = atob(s), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return new T(u.buffer); };
    const parts = {}; let nv = 0, ni = 0;
    for (const [n] of M.comps) { if (!parts[n]) { const p = M.parts[n]; parts[n] = { v: dec(p.v, Float32Array), i: dec(p.i, p.w === 4 ? Uint32Array : Uint16Array) }; } nv += parts[n].v.length / 3; ni += parts[n].i.length; }
    const P = new Float32Array(nv * 3), Cc = new Float32Array(nv * 3), Q = new Float32Array(nv * 3), I = new Uint32Array(ni), comp = [];
    let vo = 0, io = 0; const names = Object.keys(V.component_labels);
    M.comps.forEach(([n, x, y, z]) => { const { v, i } = parts[n], k = v.length / 3, c = compOf(n.split('~')[0]), ci = c ? names.indexOf(c) + 1 : 0;
      for (let j = 0; j < k; j++) { P[(vo + j) * 3] = v[j * 3] + x; P[(vo + j) * 3 + 1] = v[j * 3 + 1] + y; P[(vo + j) * 3 + 2] = v[j * 3 + 2] + z; Q[(vo + j) * 3] = ci / 255; }
      let lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9]; for (let j = 0; j < k; j++) for (let a = 0; a < 3; a++) { const q = P[(vo + j) * 3 + a]; if (q < lo[a]) lo[a] = q; if (q > hi[a]) hi[a] = q; }
      for (let j = 0; j < i.length; j++) I[io + j] = i[j] + vo; comp.push({ c, v0: vo, nv: k, name: n.split('~')[0], lo, hi, ctr: lo.map((v, a) => (v + hi[a]) / 2) }); vo += k; io += i.length; });
    A = { P, C: Cc, Q, I, comp, names };
    for (const [nm, d] of [['p', P], ['q', Q]]) { buf[nm] = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf[nm]); gl.bufferData(gl.ARRAY_BUFFER, d, gl.STATIC_DRAW); }
    buf.i = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.i); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, I, gl.STATIC_DRAW); buf.c = gl.createBuffer();
    colours();
  }
  function colours() { const C = A.C;
    for (const p of A.comp) { let k = p.c ? COL[worst(p.c)] : COL.none; if (p.c && sel && p.c !== sel) k = k.map(x => x * 0.35 + 0.2); if (p.c && p.c === hoverComp) k = k.map(x => Math.min(1, x * 1.18 + 0.05));
      for (let j = 0; j < p.nv; j++) C.set(k, (p.v0 + j) * 3); }
    gl.bindBuffer(gl.ARRAY_BUFFER, buf.c); gl.bufferData(gl.ARRAY_BUFFER, C, gl.DYNAMIC_DRAW); }
  const MV = new Float32Array(16), PR = new Float32Array(16);
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]], dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  function reset() { const asp = cv.clientWidth / (cv.clientHeight || 1) || 16 / 9; cam = { yaw: 0.67, pitch: 0.45, d: 2.6 * Math.max(1, 1.6 / asp), t: [-0.29, -0.03, 0] }; }
  function mats() { const { yaw, pitch, d } = cam, f = [-Math.cos(pitch) * Math.sin(yaw), -Math.sin(pitch), -Math.cos(pitch) * Math.cos(yaw)], t = cam.t, eye = t.map((v, i) => v - f[i] * d);
    let r = cross(f, [0, 1, 0]); const l = Math.hypot(...r) || 1; r = r.map(x => x / l); const u = cross(r, f);
    MV.set([r[0], u[0], -f[0], 0, r[1], u[1], -f[1], 0, r[2], u[2], -f[2], 0, -dot(r, eye), -dot(u, eye), dot(f, eye), 1]);
    const asp = cv.clientWidth / (cv.clientHeight || 1), n = 0.02, fa = d + 6, k = 1 / Math.tan(0.35); PR.set([k / asp, 0, 0, 0, 0, k, 0, 0, 0, 0, (fa + n) / (n - fa), -1, 0, 0, 2 * fa * n / (n - fa), 0]); }
  function scene(pick) { gl.useProgram(prog); const lp = gl.getAttribLocation(prog, 'p'), lc = gl.getAttribLocation(prog, 'c');
    gl.bindBuffer(gl.ARRAY_BUFFER, buf.p); gl.enableVertexAttribArray(lp); gl.vertexAttribPointer(lp, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, pick ? buf.q : buf.c); gl.enableVertexAttribArray(lc); gl.vertexAttribPointer(lc, 3, gl.FLOAT, false, 0, 0);
    gl.uniformMatrix4fv(gl.getUniformLocation(prog, 'M'), false, MV); gl.uniformMatrix4fv(gl.getUniformLocation(prog, 'P'), false, PR); gl.uniform1f(gl.getUniformLocation(prog, 'pick'), pick ? 1 : 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.i); gl.drawElements(gl.TRIANGLES, A.I.length, gl.UNSIGNED_INT, 0); }
  function draw() { if (raf || !gl) return; raf = requestAnimationFrame(() => { raf = 0; const dpr = Math.min(2, window.devicePixelRatio || 1), w = cv.clientWidth, h = cv.clientHeight;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, cv.width, cv.height); gl.clearColor(0.165, 0.184, 0.212, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.enable(gl.DEPTH_TEST); mats(); colours(); scene(false); pointers(); }); }
  function project(p) { const M = MV, x = M[0] * p[0] + M[4] * p[1] + M[8] * p[2] + M[12], y = M[1] * p[0] + M[5] * p[1] + M[9] * p[2] + M[13], z = M[2] * p[0] + M[6] * p[1] + M[10] * p[2] + M[14], w = -z;
    return [(PR[0] * x / w * 0.5 + 0.5) * cv.clientWidth, (1 - (PR[5] * y / w * 0.5 + 0.5)) * cv.clientHeight, w]; }
  function pointers() { const lay = $('#vmPtrLayer'), svg = $('#vmLines'); if (!lay || !A) return; const on = !$('#vmPtrs') || $('#vmPtrs').checked;
    if (!on) { lay.innerHTML = ''; svg.innerHTML = ''; return; }
    const W = cv.clientWidth, H = cv.clientHeight, cx = W / 2, cy = H / 2, PRF = PROOF();
    // nothing selected: the overview labels; a component selected: every claim about it
    const set = !sel ? PTRS : V.claims.filter(c => c.component === sel).map(c => { const b = BAL[c.id];
      if (b) return [c.id, b[0], b[1], b[2], b[3]];
      const p = A.comp.find(q => q.c === sel), st = PRF && PRF[c.id] && PRF[c.id].steps;
      return [c.id, p ? new RegExp('^' + p.name + '$') : /^$/, 0, st ? st[st.length - 1].desc || '' : '']; });
    if (lay.dataset.key !== (sel || '')) { lay.dataset.key = sel || '';
      lay.innerHTML = set.map(([id, , , lab]) => { const c = V.claims.find(x => x.id === id), r = PRF && PRF[id] && PRF[id].result;
        const v = r && typeof r.value === 'number' ? [r.value, r.unit] : c && typeof c.value === 'number' && (c.units || '').length <= 8 ? [c.value, c.units] : null;
        return `<button type="button" class="vm-ptr vm-${CHIP[c ? c.status : 'Unverified']}" data-id="${id}" title="${esc(c ? c.claim : id)}"><span class="vm-pd"></span><b>${id}</b><span class="vm-pl"> ${esc(lab)}</span>${v ? ` <span class="vm-pv">${+v[0].toPrecision(3)} ${esc(!v[1] || v[1] === '-' ? '' : v[1])}</span>` : ''}</button>`; }).join(''); }
    let lines = ''; const boxes = [];
    const pts = set.map(([id, re, k, , t], i) => { const el = lay.children[i], parts = A.comp.filter(p => re.test(p.name)), part = parts[Math.min(k, parts.length - 1)]; if (!part) { el.hidden = true; return null; }
      let at = part.ctr; if (t != null) { const ax = [0, 1, 2].reduce((m, a) => part.hi[a] - part.lo[a] > part.hi[m] - part.lo[m] ? a : m, 0); at = part.ctr.slice(); at[ax] = part.lo[ax] + t * (part.hi[ax] - part.lo[ax]); }
      const [x, y, w] = project(at); if (w <= 0 || x < 0 || y < 0 || x > W || y > H) { el.hidden = true; return null; } el.hidden = false; return { el, x, y }; }).filter(Boolean);
    if (sel && pts.length > 10) {   // many labels: two columns at the edges, each in the order of its anchors from top to bottom, so leader lines do not cross
      for (const left of [true, false]) { const col = pts.filter(p => (p.x < cx) === left).sort((a, b) => a.y - b.y); if (!col.length) continue;
        const hs = col.map(p => p.el.offsetHeight || 22), gap = Math.max(1, Math.min(4, (H - 8 - hs.reduce((a, b) => a + b, 0)) / Math.max(1, col.length - 1)));
        let ly = 4; const ys = col.map((p, j) => { ly = Math.max(ly, p.y - hs[j] / 2); const y0 = ly; ly += hs[j] + gap; return y0; });
        for (let j = col.length - 1, lim = H - 4; j >= 0; j--) { ys[j] = Math.min(ys[j], lim - hs[j]); lim = ys[j] - gap; }   // pull back up off the bottom edge
        col.forEach((p, j) => { const bw = p.el.offsetWidth || 120, lx = left ? 4 : W - bw - 4; p.el.style.transform = `translate(${lx}px,${ys[j]}px)`;
          lines += `<line x1="${p.x}" y1="${p.y}" x2="${left ? lx + bw : lx}" y2="${ys[j] + hs[j] / 2}"/><circle cx="${p.x}" cy="${p.y}" r="3.5"/>`; }); }
      svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.innerHTML = lines; return; }
    pts.forEach(({ el, x, y }) => {
      let dx = x - cx, dy = y - cy; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
      let lx = x + dx * 54, ly = y + dy * 40; const bw = el.offsetWidth || 120, bh = el.offsetHeight || 22;
      lx = dx < 0 ? lx - bw : lx; ly -= bh / 2; lx = Math.max(4, Math.min(W - bw - 4, lx)); ly = Math.max(4, Math.min(H - bh - 4, ly));
      for (let it = 0, hit = true; hit && it < 12; it++) { hit = false;   // nudge a label away from every label already placed, on the side its anchor is on
        for (const b of boxes) if (lx < b[0] + b[2] && lx + bw > b[0] && ly < b[1] + b[3] && ly + bh > b[1]) { hit = true; ly = dy >= 0 ? b[1] + b[3] + 3 : b[1] - bh - 3; } }
      ly = Math.max(4, Math.min(H - bh - 4, ly));
      boxes.push([lx, ly, bw, bh]); el.style.transform = `translate(${lx}px,${ly}px)`;
      const ex = dx < 0 ? lx + bw : lx, ey = ly + bh / 2; lines += `<line x1="${x}" y1="${y}" x2="${ex}" y2="${ey}"/><circle cx="${x}" cy="${y}" r="3.5"/>`; });
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.innerHTML = lines; }
  function pickAt(mx, my) { const w = cv.width, h = cv.height; if (!w || !h) return null;
    if (!pickFb || pickFb.w !== w || pickFb.h !== h) { const fb = gl.createFramebuffer(), tx = gl.createTexture(), rb = gl.createRenderbuffer();
      gl.bindTexture(gl.TEXTURE_2D, tx); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
      gl.bindRenderbuffer(gl.RENDERBUFFER, rb); gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, w, h);
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tx, 0); gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, rb); pickFb = { fb, w, h }; }
    const x = Math.round(mx / cv.clientWidth * w), y = h - 1 - Math.round(my / cv.clientHeight * h), px = new Uint8Array(4);
    gl.bindFramebuffer(gl.FRAMEBUFFER, pickFb.fb); gl.viewport(0, 0, w, h); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.enable(gl.DEPTH_TEST); mats(); scene(true);
    gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return px[0] ? A.names[px[0] - 1] : null; }
  function init3d() { cv = $('#vmCanvas'); if (!cv) return; gl = cv.getContext('webgl', { antialias: true });
    if (!gl || !gl.getExtension('OES_element_index_uint')) { $('#vmHint').textContent = 'WebGL is not available: use the component buttons.'; return; }
    gl.getExtension('OES_standard_derivatives');
    const sh = (t, s) => { const o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o); return o; };
    prog = gl.createProgram(); gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(prog);
    aircraft(); reset();
    let drag = null, moved = 0;
    cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); drag = { x: e.clientX, y: e.clientY }; moved = 0; });
    cv.addEventListener('pointermove', e => { const r = cv.getBoundingClientRect();
      if (drag) { const dx = e.clientX - drag.x, dy = e.clientY - drag.y; moved += Math.abs(dx) + Math.abs(dy); drag.x = e.clientX; drag.y = e.clientY; cam.yaw += dx * 0.008; cam.pitch = Math.max(-1.5, Math.min(1.5, cam.pitch + dy * 0.008)); draw(); return; }
      const c = pickAt(e.clientX - r.left, e.clientY - r.top); if (c !== hoverComp) { hoverComp = c; $('#vmHint').textContent = c ? `${V.component_labels[c]}: ${V.claims.filter(x => x.component === c).length} claims, worst status ${worst(c)}. Click to list them.` : 'Hover a part to see its status; click to list its claims.'; draw(); } });
    cv.addEventListener('pointerup', e => { const r = cv.getBoundingClientRect(); if (moved < 6) { const c = pickAt(e.clientX - r.left, e.clientY - r.top); show(c || null); } drag = null; });
    cv.addEventListener('wheel', e => { e.preventDefault(); cam.d = Math.max(0.3, Math.min(6, cam.d * Math.exp(e.deltaY * 0.0012))); draw(); }, { passive: false });
    cv.addEventListener('dblclick', () => { reset(); draw(); });
    window.addEventListener('resize', draw); draw(); }
  // data, panels and listeners once (either tab can open first); the 3-D view once its canvas is visible
  let ready = false, gl3 = false;
  function init() { if (ready) return; ready = true; V = V || JSON.parse(document.getElementById('validData').textContent);
    kpis(); show(null); table(); mfg();
    const discs = [...new Set(V.claims.map(c => c.discipline))].sort(); $('#vmFDisc').innerHTML = '<option value="">All disciplines</option>' + discs.map(d => `<option>${esc(d)}</option>`).join('');
    for (const id of ['#vmFStatus', '#vmFDisc', '#vmFText']) $(id).addEventListener('input', table);
    $('#vmChips').addEventListener('click', e => { const b = e.target.closest('button'); if (b) show(b.dataset.comp === sel ? null : b.dataset.comp); });
    $('#vmTable').addEventListener('click', e => { const a = e.target.closest('.vm-go'); if (!a) return; e.preventDefault(); Proofs.open(a.dataset.id, $('#pfPanel')); });
    $('#vmPtrLayer').addEventListener('click', e => { const b = e.target.closest('.vm-ptr'); if (!b) return;
      goClaim(b.dataset.id); });
    $('#vmPanel').addEventListener('click', e => { const r = e.target.closest('.vm-row'); if (r) expand(r.parentElement.dataset.id, false); });
    Proofs.wire($('#vmPanel'), goClaim);
    $('#vmPtrs').addEventListener('change', draw); }
  const shown = el => el && !el.closest('[hidden]');
  return { redraw() { if (!document.getElementById('validData')) return;
    if (shown($('#vmMfg')) && !mfgDone) { V = V || JSON.parse(document.getElementById('validData').textContent); mfg(); }
    if (!shown($('#claimsMap')) && !shown($('#vmTable'))) return;
    init(); if (shown($('#vmCanvas'))) { if (!gl3) { gl3 = true; started = true; init3d(); } else draw(); } } };
})();
