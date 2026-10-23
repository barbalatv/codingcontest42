import argparse,json,time,subprocess
from pathlib import Path
from solve_l6 import parse
from solve_l4 import geometry
from solve_l5 import verify
from optimize_l6 import ROOT,load_programs,Machine,Done,save_programs
from phase2_cycle_cp import extract
from phase2_regress import cyclic_free
from phase2_run import atomic_save
p=argparse.ArgumentParser();p.add_argument('--ms',type=int,default=2500);p.add_argument('--pilot',action='store_true');p.add_argument('--seed',type=int,default=42);p.add_argument('--file',default='');p.add_argument('--engine',default='retime.exe');p.add_argument('--proposals',action='store_true');p.add_argument('--free-root',action='store_true');args=p.parse_args()
start=time.perf_counter();entries=[]
for source in sorted(ROOT.glob('in_*.txt')):
 if not any(x in source.name for x in ('medium','large','enormous')) or args.file and args.file not in source.name:continue
 cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));progs=load_programs(target)
 for i,(case,prog) in enumerate(zip(cases,progs)):
  ex=extract(case,prog)
  if ex and len(ex[2])>=3:entries.append((source,target,progs,i,case,ex))
entries.sort(key=lambda e:len(e[5][2])*e[4][2],reverse=True)
if args.pilot:entries=[entries[round(i*(len(entries)-1)/9)] for i in range(10)]
engine=subprocess.Popen([args.engine],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
wins=[]
try:
 for j,(source,target,progs,i,case,ex) in enumerate(entries):
  r,pat,count=case;pose,seed,cycle=ex;rows=list(map(list,geometry(r)[0]));n=len(cycle)
  for y,x in pat:rows[y][x]='M'
  packed=sum((v+128*((pose[1]>>k)&1))<<(8*k) for k,v in enumerate(pose[0]))
  data=f'{r} {count} {n}\n'+'\n'.join(map(''.join,rows))+f'\n{n}\n'+'\n'.join(' '.join(line) for line in cycle)+f'\n{packed}\n{args.ms} {args.seed+j}\n'
  engine.stdin.write(data);engine.stdin.flush();out=engine.stdout.readline().split();assert len(out)>=2,out
  candidate=None;newroot=int(out[2]) if args.free_root else packed;newcycle=[tuple(x) for x in out[3 if args.free_root else 2:]]
  if int(out[1])>0:
   candidate=cyclic_free(case,progs[i],newroot,newcycle)
   m=Machine(*case)
   if newroot!=packed:m.required=0
   try:
    if newroot!=packed:raise ValueError("Different cyclic pose")
    for row in seed:m.emit(row)
    for rep in range(count*2):
     for row in newcycle:m.emit(row)
   except ValueError:pass
   except Done:
    if candidate is None or len(m.program)<len(candidate):candidate=m.program
   if candidate and len(candidate)<len(progs[i]):
    assert verify(r,pat,candidate)==count
    wins.append(dict(file=source.name,case=i+1,old=len(progs[i]),new=len(candidate),cycle_old=n,cycle_new=len(newcycle)))
    progs[i]=candidate
    if args.proposals:
     dest=Path('fast_candidates')/f'{source.stem}_case{i+1}.txt';dest.parent.mkdir(exist_ok=True)
     if not dest.exists() or len(candidate)<len(load_programs(dest)[0]):save_programs(dest,[candidate])
    else:atomic_save(target,progs)
  if args.pilot or candidate or (j+1)%10==0:print(f'{j+1}/{len(entries)} {source.name} case={i+1} cycle={n}->{len(newcycle)} '+str(wins[-1] if candidate and wins else '')+f' elapsed={time.perf_counter()-start:.1f}s',flush=True)
finally:engine.stdin.close();engine.wait(timeout=10)
Path(f'retime_results_{args.seed}.json').write_text(json.dumps(wins,indent=2))
print('SAVED',sum(x['old']-x['new'] for x in wins),'CASES',len(wins),flush=True)
