import sys,time,subprocess,json
from pathlib import Path
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B));from exact_acceptance import *
p=subprocess.Popen([str(BASE/'engines/acceptance_tail.exe')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(BASE/'experiments/native_stderr.log').open('w'),text=True,bufsize=1)
started=time.perf_counter();wins=0
try:
 for i in sorted(range(210),key=lambda i:len(load_programs(BASE/'best'/NAME)[i]),reverse=True):
  case=CASES[i];sim=Sim(case);prog=load_programs(BASE/'best'/NAME)[i];r,pat,K=case
  for W in (8,12,16):
   a=max(0,len(prog)-W);st=sim.prefix(prog)[a];remaining=K-st[3]
   if remaining<1:continue
   rows=list(map(list,geometry(r)[0]));cells=geometry(r)[1];words=(len(cells)+63)//64
   for y,x in pat:rows[y][x]='M'
   pack=sum((v+128*((st[1]>>e)&1))<<(8*e) for e,v in enumerate(st[0]));tail=prog[a:]
   data=f'{r} {remaining} {len(tail)}\n'+'\n'.join(map(''.join,rows))+f'\n{len(tail)}\n'+'\n'.join(' '.join(row) for row in tail)+f'\n{pack}\n'+' '.join(str((st[2]>>(64*w))&((1<<64)-1)) for w in range(words))+f'\n450 {870000+i*37+W}\n'
   t=time.perf_counter();p.stdin.write(data);p.stdin.flush();out=p.stdout.readline().split();assert out
   q=[tuple(row) for row in out[2:]]
   if len(q)<len(tail):
    cand=prog[:a]+q
    if update(i,cand,'native_acceptance_tail',time.perf_counter()-t):prog=cand;wins+=1
  if i%20==0:print('PROGRESS',i+1,'seconds',time.perf_counter()-started,flush=True)
finally:p.stdin.close();p.wait(timeout=10)
print('DONE',wins,time.perf_counter()-started,flush=True)
