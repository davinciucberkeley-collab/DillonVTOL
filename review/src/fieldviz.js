// ---------- 3-D results explorer: FEA stress and thermal fields on the real SOLIDWORKS meshes ----------
// Data: #feaData (analysis/fea_fields.json from cad/SimFields.cs) and #thermData fields (analysis/thermal/thermal_results.json).
// Drag to rotate, wheel or pinch to zoom, shift-drag or right-drag to pan, double-click to reset; hover reads the value.
const FieldViz = (() => {
  const $ = s => document.querySelector(s);
  let gl, cv, prog, buf = {}, C = null, cases = [], started = false, cam = null, tip, readout, scaleEl, raf = 0;
  // perceptually ordered ramps: stress (dark blue to yellow, viridis-like), heat (thermal camera, inferno-like)
  const RAMPS = {
    stress: [[0, [68, 1, 84]], [0.25, [59, 82, 139]], [0.5, [33, 145, 140]], [0.75, [94, 201, 98]], [1, [253, 231, 37]]],
    heat: [[0, [0, 0, 4]], [0.25, [87, 16, 110]], [0.5, [188, 55, 84]], [0.75, [249, 142, 9]], [1, [252, 255, 164]]] };
  const ramp = (name, t) => { const S = RAMPS[name]; t = Math.max(0, Math.min(1, t));
    for (let i = 1; i < S.length; i++) if (t <= S[i][0]) { const [t0, c0] = S[i - 1], [t1, c1] = S[i], k = (t - t0) / (t1 - t0); return c0.map((v, j) => (v + (c1[j] - v) * k) / 255); }
    return S[S.length - 1][1].map(v => v / 255); };

  function collect() {
    const out = [];
    try { const F = JSON.parse(document.getElementById('feaData').textContent);
      for (const [k, c] of Object.entries(F.cases)) out.push({ key: 'fea/' + k, label: c.title, unit: 'MPa', what: 'von Mises stress', ramp: 'stress', v: c.vertices, t: c.tris, val: c.von_MPa,
        ref: c.yield_MPa, refLabel: 'yield ' + c.yield_MPa + ' MPa', note: c.load + '; peak ' + c.max_von_MPa + ' MPa (SOLIDWORKS, all nodes; the surface shown peaks at ' + (c.max_surface_von_MPa != null ? c.max_surface_von_MPa : c.max_von_MPa) + ' MPa), ' + (c.yield_MPa / c.max_von_MPa).toFixed(1) + ' x below yield; displacement up to ' + c.max_disp_mm + ' mm', disp: c.disp_mm }); } catch (e) {}
    try { const T = JSON.parse(document.getElementById('thermData').textContent), lu = T.fields && T.fields.lift_unit;
      const names = { hover_90s: 'Lift unit after a 90 s hover', end_hover5: 'Lift unit at the end of the mission', steady_hover: 'Lift unit, steady hover (bound, never flown)' };
      if (lu) for (const k of ['hover_90s', 'end_hover5', 'steady_hover']) if (lu[k]) out.push({ key: 'therm/' + k, label: names[k], unit: '°C', what: 'temperature', ramp: 'heat', v: lu[k].vertices, t: lu[k].tris, val: lu[k].temps_C,
        ref: 80, refLabel: 'motor limit 80 °C', note: 'SOLIDWORKS transient thermal on a 35 °C day; motor, PA6-CF mount, boom and ESC' }); } catch (e) {}
    return out;
  }

  const VS = `attribute vec3 p; attribute vec3 n; attribute vec3 c; uniform mat4 M; uniform mat4 P; varying vec3 vc; varying vec3 vn; varying vec3 ve;
    void main(){ vc=c; vn=mat3(M)*n; vec4 e=M*vec4(p,1.0); ve=e.xyz; gl_Position=P*e; }`;
  const FS = `#extension GL_OES_standard_derivatives : enable
    precision highp float; varying vec3 vc; varying vec3 vn; varying vec3 ve; uniform vec3 L;
    void main(){ vec3 nn=normalize(cross(dFdx(ve),dFdy(ve))); float d=abs(dot(nn,normalize(L))); gl_FragColor=vec4(vc*(0.45+0.6*d),1.0); }`;
  function shader(type, src) { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; }

  // column-major 4x4 helpers
  const persp = (fov, a, n, f) => { const t = 1 / Math.tan(fov / 2); return [t / a, 0, 0, 0, 0, t, 0, 0, 0, 0, (f + n) / (n - f), -1, 0, 0, 2 * f * n / (n - f), 0]; };
  function view() {   // orbit about the target: yaw about Y (up), pitch, then distance
    const cy = Math.cos(cam.yaw), sy = Math.sin(cam.yaw), cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
    const R = [cy, sy * sp, -sy * cp, 0, 0, cp, sp, 0, sy, -cy * sp, cy * cp, 0, 0, 0, 0, 1];
    const tx = -(R[0] * cam.t[0] + R[4] * cam.t[1] + R[8] * cam.t[2]) + cam.pan[0], ty = -(R[1] * cam.t[0] + R[5] * cam.t[1] + R[9] * cam.t[2]) + cam.pan[1], tz = -(R[2] * cam.t[0] + R[6] * cam.t[1] + R[10] * cam.t[2]) - cam.d;
    R[12] = tx; R[13] = ty; R[14] = tz; return R; }

  function load(c) {
    C = c; const v = c.v, t = c.t, n = v.length / 3, nrm = new Float32Array(v.length), col = new Float32Array(v.length);
    for (let i = 0; i < t.length; i += 3) { const a = t[i] * 3, b = t[i + 1] * 3, d = t[i + 2] * 3;
      const ux = v[b] - v[a], uy = v[b + 1] - v[a + 1], uz = v[b + 2] - v[a + 2], wx = v[d] - v[a], wy = v[d + 1] - v[a + 1], wz = v[d + 2] - v[a + 2];
      const nx = uy * wz - uz * wy, ny = uz * wx - ux * wz, nz = ux * wy - uy * wx;
      for (const q of [a, b, d]) { nrm[q] += nx; nrm[q + 1] += ny; nrm[q + 2] += nz; } }
    let lo = Infinity, hi = -Infinity, imax = 0; c.val.forEach((x, i) => { if (x == null) return; if (x < lo) lo = x; if (x > hi) { hi = x; imax = i; } });
    c.lo = lo; c.hi = hi; c.imax = imax;
    for (let i = 0; i < n; i++) { const k = c.val[i] == null ? [0.5, 0.5, 0.5] : ramp(c.ramp, (c.val[i] - lo) / ((hi - lo) || 1)); col[i * 3] = k[0]; col[i * 3 + 1] = k[1]; col[i * 3 + 2] = k[2]; }
    const set = (name, data, attr) => { buf[name] = buf[name] || gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf[name]); gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW); };
    set('p', new Float32Array(v)); set('n', nrm); set('c', col);
    buf.i = buf.i || gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.i);
    const big = n > 65535; c.big = big; gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, big ? new Uint32Array(t) : new Uint16Array(t), gl.STATIC_DRAW);
    let mn = [Infinity, Infinity, Infinity], mx = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < n; i++) for (let j = 0; j < 3; j++) { mn[j] = Math.min(mn[j], v[i * 3 + j]); mx[j] = Math.max(mx[j], v[i * 3 + j]); }
    c.centre = mn.map((x, j) => (x + mx[j]) / 2); c.radius = Math.hypot(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]) / 2;
    reset(); legend(); readout.textContent = c.note; draw();
  }
  function reset() { cam = { yaw: -0.7, pitch: 0.42, d: C.radius * 1.9, t: C.centre.slice(), pan: [0, 0] }; }
  function mats() { cam.M = view(); cam.P = persp(0.7, cv.clientWidth / (cv.clientHeight || 1), C.radius * 0.01, C.radius * 20); }
  function hotspot() { if (!C) return; const i = C.imax, v = C.v; cam.t = [v[i * 3], v[i * 3 + 1], v[i * 3 + 2]]; cam.pan = [0, 0]; cam.d = C.radius * 0.7; mats(); draw(); probeAt(i); }

  function draw() {
    if (raf) return; raf = requestAnimationFrame(() => { raf = 0; if (!gl || !C) return;
      const dpr = Math.min(2, window.devicePixelRatio || 1), w = cv.clientWidth, h = cv.clientHeight;
      if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
      gl.viewport(0, 0, cv.width, cv.height); gl.clearColor(0.165, 0.184, 0.212, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.enable(gl.DEPTH_TEST);
      gl.useProgram(prog); mats();
      gl.uniformMatrix4fv(gl.getUniformLocation(prog, 'M'), false, cam.M); gl.uniformMatrix4fv(gl.getUniformLocation(prog, 'P'), false, cam.P);
      gl.uniform3f(gl.getUniformLocation(prog, 'L'), 0.3, 0.6, 1.0);
      for (const [name, size] of [['p', 3], ['n', 3], ['c', 3]]) { const loc = gl.getAttribLocation(prog, name); gl.bindBuffer(gl.ARRAY_BUFFER, buf[name]); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0); }
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.i); gl.drawElements(gl.TRIANGLES, C.t.length, C.big ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT, 0); }); }

  // screen position of vertex i (CSS px) and its depth
  function project(i) { const v = C.v, M = cam.M, P = cam.P, x = v[i * 3], y = v[i * 3 + 1], z = v[i * 3 + 2];
    const ex = M[0] * x + M[4] * y + M[8] * z + M[12], ey = M[1] * x + M[5] * y + M[9] * z + M[13], ez = M[2] * x + M[6] * y + M[10] * z + M[14];
    const cx = P[0] * ex, cy = P[5] * ey, w = -ez; return [(cx / w * 0.5 + 0.5) * cv.clientWidth, (1 - (cy / w * 0.5 + 0.5)) * cv.clientHeight, w]; }
  function probe(mx, my) {
    if (!C || !cam.M) return; let best = -1, bd = 1e9; const n = C.v.length / 3;
    for (let i = 0; i < n; i++) { const [sx, sy, w] = project(i); const dd = (sx - mx) ** 2 + (sy - my) ** 2; if (dd < 144 && w > 0) { const score = w * 1000 + dd * 0.001; if (score < bd) { bd = score; best = i; } } }
    if (best < 0) { tip.hidden = true; return; } probeAt(best);
  }
  function probeAt(i) { if (C.val[i] == null) { tip.hidden = true; return; } const [sx, sy] = project(i); tip.hidden = false;
    tip.textContent = C.what + ': ' + C.val[i].toFixed(C.unit === 'MPa' ? 1 : 0) + ' ' + C.unit + (C.disp ? ' · displacement ' + C.disp[i].toFixed(2) + ' mm' : '');
    // keep the tip inside the stage (it is offset 12 px right of the point)
    tip.style.left = Math.round(Math.max(0, Math.min(sx, cv.clientWidth - tip.offsetWidth - 16))) + 'px'; tip.style.top = Math.round(Math.max(tip.offsetHeight * 1.2, sy)) + 'px'; }

  function legend() {
    const n = 40, stops = []; for (let i = 0; i <= n; i++) { const k = ramp(C.ramp, i / n); stops.push(`rgb(${k.map(x => Math.round(x * 255)).join(',')}) ${(i / n * 100).toFixed(1)}%`); }
    const refPct = C.ref != null ? (C.ref - C.lo) / ((C.hi - C.lo) || 1) * 100 : null;
    scaleEl.innerHTML = `<span class="fz-lo">${C.lo.toFixed(C.unit === 'MPa' ? 1 : 0)} ${C.unit}</span><span class="fz-bar" style="background:linear-gradient(90deg,${stops.join(',')})"></span><span class="fz-hi">${C.hi.toFixed(C.unit === 'MPa' ? 1 : 0)} ${C.unit}</span>`
      + `<span class="fz-ref">${refPct != null && refPct <= 100 ? 'limit within the range shown: ' : ''}${C.refLabel}${refPct != null && refPct > 100 ? ', above the highest value shown' : ''}</span>`;
  }

  function init() {
    cv = $('#fzCanvas'); if (!cv) return; gl = cv.getContext('webgl', { antialias: true }); if (!gl) { readout.textContent = 'WebGL is not available in this browser.'; return; }
    gl.getExtension('OES_element_index_uint'); gl.getExtension('OES_standard_derivatives');  // face normals from derivatives: merged inner and outer tube walls cancel vertex normals
    prog = gl.createProgram(); gl.attachShader(prog, shader(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(prog);
    cases = collect(); const bar = $('#fzCases');
    bar.innerHTML = cases.map((c, i) => `<button type="button" data-i="${i}" aria-pressed="${i === 0}">${c.label.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</button>`).join('');
    bar.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; bar.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b)); tip.hidden = true; load(cases[+b.dataset.i]); });
    $('#fzHot').addEventListener('click', hotspot); $('#fzReset').addEventListener('click', () => { reset(); tip.hidden = true; draw(); });
    let drag = null, pts = new Map(), pinch = 0;
    cv.addEventListener('contextmenu', e => e.preventDefault());
    cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]); drag = { x: e.clientX, y: e.clientY, pan: e.shiftKey || e.button === 2 }; });
    cv.addEventListener('pointermove', e => { const r = cv.getBoundingClientRect();
      if (pts.has(e.pointerId)) pts.set(e.pointerId, [e.clientX, e.clientY]);
      if (pts.size === 2) { const [a, b] = [...pts.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]); if (pinch) cam.d = Math.max(C.radius * 0.08, Math.min(C.radius * 8, cam.d * pinch / d)); pinch = d; draw(); return; }
      if (drag) { const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY;
        if (drag.pan) { const s = cam.d * 0.0016; cam.pan[0] += dx * s; cam.pan[1] -= dy * s; } else { cam.yaw += dx * 0.008; cam.pitch = Math.max(-1.5, Math.min(1.5, cam.pitch + dy * 0.008)); }
        tip.hidden = true; draw(); } else probe(e.clientX - r.left, e.clientY - r.top); });
    const up = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch = 0; drag = null; };
    cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up); cv.addEventListener('pointerleave', () => { if (!drag) tip.hidden = true; });
    cv.addEventListener('wheel', e => { e.preventDefault(); cam.d = Math.max(C.radius * 0.08, Math.min(C.radius * 8, cam.d * Math.exp(e.deltaY * 0.0012))); tip.hidden = true; draw(); }, { passive: false });
    cv.addEventListener('dblclick', () => { reset(); tip.hidden = true; draw(); });
    cv.addEventListener('keydown', e => { const k = e.key; if (!C) return; if (k === 'ArrowLeft') cam.yaw -= 0.1; else if (k === 'ArrowRight') cam.yaw += 0.1; else if (k === 'ArrowUp') cam.pitch = Math.min(1.5, cam.pitch + 0.1); else if (k === 'ArrowDown') cam.pitch = Math.max(-1.5, cam.pitch - 0.1);
      else if (k === '+' || k === '=') cam.d = Math.max(C.radius * 0.08, cam.d * 0.85); else if (k === '-') cam.d = Math.min(C.radius * 8, cam.d / 0.85); else if (k === 'h') hotspot(); else return; e.preventDefault(); draw(); });
    window.addEventListener('resize', draw);
    if (cases.length) load(cases[0]); started = true;
  }
  return { redraw() { tip = tip || $('#fzTip'); readout = readout || $('#fzNote'); scaleEl = scaleEl || $('#fzScale'); const v = $('#fieldViz'); if (!v || v.closest('[hidden]')) return; if (!started) init(); else draw(); } };
})();
