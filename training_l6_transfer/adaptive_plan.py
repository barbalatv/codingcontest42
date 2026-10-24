from common import *
import math,collections

def main():
    if (BASE/'experiments/deep_selection.json').exists():
        print('ADAPTIVE_PLAN_ALREADY_FROZEN: snapshot will not be reset',flush=True);return
    profiles={(r['dataset'],r['case']):r for r in json.loads((BASE/'similarity_index/profiles.json').read_text())}
    bounds={(r['dataset'],r['case']):r for r in json.loads((REPO/'training_l6_full540/experiments/lower_bounds.json').read_text())}
    ranked=[];observations=collections.defaultdict(lambda:[dict(saved=0.,cpu=0.,n=0) for _ in range(5)])
    records=[json.loads(f.read_text()) for f in (BASE/'experiments/screen').glob('*.json') if '_' in f.stem and f.stem.split('_')[0] in DATASETS]
    assert len(records)==540
    for x in records:
        ds=x['dataset'];idx=x['case'];p=profiles[ds,idx];T=len(programs(ds)[idx-1]);lb=bounds[ds,idx]['lower_bound'];assert T>=lb
        max_saved=max(r['saved'] for r in x['rows']);edges=sum(q['operators'][0]['verified_edges']+q['operators'][1]['verified_edges']+q['operators'][2]['verified_edges'] for r in x['rows'] for q in r['queries']);bestmask=0
        for r in x['rows']:
            for q in r['queries']:
                bestmask|=q['winning_operator_mask'] if r['saved'] else 0
                for op in q['operators']:
                    for group in ['global',r['context']]:
                        v=observations[group][op['operator']];v['saved']+=op['native_saved'];v['cpu']+=op['wall_seconds'];v['n']+=1
        priority=max_saved*15+math.log1p(edges)+3*int(bestmask.bit_count()>1)+min(2,(T-lb)/max(1,T))
        if T>lb:ranked.append(dict(dataset=ds,case=idx,priority=priority,screen_saved=max_saved,new_edges=edges,split=p['split'],radius=p['radius'],K=p['K'],current=T,lower_bound=lb,mixture=bestmask.bit_count()>1))
    ranked.sort(key=lambda x:-x['priority']);chosen=ranked[:24]
    remaining=[r for r in ranked if r not in chosen and r['screen_saved']==0]
    # Exploration is stratified by radius rather than a fixed dataset quota.
    remaining.sort(key=lambda r:hashlib.sha256(f"explore{r['dataset']}{r['case']}".encode()).hexdigest())
    chosen+=remaining[:12]
    snapshot=BASE/'experiments/deep_baseline';snapshot.mkdir(exist_ok=True)
    for ds in DATASETS:save_programs(snapshot/name(ds),programs(ds))
    atomic_json(BASE/'experiments/deep_ranking.json',ranked);atomic_json(BASE/'experiments/deep_selection.json',[(r['dataset'],r['case']) for r in chosen])
    catalog=json.loads((BASE/'operators/catalog_primary_frozen.json').read_text());seen={(tuple(r['before']),tuple(r['after'])) for r in catalog['rewrites']};newrules=[];feedback=[]
    for f in (BASE/'checkpoints').glob('feedback_*.json'):
        x=json.loads(f.read_text());feedback.append(x)
        for v in x['observed_variants']:catalog['observed_variant_counts'][str(v)]=catalog['observed_variant_counts'].get(str(v),0)+1
        for r in x['new_rules']:
            token=tuple(r['before']),tuple(r['after'])
            if token not in seen:seen.add(token);r['rule_id']=len(newrules);newrules.append(r)
    catalog['rewrites']=(newrules+catalog['rewrites'])[:64];catalog['feedback_source']='post-primary optimization only; no claim of held-out policy evaluation'
    atomic_json(BASE/'operators/catalog_feedback.json',catalog)
    values={g:[(r['saved']+.1)/(r['cpu']+1) for r in rr] for g,rr in observations.items()}
    atomic_json(BASE/'operators/policy_feedback.json',dict(global_=values['global'],**{'global':values['global']},contexts={g:w for g,w in values.items() if g!='global'},observations=dict(observations),training='primary data; optimization feedback only; adaptive performance is NOT independent held-out policy evaluation'))
    atomic_json(BASE/'experiments/feedback_plan.json',dict(confirmed_improvements=len(feedback),new_short_rules=len(newrules),initial_rules=24,feedback_rules=len(catalog['rewrites']),deep_cases=len(chosen),primary_heldout_frozen=True))
    print('ADAPTIVE_PLANNED',len(chosen),'cases; feedback rules',len(newrules),flush=True)

if __name__=='__main__':main()
