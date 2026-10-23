import argparse,json,time,subprocess,random
from pathlib import Path
from solve_l6 import parse,delta
from solve_l4 import geometry
from solve_l5 import verify
from optimize_l6 import ROOT,load_programs,save_programs
from optimize_l6_compact import Sim

def neighborhoods(case,prog):
 sim=Sim(case);states=sim.prefix(prog);segments=[];begin=0
 for t in range(1,len(states)):
  if states[t][3]>states[t-1][3]:segments.append((begin,t));begin=t
 options=[]
 for lo,hi in segments:
  ones,zeros=sim.target,sim.forbidden;req={hi:(ones,zeros)}
  for t in range(hi-1,lo-1,-1):
   pos,active,_,_=states[t+1];one=two=three=0
   for e in range(6):
    if active>>e&1:
     ray=sim.rays[pos[e]][e];three|=two&ray;two|=one&ray;one|=ray
   assert not ones&three and not zeros&two&~three,(t,hi)
   ones&=~two;zeros&=~three;req[t]=(ones,zeros)
  for W in (2,3,4,6,8,12,20,32,40):
   for b in sorted(set(range(lo+W,hi,max(2,W//3)))|{hi-1}):
    a=b-W
    if a<lo:continue
    s,g=states[a],states[b]
    lower=max(abs(delta(s[0][e],g[0][e],6*case[0]))+int((s[1]>>e&1)!=(g[1]>>e&1)) for e in range(6))
    if lower>=W:continue
    ones,zeros=req[b]
    slack=W-lower;constraints=ones.bit_count()+zeros.bit_count()
    options.append((slack/(1+constraints/25),a,b,ones,zeros,s))
 options.sort(reverse=True)
 return sim,options

def optimize(engine,case,prog,budget,ms,rng):
 best=prog;deadline=time.perf_counter()+budget;tested=set();attempts=0
 r,pat,count=case;rows=list(map(list,geometry(r)[0]));words=(len(geometry(r)[1])+63)//64
 for y,x in pat:rows[y][x]='M'
 board='\n'.join(map(''.join,rows));word=lambda mask:' '.join(str((mask>>(64*w))&((1<<64)-1)) for w in range(words))
 while time.perf_counter()<deadline:
  sim,options=neighborhoods(case,best);key=hash(tuple(best));options=[o for o in options if (key,o[1],o[2]) not in tested]
  if not options:break
  # Bias toward slack but vary contexts; exact simulator decides whether to retain.
  o=options[min(len(options)-1,int(rng.expovariate(.2)))];_,a,b,ones,zeros,state=o;tested.add((key,a,b));window=best[a:b];n=len(window)
  packed=sum((v+128*((state[1]>>k)&1))<<(8*k) for k,v in enumerate(state[0]))
  data=f'{r} 1 {n}\n{board}\n{n}\n'+'\n'.join(' '.join(row) for row in window)+f'\n{packed}\n{word(state[2])}\n{word(ones)}\n{word(zeros)}\n{ms} {rng.randrange(1000000000)}\n'
  engine.stdin.write(data);engine.stdin.flush();out=engine.stdout.readline().split();assert len(out)>=2,out;attempts+=1
  if int(out[1])>0:
   newwin=[tuple(row) for row in out[2:]];candidate=best[:a]+newwin+best[b:];st=sim.initial();finish=None
   for tick,row in enumerate(candidate):
    st=sim.step(st,row)
    if st[3]>=count:finish=tick+1;break
   if finish is not None:best=candidate[:finish]
 return best,attempts

p=argparse.ArgumentParser();p.add_argument('--budget',type=float,default=2);p.add_argument('--ms',type=int,default=100);p.add_argument('--pilot',action='store_true');p.add_argument('--seed',type=int,default=500);p.add_argument('--file',default='');args=p.parse_args()
start=time.perf_counter();entries=[];rng=random.Random(args.seed)
outdir=Path('relax_candidates');outdir.mkdir(exist_ok=True)
for source in sorted(ROOT.glob('in_*.txt')):
 if not any(x in source.name for x in ('medium','large','enormous')) or args.file and args.file not in source.name:continue
 cases=parse(source);progs=load_programs(source.with_name(source.name.replace('in_','answer_',1)))
 for i,(case,prog) in enumerate(zip(cases,progs)):
  if len(prog)>=10:entries.append((source,i,case,prog))
entries.sort(key=lambda e:len(e[3]),reverse=True)
if args.pilot:entries=[entries[round(i*(len(entries)-1)/9)] for i in range(10)]
engine=subprocess.Popen(['relaxed_window.exe'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1);wins=[]
try:
 for j,(source,i,case,prog) in enumerate(entries):
  candidate,attempts=optimize(engine,case,prog,args.budget,args.ms,rng)
  if len(candidate)<len(prog):
   assert verify(case[0],case[1],candidate)==case[2],(source.name,i+1)
   wins.append(dict(file=source.name,case=i+1,old=len(prog),new=len(candidate),attempts=attempts))
   dest=outdir/f'{source.stem}_case{i+1}.txt'
   if not dest.exists() or len(candidate)<len(load_programs(dest)[0]):save_programs(dest,[candidate])
  if args.pilot or len(candidate)<len(prog) or (j+1)%10==0:print(f'{j+1}/{len(entries)} {source.name} case={i+1} {len(prog)}->{len(candidate)} tries={attempts} elapsed={time.perf_counter()-start:.1f}s',flush=True)
finally:engine.stdin.close();engine.wait(timeout=10)
Path(f'relax_results_{args.seed}.json').write_text(json.dumps(wins,indent=2))
print('SAVED',sum(x['old']-x['new'] for x in wins),'CASES',len(wins),flush=True)
