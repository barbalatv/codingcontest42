import argparse,json,time,subprocess
from pathlib import Path
from solve_l6 import parse
from solve_l4 import geometry
from solve_l5 import verify
from optimize_l6 import ROOT,load_programs,save_programs,Machine,Done
from optimize_l6_compact import Sim
p=argparse.ArgumentParser();p.add_argument('--pilot',action='store_true');p.add_argument('--ms',type=int,default=2200);p.add_argument('--seed',type=int,default=3400);a=p.parse_args();entries=[];start=time.perf_counter()
for src in sorted(ROOT.glob('in_*.txt')):
 if not any(t in src.name for t in ('medium','large','enormous')):continue
 for i,(case,prog) in enumerate(zip(parse(src),load_programs(src.with_name(src.name.replace('in_','answer_',1))))):
  if case[2]<3:continue
  states=Sim(case).prefix(prog);snaps=[(t,states[t]) for t in range(1,len(states)) if states[t][3]>states[t-1][3]];opts=[]
  for (t,s),(u,_) in zip(snaps,snaps[1:]):
   remain=case[2]-s[3]
   if remain>=2 and u-t>=3:opts.append(((u-t-1)*remain,t,u,s))
  if opts:
   _,t,u,s=max(opts);entries.append((src,i,case,prog,t,u,s))
entries.sort(key=lambda e:(e[5]-e[4]-1)*(e[2][2]-e[6][3]),reverse=True)
if a.pilot:entries=[entries[round(j*(len(entries)-1)/9)] for j in range(10)]
engine=subprocess.Popen(['bidir_repair.exe'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1);wins=[];outdir=Path('bounce_candidates');outdir.mkdir(exist_ok=True)
try:
 for j,(src,i,case,prog,t,u,state) in enumerate(entries):
  r,pat,count=case;rows=list(map(list,geometry(r)[0]));path=prog[t:u];n=len(path)
  for y,x in pat:rows[y][x]='M'
  packed=sum((v+128*((state[1]>>e)&1))<<(8*e) for e,v in enumerate(state[0]))
  data=f'{r} 1 {n}\n'+'\n'.join(map(''.join,rows))+f'\n{n}\n'+'\n'.join(' '.join(row) for row in path)+f'\n{packed}\n{a.ms} {a.seed+j}\n'
  engine.stdin.write(data);engine.stdin.flush();out=engine.stdout.readline().split();assert len(out)>=2,out;new=[tuple(x) for x in out[2:]];candidate=None
  if len(new)<n:
   inv={'F':'B','B':'F','T':'T','-':'-'};reverse=[tuple(inv[c] for c in row) for row in reversed(new[1:])];m=Machine(*case)
   try:
    for row in prog[:t]+new:m.emit(row)
    for rep in range(count*2):
     m.emit(['-']*6)
     for row in reverse if rep%2==0 else new[1:]:
      m.emit(row)
      if len(m.program)>=len(prog):raise ValueError('Bound')
   except ValueError:pass
   except Done:candidate=m.program
   if candidate and len(candidate)<len(prog):
    assert verify(r,pat,candidate)==count,(src.name,i+1)
    dest=outdir/f'{src.stem}_case{i+1}.txt'
    if not dest.exists() or len(candidate)<len(load_programs(dest)[0]):save_programs(dest,[candidate])
    wins.append(dict(file=src.name,case=i+1,before=len(prog),after=len(candidate),pass_before=n,pass_after=len(new)))
  if a.pilot or candidate or (j+1)%10==0:print(f'{j+1}/{len(entries)} {src.name} case={i+1} pass {n}->{len(new)} total {len(prog)}->{len(candidate) if candidate else len(prog)} elapsed={time.perf_counter()-start:.1f}s',flush=True)
finally:engine.stdin.close();engine.wait(timeout=10)
Path(f'bounce_results_{a.seed}.json').write_text(json.dumps(wins,indent=2));print('SAVED',sum(x['before']-x['after'] for x in wins),'CASES',len(wins),flush=True)
