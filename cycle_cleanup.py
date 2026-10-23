import argparse,json,time
from pathlib import Path
from optimize_l6 import ROOT,load_programs,save_programs
from solve_l6 import parse
from solve_l5 import verify
from optimize_l6_compact import Sim
from phase2_cycle_cp import extract
from phase2_regress import cyclic_free
p=argparse.ArgumentParser();p.add_argument('--pilot',action='store_true');p.add_argument('--phases',action='store_true');a=p.parse_args();start=time.perf_counter();entries=[];wins=[]
for source in sorted(ROOT.glob('in_*.txt')):
 if not any(x in source.name for x in ('medium','large','enormous')):continue
 for i,(case,prog) in enumerate(zip(parse(source),load_programs(source.with_name(source.name.replace('in_','answer_',1))))):
  ex=extract(case,prog)
  if ex:entries.append((source,i,case,prog,ex))
entries.sort(key=lambda e:len(e[3]),reverse=True)
if a.pilot:entries=[entries[round(i*(len(entries)-1)/9)] for i in range(10)]
for j,(source,i,case,prog,ex) in enumerate(entries):
 (poses,active),seed,cycle=ex;sim=Sim(case);best=prog;r=case[0];initial=sim.initial()[0];valid=0
 # Prefer dropping several beams; exact simulation decides which sets suffice.
 for keep in sorted(range(64),key=int.bit_count):
  newposes=tuple(poses[e] if keep>>e&1 else initial[e] for e in range(6));newactive=active&keep
  newcycle=[tuple(row[e] if keep>>e&1 else '-' for e in range(6)) for row in cycle]
  st=(newposes,newactive,0,0)
  for row in newcycle:st=sim.step(st,row)
  if st[3]!=1 or st[2]&(sim.target|sim.forbidden):continue
  valid+=1;positions=list(newposes);activation=newactive
  phases=range(len(newcycle)) if a.phases else range(1)
  for phase in phases:
   pose=sum((v+128*((activation>>e)&1))<<(8*e) for e,v in enumerate(positions));rot=newcycle[phase:]+newcycle[:phase]
   candidate=cyclic_free(case,best,pose,rot)
   if candidate and len(candidate)<len(best):best=candidate
   for e,ch in enumerate(newcycle[phase]):
    if ch=='F':positions[e]=(positions[e]-1)%(6*r)
    elif ch=='B':positions[e]=(positions[e]+1)%(6*r)
    elif ch=='T':activation^=1<<e
 if len(best)<len(prog):
  assert verify(r,case[1],best)==case[2]
  d=Path('cleanup_candidates')/f'{source.stem}_case{i+1}.txt';d.parent.mkdir(exist_ok=True)
  if not d.exists() or len(best)<len(load_programs(d)[0]):save_programs(d,[best])
  wins.append(dict(file=source.name,case=i+1,old=len(prog),new=len(best)))
 if a.pilot or len(best)<len(prog) or (j+1)%25==0:print(f'{j+1}/{len(entries)} {source.name} case={i+1} {len(prog)}->{len(best)} valid_subsets={valid} elapsed={time.perf_counter()-start:.1f}s',flush=True)
Path('cleanup_results.json').write_text(json.dumps(wins,indent=2));print('SAVED',sum(w['old']-w['new'] for w in wins),'CASES',len(wins))
