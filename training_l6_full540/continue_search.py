"""Fresh matched A/B/C experiment on adaptively selected unresolved cases."""
import screen as sc
from screen import *

SNAPSHOT='experiments/continuation4_baseline'
PASS='continuation4'

def init():
    from windows_limits import limit_current_process
    sc.MEMORY_POLICY=limit_current_process(1024)
    sc.ENGINE=Engine('cellfirst_v2.exe');atexit.register(sc.ENGINE.close)
    sc.FROZEN={ds:programs(ds,SNAPSHOT) for ds in DATASETS}

def select():
    selection=BASE/'experiments/continuation4_selection.json'
    if selection.exists():return json.loads(selection.read_text())
    snapshot=BASE/SNAPSHOT;snapshot.mkdir(exist_ok=True)
    for ds in DATASETS:save_programs(snapshot/name(ds),programs(ds))
    bounds={(r['dataset'],r['case']):r for r in json.loads((BASE/'experiments/lower_bounds.json').read_text())}
    old={(r['dataset'],r['case']) for r in json.loads((BASE/'experiments/adaptive_selection.json').read_text())}
    ranking=[]
    for ds in DATASETS:
        for i,c in enumerate(cases(ds)):
            T=len(programs(ds,SNAPSHOT)[i]);lb=bounds[ds,i+1]['lower_bound']
            if T<=lb:continue
            costs=[];close=0
            for dirname in ['pass1','pass2','pure_cycles']:
                f=BASE/'experiments'/dirname/f'{ds}_{i+1}.json'
                if not f.exists():continue
                for row in json.loads(f.read_text()).get('rows',[]):
                    for near in row.get('near_candidates',[]):
                        full_h=len(near.get('prefix',[]))+len(near['program'])+len(near.get('suffix',[]))
                        if full_h<T and near['cost']>0:costs.append(near['cost'])
                    if row.get('candidate') and row['candidate']<=T:close+=1
            cost=min(costs,default=1000)
            priority=20/(1+cost)+min(2,(T-lb)/T)+min(2,60/len(c[1]))+min(2,close*.5)
            ranking.append(dict(dataset=ds,case=i+1,priority=priority,near_cost=cost,baseline=T,lower_bound=lb,radius=c[0],K=c[2],target_cells=len(c[1]),previous_deep=(ds,i+1) in old))
    ranking.sort(key=lambda r:(-r['priority'],r['target_cells'],r['dataset'],r['case']))
    # Most effort explores cases absent from the previous deep pass; the rest
    # tests whether a fresh seed helps the strongest remaining candidates.
    chosen=[r for r in ranking if not r['previous_deep']][:36]
    chosen += [r for r in ranking if r['previous_deep']][:12]
    chosen += [r for r in ranking if r not in chosen][:max(0,48-len(chosen))]
    atomic_json(selection,chosen);atomic_json(BASE/'experiments/continuation4_ranking.json',ranking)
    return chosen

def main():
    chosen=select();folder=BASE/'experiments'/PASS;folder.mkdir(exist_ok=True)
    atomic_json(folder/'run_config.json',dict(cases=chosen,ms=3000,seed=12300000,workers=4,engine='cellfirst_v2.exe',snapshot=SNAPSHOT,pure_exact=False))
    todo=[r for r in chosen if not (folder/f"{r['dataset']}_{r['case']}.json").exists()]
    begin=time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,initializer=init) as pool:
        futures={pool.submit(run_case,r['dataset'],r['case']-1,3000,12300000,PASS,False):r for r in todo}
        for fut in concurrent.futures.as_completed(futures):
            record=fut.result();ds=record['dataset'];idx=record['case'];atomic_json(folder/f'{ds}_{idx}.json',record)
            for row in record['rows']:
                if row['program']:update(ds,idx-1,[tuple(z) for z in row['program']],f"{row['strategy']}_{PASS}",row['runtime'],row['evaluations'],row['seed'])
            print('CONTINUE',ds,idx,[(r['strategy'],r['saved']) for r in record['rows']],'elapsed',round(time.perf_counter()-begin,1),flush=True)
    records=[json.loads(f.read_text()) for f in folder.glob('*.json') if f.name!='run_config.json']
    atomic_json(BASE/'experiments/continuation4_summary.json',dict(cases=len(records),scores={ds:sum(map(len,programs(ds))) for ds in DATASETS},wall_seconds=time.perf_counter()-begin,arms={s:dict(cases=sum(r['strategy']==s for x in records for r in x['rows']),saved_vs_stage_snapshot=sum(r['saved'] for x in records for r in x['rows'] if r['strategy']==s)) for s in 'ABC'}))

if __name__=='__main__':main()
