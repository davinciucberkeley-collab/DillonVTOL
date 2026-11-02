#!/bin/sh
# Mesh rev 2 schedule (2026-11-01): geometry from the frozen design (cad/params.txt), meshes L1-L3 with the audit fixes
# (analysis/cfd3d/build_mesh.py rev 2), then the same seven cases as rev 1: L2 alpha 4 from scratch, L1, the L2 alpha sweep
# warm-started from the converged alpha-4 solution, the fine grid from scratch; then post-processing, viewer pack, checks, audit.
# Rev 1 results are kept in analysis/cfd3d/out_rev1/.
cd "$(dirname "$0")/../.."
export PYTHONIOENCODING=utf-8
export ITERS=${ITERS:-3000}
for L in 2 3; do py analysis/cfd3d/build_mesh.py $L > analysis/cfd3d/out/mesh_L$L.log 2>&1 || exit 1; done
py analysis/cfd3d/run_cases.py run L2_a4.0
py analysis/cfd3d/run_cases.py run L1_a4.0
RESTART_FROM=L2_a4.0 py analysis/cfd3d/run_cases.py run L2_a0.0 L2_a2.0 L2_a6.0 L2_a8.0
py analysis/cfd3d/run_cases.py run L3_a4.0
py analysis/cfd3d/run_cases.py summary
py analysis/cfd3d/postprocess.py L1_a4.0 L2_a0.0 L2_a2.0 L2_a4.0 L2_a6.0 L2_a8.0 L3_a4.0
py analysis/cfd3d/postprocess.py pack
py analysis/cfd3d/verify_cfd.py
py analysis/cfd3d/mesh_audit.py
echo "rev2 batch done $(date)"
