from pathlib import Path
import sys,json,csv,shutil,hashlib,subprocess,zipfile
BASE=Path(__file__).resolve().parent;REPO=BASE.parent;sys.path.insert(0,str(REPO))
from solve_l6 import parse
from solve_l5 import verify
from optimize_l6 import load_programs,save_programs

def main():
 final=BASE/'final';level=final/'level-6';level.mkdir(parents=True,exist_ok=True)
 summary=[];rows=[]
 for source in sorted((REPO/'level-6').glob('in_*.txt')):
  name=source.name.replace('in_','answer_',1);candidate=BASE/'candidates'/name;answer=candidate if candidate.exists() else source.with_name(name)
  reference=BASE/'reference_latest'/name
  baseline=load_programs(reference if reference.exists() else source.with_name(name));programs=load_programs(answer);cases=parse(source)
  programs=[b if len(b)<len(a) else a for a,b in zip(programs,baseline)]
  for alternative in sorted(BASE.glob('candidates*/'+name)):
   other=load_programs(alternative);assert len(other)==len(programs)
   programs=[b if len(b)<len(a) else a for a,b in zip(programs,other)]
  assert len(programs)==len(cases)==len(baseline)
  for i,(case,old,new) in enumerate(zip(cases,baseline,programs),1):
   assert len(new)<=len(old),(source.name,i)
   assert verify(case[0],case[1],new)==case[2],(source.name,i)
   rows.append(dict(dataset=source.stem.replace('in_level-6_',''),case=i,radius=case[0],target_cells=len(case[1]),copies=case[2],baseline=len(old),candidate=len(new),gain=len(old)-len(new),independent_pass=True))
  shutil.copyfile(source,level/source.name);save_programs(level/name,programs)
  rec=dict(dataset=source.stem.replace('in_level-6_',''),baseline=sum(map(len,baseline)),candidate=sum(map(len,programs)),gain=sum(map(len,baseline))-sum(map(len,programs)),improved_cases=sum(len(b)<len(a) for a,b in zip(baseline,programs)))
  summary.append(rec)
 shutil.copyfile(REPO/'level-6/sandbox-level-6.html',level/'sandbox-level-6.html');shutil.copyfile(REPO/'validate_l6_sandbox.cjs',final/'validate_l6_sandbox.cjs')
 result=subprocess.run(['node','validate_l6_sandbox.cjs'],cwd=final,text=True,capture_output=True,check=True);(BASE/'sandbox_validation.txt').write_text(result.stdout,encoding='utf-8');print(result.stdout)
 main=[x for x in summary if any(s in x['dataset'] for s in ('medium','large','enormous'))]
 logs=[]
 for log in BASE.glob('benchmark*.jsonl'):
  for line in log.read_text().splitlines():
   try:logs.append(json.loads(line))
   except json.JSONDecodeError:pass
 base_file=BASE/'EXPERIMENT_BASE.txt'
 initial_commit=base_file.read_text().strip() if base_file.exists() else subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
 ref=BASE/'reference_latest/COMMIT.txt'
 report=dict(baseline_commit=ref.read_text().strip() if ref.exists() else initial_commit,initial_experiment_commit=initial_commit,datasets=summary,total_baseline=sum(x['baseline'] for x in main),total_candidate=sum(x['candidate'] for x in main),gain=sum(x['gain'] for x in main),improved_cases=sum(x['improved_cases'] for x in main),benchmark_runs=len(logs),evaluations=sum(x['evaluations'] for x in logs),peak_engine_bytes=max(x['peak_bytes'] for x in logs),measured_search_wall_s=sum(x['wall_s'] for x in logs),graph_additional_gain_over_run_regression_routes=sum(x.get('graph_additional_gain',0) for x in logs),independent_validation='PASS',original_sandbox='PASS',official_submission=False)
 (BASE/'SUMMARY.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 with (BASE/'case_results.csv').open('w',newline='',encoding='utf-8') as f:
  wr=csv.DictWriter(f,list(rows[0]));wr.writeheader();wr.writerows(rows)
 with (BASE/'benchmark_flat.csv').open('w',newline='',encoding='utf-8') as f:
  flat=[{k:v for k,v in r.items() if k!='queries'} for r in logs];fields=sorted(set().union(*(r.keys() for r in flat)));wr=csv.DictWriter(f,fields);wr.writeheader();wr.writerows(flat)
 print(json.dumps(report,indent=2))

if __name__=='__main__':main()
