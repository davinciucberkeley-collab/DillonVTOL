"""FEA result fields for the review's 3-D field viewer.

Reads cad/sim/fields/boom.json and spar.json (cad/SimFields.cs: SOLIDWORKS surface mesh, nodal von Mises in MPa,
resultant displacement in metres) and writes analysis/fea_fields.json: each surface reduced by vertex clustering
(the same method as analysis/thermal/thermal_report.py) with von Mises in MPa and displacement in mm per vertex.
Usage: python analysis/fea_fields.py
"""
import json, os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'cad', 'sim', 'fields')


def reduce(path, cell):
    f = json.load(open(path, encoding='utf-8'))
    nodes = np.array(f['nodes'], float).reshape(-1, 3); tris = np.array(f['tris'], int).reshape(-1, 3)
    vm = np.array([np.nan if v is None else v for v in f['fields']['von_MPa']], float)
    du = np.array([np.nan if v is None else v for v in f['fields']['disp_mm']], float) * 1000.0   # exported in metres
    used = np.unique(tris); q = np.floor(nodes[used] / cell).astype(np.int64)
    uniq, inv = np.unique(q, axis=0, return_inverse=True); inv = inv.ravel()   # exact cells (a hashed key merged distant cells)
    remap = np.full(len(nodes), -1, int); remap[used] = inv
    nv = len(uniq); V = np.zeros((nv, 3)); cnt = np.zeros(nv); S = np.zeros(nv); D = np.zeros(nv)
    np.add.at(V, inv, nodes[used]); np.add.at(cnt, inv, 1); V /= cnt[:, None]
    # keep the peak in each cluster for stress (an average would hide the hot spot); mean for displacement
    S[:] = -np.inf; np.maximum.at(S, inv, np.nan_to_num(vm[used], nan=-np.inf)); S[~np.isfinite(S)] = np.nan
    np.add.at(D, inv, np.nan_to_num(du[used], nan=0.0)); D /= cnt
    tr = remap[tris]; tr = tr[(tr[:, 0] != tr[:, 1]) & (tr[:, 1] != tr[:, 2]) & (tr[:, 0] != tr[:, 2])]
    tr = np.unique(np.sort(tr, axis=1), axis=0)
    return {'vertices': [round(float(x), 5) for x in V.ravel()], 'tris': [int(x) for x in tr.ravel()],
            'von_MPa': [round(float(x), 2) if np.isfinite(x) else None for x in S], 'disp_mm': [round(float(x), 3) for x in D], 'cell_m': cell,
            'max_von_MPa': round(float(np.nanmax(vm)), 2), 'max_surface_von_MPa': round(float(np.nanmax(S)), 2), 'max_disp_mm': round(float(np.nanmax(du)), 3), 'nodes_full': int(len(nodes))}


out = {'note': 'cad/SimFields.cs -> cad/sim/fields/*.json -> analysis/fea_fields.py: surface meshes vertex-clustered (cell_m), '
               'von Mises = peak in each cluster (MPa), displacement = cluster mean (mm); study frame, metres',
       'cases': {}}
for name, cell, title, load, yield_MPa in (('boom', 0.003, 'Boom arm at full lift thrust (fine mesh)', 'one lift unit at maximum thrust 30.7 N, boom held in the wing clamps', 275),
                                           ('spar', 0.004, 'Wing joiner and spar at ultimate load (fine mesh)', '4.5 g ultimate root moment 73.6 N·m', 275)):
    p = os.path.join(SRC, name + '.json')
    if not os.path.exists(p): print('missing', p); continue
    c = reduce(p, cell); c.update(title=title, load=load, yield_MPa=yield_MPa)
    out['cases'][name] = c
    print(name, len(c['vertices']) // 3, 'vertices', len(c['tris']) // 3, 'triangles; max von Mises', c['max_von_MPa'], 'MPa; max displacement', c['max_disp_mm'], 'mm')
json.dump(out, open(os.path.join(ROOT, 'analysis', 'fea_fields.json'), 'w', encoding='utf-8'), separators=(',', ':'))
print('wrote analysis/fea_fields.json', os.path.getsize(os.path.join(ROOT, 'analysis', 'fea_fields.json')) // 1024, 'kB')
