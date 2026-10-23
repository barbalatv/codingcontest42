from multi_experiment import *
import importlib.util

def run(args):
 native=Native('trajectory_synthesis.exe');start=time.perf_counter()
 try:
  ids=list(map(int,args.indices.split(',')))
  for idx in ids:
   i=idx-1;c=CASES[i];g=restore(idx);best=load_programs(BASE/'best'/NAME)[i];g.walk(START,best,'current');ss,aa=qstates(g,best);intervals=[b-a for a,b in zip(aa,aa[1:])];P=round(statistics.median(intervals)) if intervals else aa[0]
   horizons=[max(2,P-1)]
   if args.macro:requests=[(2,max(3,2*P-1))]
   else:requests=[(1,H) for H in horizons]
   for copies,H in requests:
    before=len(load_programs(BASE/'best'/NAME)[i]);seed=args.seed+idx*313;hint=[];hintroot=key(ss[aa[0]])
    for ja,a in enumerate(aa):
     if ja+copies>=len(aa):continue
     b=aa[ja+copies]
     if b-a==H+1 and ss[a][:2]==ss[b][:2]:hint=best[a:b];hintroot=key(ss[a]);break
    data=f'{c[0]} {copies} {H} {args.ms} {seed}\n{board(c)}\n'
    if not args.old_input:data+=f'{len(hint)} {packed(hintroot)}\n'+' '.join(str(sum('-FBT'.index(ch)<<(2*e) for e,ch in enumerate(row))) for row in hint)+'\n'
    out,secs=native.ask(data);prog=actions(out[6:6+out[0]]);assert len(prog)==out[0];
    near_start=6+out[0];near_root=out[near_start] if near_start<len(out) else 0;near_program=actions(out[near_start+1:]) if near_start<len(out) else [];
    (BASE/'experiments'/f'near_case{idx}_h{H}_c{copies}_s{seed}.json').write_text(json.dumps(dict(case=idx,root=near_root,copies=copies,program=near_program,seed=seed,defect=out[1])))
    root=tuple((out[3]>>(8*e))&127 for e in range(6))+(sum(((out[3]>>(8*e+7))&1)<<e for e in range(6)),);embedded=False
    if prog:
     st=state(root)
     for row in prog:st=g.sim.step(st,row)
     assert st[3]==copies and key(st)==root and st[2]&(g.sim.target|g.sim.forbidden)==0
     g.walk(root,prog,'trajectory_synthesis');symmetry(g)
     prefixes=[best[:t] for t in aa[:4]]+[safe_setups(g,root)]
     for prefix in prefixes:
      pp=simulate_repeat(g,prefix,prog,before)
      if pp:g.walk(START,pp,'trajectory_startup');embedded|=update(i,pp,'trajectory_synthesis',secs,seed)
     states=[state(root)]
     for row in prog:states.append(g.sim.step(states[-1],row))
     for phase in range(1,H):
      q=key(states[phase]);script=prog[phase:]+prog[:phase];pp=simulate_repeat(g,safe_setups(g,q),script,before)
      if pp:g.walk(START,pp,'trajectory_phase');embedded|=update(i,pp,'trajectory_phase',secs,seed)
     (BASE/'experiments'/f'trajectory_case{idx}_h{H}_c{copies}_s{seed}.json').write_text(json.dumps(dict(case=idx,root=root,copies=copies,program=prog,seed=seed)))
     dp,path=g.dp(before,4096);embedded|=update(i,dp,'trajectory_dp',secs,seed);g.persist()
    after=len(load_programs(BASE/'best'/NAME)[i]);rec=dict(case=idx,method='whole_trajectory_synthesis',copies=copies,horizon=H,seed=seed,budget=args.ms,runtime=secs,engine_ms=out[2],evaluations=out[4],restarts=out[5],best_defect=out[1],valid_cycle=bool(prog),embedded=embedded,before=before,after=after,saved=before-after)
    with (BASE/'experiments'/f'{args.tag}.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
    print(rec,flush=True)
 finally:native.close()
 print('SYNTH_DONE',time.perf_counter()-start,flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--indices',default='120,108,139,29,181,41,1,134,168,51,133,162,198,50');ap.add_argument('--ms',type=int,default=2200);ap.add_argument('--seed',type=int,default=500000);ap.add_argument('--tag',default='synthesis');ap.add_argument('--macro',action='store_true');ap.add_argument('--old-input',action='store_true');run(ap.parse_args())
