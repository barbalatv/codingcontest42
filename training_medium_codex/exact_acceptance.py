import sys,json,time,hashlib,subprocess,csv,random
from pathlib import Path
BASE=Path(__file__).resolve().parent;REPO=BASE.parent;sys.path.insert(0,str(REPO))
from ortools.sat.python import cp_model
from optimize_l6 import load_programs,save_programs
from optimize_l6_compact import Sim
from solve_l6 import parse,delta
from solve_l5 import verify
from solve_l4 import geometry
CASES=parse(REPO/'level-6/in_level-6_2-medium.txt');NAME='answer_level-6_2-medium.txt'

def synth(case,start,H,copies,end=None,closed=False,hint=None,seconds=3,seed=0,free=(),root_radius=0):
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
     if free and e not in free:m.add(v==old[0][e]+L*((old[1]>>e)&1))
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
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds;solver.parameters.num_search_workers=4;solver.parameters.random_seed=seed
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

def update(i,p,method,elapsed):
 path=BASE/'best'/NAME;progs=load_programs(path);old=len(progs[i])
 if len(p)>=old:return False
 c=CASES[i];assert verify(c[0],c[1],p)==c[2]
 candidate=BASE/'experiments'/f'case{i+1}_{method}_{len(p)}.txt';save_programs(candidate,[p])
 progs[i]=p;temp=path.with_suffix('.tmp');save_programs(temp,progs)
 # Validate the exact staged full bytes before committing the checkpoint.
 check=BASE/'best'/NAME;backup=check.read_bytes();temp.replace(check)
 try:subprocess.run(['node',str(BASE/'validate_sandbox_medium.cjs')],check=True,capture_output=True,text=True)
 except Exception:check.write_bytes(backup);raise
 with (BASE/'results.csv').open('a',newline='') as f:csv.writer(f).writerow([i+1,method,old,len(p),old-len(p),elapsed])
 print('IMPROVED',i+1,old,len(p),'TOTAL',sum(map(len,progs)),method,flush=True);return True

def trace():
 progs=load_programs(BASE/'baseline'/NAME);assert len(progs)==210 and sum(map(len,progs))==5946
 out=[]
 for i,(c,p) in enumerate(zip(CASES,progs)):
  assert verify(c[0],c[1],p)==c[2];sim=Sim(c);ss=sim.prefix(p);acc=[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]]
  for t in acc:assert ss[t][2]&(sim.target|sim.forbidden)==0
  cycles=[]
  for a,t in enumerate(acc):
   for b in range(a+1,min(len(acc),a+5)):
    u=acc[b]
    if ss[t][:2]==ss[u][:2]:cycles.append(dict(start=t,end=u,copies=b-a))
  out.append(dict(case=i+1,K=c[2],ticks=len(p),setup=acc[0],intervals=[b-a for a,b in zip(acc,acc[1:])],tail=len(p)-acc[-1],acceptances=acc,cycles=cycles))
 (BASE/'experiments/trace.json').write_text(json.dumps(out,indent=2));return out

if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--mode',default='pilot');ap.add_argument('--seconds',type=float,default=3);ap.add_argument('--limit',type=int,default=210);args=ap.parse_args();traces=trace();priority=[51,81,168,50,36,120,145,159]
 if args.mode=='trace':
  for i in priority:print(traces[i-1])
  subprocess.run(['node',str(BASE/'validate_sandbox_medium.cjs')],check=True);sys.exit()
 ids=priority if args.mode=='pilot' else sorted(range(1,211),key=lambda x:traces[x-1]['setup'],reverse=True)[:args.limit]
 log=BASE/'experiments'/f'{args.mode}_log.jsonl'
 for idx in ids:
  i=idx-1;c=CASES[i];p=load_programs(BASE/'best'/NAME)[i];sim=Sim(c);ss=sim.prefix(p);acc=[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]]
  if args.mode=='pilot':
   seen=set()
   for cyc in traces[i]['cycles']:
    a,b=cyc['start'],cyc['end'];C=cyc['copies'];H=b-a-1
    if (H,C) in seen or C>4:continue
    seen.add((H,C));old=ss[a];q,info=synth(c,old,H,C,closed=True,hint=ss[a:b+1],seconds=args.seconds,seed=idx)
    if q:
     cand=list(p[:a]);st=ss[a]
     while len(cand)<len(p) and st[3]<c[2]:
      for row in q:
       st=sim.step(st,row);cand.append(row)
       if st[3]>=c[2]:break
     if st[3]==c[2]:update(i,cand,'cycle_cp',info['seconds'])
    info.update(case=idx,method='cycle_cp');print(info,flush=True)
    with log.open('a') as f:f.write(json.dumps(info)+'\n')
    if len(seen)>=3:break
  # Acceptance-boundary LNS: retain true start, exact end acceptance pose;
  # final window has free pose. Full suffix is replayed independently.
  p=load_programs(BASE/'best'/NAME)[i];ss=sim.prefix(p);acc=[0]+[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]]
  jobs=[]
  for b in acc[1:]:
   for a in acc:
    if 4<=b-a<=16 and a<b:
     lb=max(abs(delta(ss[a][0][e],ss[b][0][e],6*c[0]))+int(((ss[a][1]^ss[b][1])>>e)&1) for e in range(6))
     if lb<b-a:jobs.append((b-a-lb,a,b))
  jobs.sort(reverse=True)
  if args.mode=='tail':
   jobs=[(0,max(0,len(p)-w),len(p)) for w in (6,8,10,12) if len(p)>=w and ss[len(p)][3]>ss[max(0,len(p)-w)][3]]
  tested=set()
  for _,a,b in jobs[:(3 if args.mode=='pilot' else 2)]:
   key=(ss[a][:2],ss[b][:2],b-a,ss[b][3]-ss[a][3])
   if key in tested:continue
   tested.add(key);q,info=synth(c,ss[a],b-a-1,ss[b][3]-ss[a][3],end=ss[b] if b<len(p) else None,hint=ss[a:b+1],seconds=args.seconds,seed=idx+17)
   if q:
    cand=p[:a]+q+p[b:];st=sim.initial();finish=None
    for t,row in enumerate(cand):
     st=sim.step(st,row)
     if st[3]>=c[2]:finish=t+1;break
    if finish:update(i,cand[:finish],'acceptance_lns_cp',info['seconds'])
   info.update(case=idx,method='acceptance_lns_cp',start=a,end=b);print(info,flush=True)
   with log.open('a') as f:f.write(json.dumps(info)+'\n')
