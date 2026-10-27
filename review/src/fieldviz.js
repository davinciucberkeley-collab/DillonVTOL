// ---------- 3-D results explorer: FEA stress and thermal fields placed on the whole SOLIDWORKS aircraft ----------
// Data: #feaData (analysis/fea_fields.json from cad/SimFields.cs), #thermData fields (analysis/thermal/thermal_results.json) and the
// assembly mesh #meshData (review/mesh.mjs: pre-rotated part meshes + comp translations, the CAD viewer's data, parsed lazily into
// the shared MESH). Frame: the SOLIDWORKS assembly one, X forward, Y up, Z right, metres. Each study mesh is in its own local frame;
// place() below maps it onto the aircraft from the comp positions and cad/params.txt (CADP), never by eye.
// Drag to rotate, wheel or pinch to zoom, shift-drag or right-drag to pan, double-click to reset; hover reads the value.
// Test hook: ?fzcase=N selects case N on load, ?fzpeak=1 then flies to its peak (used for the headless screenshots).
const FieldViz = (() => {
  const $ = s => document.querySelector(s);
  let gl, cv, prog, U = {}, A = null, buf = {}, C = null, cases = [], started = false, cam = null, tip, readout, scaleEl, raf = 0, pickFb = null;
  // perceptually ordered ramps: stress (dark blue to yellow, viridis-like), heat (thermal camera, inferno-like)
  const RAMPS = {
    stress: [[0, [68, 1, 84]], [0.25, [59, 82, 139]], [0.5, [33, 145, 140]], [0.75, [94, 201, 98]], [1, [253, 231, 37]]],
    heat: [[0, [0, 0, 4]], [0.25, [87, 16, 110]], [0.5, [188, 55, 84]], [0.75, [249, 142, 9]], [1, [252, 255, 164]]] };
  const ramp = (name, t) => { const S = RAMPS[name]; t = Math.max(0, Math.min(1, t));
    for (let i = 1; i < S.length; i++) if (t <= S[i][0]) { const [t0, c0] = S[i - 1], [t1, c1] = S[i], k = (t - t0) / (t1 - t0); return c0.map((v, j) => (v + (c1[j] - v) * k) / 255); }
    return S[S.length - 1][1].map(v => v / 255); };
  const GREY = [0.72, 0.745, 0.78], GHOST = [0.86, 0.88, 0.91], GHOST_A = 0.2, FIELD_ID = 60000;
  const FAST = /^[FNWI]\d\d_/, base = n => n.split('~')[0], f3 = x => x.toFixed(3);

  // ---- the aircraft: one vertex buffer of every component in assembly coordinates, per-case index lists ----
  function aircraft() {
    if (typeof MESH !== 'undefined' && !MESH) MESH = JSON.parse(document.getElementById('meshData').textContent);
    const M = MESH, dec = (s, T) => { const b = atob(s), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return new T(u.buffer); };
    const parts = {}; let nv = 0, ni = 0;
    for (const [n] of M.comps) { if (!parts[n]) { const p = M.parts[n]; parts[n] = { v: dec(p.v, Float32Array), i: dec(p.i, p.w === 4 ? Uint32Array : Uint16Array) }; } nv += parts[n].v.length / 3; ni += parts[n].i.length; }
    const P = new Float32Array(nv * 3), Q = new Float32Array(nv * 3), I = new Uint32Array(ni), comps = [], lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
    let vo = 0, io = 0;
    M.comps.forEach(([n, x, y, z], ci) => { const { v, i } = parts[n], k = v.length / 3, o = [x, y, z], mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9], id = ci + 1;
      for (let j = 0; j < k; j++) for (let a = 0; a < 3; a++) { const w = v[j * 3 + a] + o[a]; P[(vo + j) * 3 + a] = w; if (w < mn[a]) mn[a] = w; if (w > mx[a]) mx[a] = w; }
      for (let j = 0; j < k; j++) { Q[(vo + j) * 3] = (id & 255) / 255; Q[(vo + j) * 3 + 1] = (id >> 8) / 255; Q[(vo + j) * 3 + 2] = 0; }
      for (let j = 0; j < i.length; j++) I[io + j] = i[j] + vo;
      for (let a = 0; a < 3; a++) { lo[a] = Math.min(lo[a], mn[a]); hi[a] = Math.max(hi[a], mx[a]); }
      comps.push({ name: base(n), o, mn, mx, v0: vo, nv: k, i0: io, ni: i.length }); vo += k; io += i.length; });
    const at = (name, f) => comps.filter(c => c.name === name && (!f || f(c)));
    A = { P, Q, I, comps, at, lo, hi, centre: lo.map((x, a) => (x + hi[a]) / 2), radius: Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) / 2 };
    for (const [name, data] of [['ap', P], ['aq', Q]]) { buf[name] = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf[name]); gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW); }
    buf.ak = gl.createBuffer(); buf.ai = gl.createBuffer(); buf.ag = gl.createBuffer();
  }

  // ---- where each study sits on the aircraft (world = o + (rx x, y, rz z); rx, rz = +-1: identity, 180 deg about Y, or mirror in Z) ----
  // Checked against the CAD by bounding box (local study box vs. the comp boxes of cad/mesh, numbers at rev D):
  //  boom (FEA_Boom_Arm, cad/Sim.cs Boom()): tube on +X from the restrained root face x = 0 to L = feaBoomL 0.462 m, tip block on +Y.
  //    L = xFront + c/4 (analysis/sizing.mjs structures() Lb): the arm from the wing quarter chord to the front motor axis. So the root
  //    goes at x = Lift_Motor.x - L = 0.3909 - 0.4620 = -0.0710 = -c/4 (inside Boom_Clamp_F, x -0.102..-0.068), on the boom axis
  //    y = Motor_Mount_Upper.y = -0.030 (Boom_Front box y -0.0426..-0.0174), z = +-0.4337. Front arms only: the rear arm is
  //    Lift_Motor.x - Boom_Clamp_R.x = -0.5501 + 0.2273 = 0.323 m, so the 0.462 m study is not stretched onto it.
  //  spar (FEA_Spar_Joiner, Sim.cs Spar()): Front Plane sketch, tubes along +Z from the centreline (joiner to joinLen/2 0.38 m, spar
  //    from fusR 0.08 to 0.88 m), restrained at z = 0. Spar_Tube R comp sits at (sparX -0.0853, sparY 0.0053, 0.080) with box z 0.08..0.88:
  //    translate by (sparX, sparY, 0); the symmetric half model is mirrored in Z for the left wing.
  //  lift unit (cad/Thermal.cs LiftUnit()): boom axis X, up Y, motor axis = local Y at x = z = 0, motor base at mountTop 0.021, boom
  //    segment +-0.20, ESC under the boom at x +0.075. Lift_Motor comp y -0.009 = boom axis -0.030 + 0.021: translate to (motor x,
  //    -0.030, motor z). Front units are turned 180 deg about Y: Boom_Front ends at x 0.441, 15 mm ahead of the mount (0.356..0.426),
  //    so the ESC goes on the inboard side there; the model is symmetric apart from the ESC. The modelled tube past the real boom
  //    nose is trimmed.
  //  pod (Thermal.cs Pod()): "pod local = global - (0.45, yPod, 0)", cylinder r fusR 0.08 from the nose (local 0) aft to -fusL
  //    (fixed 2026-10-27; it was centred on the nose). Translate by the Fuselage_Pod comp (0.45, -0.030, 0): the cylinder spans the
  //    real pod's x -0.40..0.45, the battery block lands on Battery_6S_LiPo (x 0.1115..0.2665) and the FC block on Flight_Controller.
  //    The near half (z > 0) is cut away, as in the thermal section, so the bays show.
  //  pusher (Thermal.cs Pusher()): axis +X from the cup floor (x 0..0.0045), motor can on the floor (0.0045..0.0365), cup wall and
  //    foam ring round the can. Pusher_Cup comp x -0.400 with its 4.5 mm floor at x -0.400..-0.3955 (cad/BuildVtol.cs PusherCup,
  //    open forward) and Pusher_Motor aft of it (-0.400..-0.444 with the shaft): turned 180 deg about Y with o.x = -0.400 + 0.0045,
  //    the floor and the can match the CAD; the modelled cup wall and foam ring then sit round the can, where the CAD has open air.
  function place(kind) {
    const P = CADP, mm = A.at('Motor_Mount_Upper'), y0 = mm.length ? mm[0].o[1] : P.yB, motors = A.at('Lift_Motor');
    const nose = Math.max(...A.at('Boom_Front').map(c => c.mx[0]));
    if (kind === 'boom') return motors.filter(m => m.o[0] > 0).map(m => ({ o: [m.o[0] - P.feaBoomL, y0, m.o[2]], rx: 1, rz: 1 }));
    if (kind === 'spar') { const s = A.at('Spar_Tube', c => c.o[2] > 0)[0]; return [1, -1].map(rz => ({ o: [s.o[0], s.o[1], 0], rx: 1, rz })); }
    if (kind === 'lift_unit') return motors.map(m => { const f = m.o[0] > 0; return { o: [m.o[0], y0, m.o[2]], rx: f ? -1 : 1, rz: f ? -1 : 1, keep: f ? w => w[0] <= nose + 1e-4 : null }; });
    if (kind === 'pod') { const p = A.at('Fuselage_Pod')[0];
      return [{ o: p.o.slice(), rx: 1, rz: 1, keep: (w, l) => l[2] <= 1e-4 }]; }
    if (kind === 'pusher') { const c = A.at('Pusher_Cup')[0]; return [{ o: [c.o[0] + 0.0045, c.o[1], c.o[2]], rx: -1, rz: -1 }]; }
    return [];
  }
  // CAD parts a study replaces (hidden where they meet a placed field), and parts clipped inside its box (the boom tube it overlays)
  const REPLACES = { boom: /^(Lift_Motor|Motor_Mount_Upper|Motor_Mount_Cap)$/, spar: /^(Spar_Tube|Wing_Joiner|Joiner_Stop)$/, lift_unit: /^(Lift_Motor|Motor_Mount_Upper|Motor_Mount_Cap)$/,
    pod: /^(Battery_6S_LiPo|Battery_Tray|Flight_Controller|FC_Tray)$/, pusher: /^Pusher_Motor$/ };
  const CLIPS = /^Boom_(Front|Rear_Stub)$/;

  function collect() {
    const out = [], T0 = (() => { try { return JSON.parse(document.getElementById('thermData').textContent); } catch (e) { return null; } })(), lim = (T0 && T0.inputs_summary && T0.inputs_summary.limits_C) || {};
    try { const F = JSON.parse(document.getElementById('feaData').textContent);
      for (const [k, c] of Object.entries(F.cases)) out.push({ key: 'fea/' + k, kind: k, label: c.title, unit: 'MPa', what: 'von Mises stress', ramp: 'stress', v: c.vertices, t: c.tris, val: c.von_MPa,
        ref: c.yield_MPa, refLabel: 'yield ' + c.yield_MPa + ' MPa', note: c.load + '; peak ' + c.max_von_MPa + ' MPa (SOLIDWORKS, all nodes; the surface shown peaks at ' + (c.max_surface_von_MPa != null ? c.max_surface_von_MPa : c.max_von_MPa) + ' MPa), ' + (c.yield_MPa / c.max_von_MPa).toFixed(1) + ' x below yield; displacement up to ' + c.max_disp_mm + ' mm', disp: c.disp_mm }); } catch (e) {}
    try { const F = T0.fields, add = (kind, k, label, ref, refLabel, note) => { const f = F[kind] && F[kind][k]; if (f) out.push({ key: 'therm/' + kind + '/' + k, kind, label, unit: '°C', what: 'temperature', ramp: 'heat', v: f.vertices, t: f.tris, val: f.temps_C, ref, refLabel, note }); };
      const lu = 'SOLIDWORKS transient thermal on a 35 °C day; motor, PA6-CF mount, boom and ESC';
      add('lift_unit', 'hover_90s', 'Lift unit after a 90 s hover', lim.motor_can_C, 'motor limit ' + lim.motor_can_C + ' °C', lu);
      add('lift_unit', 'end_hover5', 'Lift unit at the end of the mission', lim.motor_can_C, 'motor limit ' + lim.motor_can_C + ' °C', lu);
      add('lift_unit', 'steady_hover', 'Lift unit, steady hover (bound, never flown)', lim.motor_can_C, 'motor limit ' + lim.motor_can_C + ' °C', lu);
      add('pod', 'end_hover5', 'Pod at the end of the mission', lim.lipo_C, 'LiPo limit ' + lim.lipo_C + ' °C', 'SOLIDWORKS transient thermal on a 35 °C day, whole mission; battery and flight controller in their foam bays');
      add('pusher', 'end_cruise', 'Pusher after 600 s cruise', lim.motor_can_C, 'motor limit ' + lim.motor_can_C + ' °C (EST)', 'SOLIDWORKS transient thermal on a 35 °C day, 600 s cruise; X4110S can in the PA6-CF cup and foam ring');
    } catch (e) {}
    return out;
  }
  // per-case text on where the result is drawn (numbers from the comps and CADP, so they follow the CAD)
  function where(c) {
    const n = c.inst.length, P = CADP, m = A.at('Lift_Motor'), cr = A.at('Boom_Clamp_R_Upper')[0], rear = m.find(x => x.o[0] < 0);
    if (c.kind === 'boom') return 'Shown at the ' + n + ' front arms, where the study applies: its arm is ' + f3(P.feaBoomL) + ' m from the wing quarter chord (inside the front clamp) to the motor axis, the longest cantilever (analysis/sizing.mjs Lb); both front arms are the same part and load. The rear arms are '
      + f3(rear.o[0] < 0 ? cr.o[0] - rear.o[0] : 0) + ' m from the rear clamp to the motor, shorter and less loaded, and stay grey. The tip block is the study\'s lift-unit mass (' + P.feaTipMass + ' kg); the motor and mount it stands for are hidden.';
    if (c.kind === 'spar') return 'The study is a symmetric half (clamped at the centreline): shown on the right wing and mirrored to the left. The wing panels, saddle and pod around it are drawn faint.';
    if (c.kind === 'lift_unit') return 'The same lift-unit model at all ' + n + ' lift motors (identical units and loads). The front units are turned 180° about the motor axis so the ESC sits on the boom (the front boom ends 15 mm ahead of the mount), and the modelled 0.40 m boom is trimmed at the boom nose.';
    if (c.kind === 'pod') return 'The pod thermal model (a 160 mm XPS cylinder the length of the pod, with the battery and flight controller in their bays) at the pod’s position, cut at the centreline so the bays show. The real pod’s tapered nose and tail are drawn faint around it.';
    if (c.kind === 'pusher') return 'Placed by the cup floor and the motor can, which match the CAD. The model wraps the cup wall and an Ø80 foam ring round the can; the CAD (rev D) has the cup open forward and the can in the open air aft of it, so the model is the warmer case.';
    return '';
  }

  const VS = `attribute vec3 p; attribute vec3 c; attribute vec3 q; attribute float k; uniform mat4 M; uniform mat4 P; varying vec3 vc; varying vec3 vq; varying vec3 ve; varying vec3 vw; varying float vk;
    void main(){ vc=c; vq=q; vk=k; vw=p; vec4 e=M*vec4(p,1.0); ve=e.xyz; gl_Position=P*e; }`;
  // k > 0.5: discard inside the case's field boxes (CAD boom tube under a placed boom field); face normals from derivatives
  const FS = `#extension GL_OES_standard_derivatives : enable
    precision highp float; varying vec3 vc; varying vec3 vq; varying vec3 ve; varying vec3 vw; varying float vk; uniform vec3 L; uniform float pick; uniform float alpha; uniform vec3 bl[4]; uniform vec3 bh[4];
    void main(){ if(vk>0.5){ for(int i=0;i<4;i++){ if(all(greaterThan(vw,bl[i])) && all(lessThan(vw,bh[i]))) discard; } }
      if(pick>0.5){ gl_FragColor=vec4(vq,1.0); return; }
      vec3 nn=normalize(cross(dFdx(ve),dFdy(ve))); float d=abs(dot(nn,normalize(L))); gl_FragColor=vec4(vc*(0.45+0.6*d),alpha); }`;
  function shader(type, src) { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; }

  // column-major 4x4 helpers, written in place (no per-frame allocation)
  const MV = new Float32Array(16), PR = new Float32Array(16);
  function persp(fov, a, n, f) { const t = 1 / Math.tan(fov / 2); PR.fill(0); PR[0] = t / a; PR[5] = t; PR[10] = (f + n) / (n - f); PR[11] = -1; PR[14] = 2 * f * n / (n - f); }
  function view() {   // orbit about the target: yaw about Y (up), pitch, then distance
    const cy = Math.cos(cam.yaw), sy = Math.sin(cam.yaw), cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch), R = MV;
    R[0] = cy; R[1] = sy * sp; R[2] = -sy * cp; R[3] = 0; R[4] = 0; R[5] = cp; R[6] = sp; R[7] = 0; R[8] = sy; R[9] = -cy * sp; R[10] = cy * cp; R[11] = 0;
    R[12] = -(R[0] * cam.t[0] + R[4] * cam.t[1] + R[8] * cam.t[2]) + cam.pan[0]; R[13] = -(R[1] * cam.t[0] + R[5] * cam.t[1] + R[9] * cam.t[2]) + cam.pan[1]; R[14] = -(R[2] * cam.t[0] + R[6] * cam.t[1] + R[10] * cam.t[2]) - cam.d; R[15] = 1; }

  function load(c) {
    C = c; c.inst = c.inst || place(c.kind);
    let lo = Infinity, hi = -Infinity; c.val.forEach(x => { if (x == null) return; if (x < lo) lo = x; if (x > hi) hi = x; });
    c.lo = lo; c.hi = hi;
    // field instances in assembly coordinates: kept triangles only, vertices compacted; src[] maps back to the study vertex
    const v = c.v, t = c.t, nv = v.length / 3, P = [], col = [], Q = [], src = [], idx = [], boxes = [];
    c.inst.forEach((it, k) => { const map = new Int32Array(nv).fill(-1), w = (i, a) => it.o[a] + (a === 0 ? it.rx : a === 2 ? it.rz : 1) * v[i * 3 + a], v0 = src.length, mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
      const id = FIELD_ID + k, q = [(id & 255) / 255, (id >> 8) / 255, 0];
      for (let j = 0; j < t.length; j += 3) {
        if (it.keep) { const wc = [0, 1, 2].map(a => (w(t[j], a) + w(t[j + 1], a) + w(t[j + 2], a)) / 3), lc = [0, 1, 2].map(a => (v[t[j] * 3 + a] + v[t[j + 1] * 3 + a] + v[t[j + 2] * 3 + a]) / 3); if (!it.keep(wc, lc)) continue; }
        for (let e = 0; e < 3; e++) { const i = t[j + e]; if (map[i] < 0) { map[i] = src.length; src.push(i);
          for (let a = 0; a < 3; a++) { const x = w(i, a); P.push(x); if (x < mn[a]) mn[a] = x; if (x > mx[a]) mx[a] = x; }
          const kc = c.val[i] == null ? [0.5, 0.5, 0.5] : ramp(c.ramp, (c.val[i] - lo) / ((hi - lo) || 1)); col.push(kc[0], kc[1], kc[2]); Q.push(q[0], q[1], q[2]); }
          idx.push(map[i]); } }
      it.v0 = v0; it.v1 = src.length; it.mn = mn; it.mx = mx; boxes.push([mn.map(x => x - 0.002), mx.map(x => x + 0.002)]);
      if (k === 0) { let b = v0; for (let j = v0; j < src.length; j++) if (c.val[src[j]] != null && c.val[src[j]] > c.val[src[b]]) b = j;   // peak among the drawn vertices of the first instance
        c.imax = b; c.peakR = Math.hypot(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]) / 2; } });
    c.P = new Float32Array(P); c.src = src; c.n = idx.length; c.boxes = boxes;
    c.bl = new Float32Array(12).fill(1e3); c.bh = new Float32Array(12).fill(1e3); boxes.slice(0, 4).forEach((b, i) => { c.bl.set(b[0], i * 3); c.bh.set(b[1], i * 3); });   // clip boxes (unused slots never match)
    const set = (name, data, el) => { buf[name] = buf[name] || gl.createBuffer(); gl.bindBuffer(el ? gl.ELEMENT_ARRAY_BUFFER : gl.ARRAY_BUFFER, buf[name]); gl.bufferData(el ? gl.ELEMENT_ARRAY_BUFFER : gl.ARRAY_BUFFER, data, gl.STATIC_DRAW); };
    set('fp', c.P); set('fc', new Float32Array(col)); set('fq', new Float32Array(Q)); set('fi', new Uint32Array(idx), true);
    // aircraft parts: hidden (replaced by the field), faint (overlapping a field box, so the field shows through) or plain grey
    const hit = (a, b) => a.mn.every((x, j) => x <= b[1][j]) && a.mx.every((x, j) => x >= b[0][j]), inside = (a, b) => a.mn.every((x, j) => x >= b[0][j]) && a.mx.every((x, j) => x <= b[1][j]);
    const opq = [], gh = [], K = new Float32Array(A.P.length / 3); c.state = new Uint8Array(A.comps.length);
    A.comps.forEach((p, ci) => { const over = boxes.some(b => hit(p, b));
      let s = over && (REPLACES[c.kind] && REPLACES[c.kind].test(p.name) || FAST.test(p.name) && boxes.some(b => inside(p, b))) ? 0 : over && !CLIPS.test(p.name) ? 2 : 1;
      if (CLIPS.test(p.name) && over) K.fill(1, p.v0, p.v0 + p.nv);
      c.state[ci] = s; if (s) (s === 1 ? opq : gh).push(p); });
    const cat = list => { const n = list.reduce((s, p) => s + p.ni, 0), out = new Uint32Array(n); let o = 0; for (const p of list) { out.set(A.I.subarray(p.i0, p.i0 + p.ni), o); o += p.ni; } return out; };
    set('ai', cat(opq), true); set('ag', cat(gh), true); set('ak', K); c.no = opq.reduce((s, p) => s + p.ni, 0); c.ng = gh.reduce((s, p) => s + p.ni, 0);
    reset(); legend(); readout.textContent = c.note + '. ' + where(c); draw();
  }
  // whole aircraft framed, 3/4 view from above front right; narrow stages (phone, 4:3) back off so the span still fits
  function reset() { const asp = cv.clientWidth / (cv.clientHeight || 1) || 16 / 9; cam = { yaw: -0.62, pitch: 0.5, d: A.radius * 1.4 * Math.max(1, 1.7 / asp), t: A.centre.slice(), pan: [0, 0] }; }
  function mats() { view(); persp(0.7, cv.clientWidth / (cv.clientHeight || 1), Math.max(0.002, cam.d * 0.04), cam.d + A.radius * 3); }
  const DMIN = 0.06, dclamp = d => Math.max(DMIN, Math.min(A.radius * 4, d));
  function hotspot() { if (!C) return; const i = C.imax, v = C.P; cam.t = [v[i * 3], v[i * 3 + 1], v[i * 3 + 2]]; cam.pan = [0, 0]; cam.d = dclamp(Math.max(0.15, C.peakR * 0.7)); mats(); draw(); probeAt(i); }

  // one pass over the scene: aircraft (opaque), fields, then faint parts blended without depth writes
  function attrs(bp, bc, bq, kOn, col) {
    gl.bindBuffer(gl.ARRAY_BUFFER, bp); gl.enableVertexAttribArray(U.p); gl.vertexAttribPointer(U.p, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, bq); gl.enableVertexAttribArray(U.q); gl.vertexAttribPointer(U.q, 3, gl.FLOAT, false, 0, 0);
    if (bc) { gl.bindBuffer(gl.ARRAY_BUFFER, bc); gl.enableVertexAttribArray(U.c); gl.vertexAttribPointer(U.c, 3, gl.FLOAT, false, 0, 0); } else { gl.disableVertexAttribArray(U.c); gl.vertexAttrib3f(U.c, col[0], col[1], col[2]); }
    if (kOn) { gl.bindBuffer(gl.ARRAY_BUFFER, buf.ak); gl.enableVertexAttribArray(U.k); gl.vertexAttribPointer(U.k, 1, gl.FLOAT, false, 0, 0); } else { gl.disableVertexAttribArray(U.k); gl.vertexAttrib1f(U.k, 0); }
  }
  function scene(pick, ghosts) {
    gl.uniformMatrix4fv(U.M, false, MV); gl.uniformMatrix4fv(U.P, false, PR); gl.uniform1f(U.pick, pick ? 1 : 0); gl.uniform1f(U.alpha, 1);
    gl.uniform3fv(U.bl, C.bl); gl.uniform3fv(U.bh, C.bh);
    if (ghosts !== 'only') {
      if (C.no) { attrs(buf.ap, null, buf.aq, true, GREY); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.ai); gl.drawElements(gl.TRIANGLES, C.no, gl.UNSIGNED_INT, 0); }
      attrs(buf.fp, buf.fc, buf.fq, false); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.fi); gl.drawElements(gl.TRIANGLES, C.n, gl.UNSIGNED_INT, 0); }
    if (ghosts && C.ng) { attrs(buf.ap, null, buf.aq, true, GHOST);
      if (!pick) { gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false); gl.uniform1f(U.alpha, GHOST_A); }
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buf.ag); gl.drawElements(gl.TRIANGLES, C.ng, gl.UNSIGNED_INT, 0);
      gl.disable(gl.BLEND); gl.depthMask(true); }
  }
  function draw() {
    if (raf) return; raf = requestAnimationFrame(() => { raf = 0; if (!gl || !C) return;
      const dpr = Math.min(2, window.devicePixelRatio || 1), w = cv.clientWidth, h = cv.clientHeight;
      if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
      gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, cv.width, cv.height); gl.clearColor(0.165, 0.184, 0.212, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); gl.enable(gl.DEPTH_TEST);
      gl.useProgram(prog); mats(); gl.uniform3f(U.L, 0.3, 0.6, 1.0); scene(false, true); }); }

  // id under a CSS pixel: the scene drawn into an off-screen id buffer (component index + 1, or FIELD_ID + instance), 1 px read back
  function pickId(mx, my) {
    const w = cv.width, h = cv.height; if (!w || !h) return 0;
    if (!pickFb || pickFb.w !== w || pickFb.h !== h) {
      if (pickFb) { gl.deleteFramebuffer(pickFb.fb); gl.deleteTexture(pickFb.tx); gl.deleteRenderbuffer(pickFb.rb); }
      const fb = gl.createFramebuffer(), tx = gl.createTexture(), rb = gl.createRenderbuffer();
      gl.bindTexture(gl.TEXTURE_2D, tx); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
      gl.bindRenderbuffer(gl.RENDERBUFFER, rb); gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, w, h);
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tx, 0); gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, rb);
      pickFb = { fb, tx, rb, w, h, px: new Uint8Array(4) }; }
    const x = Math.round(mx / cv.clientWidth * w), y = h - 1 - Math.round(my / cv.clientHeight * h); if (x < 0 || y < 0 || x >= w || y >= h) return 0;
    gl.bindFramebuffer(gl.FRAMEBUFFER, pickFb.fb); gl.viewport(0, 0, w, h); gl.enable(gl.SCISSOR_TEST); gl.scissor(x, y, 1, 1); gl.enable(gl.DEPTH_TEST); gl.useProgram(prog); mats();
    let id = 0;
    for (const pass of [false, 'only']) {   // solid parts and fields first; the faint parts only where nothing solid is under the cursor
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT); scene(true, pass);
      gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pickFb.px); id = pickFb.px[0] + pickFb.px[1] * 256; if (id) break; }
    gl.disable(gl.SCISSOR_TEST); gl.bindFramebuffer(gl.FRAMEBUFFER, null); return id;
  }

  // screen position of field vertex i (CSS px) and its depth
  function project(i) { const v = C.P, M = MV, P = PR, x = v[i * 3], y = v[i * 3 + 1], z = v[i * 3 + 2];
    const ex = M[0] * x + M[4] * y + M[8] * z + M[12], ey = M[1] * x + M[5] * y + M[9] * z + M[13], ez = M[2] * x + M[6] * y + M[10] * z + M[14];
    const cx = P[0] * ex, cy = P[5] * ey, w = -ez; return [(cx / w * 0.5 + 0.5) * cv.clientWidth, (1 - (cy / w * 0.5 + 0.5)) * cv.clientHeight, w]; }
  let lastPick = 0;
  function probe(mx, my) {
    if (!C || !cam) return; const now = performance.now(); if (now - lastPick < 40) return; lastPick = now;
    const id = pickId(mx, my); if (!id) { tip.hidden = true; return; }
    if (id < FIELD_ID) { const p = A.comps[id - 1]; if (!p) { tip.hidden = true; return; } showTip(p.name.replace(/_/g, ' ') + ': not in this study', mx, my); return; }
    const it = C.inst[id - FIELD_ID]; if (!it) { tip.hidden = true; return; }
    let best = -1, bd = 1e9;   // nearest field vertex of that instance within 12 px, the front-most first
    for (let i = it.v0; i < it.v1; i++) { const [sx, sy, w] = project(i); const dd = (sx - mx) ** 2 + (sy - my) ** 2; if (dd < 144 && w > 0) { const score = w * 1000 + dd * 0.001; if (score < bd) { bd = score; best = i; } } }
    if (best < 0) { tip.hidden = true; return; } probeAt(best);
  }
  function probeAt(i) { const s = C.src[i]; if (C.val[s] == null) { tip.hidden = true; return; } const [sx, sy] = project(i);
    showTip(C.what + ': ' + C.val[s].toFixed(C.unit === 'MPa' ? 1 : 0) + ' ' + C.unit + (C.disp ? ' · displacement ' + C.disp[s].toFixed(2) + ' mm' : ''), sx, sy); }
  function showTip(text, sx, sy) { tip.hidden = false; tip.textContent = text;
    // keep the tip inside the stage (it is offset 12 px right of the point)
    tip.style.left = Math.round(Math.max(0, Math.min(sx, cv.clientWidth - tip.offsetWidth - 16))) + 'px'; tip.style.top = Math.round(Math.max(tip.offsetHeight * 1.2, sy)) + 'px'; }

  function legend() {
    const n = 40, stops = []; for (let i = 0; i <= n; i++) { const k = ramp(C.ramp, i / n); stops.push(`rgb(${k.map(x => Math.round(x * 255)).join(',')}) ${(i / n * 100).toFixed(1)}%`); }
    const refPct = C.ref != null ? (C.ref - C.lo) / ((C.hi - C.lo) || 1) * 100 : null;
    scaleEl.innerHTML = `<span class="fz-lo">${C.lo.toFixed(C.unit === 'MPa' ? 1 : 0)} ${C.unit}</span><span class="fz-bar" style="background:linear-gradient(90deg,${stops.join(',')})"></span><span class="fz-hi">${C.hi.toFixed(C.unit === 'MPa' ? 1 : 0)} ${C.unit}</span>`
      + `<span class="fz-ref">${refPct != null && refPct <= 100 ? 'limit within the range shown: ' : ''}${C.refLabel}${refPct != null && refPct > 100 ? ', above the highest value shown' : ''}. Grey: parts outside this study.</span>`;
  }

  function init() {
    cv = $('#fzCanvas'); if (!cv) return; gl = cv.getContext('webgl', { antialias: true }); if (!gl) { readout.textContent = 'WebGL is not available in this browser.'; return; }
    if (!gl.getExtension('OES_element_index_uint')) { readout.textContent = 'This browser lacks 32-bit WebGL indices, which the whole-aircraft view needs.'; return; }
    gl.getExtension('OES_standard_derivatives');  // face normals from derivatives: merged inner and outer tube walls cancel vertex normals
    prog = gl.createProgram(); gl.attachShader(prog, shader(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(prog);
    for (const a of ['p', 'c', 'q', 'k']) U[a] = gl.getAttribLocation(prog, a);
    for (const u of ['M', 'P', 'L', 'pick', 'alpha', 'bl', 'bh']) U[u] = gl.getUniformLocation(prog, u);
    aircraft();
    cases = collect(); const bar = $('#fzCases');
    bar.innerHTML = cases.map((c, i) => `<button type="button" data-i="${i}" aria-pressed="${i === 0}">${c.label.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</button>`).join('');
    const choose = i => { bar.querySelectorAll('button').forEach((x, j) => x.setAttribute('aria-pressed', j === i)); tip.hidden = true; load(cases[i]); };
    bar.addEventListener('click', e => { const b = e.target.closest('button'); if (b) choose(+b.dataset.i); });
    $('#fzHot').addEventListener('click', hotspot); $('#fzReset').addEventListener('click', () => { reset(); tip.hidden = true; draw(); });
    let drag = null, pts = new Map(), pinch = 0;
    cv.addEventListener('contextmenu', e => e.preventDefault());
    cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]); drag = { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, pan: e.shiftKey || e.button === 2 }; });
    cv.addEventListener('pointermove', e => { const r = cv.getBoundingClientRect();
      if (pts.has(e.pointerId)) pts.set(e.pointerId, [e.clientX, e.clientY]);
      if (pts.size === 2) { const [a, b] = [...pts.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]); if (pinch) cam.d = dclamp(cam.d * pinch / d); pinch = d; draw(); return; }
      if (drag) { const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY;
        if (drag.pan) { const s = cam.d * 0.0016; cam.pan[0] += dx * s; cam.pan[1] -= dy * s; } else { cam.yaw += dx * 0.008; cam.pitch = Math.max(-1.5, Math.min(1.5, cam.pitch + dy * 0.008)); }
        tip.hidden = true; draw(); } else probe(e.clientX - r.left, e.clientY - r.top); });
    const up = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch = 0;
      // a tap (touch, no drag) reads the value or part under the finger
      if (drag && e.pointerType !== 'mouse' && Math.hypot(e.clientX - drag.x0, e.clientY - drag.y0) < 6) { const r = cv.getBoundingClientRect(); lastPick = 0; probe(e.clientX - r.left, e.clientY - r.top); }
      drag = null; };
    cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up); cv.addEventListener('pointerleave', () => { if (!drag) tip.hidden = true; });
    cv.addEventListener('wheel', e => { e.preventDefault(); cam.d = dclamp(cam.d * Math.exp(e.deltaY * 0.0012)); tip.hidden = true; draw(); }, { passive: false });
    cv.addEventListener('dblclick', () => { reset(); tip.hidden = true; draw(); });
    cv.addEventListener('keydown', e => { const k = e.key; if (!C) return; if (k === 'ArrowLeft') cam.yaw -= 0.1; else if (k === 'ArrowRight') cam.yaw += 0.1; else if (k === 'ArrowUp') cam.pitch = Math.min(1.5, cam.pitch + 0.1); else if (k === 'ArrowDown') cam.pitch = Math.max(-1.5, cam.pitch - 0.1);
      else if (k === '+' || k === '=') cam.d = dclamp(cam.d * 0.85); else if (k === '-') cam.d = dclamp(cam.d / 0.85); else if (k === 'h') hotspot(); else return; e.preventDefault(); draw(); });
    window.addEventListener('resize', draw);
    const qs = /[?&]fzcase=(\d+)/.exec(location.search), i0 = qs && cases[+qs[1]] ? +qs[1] : 0;
    if (cases.length) { choose(i0); if (/[?&]fzpeak=1/.test(location.search)) hotspot(); } started = true;
  }
  return { redraw() { tip = tip || $('#fzTip'); readout = readout || $('#fzNote'); scaleEl = scaleEl || $('#fzScale'); const v = $('#fieldViz'); if (!v || v.closest('[hidden]')) return; if (!started) init(); else draw(); } };
})();
