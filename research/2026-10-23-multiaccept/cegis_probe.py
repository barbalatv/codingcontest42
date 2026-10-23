import sys,json,time,argparse
from pathlib import Path
B=Path(__file__).parent;sys.path[:0]=[str(B),str(B.resolve().parents[1])]
from ortools.sat.python import cp_model
from optimize_l6 import Machine
from optimize_l6_compact import Sim
from solve_l6 import delta

def synth(case,program,H,budget=12):
 r,pat,K=case;sim=Sim(case);m=Machine(*case);L=6*r;model=cp_model.CpModel();P={};A={};Z={};anchor=sim.initial()[0]
 states=sim.prefix(program);first=next(t for t in range(1,len(states)) if states[t][3]);hint=states[:first+1]
 for t in range(H+1):
  for i in range(6):
   D=min(t,L//2);P[t,i]=model.new_int_var(-D,D,f'p{t}_{i}');A[t,i]=model.new_bool_var(f'a{t}_{i}')
   if not t:model.add(A[t,i]==0);continue
   dd=model.new_int_var(-1,1,f'd{t}_{i}');model.add(dd==P[t,i]-P[t-1,i])
   model.add_allowed_assignments([dd,A[t-1,i],A[t,i]],[(d,a,b) for d in (-1,0,1) for a in (0,1) for b in (0,1) if d==0 or a==b])
   Z[t,i]={}
   for q in range(-D,D+1):
    if not m.rays[(anchor[i]+q)%L][i]:continue
    z=model.new_bool_var(f'z{t}_{i}_{q}');model.add(P[t,i]==q).only_enforce_if(z);Z[t,i][q]=z
   # An active outward beam is equivalent to an inactive beam for matter,
   # but not for motion/toggle costs. Include its ray option as well.
   for q in range(-D,D+1):
    if q not in Z[t,i]:
     z=model.new_bool_var(f'z{t}_{i}_{q}');model.add(P[t,i]==q).only_enforce_if(z);Z[t,i][q]=z
   model.add(sum(Z[t,i].values())==A[t,i])
   hs=hint[round(t*first/H)];q=delta(anchor[i],hs[0][i],L)
   model.add_hint(P[t,i],max(-D,min(D,q)));model.add_hint(A[t,i],bool(hs[1]>>i&1))
 constrained=set();iterations=[];start=time.perf_counter()
 def addcell(k):
  if k in constrained:return
  constrained.add(k);cs=[];ds=[]
  for t in range(1,H+1):
   hits=[z for i in range(6) for q,z in Z[t,i].items() if (anchor[i]+q)%L==m.origins[i][k]]
   n=model.new_int_var(0,6,f'n{t}_{k}');model.add(n==sum(hits))
   c=model.new_bool_var(f'c{t}_{k}');d=model.new_bool_var(f'd{t}_{k}')
   model.add(n==2).only_enforce_if(c);model.add(n!=2).only_enforce_if(c.Not())
   model.add(n>=3).only_enforce_if(d);model.add(n<=2).only_enforce_if(d.Not())
   cv=model.new_int_var(0,t,f'cv{t}_{k}');dv=model.new_int_var(0,t,f'dv{t}_{k}');model.add(cv==t*c);model.add(dv==t*d);cs.append(cv);ds.append(dv)
  C=model.new_int_var(0,H,f'C{k}');D=model.new_int_var(0,H,f'D{k}');model.add_max_equality(C,cs);model.add_max_equality(D,ds)
  if m.target>>k&1:model.add(C>D)
  else:model.add(C<=D)
 targets=[k for k in range(len(m.cells)) if m.target>>k&1];guards=[k for k in range(len(m.cells)) if m.forbidden>>k&1]
 for ii in range(min(6,len(targets))):addcell(targets[ii*(len(targets)-1)//max(1,min(6,len(targets))-1)])
 for iteration in range(12):
  remaining=budget-(time.perf_counter()-start)
  if remaining<=0:break
  solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=min(3,remaining);solver.parameters.num_search_workers=8
  status=solver.solve(model);stats=dict(iteration=iteration,cells=len(constrained),status=solver.status_name(status),sec=solver.wall_time);iterations.append(stats)
  if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):break
  raw=[]
  for t in range(1,H+1):
   line=[]
   for i in range(6):
    d=solver.value(P[t,i])-solver.value(P[t-1,i]);toggle=solver.value(A[t,i])!=solver.value(A[t-1,i]);line.append('T' if toggle else 'B' if d>0 else 'F' if d<0 else '-')
   raw.append(tuple(line))
  s=sim.initial()
  for t,line in enumerate(raw):
   s=sim.step(s,line)
   if s[3]:return raw[:t+1],iterations
  wrong=(s[2]^m.target)&(m.target|m.forbidden)
  assert wrong
  for k in range(len(m.cells)):
   if wrong>>k&1:addcell(k)
 return None,iterations

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cases',default='133,60,97');p.add_argument('--kind',default='4-enormous');p.add_argument('--budget',type=float,default=12);a=p.parse_args();data=json.loads((B/'inventory.json').read_text());results=[]
 for index in map(int,a.cases.split(',')):
  b=data['bundles'][a.kind][index-1];case=(b['r'],frozenset(map(tuple,b['P'])),b['K']);program=list(map(tuple,b['program']));sim=Sim(case);states=sim.prefix(program);first=next(t for t in range(1,len(states)) if states[t][3]);H=first-2
  out,stats=synth(case,program,H,a.budget);rec=dict(kind=a.kind,case=index,copies=b['K'],before=first,H=H,after=len(out) if out else None,iterations=stats,program=out);results.append(rec);print(json.dumps({k:v for k,v in rec.items() if k!='program'}),flush=True)
 (B/'cegis_results.json').write_text(json.dumps(results,indent=1))
