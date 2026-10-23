from multi_experiment import *
import importlib.util
spec=importlib.util.spec_from_file_location('exact_model',REPO/'training_medium_codex/exact_acceptance.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
files=[]
for f in (BASE/'experiments').glob('near_case*.json'):
 d=json.loads(f.read_text())
 if d['defect']<=2 and len(d['program'])<=5:files.append((d['defect'],len(d['program']),f,d))
for _,H,f,d in sorted(files,key=lambda x:(x[0],x[1],str(x[2])))[:6]:
 idx=d['case'];root=tuple((d['root']>>(8*e))&127 for e in range(6))+(sum(((d['root']>>(8*e+7))&1)<<e for e in range(6)),);c=CASES[idx-1];sim=Sim(c);hint=[state(root)]
 for row in d['program']:hint.append(sim.step(hint[-1],row))
 p,info=mod.synth(c,state(root),H,d['copies'],closed=True,hint=hint,seconds=2,seed=d['seed']+91,root_radius=2)
 info.update(case=idx,method='geometry_near_exact_repair',source=f.name,defect=d['defect'])
 with (BASE/'experiments/near_cp.jsonl').open('a') as out:out.write(json.dumps(info)+'\n')
 if p:
  q=info['root'];root=tuple(q[0])+(q[1],);(BASE/'experiments'/f'cp_cycle_case{idx}_h{H}_c{d["copies"]}_s{d["seed"]}.json').write_text(json.dumps(dict(case=idx,root=root,copies=d['copies'],program=p,seed=d['seed'],method='geometry_near_exact_repair')))
 print(info,flush=True)
