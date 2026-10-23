from run_geometry import *
from symmetry_graph import restore

def unpack_response(out):
 n=out[0];primary=actions(out[5:5+n]);cursor=5+n;extra=[]
 if cursor<len(out):
  count=out[cursor];cursor+=1
  for _ in range(count):
   m,end=out[cursor:cursor+2];cursor+=2;pp=actions(out[cursor:cursor+m]);cursor+=m;extra.append((end,pp))
 assert cursor==len(out),(cursor,len(out))
 return primary,extra

def run(args):
 start=time.perf_counter();service=Native('geometry_search.exe');records=[]
 try:
  ids=list(map(int,args.indices.split(',')))
  for idx in ids:
   tcase=time.perf_counter();i=idx-1;c=CASES[i];g=restore(idx);pp=load_programs(BASE/'best'/NAME)[i];g.walk(START,pp,'current_incumbent');ss,acc=qstates(g,pp);P=round(statistics.median([b-a for a,b in zip(acc,acc[1:])])) if len(acc)>1 else acc[0];initial=key(g.sim.initial());first=key(ss[acc[0]]);goals=list(dict.fromkeys(key(ss[t]) for t in acc));seenposes={canonical_py(q,c[0]) for q in g.nodes};newposes={};allcalls=0
   def query(mode,label,root,H,copies=1,goal=MAX,ms=None):
    nonlocal allcalls
    before=len(load_programs(BASE/'best'/NAME)[i]);seed=args.seed+idx*233+allcalls;allcalls+=1;budget=ms or args.ms
    text=f'{c[0]} {copies} {args.width} {budget} {H} {mode} {seed}\n{board(c)}\n{packed(root)} {goal}\n{len(goals)}\n'+' '.join(map(str,map(packed,goals)))+'\n';out,secs=service.ask(text);primary,extras=unpack_response(out);fragments=[primary]+[p for end,p in extras];added=0;new=0
    for p in fragments:
     if not p:continue
     st=state(root)
     for row in p:st=g.sim.step(st,row)
     assert st[3]==copies,(idx,label,st[3],copies);q=key(st);assert st[2]&(g.sim.target|g.sim.forbidden)==0
     added+=g.walk(START if root==initial else root,p,label)
     can=canonical_py(q,c[0])
     if can not in seenposes:seenposes.add(can);newposes[q]=min(len(p),newposes.get(q,999));new+=1
    if added:
     g.bounce(1,80);symmetry(g);p,path=g.dp(before,4096);update(i,p,label,secs,seed)
    after=len(load_programs(BASE/'best'/NAME)[i]);rec=dict(case=idx,method=label,root=root,horizon=H,copies=copies,budget_ms=budget,width=args.width,seed=seed,runtime=secs,explored=out[1],bridge_checks=out[4],new_poses=new,added_edges=added,fragment_ticks=out[0],before=before,after=after,saved=before-after);records.append(rec)
    with (BASE/'experiments'/f'{args.tag}.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
    print(rec,flush=True)
   methods=[(2,'meet'),(3,'ordinary'),(4,'chord')]
   if args.method:methods=[p for p in methods if args.method in p[1]]
   for mode,label in methods:
    query(mode,label+'_plateau_setup',initial,acc[0])
    if len(acc)>1:query(mode,label+'_plateau_edge',first,P)
   # Expand equal-cost endpoints, not just the original incumbent cycle pose.
   def merit(q):
    one=two=three=0
    for e in range(6):
     if q[6]>>e&1:
      ray=g.sim.rays[q[e]][e];three|=two&ray;two|=one&ray;one|=ray
    return ((two&~three&g.sim.target).bit_count()*2-(three&g.sim.target).bit_count(),-newposes[q],q)
   candidates=sorted(newposes,key=merit,reverse=True)[:args.roots]
   for q in candidates:
    for mode,label in methods:
     query(mode,label+'_new_pose_edge',q,max(2,P-1))
   # A genuinely different 2-3-copy alternating period can beat one-copy closure.
   if candidates and c[2]>=4:
    root=candidates[0]
    for copies in (2,3):query(4,'chord_new_cycle'+str(copies),root,max(copies,copies*P-1),copies,packed(root),ms=args.ms*2)
   g.persist();print('CHAIN_CASE_DONE',idx,'nodes',len(g.nodes),'newposes',len(newposes),'total',sum(map(len,load_programs(BASE/'best'/NAME))),'seconds',time.perf_counter()-tcase,flush=True)
 finally:service.close()
 print('CHAIN_DONE',time.perf_counter()-start,flush=True)
def canonical_py(q,r):
 from symmetry_graph import swapq
 return min(swapq(q,m,r) for m in range(8))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--indices',default='120,108,139,29,181,41,1,134,168,51,133,162,198,50');ap.add_argument('--ms',type=int,default=1000);ap.add_argument('--width',type=int,default=96);ap.add_argument('--seed',type=int,default=82000);ap.add_argument('--tag',default='chain');ap.add_argument('--method',default='');ap.add_argument('--roots',type=int,default=2);run(ap.parse_args())
