import argparse,subprocess,time,json
from pathlib import Path
from solve_l6 import parse
from solve_l5 import verify
from optimize_l6 import ROOT,load_programs,save_programs
p=argparse.ArgumentParser();p.add_argument('--pilot',action='store_true');p.add_argument('--min-count',type=int,default=0);p.add_argument('--engine',default='symsplice');p.add_argument('--timeout',type=float,default=4);p.add_argument('--budget',type=float,default=240);p.add_argument('--extra',nargs='*',default=[]);a=p.parse_args()
entries=[];start=time.perf_counter();outdir=Path(a.engine+'_candidates');outdir.mkdir(exist_ok=True);jobs=Path('archive_jobs');jobs.mkdir(exist_ok=True)
for src in sorted(ROOT.glob('in_*.txt')):
 if not any(t in src.name for t in ('medium','large','enormous')):continue
 for i,(case,prog) in enumerate(zip(parse(src),load_programs(src.with_name(src.name.replace('in_','answer_',1))))):
  if len(prog)>=8 and case[2]>=a.min_count:entries.append((src,i,case,prog))
entries.sort(key=lambda e:len(e[3]),reverse=True)
if a.pilot:entries=[entries[round(j*(len(entries)-1)/9)] for j in range(10)]
results=[]
for j,(src,i,case,prog) in enumerate(entries):
 if time.perf_counter()-start>a.budget:break
 r,pat,need=case;source=jobs/f'{a.engine}_input.txt';dest=jobs/f'{a.engine}_output.txt'
 data=['1',f'{r} {need} {len(pat)} {len(prog)}']+[f'{y} {x}' for y,x in sorted(pat)]+[' '.join(str('-FBT'.index(c)) for c in row) for row in prog]
 source.write_text('\n'.join(data)+'\n')
 try:
  cp=subprocess.run([str(Path('archive_engines',a.engine+'.exe').resolve()),str(source.resolve()),str(dest.resolve())]+a.extra,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=a.timeout)
  assert cp.returncode==0,(cp.returncode,cp.stderr)
  tokens=list(map(int,dest.read_text().split()));assert tokens[0]==1 and len(tokens)==2+6*tokens[1],tokens[:5]
  candidate=[tuple('-FBT'[v] for v in tokens[2+6*k:8+6*k]) for k in range(tokens[1])];status='DONE'
  if len(candidate)<len(prog):
   assert verify(r,pat,candidate)==need,(src.name,i+1)
   path=outdir/f'{src.stem}_case{i+1}.txt'
   if not path.exists() or len(candidate)<len(load_programs(path)[0]):save_programs(path,[candidate])
   results.append(dict(file=src.name,case=i+1,before=len(prog),after=len(candidate)))
 except subprocess.TimeoutExpired:status='TIMEOUT';candidate=prog
 if a.pilot or len(candidate)<len(prog) or (j+1)%20==0:print(f'{j+1}/{len(entries)} {src.name} case={i+1} {len(prog)}->{len(candidate)} {status} elapsed={time.perf_counter()-start:.1f}s',flush=True)
Path(a.engine+'_results.json').write_text(json.dumps(results,indent=2));print('SAVED',sum(x['before']-x['after'] for x in results),'CASES',len(results),flush=True)
