// ---------- Claims map: every engineering claim tied to the part it is about ----------
// Data: #validData (analysis/validation/build_matrix.py -> validation_matrix.json; claims from check_aero.py, check_struct.py and
// analysis/cfd3d/verify_cfd.py) and the SOLIDWORKS assembly mesh #meshData (review/mesh.mjs, the CAD viewer's data, parsed lazily
// into the shared MESH). Each part is coloured by the worst status among the claims about its component; clicking a part (or a
// component chip) lists those claims with their equations, inputs, assumptions, evidence and independent check.
const ClaimsMap = (() => {
  const $ = s => document.querySelector(s);
  let V = null, gl, cv, prog, buf = {}, A = null, cam, raf = 0, started = false, sel = null, pickFb = null, hoverComp = null;
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
  const worst = comp => { const st = V.claims.filter(c => c.component === comp).map(c => c.status); return ORDER.find(s => st.includes(s)) || 'none'; };

  // ---------------------------------------------------------------- panels
  function kpis() { const c = V.counts, n = V.claims.length;
    $('#vmKpis').innerHTML = ORDER.slice().reverse().map(s => `<div class="kpi"><div class="l"><span class="chip ${CHIP[s]}">${s}</span></div><div class="v">${c[s] || 0}</div><div class="s">${esc(V.status_definitions[s])}</div></div>`).join('')
      + `<div class="kpi"><div class="l">Claims checked</div><div class="v">${n}</div><div class="s">${Object.entries(V.sources).map(([f, s]) => `${f} (${s.n})`).join(', ')}</div></div>`; }
  function chips() { const comps = Object.keys(V.component_labels);
    $('#vmChips').innerHTML = comps.map(k => { const n = V.claims.filter(c => c.component === k).length, w = worst(k);
      return `<button type="button" data-comp="${k}" aria-pressed="${k === sel}"><span class="vm-dot" style="background:rgb(${COL[w].map(x => Math.round(x * 255)).join(',')})"></span>${esc(V.component_labels[k])} <span class="vm-n">${n}</span></button>`; }).join(''); }
  function card(c) { const ic = c.independent_check || {}, d = ic.delta_pct;
    const val = c.value == null ? '—' : (typeof c.value === 'number' ? (Math.abs(c.value) >= 1000 ? c.value.toLocaleString(undefined, { maximumFractionDigits: 0 }) : +c.value.toPrecision(4)) : esc(c.value));
    const list = (h, a) => a && a.length ? `<h5>${h}</h5><ul>${a.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : '';
    const inputs = c.inputs && Object.keys(c.inputs).length ? `<h5>Inputs</h5><dl class="vm-in">${Object.entries(c.inputs).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(typeof v === 'object' ? JSON.stringify(v) : v)}</dd>`).join('')}</dl>` : '';
    return `<article class="vm-card vm-${CHIP[c.status]}" id="claim-${esc(c.id)}">
      <header><span class="vm-id">${esc(c.id)}</span><span class="chip ${CHIP[c.status]}">${esc(c.status)}</span><span class="vm-disc">${esc(c.discipline)}</span></header>
      <p class="vm-claim">${esc(c.claim)}</p>
      <div class="vm-num"><span>Claimed <b>${val}</b> ${esc(c.units || '')}</span>${ic.value != null ? `<span>Independent <b>${typeof ic.value === 'number' ? +ic.value.toPrecision(4) : esc(ic.value)}</b></span>` : ''}${d != null ? `<span>Δ <b class="${Math.abs(d) > 10 ? 'bad-t' : Math.abs(d) > 5 ? 'warn-t' : 'ok-t'}">${d >= 0 ? '+' : ''}${(+d).toFixed(1)} %</b></span>` : ''}</div>
      <p class="vm-why"><b>Why this status:</b> ${esc(c.status_reason)}</p>
      <details><summary>Equations, inputs, assumptions and evidence</summary>
        ${c.equations && c.equations.length ? `<h5>Equations</h5><ul class="vm-eq">${c.equations.map(e => `<li><code>${esc(e)}</code></li>`).join('')}</ul>` : ''}
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
    $('#vmPanel').innerHTML = `<div class="vm-ph"><h4>${esc(lab)}</h4><div>${cnt}</div>${ch ? `<a class="xref" href="#${ch}">Evidence chapter</a>` : ''}</div>${list.map(card).join('') || '<p>No claims recorded for this component.</p>'}`;
    draw(); }
  function table() {
    const f = { st: $('#vmFStatus').value, di: $('#vmFDisc').value, q: $('#vmFText').value.toLowerCase() };
    const rows = V.claims.filter(c => (!f.st || c.status === f.st) && (!f.di || c.discipline === f.di) && (!f.q || (c.id + ' ' + c.claim + ' ' + c.status_reason).toLowerCase().includes(f.q)));
    $('#vmTable tbody').innerHTML = rows.map(c => { const d = c.independent_check && c.independent_check.delta_pct;
      return `<tr><td><a href="#claim-${esc(c.id)}" data-comp="${c.component}" class="vm-go">${esc(c.id)}</a></td><td>${esc(V.component_labels[c.component])}</td><td>${esc(c.discipline)}</td><td>${esc(c.claim)}</td><td><span class="chip ${CHIP[c.status]}">${esc(c.status)}</span></td><td class="n">${d == null ? '—' : (d >= 0 ? '+' : '') + (+d).toFixed(1) + ' %'}</td><td>${esc(c.status_reason)}</td></tr>`; }).join('');
    $('#vmCount').textContent = `${rows.length} of ${V.claims.length} claims`; }
  function mfg() { const M = V.manufacturing, LV = { 'Ready': 'met', 'Needs minor specification': 'risk', 'Not ready': 'fail' };
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
      for (let j = 0; j < i.length; j++) I[io + j] = i[j] + vo; comp.push({ c, v0: vo, nv: k }); vo += k; io += i.length; });
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
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, cv.width, cv.height); gl.clearColor(0.165, 0.184, 0.212, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.enable(gl.DEPTH_TEST); mats(); colours(); scene(false); }); }
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
  function init() { started = true; V = JSON.parse(document.getElementById('validData').textContent);
    kpis(); show(null); table(); mfg();
    const discs = [...new Set(V.claims.map(c => c.discipline))].sort(); $('#vmFDisc').innerHTML = '<option value="">All disciplines</option>' + discs.map(d => `<option>${esc(d)}</option>`).join('');
    for (const id of ['#vmFStatus', '#vmFDisc', '#vmFText']) $(id).addEventListener('input', table);
    $('#vmChips').addEventListener('click', e => { const b = e.target.closest('button'); if (b) show(b.dataset.comp === sel ? null : b.dataset.comp); });
    $('#vmTable').addEventListener('click', e => { const a = e.target.closest('.vm-go'); if (!a) return; e.preventDefault(); show(a.dataset.comp);
      const el = document.getElementById('claim-' + a.textContent); if (el) { el.querySelector('details').open = true; el.scrollIntoView({ behavior: 'smooth', block: 'center' }); } });
    init3d(); }
  return { redraw() { const v = $('#claimsMap'); if (!v || v.closest('[hidden]') || !document.getElementById('validData')) return; if (!started) init(); else draw(); } };
})();
