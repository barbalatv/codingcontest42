from common import *
from collections import Counter
def main():
    folder=BASE/'experiments/pass1';allrows=[]
    profiles={(x['dataset'],x['case']):x for x in json.loads((BASE/'experiments/case_profiles.json').read_text())}
    for ds in DATASETS:
        for idx in range(1,len(cases(ds))+1):
            f=folder/f'{ds}_{idx}.json';x=json.loads(f.read_text());assert {r['strategy'] for r in x['rows']}=={'A','B','C'}
            for r in x['rows']:
                r['state_hints_used']=r['strategy']=='A' and any(q['kind']=='cross_acceptance' for q in r['queries'])
                if r['strategy']=='B':assert not r['incumbent_structure_used'] and not r['incumbent_trajectory_used'] and not r['state_hints_used']
            atomic_json(f,x);p=profiles[ds,idx];cpu=sum(r['search_cpu_seconds'] for r in x['rows']);gain=max(r['saved'] for r in x['rows']);near=min((z['cost'] for r in x['rows'] for z in r['near_candidates']),default=10**6);novel=max(len(r['pure_discoveries']) for r in x['rows']);eligible=p['score']<=12 and p['target_cells']<=45 and p['K']<=4
            score=gain*20+(8 if near<=4 else 3 if near<=12 else 0)+min(4,novel/4)+p['estimated_reserve']/max(1,p['score'])+(3 if eligible else 0)
            allrows.append(dict(dataset=ds,case=idx,priority=score,max_saved=gain,near_cost=near,pure_poses=novel,cpu=cpu,cp_eligible=eligible,radius=p['radius'],K=p['K']))
    assert len(allrows)==540
    allrows.sort(key=lambda r:r['priority'],reverse=True);selected=[]
    for ds in DATASETS:selected += [x for x in allrows if x['dataset']==ds][:2]
    for x in allrows:
        if x not in selected:selected.append(x)
        if len(selected)>=24:break
    atomic_json(BASE/'experiments/adaptive_ranking.json',allrows);atomic_json(BASE/'experiments/adaptive_selection.json',selected)
    folder=BASE/'experiments/pass2_baseline';folder.mkdir(exist_ok=True)
    for ds in DATASETS:save_programs(folder/name(ds),programs(ds))
    print('PASS1_COMPLETE_ABC_540',Counter(r['dataset'] for r in selected),flush=True)
if __name__=='__main__':main()
