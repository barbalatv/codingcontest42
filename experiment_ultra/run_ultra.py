import sys,json,time,os,csv,argparse,ctypes
from pathlib import Path
from subprocess import Popen,PIPE
BASE=Path(__file__).resolve().parent;REPO=BASE.parent;sys.path.insert(0,str(REPO))
from solve_l6 import parse
from solve_l4 import geometry
from solve_l5 import verify
from optimize_l6 import load_programs,save_programs
from optimize_l6_compact import Sim
from phase2_regress import regenerate
CHARS='-FBT';MAX64=(1<<64)-1

def transform_pattern(pattern,r,k,reflect):
 out=set()
 for y,x in pattern:
  a=y-r;b=(x-2*r-a)//2
  if reflect:a,b=b,a
  for _ in range(k):a,b=-b,a+b
  out.add((a+r,2*b+a+2*r))
 return frozenset(out)

def transform_program(program,k,reflect,inverse=False):
 out=[]
 for line in program:
  row=['-']*6
  for i in range(6):
   j=((1-i if reflect else i)-k)%6;c=line[j] if inverse else line[i]
   if reflect:c={'F':'B','B':'F'}.get(c,c)
   row[i if inverse else j]=c
  out.append(tuple(row))
 return out

def packed(s):return sum((p+128*((s[1]>>i)&1))<<(8*i) for i,p in enumerate(s[0]))
def peak(pid):
 class PMC(ctypes.Structure):
  _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(s,ctypes.c_size_t) for s in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
 k=ctypes.windll.kernel32;k.OpenProcess.restype=ctypes.c_void_p;h=k.OpenProcess(0x410,False,pid)
 p=PMC();p.cb=ctypes.sizeof(p);ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(h),ctypes.byref(p),p.cb);k.CloseHandle(ctypes.c_void_p(h));return p.PeakWorkingSetSize

class Engine:
 def __init__(self,exe='ultra_regress.exe'):self.p=Popen([str(BASE/exe)],stdin=PIPE,stdout=PIPE,stderr=(BASE/'engine_stderr.txt').open('a'),text=True,bufsize=1)
 def query(self,case,end,variant,ms,width=48,start=None,goal=None,depth=160):
  r,pat,K=case;rows=list(map(list,geometry(r)[0]))
  for y,x in pat:rows[y][x]='M'
  v=100+variant if start is not None else variant
  text=f'{r} 1 100000 {width} {ms} {depth} {v}\n'+'\n'.join(map(''.join,rows))+'\n'
  text+=(f'{start} {MAX64 if goal is None else goal}\n' if start is not None else f'{end}\n')
  t=time.perf_counter();self.p.stdin.write(text);self.p.stdin.flush();raw=self.p.stdout.readline();a=list(map(int,raw.split()));assert len(a)>=4,raw
  lines=[tuple(CHARS[(z>>(2*i))&3] for i in range(6)) for z in a[4:]];assert len(lines)==a[0]
  return lines,dict(evaluations=a[1],engine_ms=a[2],pose=a[3],wall_s=time.perf_counter()-t,peak_bytes=peak(self.p.pid))
 def close(self):self.p.stdin.close();self.p.wait(timeout=10)

class Graph:
 def __init__(self,case):self.case=case;self.sim=Sim(case);self.initial=packed(self.sim.initial());self.edges={};self.vertices={self.initial:self.sim.initial()[:2]};self.seeds={};self.stats=[]
 def add_program(self,lines):
  s=self.sim.initial();last=self.initial;segment=[]
  for line in lines:
   old=s[3];s=self.sim.step(s,line);segment.append(tuple(line))
   if s[3]>old:
    dst=packed(s);self.add_edge(last,dst,segment);self.vertices[dst]=s[:2];last=dst;segment=[]
 def add_edge(self,a,b,lines):
  key=a,b
  if key not in self.edges or len(lines)<len(self.edges[key]):self.edges[key]=list(lines)
 def add_query(self,start,lines):
  if not lines:return None
  pose,active=self.vertices[start];s=(pose,active,0,0)
  for t,line in enumerate(lines):
   old=s[3];s=self.sim.step(s,line)
   if s[3]>old:
    assert s[3]==1
    dst=packed(s);self.vertices[dst]=s[:2];self.add_edge(start,dst,lines[:t+1]);return dst
  return None
 def solve(self,K):
  dp={self.initial:(0,[])}
  for _ in range(K):
   nxt={}
   for (a,b),lines in self.edges.items():
    if a not in dp:continue
    cost,out=dp[a];cost+=len(lines)
    if b not in nxt or cost<nxt[b][0]:nxt[b]=cost,out+lines
   dp=nxt
   if not dp:return None
  return min(dp.values(),key=lambda x:x[0])[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--pilot',action='store_true');p.add_argument('--file',default='');p.add_argument('--indices',default='');p.add_argument('--ms',type=int,default=700);p.add_argument('--width',type=int,default=48);p.add_argument('--variants',default='0,1,2');p.add_argument('--graph-budget',type=int,default=6);p.add_argument('--limit',type=int,default=999);p.add_argument('--rotate',type=int,default=0);p.add_argument('--reflect',action='store_true');p.add_argument('--min-length',type=int,default=0);p.add_argument('--tag',default='');args=p.parse_args()
 OUT=BASE/('candidates_'+args.tag if args.tag else 'candidates');OUT.mkdir(exist_ok=True);results=[];service=Engine();started=time.perf_counter();updates=[]
 try:
  for kind,indices in [('2-medium',[51,159,187,193]),('3-large',[63,87,119,144]),('4-enormous',[65,52,115,30,129])]:
   if args.file and args.file not in kind:continue
   source=REPO/f'level-6/in_level-6_{kind}.txt';cases=parse(source);answer=REPO/f'level-6/answer_level-6_{kind}.txt';original=load_programs(answer);dest=OUT/answer.name
   previous=BASE/'candidates'/answer.name
   programs=load_programs(dest) if dest.exists() else load_programs(previous) if previous.exists() else list(original)
   if args.indices:indices=list(map(int,args.indices.split(',')))
   elif not args.pilot:indices=[i+1 for i in sorted(range(len(cases)),key=lambda i:len(programs[i]),reverse=True)[:args.limit]]
   for idx in indices:
    i=idx-1;actual_case=cases[i];before=len(programs[i])
    if before<args.min_length:continue
    case=(actual_case[0],transform_pattern(actual_case[1],actual_case[0],args.rotate,args.reflect),actual_case[2]);seed=transform_program(programs[i],args.rotate,args.reflect);graph=Graph(case);graph.add_program(seed);states=graph.sim.prefix(seed);first=next(s for s in states if s[3]);end=packed(first);case_stats=[];t0=time.perf_counter()
    for variant in map(int,args.variants.split(',')):
     raw,stats=service.query(case,end,20+variant,args.ms,args.width);stats.update(mode='regress',variant=variant);case_stats.append(stats)
     if raw:
      graph.add_program(raw)
      try:
       repeated=regenerate(case,raw);graph.add_program(repeated)
      except (AssertionError,Exception) as e:stats['fallback_error']=str(e)
    reg_candidate=graph.solve(case[2]);reg_best=len(reg_candidate) if reg_candidate else before
    # Dynamic graph: direct continuation, a one-copy cycle and a return edge.
    nodes=sorted((v for v in graph.vertices if v!=graph.initial),key=lambda v:min((len(e) for (a,b),e in graph.edges.items() if b==v),default=999))
    tasks=[(graph.initial,None,0)] if case[2]==1 else []
    if nodes:tasks.extend([(nodes[0],None,0),(nodes[0],nodes[0],1)])
    for node in nodes[1:3]:tasks.append((node,None,1))
    n=0
    while tasks and n<args.graph_budget:
     start,goal,variant=tasks.pop(0);raw,stats=service.query(case,end,variant,args.ms,args.width,start,goal,depth=min(160,before-1));stats.update(mode='free' if goal is None else 'cycle' if goal==start else 'pingpong',start=start,goal=goal);case_stats.append(stats);n+=1
     dst=graph.add_query(start,raw)
     if dst is not None and dst!=start and dst!=graph.initial:
      if (dst,start) not in graph.edges:tasks.insert(min(1,len(tasks)),(dst,start,2))
      if dst not in nodes:nodes.append(dst);tasks.append((dst,None,1))
    candidate=graph.solve(case[2]);after=before;valid=False
    if candidate and len(candidate)<before:
     candidate=transform_program(candidate,args.rotate,args.reflect,True)
     actual=verify(actual_case[0],actual_case[1],candidate);assert actual==actual_case[2],(kind,idx,actual,actual_case[2]);programs[i]=candidate;after=len(candidate);valid=True
     temp=dest.with_suffix('.tmp');save_programs(temp,programs);os.replace(temp,dest)
     updates.append(dict(kind=kind,case=idx,before=before,after=after))
    rec=dict(kind=kind,case=idx,rotate=args.rotate,reflect=args.reflect,baseline=len(original[i]),before=before,after=after,gain=before-after,regression_route_length=reg_best,graph_additional_gain=max(0,min(before,reg_best)-after),wall_s=time.perf_counter()-t0,evaluations=sum(s['evaluations'] for s in case_stats),peak_bytes=max(s['peak_bytes'] for s in case_stats),vertices=len(graph.vertices),edges=len(graph.edges),independent_validated=valid,queries=case_stats)
    results.append(rec)
    if after<before or idx%25==0:print(json.dumps({k:v for k,v in rec.items() if k!='queries'}),flush=True)
    log=BASE/(f'benchmark_{args.tag}.jsonl' if args.tag else 'benchmark.jsonl')
    with log.open('a') as f:f.write(json.dumps(rec)+'\n')
    if not dest.exists():save_programs(dest,programs)
   print('TOTAL',kind,sum(map(len,original)),'->',sum(map(len,programs)),flush=True)
 finally:service.close()
 (BASE/f'run_{int(time.time())}.json').write_text(json.dumps(results,indent=1));print('DONE',time.perf_counter()-started,'UPDATES',updates,flush=True)

if __name__=='__main__':main()
