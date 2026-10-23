from chain_experiment import *
from solve_l6 import origins
from itertools import combinations
pp=load_programs(BASE/'best'/NAME);ranks=[]
for i,c in enumerate(CASES):
 if c[0]>4 or c[2]<2:continue
 g=Graph(i);ss,aa=qstates(g,pp[i]);origin=origins(c[0]);cells=geometry(c[0])[1];initial=g.sim.initial();lb=0
 for k,cell in enumerate(cells):
  if cell not in c[1]:continue
  dt=[abs(delta(initial[0][e],origin[e][k],6*c[0]))+1 for e in range(6)]
  lb=max(lb,min(max(dt[a],dt[b]) for a,b in combinations(range(6),2)))
 if aa[0]>lb:ranks.append(dict(case=i+1,radius=c[0],K=c[2],score=len(pp[i]),setup=aa[0],lower_bound=lb,priority=(aa[0]-lb)/(1+len(c[1])/20)))
ranks.sort(key=lambda x:x['priority'],reverse=True);(BASE/'experiments/priority.json').write_text(json.dumps(ranks,indent=2));engine=Native('geometry_search.exe');started=time.perf_counter()
try:
 for info in ranks[:24]:
  idx=info['case'];i=idx-1;c=CASES[i];g=restore(idx);p=load_programs(BASE/'best'/NAME)[i];g.walk(START,p,'current');ss,aa=qstates(g,p);initial=key(g.sim.initial());goals=list(dict.fromkeys(key(ss[t]) for t in aa))[:12]
  for mode,label in [(2,'meet_setup_discovery'),(3,'ordinary_setup_discovery'),(4,'chord_setup_discovery')]:
   seed=1700000+idx*421;before=len(load_programs(BASE/'best'/NAME)[i]);H=aa[0]-1;data=f'{c[0]} 1 128 500 {H} {mode} {seed}\n{board(c)}\n{packed(initial)} {MAX}\n{len(goals)}\n'+' '.join(map(str,map(packed,goals)))+'\n';out,secs=engine.ask(data);primary,extra=unpack_response(out);added=0
   for q,prog in [(out[3],primary)]+extra:
    if not prog:continue
    st=g.sim.initial()
    for row in prog:st=g.sim.step(st,row)
    assert st[3]==1
    added+=g.walk(START,prog,label)
    # Try known continuation phases from this exact new start, simulating every tick.
    for j,a in enumerate(aa[:4]):
     continuation=p[a:];state_now=st;whole=list(prog)
     for row in continuation:
      state_now=g.sim.step(state_now,row);whole.append(row)
      if state_now[3]>=c[2]:break
     if state_now[3]==c[2] and len(whole)<before:g.walk(START,whole,label+'_continuation')
   if added:
    g.bounce(2,140);symmetry(g);ans,path=g.dp(before,4096);update(i,ans,label,secs,seed)
   after=len(load_programs(BASE/'best'/NAME)[i]);rec=dict(**info,method=label,before=before,after=after,saved=before-after,seed=seed,runtime=secs,explored=out[1],bridge_checks=out[4],added_edges=added)
   with (BASE/'experiments/discovery.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
   print(rec,flush=True)
  g.persist()
finally:engine.close()
print('DISCOVERY_DONE',time.perf_counter()-started,flush=True)
