from multi_experiment import *
import importlib.util
spec=importlib.util.spec_from_file_location('exact_model',REPO/'training_medium_codex/exact_acceptance.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
f=BASE/'experiments/near_case41_h5_c2_s1412833.json';d=json.loads(f.read_text());idx=d['case'];g=restore(idx);root=tuple((d['root']>>(8*e))&127 for e in range(6))+(sum(((d['root']>>(8*e+7))&1)<<e for e in range(6)),);hint=[state(root)]
for row in d['program']:hint.append(g.sim.step(hint[-1],row))
p,info=mod.synth(g.case,state(root),5,2,closed=True,hint=hint,seconds=12,seed=d['seed']+301,root_radius=3)
info.update(case=idx,source=f.name,method='deep_geometry_near_repair',radius=3)
(BASE/'experiments/deep_near.json').write_text(json.dumps(info,indent=2));print(info,flush=True)
if p:
 q=info['root'];root=tuple(q[0])+(q[1],);best=load_programs(BASE/'best'/NAME)[idx-1];states=[state(root)]
 for row in p:states.append(g.sim.step(states[-1],row))
 for phase in range(len(p)):
  cyc=p[phase:]+p[:phase];pp=simulate_repeat(g,safe_setups(g,key(states[phase])),cyc,len(best))
  if pp:g.walk(START,pp,'deep_near');update(idx-1,pp,'geometry_near_cp',info['seconds'],d['seed']+301)
 (BASE/'experiments/deep_cycle.json').write_text(json.dumps(dict(case=idx,root=root,program=p,copies=2)))
