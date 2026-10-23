from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from training_medium.setup_and_manager import MediumManager
from optimize_l6_compact import Sim

mgr = MediumManager()
case = mgr.cases[50]
sim = Sim(case)
st = sim.initial()
p = mgr.best_progs[50]

for t in range(8): st = sim.step(st, p[t])
print('t=8 (end of setup / acc 1):')
print('pos:', st[0])
print('act:', [(st[1]>>i)&1 for i in range(6)])
print('matter count:', bin(st[2]).count('1'))

for step in range(1, 7):
    st = sim.step(st, p[7+step])
    mc = bin(st[2]).count('1')
    act = [(st[1]>>i)&1 for i in range(6)]
    print(f"t={8+step} ({' '.join(p[7+step])}): pos={st[0]}, act={act}, matter={mc}, acc={st[3]}")
