from chain_experiment import *

def simulate_repeat(g,prefix,cycle,bound):
 st=g.sim.initial();out=[]
 for row in prefix:
  st=g.sim.step(st,row);out.append(row)
  if st[3]>=g.case[2]:return out if len(out)<bound else None
 for rep in range(g.case[2]*4+8):
  for row in cycle:
   st=g.sim.step(st,row);out.append(row)
   if len(out)>=bound:return None
   if st[3]>=g.case[2]:return out
 return None

def safe_setups(g,q):
 r=g.case[0];initial=g.sim.initial();pos=list(initial[0]);out=[]
 while tuple(pos)!=tuple(q[:6]):
  row=[]
  for e in range(6):
   d=delta(pos[e],q[e],6*r);row.append('B' if d>0 else 'F' if d<0 else '-');pos[e]=(pos[e]+(1 if d>0 else -1 if d<0 else 0))%(6*r)
  out.append(tuple(row))
 if q[6]:out.append(tuple('T' if q[6]>>e&1 else '-' for e in range(6)))
 return out

def run(args):
 service=Native('multi_flood.exe');native=Native('geometry_search.exe');started=time.perf_counter()
 try:
  ids=list(map(int,args.indices.split(',')))
  for idx in ids:
   i=idx-1;c=CASES[i];g=restore(idx);best=load_programs(BASE/'best'/NAME)[i];g.walk(START,best,'current');ss,acc=qstates(g,best);cycles=[];seen=set()
   for ia,a in enumerate(acc):
    for ib in range(ia+1,min(len(acc),ia+5)):
     b=acc[ib];C=ib-ia
     if canonical_py(key(ss[a]),c[0])!=canonical_py(key(ss[b]),c[0]):continue
     token=C,b-a,key(ss[a])
     if token in seen:continue
     seen.add(token);cycles.append((C,a,b,b-a))
   # Test new multi-copy horizons before one-copy queries; do not duplicate old root searches.
   cycles.sort(key=lambda v:(v[0]==1,v[3]/v[0],v[0]));used=set();queries=0
   for copies,a,b,oldn in cycles:
    if copies==1 and args.no_single:continue
    token=copies,oldn
    if token in used:continue
    used.add(token);q=key(ss[a]);seed=args.seed+idx*401+queries;prog=best[a:b];data=f'{c[0]} {copies} {len(prog)} {args.ms} {seed} 1\n{board(c)}\n{packed(q)}\n'+' '.join(str(sum('-FBT'.index(ch)<<(2*e) for e,ch in enumerate(row))) for row in prog)+'\n'
    out,secs=service.ask(data);candidate=actions(out[5:]);root=tuple((out[3]>>(8*e))&127 for e in range(6))+(sum(((out[3]>>(8*e+7))&1)<<e for e in range(6)),);before=len(load_programs(BASE/'best'/NAME)[i]);found=False
    if candidate:
     st=state(root)
     for row in candidate:st=g.sim.step(st,row)
     assert st[3]==copies and canonical_py(key(st),c[0])==canonical_py(root,c[0]) and st[2]&(g.sim.target|g.sim.forbidden)==0
     found=True;g.walk(root,candidate,'multi_flood_cycle');symmetry(g)
     # Evaluate startup effects exactly. Activation is never treated as an empty-field operation.
     prefixes=[best[:a],safe_setups(g,root)]
     for prefix in prefixes:
      pp=simulate_repeat(g,prefix,candidate,before)
      if pp:g.walk(START,pp,'multi_flood_startup');update(i,pp,'multi_flood_cycle',secs,seed)
     states=[state(root)]
     for row in candidate:states.append(g.sim.step(states[-1],row))
     for phase in range(1,len(candidate)):
      rotated=candidate[phase:]+candidate[:phase];prefix=safe_setups(g,key(states[phase]));pp=simulate_repeat(g,prefix,rotated,before)
      if pp:g.walk(START,pp,'multi_flood_phase');update(i,pp,'multi_flood_phase',secs,seed)
     dp,path=g.dp(before,4096);update(i,dp,'multi_flood_dp',secs,seed)
     # Save isolated cycles even if their startup has not yet paid for itself.
     (BASE/'experiments'/f'cycle_case{idx}_c{copies}_h{len(candidate)}_s{seed}.json').write_text(json.dumps(dict(case=idx,root=root,copies=copies,program=candidate,seed=seed)))
    after=len(load_programs(BASE/'best'/NAME)[i]);rec=dict(case=idx,method='multi_flood',copies=copies,old_period=oldn,horizon=oldn-1,ms=args.ms,runtime=secs,seed=seed,best_defect=out[1],evaluations=out[4],found_valid_cycle=found,before=before,after=after,saved=before-after)
    with (BASE/'experiments'/f'{args.tag}.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
    print(rec,flush=True);queries+=1
    if queries>=args.queries:break
   g.persist()
 finally:service.close();native.close()
 print('MULTI_DONE',time.perf_counter()-started,flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--indices',default='168,51,36,145,159,81,204,198,162,133,50,120,108,139,29');ap.add_argument('--ms',type=int,default=1800);ap.add_argument('--seed',type=int,default=200000);ap.add_argument('--queries',type=int,default=3);ap.add_argument('--tag',default='multi_flood');ap.add_argument('--no-single',action='store_true');run(ap.parse_args())
