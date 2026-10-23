import sys,json,time,csv,subprocess,hashlib,random,argparse
from pathlib import Path
from collections import defaultdict,Counter
BASE=Path(__file__).resolve().parent;REPO=BASE.parent;sys.path.insert(0,str(REPO))
from solve_l6 import parse,delta
from solve_l5 import verify
from solve_l4 import geometry
from optimize_l6 import load_programs,save_programs
from optimize_l6_compact import Sim
NAME='answer_level-6_2-medium.txt';CASES=parse(REPO/'level-6/in_level-6_2-medium.txt');START='initial'
PILOT=[168,51,36,145,159,81,204,131,120,50]
def key(st):return tuple(st[0])+(st[1],)
def state(q):return (tuple(q[:6]),q[6],0,0)
def packed(q):return sum((p+128*((q[6]>>e)&1))<<(8*e) for e,p in enumerate(q[:6]))
def inverse(prog):return [tuple({'F':'B','B':'F'}.get(c,c) for c in row) for row in reversed(prog)]
def dist(q,r,L):return max(abs(delta(q[e],r[e],L))+int(((q[6]^r[6])>>e)&1) for e in range(6))
class Graph:
 def __init__(self,i):self.i=i;self.case=CASES[i];self.sim=Sim(self.case);self.E={};self.nodes=set();self.origin_counts=Counter();self.tested=set();self.stats=[]
 def add(self,a,b,c,prog,origin):
  assert 1<=c<=4
  st=self.sim.initial() if a==START else state(a)
  for row in prog:st=self.sim.step(st,row)
  assert st[3]==c and key(st)==b and st[2]&(self.sim.target|self.sim.forbidden)==0
  ek=(a,b,c);old=self.E.get(ek)
  if old is None or len(prog)<len(old['program']):
   self.E[ek]=dict(start=a,end=b,copies=c,ticks=len(prog),program=list(prog),origin=origin,verified=True);self.nodes.add(b);self.origin_counts[origin]+=1;return True
  return False
 def walk(self,start,prog,origin):
  # Every intermediate pickup splits a trajectory; retain macro edges up to 4.
  st=self.sim.initial() if start==START else state(start);anchors=[(0,start)];added=0
  for t,row in enumerate(prog,1):
   old=st[3];st=self.sim.step(st,row)
   if st[3]>old:
    q=key(st)
    for j,(a,qa) in enumerate(anchors[-4:]):added+=self.add(qa,q,len(anchors)-max(0,len(anchors)-4)-j,prog[a:t],origin)
    anchors.append((t,q))
  return added
 def dp(self,bound=10**9,frontier=256):
  K=self.case[2];dp=[{} for _ in range(K+1)];dp[0][START]=(0,None);pred={};adj=defaultdict(list)
  for ek,e in self.E.items():adj[ek[0]].append((ek,e))
  for k in range(K):
   if len(dp[k])>frontier:dp[k]=dict(sorted(dp[k].items(),key=lambda x:x[1][0])[:frontier])
   for q,(cost,_) in dp[k].items():
    for ek,e in adj[q]:
     n=k+e['copies'];v=e['end'];nc=cost+e['ticks']
     if n>K or nc>=bound:continue
     if v not in dp[n] or nc<dp[n][v][0]:dp[n][v]=(nc,ek);pred[n,v]=(k,q,ek)
  if not dp[K]:return None,[]
  q=min(dp[K],key=lambda q:dp[K][q][0]);edges=[];k=K
  while k:
   oldk,oldq,ek=pred[k,q];edges.append(self.E[ek]);k,q=oldk,oldq
  edges.reverse();return [row for e in edges for row in e['program']],edges
 def bounce(self,rounds=2,cap=180):
  for iteration in range(rounds):
   edges=sorted([e for e in self.E.values() if e['start']!=START],key=lambda e:e['ticks']/e['copies'])[:cap];gains=0
   for e in edges:
    p=e['program'];rev=inverse(p);noop=tuple('------')
    variants=[p,rev,[noop]+rev[:-1],rev[1:]+[noop],rev[:-1],rev[1:],p[1:]+p[:1],p[-1:]+p[:-1]]
    # Reuse a trajectory from its actual endpoint and alternate nearby donor poses.
    starts=[e['end']]+sorted(self.nodes,key=lambda q:(dist(q,e['start'],6*self.case[0]),q))[:3]
    for q in dict.fromkeys(starts):
     for prog in variants:
      token=q,tuple(prog)
      if not prog or token in self.tested:continue
      self.tested.add(token);gains+=self.walk(q,prog,'generalized_bounce')
   if not gains:break
 def persist(self):
  (BASE/'edges'/f'case{self.i+1}.json').write_text(json.dumps(dict(case=self.i+1,nodes=len(self.nodes),edges=list(self.E.values()),stats=self.stats),separators=(',',':')))

def sources():
 banks=defaultdict(list);seen=set()
 for f in sorted(REPO.rglob(NAME)):
  if 'training_medium_breakthrough' in str(f):continue
  try:
   pp=load_programs(f)
   if len(pp)!=210:continue
   for i,p in enumerate(pp):
    token=i,tuple(p)
    if token not in seen:seen.add(token);banks[i].append((p,str(f.relative_to(REPO))))
  except Exception:continue
 for directory in [REPO/'training_medium_codex/experiments',REPO/'training_medium/candidates']:
  for f in directory.glob('case*.txt'):
   import re
   match=re.match(r'case_?(\d+)',f.name)
   if not match:continue
   i=int(match[1])-1
   try:
    p=load_programs(f)[0];token=i,tuple(p)
    if token not in seen:seen.add(token);banks[i].append((p,str(f.relative_to(REPO))))
   except Exception:continue
 return banks

def update(i,prog,method,elapsed,seed=0):
 if prog is None:return False
 best=BASE/'best'/NAME;pp=load_programs(best);old=len(pp[i])
 if len(prog)>=old:return False
 c=CASES[i];assert verify(c[0],c[1],prog)==c[2]
 pp[i]=prog;tmp=best.with_suffix('.pending');save_programs(tmp,pp)
 subprocess.run(['node',str(BASE/'validate_sandbox_medium.cjs'),str(tmp)],capture_output=True,text=True,check=True)
 cand=BASE/'experiments'/f'case{i+1}_{method}_{len(prog)}.txt';ct=cand.with_suffix('.tmp');save_programs(ct,[prog]);ct.replace(cand);tmp.replace(best)
 with (BASE/'results.csv').open('a',newline='') as f:csv.writer(f).writerow([i+1,method,old,len(prog),old-len(prog),seed,elapsed])
 print('IMPROVED',i+1,old,'->',len(prog),'TOTAL',sum(map(len,pp)),method,flush=True);return True
class Engine:
 def __init__(self):self.p=subprocess.Popen([str(BASE/'engines/edge_search.exe')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(BASE/'experiments/engine_stderr.log').open('a'),text=True,bufsize=1)
 def query(self,g,e,ms,seed,goal=None):
  r,pat,_=g.case;rows=list(map(list,geometry(r)[0]));p=e['program'];q=e['start'];q=key(g.sim.initial()) if q==START else q
  for y,x in pat:rows[y][x]='M'
  words=(len(geometry(r)[1])+63)//64
  data=f'{r} {e["copies"]} {len(p)}\n'+'\n'.join(map(''.join,rows))+f'\n{len(p)}\n'+'\n'.join(' '.join(row) for row in p)+f'\n{packed(q)}\n'+' '.join('0' for _ in range(words))+f'\n{ms} {seed} {packed(goal) if goal else (1<<64)-1}\n'
  t=time.perf_counter();self.p.stdin.write(data);self.p.stdin.flush();out=self.p.stdout.readline().split();assert len(out)>=2,out
  p=[tuple(row) for row in out[2:]];assert len(p)==int(out[0]);return p,time.perf_counter()-t
 def close(self):self.p.stdin.close();self.p.wait(timeout=10)

def run(args):
 t0=time.perf_counter();banks=sources();engine=Engine();ids=PILOT if args.mode in ('pilot','focused') else sorted(range(1,211),key=lambda j:len(load_programs(BASE/'best'/NAME)[j-1]),reverse=True)
 metrics=[]
 try:
  for idx in ids:
   i=idx-1;ct=time.perf_counter();g=Graph(i);p=load_programs(BASE/'best'/NAME)[i];g.walk(START,p,'incumbent');valid=0
   for donor,origin in banks[i]:
    try:
     assert verify(CASES[i][0],CASES[i][1],donor)==CASES[i][2];g.walk(START,donor,origin);valid+=1
    except (AssertionError,ValueError):pass
   before=len(p);dp,_=g.dp(before);update(i,dp,'history_dp',time.perf_counter()-ct)
   g.bounce(rounds=2,cap=100 if args.mode=='pilot' else 60);p=load_programs(BASE/'best'/NAME)[i];dp,path=g.dp(len(p));update(i,dp,'generalized_bounce_dp',time.perf_counter()-ct)
   from symmetry_graph import symmetry
   symmetry(g);p=load_programs(BASE/'best'/NAME)[i];dp,path=g.dp(len(p),frontier=2048);update(i,dp,'symmetry_graph_dp',time.perf_counter()-ct)
   # Prioritize edges on the best DP path, rather than globally expensive historical paths.
   _,optimal_path=g.dp(frontier=2048)
   repeats=Counter((e['start'],e['end'],e['copies']) for e in optimal_path)
   choices=sorted(g.E.values(),key=lambda e:(e['start']==START,-repeats[(e['start'],e['end'],e['copies'])],e['ticks']/e['copies']))
   choices=[e for e in choices if 3<=e['ticks']<=40]
   selected=[];done=set()
   for e in choices:
    token=e['start'],e['copies'],e['ticks']
    if token in done:continue
    done.add(token);selected.append(e)
    if len(selected)>=args.queries:break
   # Always retain an opportunity to shorten a setup.
   setups=sorted((e for e in g.E.values() if e['start']==START and e['copies']==1),key=lambda e:e['ticks'])
   if setups:selected.append(setups[0])
   for j,e in enumerate(selected):
    seed=args.seed+idx*100+j;q,secs=engine.query(g,e,args.ms,seed)
    additions=g.walk(e['start'],q,'native_new_edge');info=dict(case=idx,seed=seed,seconds=secs,old=e['ticks'],new=len(q),copies=e['copies'],added=additions);g.stats.append(info)
    if additions:
     g.bounce(rounds=1,cap=60);symmetry(g);p=load_programs(BASE/'best'/NAME)[i];dp,path=g.dp(len(p));update(i,dp,'new_edges_dp',secs,seed)
   # A distinct return bridge is searched independently of physical reversibility.
   if optimal_path:
    donor=next((e for e in optimal_path if e['start']!=START and e['ticks']<=32),None)
    if donor:
     rev=dict(donor,start=donor['end'],end=donor['start'],program=[tuple('------')]+inverse(donor['program']),ticks=donor['ticks']+1)
     seed=args.seed+idx*100+99;bridge,secs=engine.query(g,rev,args.ms,seed,goal=donor['start']);n=g.walk(rev['start'],bridge,'fixed_pose_bridge')
     g.stats.append(dict(case=idx,seed=seed,seconds=secs,method='fixed_pose_bridge',added=n))
     if n:
      symmetry(g);p=load_programs(BASE/'best'/NAME)[i];dp,path=g.dp(len(p),frontier=2048);update(i,dp,'bridge_dp',secs,seed)
   g.persist();after=len(load_programs(BASE/'best'/NAME)[i]);rec=dict(case=idx,before=before,after=after,nodes=len(g.nodes),edges=len(g.E),historical_programs=valid,seconds=time.perf_counter()-ct);metrics.append(rec)
   with (BASE/'experiments'/f'{args.mode}.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
   print(rec,flush=True)
 finally:engine.close()
 print('DONE',args.mode,'seconds',time.perf_counter()-t0,flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--mode',default='pilot');ap.add_argument('--ms',type=int,default=600);ap.add_argument('--queries',type=int,default=8);ap.add_argument('--seed',type=int,default=20000);run(ap.parse_args())
