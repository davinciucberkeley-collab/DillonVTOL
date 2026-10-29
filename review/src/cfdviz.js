// ---------- Whole-aircraft 3-D CFD explorer: SU2 incompressible Euler on the gmsh tetrahedral mesh ----------
// Data: #cfd3dData (analysis/cfd3d/postprocess.py pack -> out/viz/cfd3d_viz.json). Everything drawn comes from the solver files:
// the wall triangles are the SU2 mesh's own wall markers, Cp and speed are its nodal solution, streamlines are traced through the
// solution interpolated inside its tetrahedra, the wake planes and symmetry slice are samples of the same field, and the mesh
// layers are the real wall, symmetry-plane and cut-volume elements. Frames: the data is in the SU2 frame (x aft, y starboard,
// z up); drawn in the CAD frame (X = -x, Y = z, Z = y). The half model is mirrored to port for display (symmetric case, beta 0).
// Drag to rotate, wheel or pinch to zoom, shift-drag or right-drag to pan, double-click to reset; hover reads Cp and speed.
// Test hook: ?cfcase=L2_a8.0 selects that case on load.
const CfdViz = (() => {
  const $ = s => document.querySelector(s);
  let D = null, gl, cv, progS, cam = null, raf = 0, started = false, busy = false, tip, cur = null;
  const S = { field: 'cp', layers: new Set(['surface', 'stream', 'planes']), plane: 'cp', mirror: true, playing: true };
  const geo = {}, caseCache = {}, buf = {};
  // ---- colour ramps: diverging blue-white-red for Cp and vorticity, viridis-like for speed, element quality red -> green ----
  const RAMPS = {
    div: [[0, [33, 102, 172]], [0.25, [103, 169, 207]], [0.5, [247, 247, 247]], [0.75, [239, 138, 98]], [1, [178, 24, 43]]],
    seq: [[0, [68, 1, 84]], [0.25, [59, 82, 139]], [0.5, [33, 145, 140]], [0.75, [94, 201, 98]], [1, [253, 231, 37]]],
    qual: [[0, [200, 30, 40]], [0.3, [240, 160, 40]], [0.6, [210, 210, 80]], [1, [60, 170, 90]]] };
  const ramp = (name, t) => { const R = RAMPS[name]; t = Math.max(0, Math.min(1, t));
    for (let i = 1; i < R.length; i++) if (t <= R[i][0]) { const [t0, c0] = R[i - 1], [t1, c1] = R[i], k = (t - t0) / (t1 - t0); return c0.map((v, j) => (v + (c1[j] - v) * k) / 255); }
    return R[R.length - 1][1].map(v => v / 255); };
  const FIELDS = { cp: { label: 'Pressure coefficient Cp', lo: -1.6, hi: 1.0, ramp: 'div', mid: 0 }, s: { label: 'Speed |V| / V∞', lo: 0.4, hi: 1.5, ramp: 'seq' } };
  const PLANES = { cp: { label: 'Cp', lo: -0.08, hi: 0.08, ramp: 'div', mid: 0 }, omx: { label: 'Axial vorticity ωx·c/V∞ (sign flips on the mirrored side)', lo: -1, hi: 1, ramp: 'div', mid: 0 } };
  const colOf = (f, v) => { if (f.mid != null) { const a = Math.max(-f.lo, f.hi); return ramp(f.ramp, 0.5 + v / (2 * a)); } return ramp(f.ramp, (v - f.lo) / (f.hi - f.lo)); };

  // ---- data: base64 of gzipped typed arrays, inflated with the browser's DecompressionStream ----
  async function inflate(b64, T) { const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    const ab = await new Response(new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer(); return new T(ab); }
  const toCad = (x, y, z) => [-x, z, y];

  // ---- one shader: lit surfaces (face normals from derivatives) or unlit lines and points ----
  const VS = 'attribute vec3 p; attribute vec3 c; attribute float a; uniform mat4 M, P; uniform float ps; varying vec3 vc; varying vec3 ve; varying float va; void main(){ vec4 e = M * vec4(p,1.0); ve = e.xyz; vc = c; va = a; gl_Position = P * e; gl_PointSize = ps; }';
  const FS = '#extension GL_OES_standard_derivatives : enable\nprecision mediump float; varying vec3 vc; varying vec3 ve; varying float va; uniform float lit, alpha; void main(){ vec3 col = vc; if (lit > 0.5) { vec3 n = normalize(cross(dFdx(ve), dFdy(ve))); float d = abs(dot(n, normalize(vec3(0.3,0.6,1.0)))); col = vc * (0.45 + 0.6 * d); } gl_FragColor = vec4(col, alpha * va); }';
  function prog(vs, fs) { const sh = (t, s) => { const o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o); if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(o)); return o; };
    const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(p); return p; }

  // ---- camera: orbit about a target in the CAD frame ----
  const MV = new Float32Array(16), PR = new Float32Array(16);
  // presets by eye direction e (target -> eye, CAD frame): yaw = atan2(e.x, e.z), pitch = asin(e.y)
  const VIEWS = { iso: [[0.62, 0.5, 0.78], [-0.55, -0.02, 0], 3.1], front: [[1, 0.12, 0.02], [-0.3, -0.02, 0], 2.9], top: [[0.001, 1, 0.02], [-0.7, 0, 0], 3.4],
    side: [[0.02, 0.06, 1], [-0.7, -0.02, 0], 3.0], rear: [[-1, 0.28, 0.25], [-0.4, -0.02, 0], 3.0], tip: [[-0.55, 0.35, 0.75], [-0.25, 0.0, 1.15], 0.85] };
  function reset(view) { const asp = cv.clientWidth / (cv.clientHeight || 1) || 16 / 9, [e, t, d] = VIEWS[view || 'iso'], l = Math.hypot(...e);
    cam = { yaw: Math.atan2(e[0], e[2]), pitch: Math.asin(e[1] / l), d: d * (view === 'tip' ? 1 : Math.max(1, 1.7 / asp)), t: t.slice(), pan: [0, 0] }; }
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]], dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const norm = a => { const l = Math.hypot(...a) || 1; return a.map(x => x / l); };
  function mats() {
    const { yaw, pitch, d } = cam, cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const f = [-cp * sy, -sp, -cp * cy], t = cam.t, eye = [t[0] - f[0] * d, t[1] - f[1] * d, t[2] - f[2] * d];
    const r = norm(cross(f, [0, 1, 0])), u = cross(r, f);
    MV.set([r[0], u[0], -f[0], 0, r[1], u[1], -f[1], 0, r[2], u[2], -f[2], 0, -dot(r, eye) - cam.pan[0], -dot(u, eye) - cam.pan[1], dot(f, eye), 1]);
    const asp = cv.clientWidth / (cv.clientHeight || 1), n = Math.max(0.005, d * 0.03), fa = d + 8, k = 1 / Math.tan(0.35);
    PR.set([k / asp, 0, 0, 0, 0, k, 0, 0, 0, 0, (fa + n) / (n - fa), -1, 0, 0, 2 * fa * n / (n - fa), 0]);
  }

  // ---- buffers ----
  function vbo(name, data, el) { buf[name] = buf[name] || gl.createBuffer(); gl.bindBuffer(el ? gl.ELEMENT_ARRAY_BUFFER : gl.ARRAY_BUFFER, buf[name]); gl.bufferData(el ? gl.ELEMENT_ARRAY_BUFFER : gl.ARRAY_BUFFER, data, gl.STATIC_DRAW); return buf[name]; }
  // mirrored copy (port side) of a CAD-frame position array, and the index list with flipped winding
  function withMirror(P) { const n = P.length, out = new Float32Array(n * 2); out.set(P); for (let i = 0; i < n; i += 3) { out[n + i] = P[i]; out[n + i + 1] = P[i + 1]; out[n + i + 2] = -P[i + 2]; } return out; }
  function mirIdx(I, nv) { const out = new Uint32Array(I.length * 2); out.set(I); for (let i = 0; i < I.length; i += 3) { out[I.length + i] = I[i] + nv; out[I.length + i + 1] = I[i + 2] + nv; out[I.length + i + 2] = I[i + 1] + nv; } return out; }
  function edges(I, nv) { const seen = new Set(), out = []; for (let i = 0; i < I.length; i += 3) for (const [a, b] of [[I[i], I[i + 1]], [I[i + 1], I[i + 2]], [I[i + 2], I[i]]]) { const k = a < b ? a * nv + b : b * nv + a; if (!seen.has(k)) { seen.add(k); out.push(a, b); } } return new Uint32Array(out); }

  async function loadGeometry() {
    const s = D.surf, q = await inflate(s.pos, Uint16Array), I = await inflate(s.idx, Uint32Array), nv = s.nv, P = new Float32Array(nv * 3);
    for (let i = 0; i < nv; i++) { const x = s.lo[0] + q[i * 3] / 65535 * (s.hi[0] - s.lo[0]), y = s.lo[1] + q[i * 3 + 1] / 65535 * (s.hi[1] - s.lo[1]), z = s.lo[2] + q[i * 3 + 2] / 65535 * (s.hi[2] - s.lo[2]); P.set(toCad(x, y, z), i * 3); }
    geo.nv = nv; geo.P = P; geo.I = I; geo.groupOf = new Uint8Array(I.length / 3); s.groups.forEach((g, gi) => geo.groupOf.fill(gi, g.i0, g.i0 + g.n));
    vbo('sp', withMirror(P)); vbo('si', mirIdx(I, nv), true); geo.ni = I.length * 2;
    const E = edges(I, nv), E2 = new Uint32Array(E.length * 2); E2.set(E); for (let i = 0; i < E.length; i++) E2[E.length + i] = E[i] + nv; vbo('se', E2, true); geo.ne = E2.length;
    vbo('sg', new Float32Array(nv * 6).fill(0.62));
    // symmetry-plane triangles: the volume mesh's footprint on the centre plane
    const sp = await inflate(D.symmesh.pos, Float32Array), si = await inflate(D.symmesh.idx, Uint32Array), SP = new Float32Array(sp.length);
    for (let i = 0; i < sp.length; i += 3) SP.set(toCad(sp[i], sp[i + 1], sp[i + 2]), i);
    const YE = edges(si, sp.length / 3); vbo('yp', SP); vbo('ye', YE, true); geo.nye = YE.length; vbo('yc', new Float32Array(SP.length).fill(0.78));
    // tetrahedra cut by the crossflow plane: one polygon per cut element, edges coloured by that element's shape quality
    if (D.cut) { const segs = [], cols = [], x = -D.cut.x, cn = await inflate(D.cut.n, Uint8Array), yz = await inflate(D.cut.yz, Float32Array), cq = await inflate(D.cut.q, Uint8Array);
      let o = 0; for (let k = 0; k < cn.length; k++) { const n = cn[k], c = ramp('qual', cq[k] / 255); for (let j = 0; j < n; j++) { const a = o + j * 2, b = o + ((j + 1) % n) * 2;
        for (const zs of [1, -1]) { segs.push(x, yz[a + 1], zs * yz[a], x, yz[b + 1], zs * yz[b]); cols.push(...c, ...c); } } o += n * 2; }
      vbo('cp_', new Float32Array(segs)); vbo('cc_', new Float32Array(cols)); geo.ncut = segs.length / 3; }
  }

  async function loadCase(name) {
    if (caseCache[name]) return caseCache[name];
    const c = D.cases[name], cp = await inflate(c.cp, Int8Array), sp = await inflate(c.s, Uint8Array), out = { name, c, cp, sp };
    // streamlines (mm, int16), mirrored; coloured by local speed
    const sn = await inflate(c.stream.n, Uint16Array), sx = await inflate(c.stream.xyz, Int16Array), ss = await inflate(c.stream.s, Uint8Array);
    const lp = [], lc = [], li = [], lines = []; let o = 0;
    for (let k = 0; k < sn.length; k++) { const n = sn[k]; for (const zs of [1, -1]) { const base = lp.length / 3, pts = [];
      for (let j = 0; j < n; j++) { const q = (o + j) * 3, p = toCad(sx[q] / 1000, sx[q + 1] / 1000, sx[q + 2] / 1000); p[2] *= zs; lp.push(...p); pts.push(p); lc.push(...colOf(FIELDS.s, ss[o + j] / 100)); if (j) li.push(base + j - 1, base + j); }
      lines.push(pts); } o += n; }
    out.lp = new Float32Array(lp); out.lc = new Float32Array(lc); out.li = new Uint32Array(li); out.lines = lines;
    // wake planes and symmetry slice (int8 / uint8 grids)
    out.planes = []; for (const pl of c.planes) out.planes.push({ ...pl, cp: Array.from(await inflate(pl.cp, Int8Array), v => v / 100), omx: Array.from(await inflate(pl.omx, Int8Array), v => v / 20), inside: await inflate(pl.inside, Uint8Array) });
    const sy = c.sym; out.sym = { ...sy, cp: Array.from(await inflate(sy.cp, Int8Array), v => v / 40), s: Array.from(await inflate(sy.s, Uint8Array), v => v / 100), inside: await inflate(sy.inside, Uint8Array) };
    caseCache[name] = out; return out;
  }
  function surfColours(cs) { const nv = geo.nv, f = FIELDS[S.field] || FIELDS.cp, col = new Float32Array(nv * 6);
    for (let i = 0; i < nv; i++) { const v = S.field === 's' ? cs.sp[i] / 100 : cs.cp[i] / 40, k = colOf(f, v); col.set(k, i * 3); col.set(k, (nv + i) * 3); } return col; }
  function gridMesh(ny, nz, pos, val, f, skip, fade) { const P = [], Cc = [], I = [], Al = [], amp = Math.max(-f.lo, f.hi);
    for (let a = 0; a < ny; a++) for (let b = 0; b < nz; b++) { const v = val[a * nz + b]; P.push(...pos(a, b)); Cc.push(...colOf(f, v)); Al.push(fade ? Math.min(1, 0.04 + Math.abs(v) / (0.45 * amp)) : 1); }
    for (let a = 0; a + 1 < ny; a++) for (let b = 0; b + 1 < nz; b++) { const i = a * nz + b; if (skip && (skip[i] || skip[i + 1] || skip[i + nz] || skip[i + nz + 1])) continue; I.push(i, i + nz, i + 1, i + 1, i + nz, i + nz + 1); }
    return { P: new Float32Array(P), C: new Float32Array(Cc), A: new Float32Array(Al), I: new Uint32Array(I) }; }
  function buildFields(cs) {
    vbo('sc', surfColours(cs));
    vbo('lp', cs.lp); vbo('lc', cs.lc); vbo('li', cs.li, true); geo.nl = cs.li.length;
    const pf = PLANES[S.plane], parts = [];
    for (const pl of cs.planes) for (const zs of [1, -1]) parts.push(gridMesh(pl.ny, pl.nz, (a, b) => { const p = toCad(pl.x, pl.y0 + a * pl.h, pl.z0 + b * pl.h); p[2] *= zs; return p; },
      S.plane === 'omx' && zs < 0 ? pl.omx.map(v => -v) : pl[S.plane], pf, pl.inside, true));   // axial vorticity is a pseudo-scalar: mirroring flips its sign
    const sy = cs.sym, sf = S.field === 's' ? FIELDS.s : FIELDS.cp;
    parts.push(gridMesh(sy.nx, sy.nz, (a, b) => toCad(sy.x0 + a * sy.h, 0, sy.z0 + b * sy.h), S.field === 's' ? sy.s : sy.cp, sf, sy.inside));
    const cat = (k, T) => { const n = parts.reduce((s, p) => s + p[k].length, 0), o = new T(n); let at = 0, base = 0; for (const p of parts) { if (k === 'I') for (let i = 0; i < p.I.length; i++) o[at + i] = p.I[i] + base; else o.set(p[k], at); at += p[k].length; base += p.P.length / 3; } return o; };
    const nPl = cs.planes.length * 2;
    vbo('pp', cat('P', Float32Array)); vbo('pc', cat('C', Float32Array)); vbo('pa', cat('A', Float32Array)); vbo('pi', cat('I', Uint32Array), true);
    geo.npl = parts.slice(0, nPl).reduce((s, p) => s + p.I.length, 0); geo.nsym = parts[nPl].I.length;
    geo.part = new Float32Array(cs.lines.length * 2 * 3); vbo('qp', geo.part); vbo('qc', new Float32Array(geo.part.length).fill(1));
    legend();
  }

  // ---- drawing ----
  function use(posBuf, colBuf, lit, alpha, ps, aBuf) { gl.useProgram(progS); const la = gl.getAttribLocation(progS, 'a');
    if (aBuf) { gl.bindBuffer(gl.ARRAY_BUFFER, buf[aBuf]); gl.enableVertexAttribArray(la); gl.vertexAttribPointer(la, 1, gl.FLOAT, false, 0, 0); } else { gl.disableVertexAttribArray(la); gl.vertexAttrib1f(la, 1); }
    for (const [nm, b] of [['p', posBuf], ['c', colBuf]]) { const loc = gl.getAttribLocation(progS, nm); gl.bindBuffer(gl.ARRAY_BUFFER, buf[b]); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 3, gl.FLOAT, false, 0, 0); }
    gl.uniformMatrix4fv(gl.getUniformLocation(progS, 'M'), false, MV); gl.uniformMatrix4fv(gl.getUniformLocation(progS, 'P'), false, PR);
    gl.uniform1f(gl.getUniformLocation(progS, 'lit'), lit ? 1 : 0); gl.uniform1f(gl.getUniformLocation(progS, 'alpha'), alpha); gl.uniform1f(gl.getUniformLocation(progS, 'ps'), ps || 1); }
  function draw() { if (!raf) raf = requestAnimationFrame(frame); }
  function frame(now) {
    raf = 0; if (!gl || !cur) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1), w = cv.clientWidth, h = cv.clientHeight;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    gl.viewport(0, 0, cv.width, cv.height); gl.clearColor(0.165, 0.184, 0.212, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.enable(gl.DEPTH_TEST);
    mats();
    const Ly = S.layers, half = !S.mirror;
    if (Ly.has('surface')) { use('sp', S.field === 'grey' ? 'sg' : 'sc', true, 1); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.si); gl.drawElements(gl.TRIANGLES, half ? geo.ni / 2 : geo.ni, gl.UNSIGNED_INT, 0); }
    if (Ly.has('wall')) { use('sp', 'sg', false, 1); const lc = gl.getAttribLocation(progS, 'c'); gl.disableVertexAttribArray(lc);
      if (Ly.has('surface')) gl.vertexAttrib3f(lc, 0.08, 0.09, 0.11); else gl.vertexAttrib3f(lc, 0.82, 0.85, 0.9);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.se); gl.drawElements(gl.LINES, half ? geo.ne / 2 : geo.ne, gl.UNSIGNED_INT, 0); }
    if (Ly.has('stream')) { gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); use('lp', 'lc', false, 0.6); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.li); gl.drawElements(gl.LINES, geo.nl, gl.UNSIGNED_INT, 0); gl.disable(gl.BLEND);
      if (S.playing) { particles(now || 0); use('qp', 'qc', false, 1, 4 * dpr); gl.drawArrays(gl.POINTS, 0, geo.part.length / 3); } }
    if (Ly.has('symmesh')) { use('yp', 'yc', false, 1); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.ye); gl.drawElements(gl.LINES, geo.nye, gl.UNSIGNED_INT, 0); }
    if (Ly.has('cut') && geo.ncut) { use('cp_', 'cc_', false, 1); gl.drawArrays(gl.LINES, 0, geo.ncut); }
    if (Ly.has('planes') || Ly.has('sym')) { gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false);
      use('pp', 'pc', false, 0.85, 1, 'pa'); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.pi);
      if (Ly.has('planes')) gl.drawElements(gl.TRIANGLES, geo.npl, gl.UNSIGNED_INT, 0);
      if (Ly.has('sym')) gl.drawElements(gl.TRIANGLES, geo.nsym, gl.UNSIGNED_INT, geo.npl * 4);
      gl.disable(gl.BLEND); gl.depthMask(true); }
    if (Ly.has('stream') && S.playing && !document.hidden) raf = requestAnimationFrame(frame);
  }
  function particles(now) { const L = cur.lines, P = geo.part; let k = 0;
    for (let i = 0; i < L.length; i++) { const pts = L[i], n = pts.length; for (let j = 0; j < 2; j++) { const u = ((now * 0.015 / n + j / 2 + i * 0.137) % 1) * (n - 1), a = Math.floor(u), f = u - a, p = pts[a], q = pts[Math.min(n - 1, a + 1)];
      P[k++] = p[0] + (q[0] - p[0]) * f; P[k++] = p[1] + (q[1] - p[1]) * f; P[k++] = p[2] + (q[2] - p[2]) * f; } }
    gl.bindBuffer(gl.ARRAY_BUFFER, buf.qp); gl.bufferData(gl.ARRAY_BUFFER, P.subarray(0, k), gl.DYNAMIC_DRAW); }

  // ---- hover probe: nearest wall vertex on screen, front-most ----
  function project(x, y, z) { const M = MV, P = PR, ex = M[0] * x + M[4] * y + M[8] * z + M[12], ey = M[1] * x + M[5] * y + M[9] * z + M[13], ez = M[2] * x + M[6] * y + M[10] * z + M[14], w = -ez;
    return [(P[0] * ex / w * 0.5 + 0.5) * cv.clientWidth, (1 - (P[5] * ey / w * 0.5 + 0.5)) * cv.clientHeight, w]; }
  const groupName = k => ({ wing: 'Wing', htail: 'Horizontal tail', fins: 'Fins, shoes, tail servos', pod: 'Pod, canopy, pusher motor', booms: 'Booms, mounts, clamps', motors: 'Lift motors (stopped)', gear: 'Landing gear' }[k] || k);
  let vgroup = null, lastProbe = 0;
  function groupOfVertex(v) { if (!vgroup) { vgroup = new Uint8Array(geo.nv); const I = geo.I; for (let t = 0; t < I.length / 3; t++) for (let k = 0; k < 3; k++) vgroup[I[t * 3 + k]] = geo.groupOf[t]; }
    return groupName(D.surf.groups[vgroup[v]].name); }
  function probe(mx, my) { if (!cur || !S.layers.has('surface')) { tip.hidden = true; return; } const now = performance.now(); if (now - lastProbe < 60) return; lastProbe = now;
    const P = geo.P, nv = geo.nv; let best = -1, bw = 1e9, side = 1;
    for (const zs of S.mirror ? [1, -1] : [1]) for (let i = 0; i < nv; i++) { const [sx, sy, w] = project(P[i * 3], P[i * 3 + 1], zs * P[i * 3 + 2]); if (w > 0 && w < bw && (sx - mx) ** 2 + (sy - my) ** 2 < 49) { bw = w; best = i; side = zs; } }
    if (best < 0) { tip.hidden = true; return; }
    tip.hidden = false; tip.textContent = `${groupOfVertex(best)} · Cp ${(cur.cp[best] / 40).toFixed(2)} · |V|/V∞ ${(cur.sp[best] / 100).toFixed(2)} · X ${P[best * 3].toFixed(3)} Z ${(side * P[best * 3 + 2]).toFixed(3)} m`;
    tip.style.left = Math.round(Math.min(mx, cv.clientWidth - tip.offsetWidth - 16)) + 'px'; tip.style.top = Math.round(Math.max(tip.offsetHeight * 1.2, my)) + 'px'; }

  // ---- legend, numbers, residual history, mesh comparison ----
  const stopsOf = (f, lo, hi) => { const out = [], n = 30; for (let i = 0; i <= n; i++) out.push(`rgb(${colOf(f, lo + (hi - lo) * i / n).map(x => Math.round(x * 255)).join(',')}) ${(i / n * 100).toFixed(1)}%`); return out.join(','); };
  function legend() { const f = FIELDS[S.field], pf = PLANES[S.plane], pa = Math.max(-pf.lo, pf.hi); let h = '';
    if (f && S.layers.has('surface')) { const lo = f.mid != null ? -Math.max(-f.lo, f.hi) : f.lo, hi = f.mid != null ? Math.max(-f.lo, f.hi) : f.hi;
      h += `<span class="cf-lk">Surface${S.layers.has('sym') ? ' and symmetry slice' : ''}: ${f.label}</span><span>${lo.toFixed(1)}</span><span class="fz-bar" style="background:linear-gradient(90deg,${stopsOf(f, lo, hi)})"></span><span>${hi.toFixed(1)}</span>`; }
    if (S.layers.has('stream')) h += `<span class="cf-lk">Streamlines: speed |V|/V∞</span><span>0.4</span><span class="fz-bar" style="background:linear-gradient(90deg,${stopsOf(FIELDS.s, 0.4, 1.5)})"></span><span>1.5</span>`;
    if (S.layers.has('planes')) h += `<span class="cf-lk">Wake planes (X = ${(cur ? cur.planes.map(p => (-p.x).toFixed(2)).join(', ') : '')} m): ${pf.label}; faint where near zero</span><span>${(-pa).toFixed(2)}</span><span class="fz-bar" style="background:linear-gradient(90deg,${stopsOf(pf, -pa, pa)})"></span><span>${pa.toFixed(2)}</span>`;
    if (S.layers.has('cut') && D.cut) h += `<span class="cf-lk">Volume cut at X = ${(-D.cut.x).toFixed(2)} m (${D.cut.count.toLocaleString()} tetrahedra): shape quality 0 → 1</span><span class="fz-bar" style="background:linear-gradient(90deg,${[0, .3, .6, 1].map(t => `rgb(${ramp('qual', t).map(x => Math.round(x * 255)).join(',')}) ${t * 100}%`).join(',')})"></span>`;
    $('#cfLegend').innerHTML = h; }
  const f4 = x => x == null ? '—' : (+x).toFixed(4), f3 = x => x == null ? '—' : (+x).toFixed(3);
  function numbers(name) { const R = D.results, c = R && R.cases[name], p = D.cases[name].post;
    if (!c) { $('#cfNums').innerHTML = ''; return; }
    const comp = Object.entries(c.components || {}).map(([k, v]) => `<tr><td>${groupName(k)}</td><td class="n">${f4(v.CL)}</td><td class="n">${f4(v.CMy)}</td></tr>`).join('');
    $('#cfNums').innerHTML = `<div class="kpis cf-k">
      <div class="kpi"><div class="l">CL</div><div class="v">${f3(c.CL)}</div><div class="s">SU2; own pressure integration ${f3(p.integrated.CL)}</div></div>
      <div class="kpi"><div class="l">CMy about the CG</div><div class="v">${f3(c.CMy)}</div><div class="s">nose-up positive, elevator 0°</div></div>
      <div class="kpi"><div class="l">Induced drag (Trefftz plane)</div><div class="v">${f4(p.trefftz.CDi)}</div><div class="s">surface CD ${f4(c.CD)} is not a drag prediction (inviscid)</div></div>
      <div class="kpi"><div class="l">Convergence</div><div class="v">${c.iterations} it</div><div class="s">log10 rms(p) ${c.rms_p_first.toFixed(1)} → ${c.rms_p_last.toFixed(1)}; Cauchy CL ${(+c.cauchy_CL).toExponential(1)}</div></div></div>
      <div class="grid2 cf-g"><div class="tbl"><table><thead><tr><th>Component</th><th class="n">CL share</th><th class="n">CMy share</th></tr></thead><tbody>${comp}</tbody></table></div>
      <div class="tbl"><table><tbody><tr><td>Peak speed</td><td class="n">${p.field_extrema.speed_max_over_V.toFixed(2)} V∞</td></tr><tr><td>Cp min / max (nodes)</td><td class="n">${p.field_extrema.Cp_min.toFixed(2)} / ${p.field_extrema.Cp_max.toFixed(2)}</td></tr>
      <tr><td>Symmetry plane, max |v<sub>y</sub>|/V∞</td><td class="n">${p.symmetry_max_abs_vy_over_V.toExponential(1)}</td></tr><tr><td>Far field |V|/V∞</td><td class="n">${p.farfield_speed_ratio.min.toFixed(3)}–${p.farfield_speed_ratio.max.toFixed(3)}</td></tr>
      <tr><td>Mesh</td><td class="n">L${c.level}: ${c.tets.toLocaleString()} tets</td></tr><tr><td>Solver wall time</td><td class="n">${c.wall_s != null ? Math.round(c.wall_s / 60) + ' min' : '—'}</td></tr></tbody></table></div></div>`;
    hist(name); }
  function hist(name) { const h = D.cases[name].hist, svg = $('#cfHist'); if (!h || !svg || !h.it || h.it.length < 2) return;
    const W = 640, H = 220, l = 48, r = 64, t = 14, b = 30, it = h.it, n = it.length, X = i => l + (it[i] - it[0]) / ((it[n - 1] - it[0]) || 1) * (W - l - r);
    const rp = h.rp, rmin = Math.floor(Math.min(...rp)), rmax = Math.ceil(Math.max(...rp)), Y = v => t + (rmax - v) / ((rmax - rmin) || 1) * (H - t - b);
    const cl = h.cl, cl1 = cl[n - 1], cmin = cl1 - 0.1, cmax = cl1 + 0.1, Yc = v => t + (cmax - Math.max(cmin, Math.min(cmax, v))) / (cmax - cmin) * (H - t - b);
    const path = (arr, f) => arr.map((v, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ',' + f(v).toFixed(1)).join('');
    let g = ''; for (let v = rmin; v <= rmax; v++) g += `<line x1="${l}" x2="${W - r}" y1="${Y(v)}" y2="${Y(v)}" class="grid"/><text x="${l - 6}" y="${Y(v) + 4}" text-anchor="end" class="tick">${v}</text>`;
    svg.innerHTML = `${g}<path d="${path(rp, Y)}" class="cf-res" fill="none"/><path d="${path(cl, Yc)}" class="cf-cl" fill="none"/>
      <text x="${l}" y="${H - 8}" class="tick">iteration ${it[0]}</text><text x="${W - r}" y="${H - 8}" text-anchor="end" class="tick">${it[n - 1]}</text>
      <text x="${W - r + 6}" y="${Yc(cl1) + 4}" class="tick">CL ${cl1.toFixed(3)}</text><text x="${l + 6}" y="${t + 10}" class="tick">solid: log10 rms(p) (left axis) · dashed: CL, ±0.1 window</text>`; }
  async function meshCompare() { const box = $('#cfMeshCmp'); if (!box || box.dataset.done) return; box.dataset.done = 1; const out = [];
    for (const [lv, s] of Object.entries(D.levels)) { if (!s.tip_patch) continue; const P = await inflate(s.tip_patch.pos, Float32Array), I = await inflate(s.tip_patch.idx, Uint32Array);
      let d = ''; const X = x => (x + 0.02) / 0.33 * 300, Yp = y => (1.205 - y) / 0.27 * 240;   // SU2 x (aft) across, y (span) down: top view of the outer wing
      for (let i = 0; i < I.length; i += 3) { const a = I[i] * 3, b = I[i + 1] * 3, c = I[i + 2] * 3; d += `M${X(P[a]).toFixed(1)},${Yp(P[a + 1]).toFixed(1)}L${X(P[b]).toFixed(1)},${Yp(P[b + 1]).toFixed(1)}L${X(P[c]).toFixed(1)},${Yp(P[c + 1]).toFixed(1)}Z`; }
      out.push(`<figure class="cf-patch"><svg viewBox="0 0 300 240" role="img" aria-label="Wing-tip surface mesh, level ${lv}"><path d="${d}" class="cf-wire"/></svg><figcaption>L${lv}: ${s.tip_patch.n.toLocaleString()} wall triangles on the outer 0.25 m (top view)</figcaption></figure>`); }
    box.innerHTML = out.join(''); }

  // ---- tables filled from the packed results (no WebGL needed) ----
  const CHIP = { 'Verified': 'met', 'Partially Verified': 'risk', 'Unverified': 'open', 'Failed': 'fail' };
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  function tables() {
    const R = D.results; if (!R) return;
    $('#cfMeshTable tbody').innerHTML = Object.entries(D.levels).map(([lv, s]) => `<tr><td>L${lv}</td><td class="n">${s.tetrahedra.toLocaleString()}</td><td class="n">${s.nodes.toLocaleString()}</td><td class="n">${(s.surface_triangles.wing || 0).toLocaleString()}</td><td class="n">${(s.sizes_m.wall_default * 1000).toFixed(1)}</td><td class="n">${(s.sizes_m.trailing_edges * 1000).toFixed(1)}</td><td class="n">${s.quality_minSICN.min.toFixed(3)}</td><td class="n">${s.quality_minSICN.p01.toFixed(3)}</td><td class="n">${s.quality_minSICN.mean.toFixed(2)}</td></tr>`).join('');
    const rows = Object.entries(R.cases).sort((a, b) => a[1].level - b[1].level || a[1].alpha_deg - b[1].alpha_deg);
    $('#cfCaseTable tbody').innerHTML = rows.map(([n, c]) => { const p = D.post && D.post[n];
      return `<tr><td>${n}</td><td class="n">${c.alpha_deg.toFixed(1)}°</td><td class="n">${c.tets.toLocaleString()}</td><td class="n">${f4(c.CL)}</td><td class="n">${f4(c.CMy)}</td><td class="n">${p ? f4(p.trefftz.CDi) : '—'}</td><td class="n">${p ? f4(p.integrated.CL) : '—'}</td><td class="n">${c.iterations}</td><td class="n">${(c.rms_p_first - c.rms_p_last).toFixed(1)}</td></tr>`; }).join('');
    if (D.checks) $('#cfCheckTable tbody').innerHTML = D.checks.map(c => `<tr><td><b>${c.id}</b> ${esc(c.claim)}</td><td><span class="chip ${CHIP[c.status]}">${c.status}</span></td><td>${esc(c.status_reason)}</td></tr>`).join('');
    if (D.geometry) { $('#cfGeoTable tbody').innerHTML = D.geometry.defeaturing.map(r => `<tr><td>${esc(r.cad_parts)}</td><td>${esc(r.cfd_representation)}</td><td>${esc(r.differences)}</td></tr>`).join('');
      $('#cfFidTable tbody').innerHTML = D.geometry.fidelity.map(r => `<tr><td>${esc(r.part)}</td><td class="n">${r.n_step}</td><td class="n">${r.max_bbox_dev_mm.toFixed(1)}</td><td>${esc(r.note || '')}</td></tr>`).join(''); }
    const g = R.cases['L3_a4.0'] || R.cases['L2_a4.0'], ck = id => D.checks && D.checks.find(c => c.id === id), gc = ck('CFD-02'), sl = ck('CFD-05'), np = ck('CFD-07');
    const sc = ck('CFD-12'), cp1 = ck('CFD-11');
    if (g) $('#cfVerdict').innerHTML = `<b>The whole-aircraft CFD ran on three meshes: CL ${g.CL.toFixed(3)} at α 4° with the elevator at 0° on the finest. It confirms the neutral point${np ? ` (${np.value.toFixed(1)} % MAC against AVL 39.8 %)` : ''} and the induced drag, but its absolute lift is mesh-limited.</b> `
      + (sl ? `The lift slope is ${sl.value.toFixed(2)} /rad against AVL ${sl.independent_check.value.toFixed(2)}, and a 2-D check with the same numerics shows the scheme loses lift at this wall spacing (${sc ? sc.status : '—'}, CFD-12). ` : '')
      + (cp1 && cp1.status === 'Failed' ? 'Local Cp at the tail leading edge overshoots the stagnation value (CFD-11). ' : '') + 'The run is inviscid, so it predicts no profile drag or stall.';
  }

  // ---- case selection and controls ----
  async function choose(name) { busy = true; $('#cfNote').textContent = 'Loading ' + name + ' …'; cur = await loadCase(name); buildFields(cur); numbers(name); busy = false;
    const c = D.cases[name]; $('#cfNote').textContent = `Case ${name}: cruise, V∞ ${D.results.conditions.V_mps} m/s, α ${c.alpha}°, β 0°, elevator 0°, power off; mesh L${D.level} (${D.levels[D.level].tetrahedra.toLocaleString()} tetrahedra).`;
    document.querySelectorAll('#cfCases button').forEach(b => b.setAttribute('aria-pressed', b.dataset.case === name)); draw(); }
  async function init() {
    cv = $('#cfCanvas'); tip = $('#cfTip'); if (!cv) return; started = true;
    D = JSON.parse(document.getElementById('cfd3dData').textContent); tables();
    if (typeof DecompressionStream === 'undefined') { $('#cfNote').textContent = 'This browser cannot inflate the embedded CFD data (no DecompressionStream). Use a current Chrome, Edge, Firefox or Safari 16.4+.'; return; }
    gl = cv.getContext('webgl', { antialias: true }); if (!gl || !gl.getExtension('OES_element_index_uint')) { $('#cfNote').textContent = 'WebGL with 32-bit indices is not available in this browser.'; return; }
    gl.getExtension('OES_standard_derivatives'); progS = prog(VS, FS); gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1, 1);
    $('#cfNote').textContent = 'Inflating the mesh …'; await loadGeometry(); reset('iso');
    const names = Object.keys(D.cases).sort((a, b) => D.cases[a].alpha - D.cases[b].alpha);
    $('#cfCases').innerHTML = names.map(n => `<button type="button" data-case="${n}">α ${D.cases[n].alpha}°</button>`).join('');
    $('#cfCases').addEventListener('click', e => { const b = e.target.closest('button'); if (b && !busy) choose(b.dataset.case); });
    const radio = (sel, key, attr) => document.querySelectorAll(sel + ' button').forEach(b => b.addEventListener('click', () => { S[key] = b.dataset[attr]; document.querySelectorAll(sel + ' button').forEach(x => x.setAttribute('aria-pressed', x === b)); if (cur) buildFields(cur); draw(); }));
    radio('#cfField', 'field', 'f'); radio('#cfPlaneF', 'plane', 'p');
    document.querySelectorAll('#cfLayers input[type=checkbox][value]').forEach(i => { i.checked = S.layers.has(i.value); i.addEventListener('change', () => { i.checked ? S.layers.add(i.value) : S.layers.delete(i.value); legend(); draw(); }); });
    document.querySelectorAll('#cfCam button').forEach(b => b.addEventListener('click', () => { reset(b.dataset.cam); draw(); }));
    $('#cfMirror').addEventListener('change', e => { S.mirror = e.target.checked; draw(); });
    $('#cfPlay').addEventListener('click', e => { S.playing = !S.playing; e.target.setAttribute('aria-pressed', !S.playing); e.target.textContent = S.playing ? 'Pause particles' : 'Play particles'; draw(); });
    let drag = null, pts = new Map(), pinch = 0; const dcl = d => Math.max(0.05, Math.min(8, d));
    cv.addEventListener('contextmenu', e => e.preventDefault());
    cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]); drag = { x: e.clientX, y: e.clientY, pan: e.shiftKey || e.button === 2 }; });
    cv.addEventListener('pointermove', e => { const r = cv.getBoundingClientRect(); if (pts.has(e.pointerId)) pts.set(e.pointerId, [e.clientX, e.clientY]);
      if (pts.size === 2) { const [a, b] = [...pts.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]); if (pinch) cam.d = dcl(cam.d * pinch / d); pinch = d; draw(); return; }
      if (drag) { const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY;
        if (drag.pan) { const s = cam.d * 0.0016; cam.pan[0] -= dx * s; cam.pan[1] += dy * s; } else { cam.yaw += dx * 0.008; cam.pitch = Math.max(-1.55, Math.min(1.55, cam.pitch + dy * 0.008)); } tip.hidden = true; draw(); }
      else probe(e.clientX - r.left, e.clientY - r.top); });
    const up = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch = 0; drag = null; };
    cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up); cv.addEventListener('pointerleave', () => { tip.hidden = true; });
    cv.addEventListener('wheel', e => { e.preventDefault(); cam.d = dcl(cam.d * Math.exp(e.deltaY * 0.0012)); draw(); }, { passive: false });
    cv.addEventListener('dblclick', () => { reset('iso'); draw(); });
    cv.addEventListener('keydown', e => { const k = e.key; if (k === 'ArrowLeft') cam.yaw -= 0.1; else if (k === 'ArrowRight') cam.yaw += 0.1; else if (k === 'ArrowUp') cam.pitch = Math.min(1.55, cam.pitch + 0.1); else if (k === 'ArrowDown') cam.pitch = Math.max(-1.55, cam.pitch - 0.1); else if (k === '+' || k === '=') cam.d = dcl(cam.d * 0.85); else if (k === '-') cam.d = dcl(cam.d / 0.85); else return; e.preventDefault(); draw(); });
    window.addEventListener('resize', draw);
    const q = /[?&]cfcase=([\w.]+)/.exec(location.search);
    await choose(q && D.cases[q[1]] ? q[1] : (names.find(n => D.cases[n].alpha === 4) || names[0]));
    meshCompare();
  }
  return { redraw() { const v = $('#cfdViz'); if (!v || v.closest('[hidden]') || !document.getElementById('cfd3dData')) return; if (!started) init(); else draw(); } };
})();
