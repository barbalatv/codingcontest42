"""Close the newly productive graph neighborhoods before final validation."""
from common import *

def main():
    rows=list(csv.DictReader((BASE/'improvements.csv').open()))
    selected=sorted({(r['dataset'],int(r['case'])) for r in rows if r['algorithm'] in ['B_independent_graph','C_extended_graph'] or r['algorithm'].endswith('_continuation4')})
    summary_file=BASE/'experiments/graph_refinement_summary.json'
    previous=json.loads(summary_file.read_text()) if summary_file.exists() else None
    passes=previous.get('passes',[previous]) if previous else []
    initial=previous['before'] if previous else {ds:sum(map(len,programs(ds))) for ds in DATASETS}
    atomic_json(BASE/'experiments/graph_refinement_selection.json',dict(cases=selected,bounce_rounds_per_pass=2,max_passes=6,cap=50,before=initial,reason='only neighborhoods producing a new best in the continuation; stop on a complete pass without score gain'))
    while len(passes)<6 and (not passes or passes[-1]['saved']):
        before={ds:sum(map(len,programs(ds))) for ds in DATASETS};begin=time.perf_counter()
        for ds in DATASETS:
            ids=[str(i) for d,i in selected if d==ds]
            if ids:subprocess.run([sys.executable,str(BASE/'consolidate.py'),'--pure-library','--bounce','2','--datasets',ds,'--indices',','.join(ids)],check=True)
        after={ds:sum(map(len,programs(ds))) for ds in DATASETS}
        passes.append(dict(cases=len(selected),before=before,after=after,saved=sum(before.values())-sum(after.values()),wall_seconds=time.perf_counter()-begin))
        atomic_json(summary_file,dict(cases=len(selected),before=initial,after=after,saved=sum(initial.values())-sum(after.values()),passes=passes,stop_reason='NO_SCORE_GAIN' if passes[-1]['saved']==0 else 'PASS_LIMIT' if len(passes)==6 else 'IN_PROGRESS',wall_seconds=sum(r['wall_seconds'] for r in passes)))
        print('REFINEMENT_PASS',len(passes),'saved',passes[-1]['saved'],'total',sum(after.values()),flush=True)

if __name__=='__main__':main()
