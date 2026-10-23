from symmetry_graph import *
import importlib.util
spec=importlib.util.spec_from_file_location('previous_exact',REPO/'training_medium_codex/exact_acceptance.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
for idx in [51,168,36,145,159,81,204,131,120,50]:
 g=restore(idx);before=len(load_programs(BASE/'best'/NAME)[idx-1]);_,path=g.dp(frontier=2048);options=[]
 roots={e['start'] for e in path if e['start']!=START}
 for e in sorted(g.E.values(),key=lambda e:(e['ticks']/e['copies'],e['ticks'])):
  if e['start'] not in roots or e['copies']>2:continue
  if e['start']==START or len(e['program'])>18:continue
  for cut,row in enumerate(e['program']):
   free=tuple(j for j,ch in enumerate(row) if ch!='-')
   if 1<=len(free)<=3:options.append((len(free),cut,e,free))
 options.sort(key=lambda v:(v[0],v[2]['ticks']/v[2]['copies']))
 seen=set();queries=0
 for _,cut,e,free in options:
  token=e['start'],e['copies'],e['ticks'],cut
  if token in seen:continue
  seen.add(token);ss=[state(e['start'])]
  for row in e['program']:ss.append(g.sim.step(ss[-1],row))
  hint=ss[:cut+1]+ss[cut+2:]
  t=time.perf_counter();p,info=mod.synth(g.case,state(e['start']),e['ticks']-1,e['copies'],hint=hint,free=free,seconds=1.5,seed=idx+cut*257)
  info.update(case=idx,cut=cut,free=free,method='partial_emitter_cp')
  with (BASE/'experiments/partial_cp.jsonl').open('a') as f:f.write(json.dumps(info)+'\n')
  queries+=1
  if p:
   g.walk(e['start'],p,'partial_emitter_cp');g.bounce(1,80);symmetry(g);answer,_=g.dp(before,frontier=2048);update(idx-1,answer,'partial_emitter_dp',time.perf_counter()-t,idx+cut*257);g.persist()
  if queries>=3:break
 print('PARTIAL',idx,'queries',queries,'best',len(load_programs(BASE/'best'/NAME)[idx-1]),flush=True)
