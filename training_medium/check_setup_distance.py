import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training_medium.setup_and_manager import MediumManager
from solve_l6 import delta
from optimize_l6_compact import Sim

mgr = MediumManager()

cases_to_check = [133, 198, 59, 162, 168, 27, 31, 51, 125, 145, 36, 50]

print(f"{'Case':>5} | {'R':>2} | {'CurrentSetup':>12} | {'Dist to Cycle Pose':>18} | {'Setup Lines'}")
print("-" * 65)

for c in cases_to_check:
    c_idx = c - 1
    case = mgr.cases[c_idx]
    r, pat, count = case
    prog = mgr.best_progs[c_idx]
    sim = Sim(case)
    st = sim.initial()
    
    first_acc = None
    for t, line in enumerate(prog):
        st = sim.step(st, line)
        if st[3] > 0:
            first_acc = t + 1
            pose_acc = st[0]
            break
            
    initial = (0, 5 * r, 4 * r, 3 * r, 2 * r, r)
    distances = [abs(delta(initial[i], pose_acc[i], 6 * r)) for i in range(6)]
    max_dist = max(distances)
    
    print(f"{c:5d} | {r:2d} | {first_acc:12d} | {max_dist:18d} | {distances}")
