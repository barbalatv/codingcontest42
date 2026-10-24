from common import *
from ortools.sat.python import cp_model
from solve_l6 import delta
def synth(case,start,H,copies,end=None,closed=False,hint=None,seconds=3,seed=0,free=(),root_radius=0,free_slots=None):
 """Exact relevant-matter recurrence and iff acceptance at every tick.
 start is actual simulated state; end constrains pose and relevant matter.
 free lists emitters allowed to change; others can be fixed by hint.
 """
 t0=time.perf_counter();r,pattern,K=case;sim=Sim(case);rel=sim.target|sim.forbidden;L=6*r;m=cp_model.CpModel()
 states={};hit={};accept=[];cells=[k for k in range(len(geometry(r)[1])) if rel>>k&1]
 trans=[]
 for a in range(2):
  for p in range(L):
   s=p+L*a
   trans.extend([(s,s,0),(s,(p-1)%L+L*a,1),(s,(p+1)%L+L*a,2),(s,p+L*(1-a),3)])
 for t in range(H+1):
  for e in range(6):
   v=m.new_int_var(0,2*L-1,f's{t}_{e}');states[t,e]=v
   if t==0:
    if root_radius:
     allowed=[((start[0][e]+d)%L)+L*a for d in range(-root_radius,root_radius+1) for a in range(2)];m.add_allowed_assignments([v],[(z,) for z in allowed])
    else:m.add(v==start[0][e]+L*((start[1]>>e)&1))
   if t:
    op=m.new_int_var(0,3,f'op{t}_{e}');m.add_allowed_assignments([states[t-1,e],v,op],trans)
    if hint:
     old=hint[min(t,len(hint)-1)];m.add_hint(v,old[0][e]+L*((old[1]>>e)&1))
     if (free and e not in free) or (free_slots is not None and (t,e) not in free_slots):m.add(v==old[0][e]+L*((old[1]>>e)&1))
 if closed:
  for e in range(6):m.add(states[H,e]==states[0,e])
 if end:
  for e in range(6):m.add(states[H,e]==end[0][e]+L*((end[1]>>e)&1))
 previous={k:int(start[2]>>k&1) for k in cells}
 table=[(p,n,0 if n>=3 else 1 if n==2 else p) for p in (0,1) for n in range(7)]
 for t in range(1,H+1):
  raw={}
  for k in cells:
   hits=[]
   for e in range(6):
    key=e,k
    if key not in hit:hit[key]=[int(a and (sim.rays[p][e]>>k&1)) for a in range(2) for p in range(L)]
    b=m.new_bool_var(f'h{t}_{e}_{k}');m.add_element(states[t,e],hit[key],b);hits.append(b)
   n=m.new_int_var(0,6,f'n{t}_{k}');m.add(n==sum(hits));v=m.new_bool_var(f'raw{t}_{k}');raw[k]=v
   m.add_allowed_assignments([previous[k],n,v],table)
  acc=m.new_bool_var(f'accept{t}');accept.append(acc)
  good=[raw[k] if sim.target>>k&1 else raw[k].Not() for k in cells]
  for b in good:m.add_implication(acc,b)
  m.add_bool_or([acc]+[b.Not() for b in good])
  previous={}
  for k in cells:
   if sim.target>>k&1:
    v=m.new_bool_var(f'post{t}_{k}');m.add(v==raw[k]).only_enforce_if(acc.Not());m.add(v==0).only_enforce_if(acc);previous[k]=v
   else:previous[k]=raw[k]
 m.add(sum(accept)==copies)
 if closed:m.add(accept[-1]==1)
 if end:
  for k in cells:m.add(previous[k]==int(end[2]>>k&1))
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds;solver.parameters.num_search_workers=2;solver.parameters.random_seed=seed
 solver.parameters.max_memory_in_mb=1024
 status=solver.solve(m);prog=None
 if status in (cp_model.FEASIBLE,cp_model.OPTIMAL):
  prog=[];old=start
  if root_radius:old=(tuple(solver.value(states[0,e])%L for e in range(6)),sum((solver.value(states[0,e])//L)<<e for e in range(6)),0,0)
  solved_root=old
  for t in range(1,H+1):
   row=[]
   for e in range(6):
    v=solver.value(states[t,e]);p=v%L;a=v//L
    row.append('T' if a!=((old[1]>>e)&1) else '-BF'[delta(old[0][e],p,L)] if delta(old[0][e],p,L) in (0,1,-1) else '?')
   row=tuple(row);old=sim.step(old,row);prog.append(row)
  assert old[3]-start[3]==copies
  if end:assert old[:2]==end[:2] and (old[2]^end[2])&rel==0
 return prog,dict(status=solver.status_name(status),seconds=time.perf_counter()-t0,horizon=H,copies=copies,branches=solver.num_branches,root=solved_root if prog is not None else None)
