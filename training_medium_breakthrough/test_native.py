from run_geometry import *
p=Native('test_sim.exe');rng=random.Random(179);pp=load_programs(BASE/'best'/NAME);ticks=0
try:
 for i,c in enumerate(CASES):
  sim=Sim(c);program=pp[i]+[tuple(rng.choice('-FBT') for _ in range(6)) for t in range(20)];text=f'{c[0]} {len(program)}\n{board(c)}\n'+' '.join(str(sum('-FBT'.index(ch)<<(2*e) for e,ch in enumerate(row))) for row in program)+'\n';out,secs=p.ask(text);assert len(out)==3*len(program)
  st=sim.initial()
  for t,row in enumerate(program):
   st=sim.step(st,row);assert packed(key(st))==out[3*t] and st[2]&(sim.target|sim.forbidden)==out[3*t+1] and st[3]==out[3*t+2],(i+1,t);ticks+=1
finally:p.close()
print('CPP_PYTHON_STATE_EQUIVALENCE_PASS',210,ticks,flush=True)
