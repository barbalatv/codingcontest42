import argparse,json,time,subprocess
from pathlib import Path
from solve_l6 import parse
from solve_l4 import geometry
from solve_l5 import verify
from optimize_l6 import ROOT,load_programs,save_programs
p=argparse.ArgumentParser();p.add_argument('--ms',type=int,default=2500);p.add_argument('--pilot',action='store_true');p.add_argument('--seed',type=int,default=500);p.add_argument('--file',default='');p.add_argument('--count',type=int,default=0);p.add_argument('--mode',type=int,default=0);args=p.parse_args()
start=time.perf_counter();entries=[]
outdir=Path('causal_candidates');outdir.mkdir(exist_ok=True)
for source in sorted(ROOT.glob('in_*.txt')):
 if not any(x in source.name for x in ('medium','large','enormous')) or args.file and args.file not in source.name:continue
 cases=parse(source);progs=load_programs(source.with_name(source.name.replace('in_','answer_',1)))
 for i,(case,prog) in enumerate(zip(cases,progs)):
  if len(prog)>=8 and (not args.count or case[2]==args.count):entries.append((source,i,case,prog))
entries.sort(key=lambda e:len(e[3]),reverse=True)
if args.pilot:entries=[entries[round(i*(len(entries)-1)/9)] for i in range(10)]
engine=subprocess.Popen(['causal_compact.exe'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
wins=[]
try:
 for j,(source,i,case,prog) in enumerate(entries):
  r,pat,count=case;rows=list(map(list,geometry(r)[0]));n=len(prog)
  for y,x in pat:rows[y][x]='M'
  packed=sum(v<<(8*k) for k,v in enumerate((0,5*r,4*r,3*r,2*r,r)))
  data=f'{r} {count} {n}\n'+'\n'.join(map(''.join,rows))+f'\n{n}\n'+'\n'.join(' '.join(line) for line in prog)+f'\n{args.ms} {args.mode} {args.seed+j}\n'
  engine.stdin.write(data);engine.stdin.flush();out=engine.stdout.readline().split();assert len(out)>=2,out
  candidate=[tuple(x) for x in out[2:]]
  if len(candidate)<len(prog):
   assert len(candidate)==int(out[0]);assert verify(r,pat,candidate)==count,(source.name,i+1)
   wins.append(dict(file=source.name,case=i+1,old=n,new=len(candidate)))
   dest=outdir/f'{source.stem}_case{i+1}.txt'
   if not dest.exists() or len(candidate)<len(load_programs(dest)[0]):save_programs(dest,[candidate])
  if args.pilot or len(candidate)<n or (j+1)%10==0:print(f'{j+1}/{len(entries)} {source.name} case={i+1} {n}->{len(candidate)} elapsed={time.perf_counter()-start:.1f}s',flush=True)
finally:engine.stdin.close();engine.wait(timeout=10)
Path(f'causal_results_{args.seed}.json').write_text(json.dumps(wins,indent=2))
print('SAVED',sum(x['old']-x['new'] for x in wins),'CASES',len(wins),flush=True)
