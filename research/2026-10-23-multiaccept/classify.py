import sys,json,csv,time,math
from pathlib import Path
from collections import Counter
B=Path(__file__).parent;sys.path[:0]=[str(B),str(B.resolve().parents[1])]
from ortools.sat.python import cp_model
from optimize_l6 import Machine
from solve_l6 import delta

def static(case,seconds=.2):
 m=Machine(*case);r=case[0];model=cp_model.CpModel();choices=[]
 for i in range(6):
  options={p:model.new_bool_var(f'z{i}_{p}') for p in range(6*r) if m.rays[p][i]};model.add(sum(options.values())<=1);choices.append(options)
 for k in range(len(m.cells)):
  if not (m.target|m.forbidden)>>k&1:continue
  hits=sum(choices[i][m.origins[i][k]] for i in range(6))
  if m.target>>k&1:model.add(hits==2)
  else:model.add_linear_expression_in_domain(hits,cp_model.Domain.from_values([0,1,3,4,5,6]))
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds;solver.parameters.num_search_workers=1;status=solver.solve(model)
 if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
  pose=[next((p for p,z in choices[i].items() if solver.value(z)),None) for i in range(6)]
  return solver.status_name(status),pose
 return solver.status_name(status),None

if __name__=='__main__':
 data=json.loads((B/'inventory.json').read_text());start=time.perf_counter()
 for n,rec in enumerate(data['records']):
  b=data['bundles'][rec['kind']][rec['case']-1];case=(b['r'],frozenset(map(tuple,b['P'])),b['K'])
  status,pose=static(case);rec['static']=status;rec['static_pose']=pose
  if (n+1)%100==0:print('classified',n+1,'sec',time.perf_counter()-start,flush=True)
 (B/'inventory.json').write_text(json.dumps(data,indent=1))
 fields=list(data['records'][0])
 with (B/'cases.csv').open('w',newline='',encoding='utf-8') as f:
  wr=csv.DictWriter(f,fields);wr.writeheader();wr.writerows(data['records'])
 for kind in data['bundles']:
  rr=[x for x in data['records'] if x['kind']==kind];print(kind,dict(Counter(x['static'] for x in rr)))
  for category in ('static','small','dense','other'):
   def cat(x):return 'static' if x['static'] in ('OPTIMAL','FEASIBLE') else 'small' if x['target_cells']<=19 else 'dense' if x['target_cells']>=50 else 'other'
   rows=[x for x in rr if cat(x)==category];print(category,len(rows),sum(x['length'] for x in rows),sum(x['copies'] for x in rows))
