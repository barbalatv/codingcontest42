from graph_cycles import *
from symmetry_graph import symmetry
import argparse,statistics
PILOT=[168,51,36,145,159,81,204,198,162,133,50]
MAX=(1<<64)-1
class Native:
 def __init__(self,exe):self.p=subprocess.Popen([str(BASE/'engines'/exe)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(BASE/'experiments'/f'{exe}.stderr').open('a'),text=True,bufsize=1)
 def ask(self,text):
  start=time.perf_counter();self.p.stdin.write(text);self.p.stdin.flush();out=list(map(int,self.p.stdout.readline().split()));assert len(out)>=4,out
  return out,time.perf_counter()-start
 def close(self):self.p.stdin.close();self.p.wait(timeout=10)
def board(c):
 rows=list(map(list,geometry(c[0])[0]))
 for y,x in c[1]:rows[y][x]='M'
 return '\n'.join(map(''.join,rows))
def actions(values):return [tuple('-FBT'[(v>>(2*e))&3] for e in range(6)) for v in values]
def qstates(g,p):
 ss=g.sim.prefix(p);acc=[t for t in range(1,len(ss)) if ss[t][3]>ss[t-1][3]];return ss,acc

def root_test(old,fix):
 # First candidate deletes the only target with 3 beams. Second creates it
 # with exactly 2 beams. Both use a synthetic one-cell pattern at R=3.
 c=(3,frozenset([(3,6)]),1);sim=Sim(c);cells=geometry(3)[1];k=cells.index((3,6));q=list(key(sim.initial()));q[6]=0
 for e in range(3):q[e]=next(p for p in range(18) if sim.rays[p][e]>>k&1)
 q[6]=7;bad=packed(q);q[6]=3;good=packed(q);data=f'3 1 100 32 200 8 99\n{board(c)}\n{bad}\n{bad} {good}\n'
 a,ta=old.ask(data);b,tb=fix.ask(data);assert a[0]==0 and b[0]>0,(a,b)
 pp=actions(b[4:]);assert verify(*c[:2],pp)==1
 info=dict(status='PASS',program=pp,input=str(c[0])+' '+str(2*c[0]+1)+' '+str(4*c[0]+1)+' 1\n'+board(c),invalid_first=bad,valid_second=good,old_length=a[0],fixed_length=b[0],old_seconds=ta,fixed_seconds=tb);(BASE/'experiments/root_regression_test.json').write_text(json.dumps(info,indent=2));print('ROOT_REGRESSION_PASS',info,flush=True)

def run(args):
 began=time.perf_counter();old=Native('regress_old.exe');fix=Native('regress_fixed.exe');engine=Native('geometry_search.exe');banks=sources();records=[]
 try:
  root_test(old,fix)
  ids=PILOT if args.mode=='pilot' else list(map(int,args.indices.split(','))) if args.indices else sorted(range(1,211),key=lambda i:len(load_programs(BASE/'best'/NAME)[i-1]),reverse=True)
  for idx in ids:
   tcase=time.perf_counter();i=idx-1;c=CASES[i];p=load_programs(BASE/'best'/NAME)[i];g=Graph(i);g.walk(START,p,'incumbent');ss,acc=qstates(g,p);first=key(ss[acc[0]]);initial=key(g.sim.initial());intervals=[b-a for a,b in zip(acc,acc[1:])];P=round(statistics.median(intervals)) if intervals else acc[0]
   for donor,origin in banks[i]:
    try:
     if verify(c[0],c[1],donor)==c[2]:g.walk(START,donor,origin)
    except Exception:pass
   symmetry(g);dp,_=g.dp(len(p),4096);update(i,dp,'initial_bank',time.perf_counter()-tcase)
   def integrate(start,prog,method,secs,seed,meta):
    before=len(load_programs(BASE/'best'/NAME)[i]);added=g.walk(start,prog,method) if prog else 0
    if added:
     g.bounce(1,100);symmetry(g);dp,path=g.dp(before,4096);update(i,dp,method,secs,seed)
    after=len(load_programs(BASE/'best'/NAME)[i]);rec=dict(case=idx,method=method,before=before,after=after,saved=before-after,runtime=secs,seed=seed,added_edges=added,fragment_ticks=len(prog),**meta);records.append(rec)
    with (BASE/'experiments'/f'{args.mode}.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
    print(rec,flush=True)
   if args.mode=='pilot':
    for label,service in [('old_regression',old),('fixed_regression',fix)]:
     data=f'{c[0]} 1 10000 {args.width} {args.ms} {max(4,acc[0]-1)} {20+args.seed%4}\n{board(c)}\n{packed(first)}\n';out,secs=service.ask(data);prog=actions(out[4:]);integrate(START,prog,label,secs,args.seed,dict(explored=out[1],engine_ms=out[2],validation='GRAPH_REPLAY'))
   goals=list(dict.fromkeys(key(ss[t]) for t in acc))[:16]
   # Endpoint variants generate geometrically new acceptance poses. Last-tick
   # feasibility is filtered only; full exact dynamics are checked downstream.
   rng=random.Random(args.seed+idx)
   for q in list(goals)[:4]:
    for trial in range(24):
     z=list(q)
     for e in rng.sample(range(6),2):z[e]=(z[e]+rng.choice([-1,0,1]))%(6*c[0])
     if rng.randrange(3)==0:z[6]^=1<<rng.randrange(6)
     matter=(tuple(z[:6]),z[6],0,0);one=two=three=0
     for e in range(6):
      if z[6]>>e&1:
       ray=g.sim.rays[z[e]][e];three|=two&ray;two|=one&ray;one|=ray
     if not (three&g.sim.target) and not ((two&~three)&g.sim.forbidden):goals.append(tuple(z))
   goals=list(dict.fromkeys(goals))[:64]
   specs=[]
   methods=[(2,'six_emitter_meet'),(3,'ordinary_beam'),(4,'macro_chord')]
   if args.method:methods=[x for x in methods if args.method in x[1]]
   for mode,label in methods:
    specs.append((mode,label+'_setup',initial,MAX,max(2,acc[0]-1),1))
    if c[2]>=2:specs.append((mode,label+'_edge',first,MAX,max(2,P-1),1))
    if c[2]>=3 and mode!=2:specs.append((mode,label+'_cycle2',first,packed(first),max(3,2*P-1),2))
   for j,(mode,label,start,goal,H,C) in enumerate(specs):
    seed=args.seed+idx*101+j
    data=f'{c[0]} {C} {args.width} {args.ms} {H} {mode} {seed}\n{board(c)}\n{packed(start)} {goal}\n{len(goals)}\n'+' '.join(map(str,map(packed,goals)))+'\n'
    out,secs=engine.ask(data);prog=actions(out[5:5+out[0]]);assert len(prog)==out[0]
    if prog:
     st=state(start)
     for row in prog:st=g.sim.step(st,row)
     assert st[3]==C and packed(key(st))==out[3],(idx,label,out)
    integrate(START if start==initial else start,prog,label,secs,seed,dict(explored=out[1],engine_ms=out[2],bridge_checks=out[4],copies=C,horizon=H,validation='PYTHON_REPLAY' if prog else 'NO_SOLUTION_IN_BUDGET'))
   g.persist();print('CASE_DONE',idx,'score',sum(map(len,load_programs(BASE/'best'/NAME))),'seconds',time.perf_counter()-tcase,flush=True)
 finally:old.close();fix.close();engine.close()
 print('DONE',args.mode,time.perf_counter()-began,flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--mode',default='pilot');ap.add_argument('--ms',type=int,default=700);ap.add_argument('--width',type=int,default=56);ap.add_argument('--seed',type=int,default=71000);ap.add_argument('--indices',default='');ap.add_argument('--method',default='');run(ap.parse_args())
