import sys,json,random
from pathlib import Path
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B.parent))
from solve_l6 import parse
from solve_l4 import geometry
from optimize_l6 import load_programs
from optimize_l6_compact import Sim
cases=parse(B.parent/'level-6/in_level-6_2-medium.txt');progs=load_programs(B/'baseline/answer_level-6_2-medium.txt');tr=[];rng=random.Random(179)
for i,c in enumerate(cases):
 sim=Sim(c);cells=geometry(c[0])[1];ss=sim.initial();p=progs[i]+[tuple(rng.choice('-FBT') for _ in range(6)) for t in range(20)]
 states=[]
 for row in p:
  ss=sim.step(ss,row);states.append(dict(positions=ss[0],accepted=ss[3],active=[bool(ss[1]>>e&1) for e in range(6)],matter=[list(cells[k]) for k in range(len(cells)) if ((sim.target|sim.forbidden)&ss[2])>>k&1]))
 tr.append(dict(program=p,states=states,relevant=[list(cells[k]) for k in range(len(cells)) if (sim.target|sim.forbidden)>>k&1]))
(B/'experiments/expected_traces.json').write_text(json.dumps(tr))
