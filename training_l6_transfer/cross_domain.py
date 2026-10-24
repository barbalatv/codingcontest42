from experiment import *
import experiment as ex

def task(ds,i):
    c=cases(ds)[i];inc=ex.FROZEN[ds][i];support=json.loads((BASE/'experiments/counterfactual_operator_fit.json').read_text())['executable_variant_support'];profiles=ex.PROFILES
    variants=[];donors=[]
    for v,ids in support.items():
        allowed=[tuple(d) for d in ids if d[0]!=ds and profiles[tuple(d)]['radius']!=c[0]]
        if allowed:variants.append(int(v));donors+=allowed
    mask=sum(1<<v for v in variants);assert mask
    results=[]
    for rep in range(3):
        seed=44210000+i*137+rep*700000+list(DATASETS).index(ds)*100000
        p,_,info=ex.ENGINE.ask(c,k=c[2],horizon=len(inc)-1,hint=inc,mode=14,ms=600,seed=seed,operator_mask=1,variant_mask=mask,rules=[],motifs=[],weights=[1]*5)
        if p:exact(c,p);js_check(ds,i,p)
        results.append(dict(seed=seed,program=p,candidate=len(p) if p else None,saved=len(inc)-len(p) if p else 0,cpu_seconds=info['cpu_seconds'],runtime=info['runtime'],evaluations=info['evaluations'],operators=info['operators']))
    return dict(dataset=ds,case=i+1,radius=c[0],baseline=len(inc),split=profiles[ds,i+1]['split'],variants=variants,donors=[dict(dataset=d[0],case=d[1],radius=profiles[d]['radius']) for d in sorted(set(donors))],source_restriction='all fitting donor exemplars are from a different dataset AND radius; only learned reversal variants enabled; no learned short rules or pure motifs',results=results)

def main():
    selection=[]
    for f in (BASE/'experiments/screen').glob('*.json'):
        x=json.loads(f.read_text())
        if not x.get('rows'):continue
        rows=[r for r in x['rows'] if r['arm']!='A' and r['saved'] and r['queries'][-1]['winning_operator_mask']==1 and r['split']=='heldout_family']
        if rows:selection.append((x['dataset'],x['case']))
    folder=BASE/'experiments/cross_domain';folder.mkdir(exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,initializer=init,initargs=('baseline','operators/policy.json','operators/catalog_primary_frozen.json')) as pool:
        for record in pool.map(task_wrapper,selection):
            ds=record['dataset'];idx=record['case'];atomic_json(folder/f'{ds}_{idx}.json',record)
            for r in record['results']:
                if r['program']:
                    before=programs(ds)[idx-1]
                    if update(ds,idx-1,[tuple(z) for z in r['program']],'Historical_cross_domain',r['runtime'],r['evaluations'],r['seed']):feedback(ds,idx-1,before,[tuple(z) for z in r['program']],'Historical_cross_domain',r['seed'])
            print('CROSS_DOMAIN',ds,idx,[r['saved'] for r in record['results']],flush=True)
    records=[json.loads(f.read_text()) for f in folder.glob('*.json')]
    atomic_json(BASE/'experiments/cross_domain_summary.json',dict(cases=len(records),queries=3*len(records),cases_reproduced=sum(any(r['saved']>0 for r in x['results']) for x in records),all_three_seeds_success=sum(all(r['saved']>0 for r in x['results']) for x in records),cpu_seconds=sum(r['cpu_seconds'] for x in records for r in x['results']),records=records,selection_bias='selected primary transfer winners, not a random estimate of universal success probability'))

def task_wrapper(pair):return task(pair[0],pair[1]-1)
if __name__=='__main__':main()
