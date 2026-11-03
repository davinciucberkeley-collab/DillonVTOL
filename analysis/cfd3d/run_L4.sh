#!/bin/sh
# Fourth grid level (2026-11-02): L4 mesh (f = 0.52) and the alpha-4 case, same solver settings as the rev 2 batch
# (run_batch_rev2.sh), then post-processing and the checks that use the grid study.
cd "$(dirname "$0")/../.."
export PYTHONIOENCODING=utf-8
export ITERS=${ITERS:-3000}
[ -f analysis/cfd3d/out/L4/mesh.su2 ] || py analysis/cfd3d/build_mesh.py 4 > analysis/cfd3d/out/mesh_L4.log 2>&1 || exit 1
py analysis/cfd3d/run_cases.py run L4_a4.0
py analysis/cfd3d/run_cases.py summary
py analysis/cfd3d/postprocess.py L4_a4.0
echo "L4 done $(date)"
