import sys,json,csv,time,math
from pathlib import Path
from collections import Counter
B=Path(__file__).parent;sys.path[:0]=[str(B),str(B.resolve().parents[1])]
from ortools.sat.python import cp_model
from solve_l6 import origins
from solve_l4 import geometry

def possible(b,h):
 r=b['r'];L=6*r;o=origins(r);ix={p:k for k,p in enumerate(geometry(r)[1])};model=cp_model.CpModel();Z=[]
 for i in range(6):
  opts={s:model.new_bool_var(f'z{i}_{s}') for s in range(L)};model.add(sum(opts.values())==1);Z.append(opts)
 for p in b['P']:
  k=ix[tuple(p)];model.add(sum(Z[i][(o[i][k]-d)%L] for i in range(6) for d in range(h))>=2)
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=.15;solver.parameters.num_search_workers=1;status=solver.solve(model)
 return solver.status_name(status)

d=json.loads((B/'inventory.json').read_text());start=time.perf_counter()
for n,rec in enumerate(d['records']):
 b=d['bundles'][rec['kind']][rec['case']-1];lo=rec['interval_lower_bound'];hi=2*b['r']-1;checks=[]
 while lo<hi:
  h=(lo+hi)//2;status=possible(b,h);checks.append((h,status))
  if status=='INFEASIBLE':lo=h+1
  elif status in ('OPTIMAL','FEASIBLE'):hi=h
  else:break
 rec['reach_interval_lower_bound']=lo;rec['reach_checks']=checks
 rec['lower_bound']=max(rec['earliest_geometric'],lo)+(rec['copies']-1)*lo;rec['gap']=rec['length']-rec['lower_bound'];assert rec['gap']>=0
 if (n+1)%100==0:print('reach bounds',n+1,'sec',time.perf_counter()-start,flush=True)
(B/'inventory.json').write_text(json.dumps(d,indent=1))
with (B/'cases.csv').open('w',newline='',encoding='utf-8') as f:
 wr=csv.DictWriter(f,list(d['records'][0]));wr.writeheader();wr.writerows(d['records'])
for kind in d['bundles']:
 rr=[x for x in d['records'] if x['kind']==kind];print(kind,'LB',sum(x['lower_bound'] for x in rr),'h',dict(Counter(x['reach_interval_lower_bound'] for x in rr)))
