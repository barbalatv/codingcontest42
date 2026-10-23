import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training_medium.setup_and_manager import MediumManager
from optimize_l6_compact import Sim

mgr = MediumManager()
case = mgr.cases[50]
sim = Sim(case)
st = sim.initial()
p = mgr.best_progs[50]

for t, line in enumerate(p):
    prev = st[3]
    st = sim.step(st, line)
    if st[3] > prev:
        extra_matter = bin(st[2]).count('1')
        print(f"Acceptance {st[3]} at tick {t+1}: remaining matter = {extra_matter}, active = {bin(st[1])}")
