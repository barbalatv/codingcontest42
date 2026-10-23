import argparse,json,time
from pathlib import Path
from ortools.sat.python import cp_model
from solve_l6 import parse,origins
from solve_l4 import geometry
from solve_l5 import verify
from optimize_l6 import ROOT,load_programs,save_programs,Machine,Done
from optimize_l6_compact import Sim

def solve(case,state,old,H,seconds,unsafe=False):
 r,pat,count=case;_,cells,_=geometry(r);n=2*r-1;org=origins(r);axes=[(y-1,(x-y-(2-r))//2,(x+y-(r+2))//2) for y,x in cells]
 positions=[];start=[]
 for e in range(6):
  mapping={a[e%3]:org[e][k] for k,a in enumerate(axes)};positions.append(mapping)
  inv={p:q for q,p in mapping.items()}
  if state[0][e] not in inv:return None,'OUTSIDE'
  start.append(inv[state[0][e]])
 model=cp_model.CpModel();P={};A={};Z={}
 for e in range(6):
  P[0,e]=model.new_constant(start[e]);A[0,e]=model.new_constant((state[1]>>e)&1)
 for t in range(1,H+1):
  for e in range(6):
   lo=max(0,start[e]-t);hi=min(n-1,start[e]+t);P[t,e]=model.new_int_var(lo,hi,f'p{t}_{e}');A[t,e]=model.new_bool_var(f'a{t}_{e}')
   d=model.new_int_var(-1,1,f'd{t}_{e}');model.add(P[t,e]-P[t-1,e]==d)
   model.add_allowed_assignments([d,A[t-1,e],A[t,e]],[(q,a,b) for q in (-1,0,1) for a in (0,1) for b in (0,1) if q==0 or a==b])
   options={}
   for q in range(lo,hi+1):
    v=model.new_bool_var(f'z{t}_{e}_{q}');model.add(P[t,e]==q).only_enforce_if(v);options[q]=v
   model.add(sum(options.values())==A[t,e]);Z[t,e]=options
 sim=Sim(case)
 hitVars={};relevant=[]
 for k,cell in enumerate(cells):
  target=cell in pat
  if not target and not (sim.forbidden>>k&1):continue
  covered=[];relevant.append(k)
  for t in range(1,H+1):
   hits=model.new_int_var(0,6,f'h{t}_{k}');model.add(hits==sum(Z[t,e].get(axes[k][e%3],0) for e in range(6)));hitVars[t,k]=hits
   if unsafe:continue
   if target:
    model.add(hits<=2);v=model.new_bool_var(f'c{t}_{k}');model.add(hits==2).only_enforce_if(v);model.add(hits<=1).only_enforce_if(v.Not());covered.append(v)
   else:model.add_linear_expression_in_domain(hits,cp_model.Domain.from_values([0,1,3,4,5,6]))
  if target and not unsafe:model.add_bool_or(covered)
 if unsafe:
  table=[(p,n,0 if n>=3 else 1 if n==2 else p) for p in (0,1) for n in range(7)]
  for direction in (0,1):
   levels={}
   for k in relevant:
    previous=0
    for step in range(1,H+1):
     t=step if not direction else H+1-step
     current=model.new_bool_var(f'm{direction}_{step}_{k}');model.add_allowed_assignments([previous,hitVars[t,k],current],table);previous=current;levels[step,k]=current
    model.add(previous==int(cells[k] in pat))
   for step in range(1,H):model.add_bool_or([levels[step,k].Not() if cells[k] in pat else levels[step,k] for k in relevant])
 # Hints are physical states from a time-compressed incumbent passage.
 hints=Sim(case).initial();hints=state;history=[state]
 for row in old:history.append(sim.step(history[-1],row))
 for t in range(1,H+1):
  s=history[min(len(old),round(t*len(old)/H))]
  for e in range(6):
   inv={p:q for q,p in positions[e].items()};q=inv.get(s[0][e],start[e]);q=max(max(0,start[e]-t),min(min(n-1,start[e]+t),q));model.add_hint(P[t,e],q);model.add_hint(A[t,e],(s[1]>>e)&1)
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds;solver.parameters.num_search_workers=4
 status=solver.solve(model)
 if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return None,solver.status_name(status)
 prog=[];p=list(state[0]);active=state[1];st=state
 for t in range(1,H+1):
  row=[]
  for e in range(6):
   q=positions[e][solver.value(P[t,e])];on=solver.value(A[t,e]);a=(active>>e)&1
   if on!=a:row.append('T');active^=1<<e
   else:
    diff=(q-p[e]+3*r)%(6*r)-3*r;assert abs(diff)<=1;row.append('B' if diff>0 else 'F' if diff<0 else '-')
   p[e]=q
  prog.append(tuple(row));st=sim.step(st,row)
  if st[3]>state[3]:break
 return prog,solver.status_name(status)

def bounce(case,baseline,t,path):
 m=Machine(*case);inv={'F':'B','B':'F','T':'T','-':'-'};rev=[tuple(inv[c] for c in row) for row in reversed(path[1:])]
 try:
  for row in baseline[:t]+path:m.emit(row)
  for rep in range(case[2]*2):
   m.emit(['-']*6)
   for row in rev if rep%2==0 else path[1:]:
    m.emit(row)
    if len(m.program)>=len(baseline):return None
 except Done:return m.program
 return None

p=argparse.ArgumentParser();p.add_argument('--pilot',action='store_true');p.add_argument('--unsafe',action='store_true');p.add_argument('--seconds',type=float,default=1);p.add_argument('--limit',type=int,default=10000);a=p.parse_args();entries=[];started=time.perf_counter()
for src in sorted(ROOT.glob('in_*.txt')):
 if not any(x in src.name for x in ('medium','large','enormous')):continue
 for i,(case,prog) in enumerate(zip(parse(src),load_programs(src.with_name(src.name.replace('in_','answer_',1))))):
  if case[2]<3:continue
  st=Sim(case).prefix(prog);snaps=[(t,st[t]) for t in range(1,len(st)) if st[t][3]>st[t-1][3]];options=[]
  for (t,s),(u,_) in zip(snaps,snaps[1:]):
   remain=case[2]-s[3]
   if remain>=2 and u-t>=3:options.append(((u-t-1)*remain,t,u,s))
  if options:
   value,t,u,s=max(options);entries.append((value,src,i,case,prog,t,u,s))
entries.sort(key=lambda e:e[0],reverse=True)
if a.pilot:entries=[entries[round(j*(len(entries)-1)/9)] for j in range(10)]
entries=entries[:a.limit];wins=[]
for j,(_,src,i,case,prog,t,u,state) in enumerate(entries):
 path,status=solve(case,state,prog[t:u],u-t-1,a.seconds,a.unsafe);candidate=bounce(case,prog,t,path) if path else None
 if candidate and len(candidate)<len(prog):
  assert verify(case[0],case[1],candidate)==case[2]
  dest=Path('cp_bounce_candidates')/f'{src.stem}_case{i+1}.txt';dest.parent.mkdir(exist_ok=True)
  if not dest.exists() or len(candidate)<len(load_programs(dest)[0]):save_programs(dest,[candidate])
  wins.append(dict(file=src.name,case=i+1,before=len(prog),after=len(candidate)))
 if a.pilot or candidate or (j+1)%10==0:print(f'{j+1}/{len(entries)} {src.name} case={i+1} H={u-t-1} {status} {len(prog)}->{len(candidate) if candidate else len(prog)} elapsed={time.perf_counter()-started:.1f}s',flush=True)
Path('cp_bounce_unsafe_results.json' if a.unsafe else 'cp_bounce_results.json').write_text(json.dumps(wins,indent=2));print('SAVED',sum(x['before']-x['after'] for x in wins),'CASES',len(wins),flush=True)
