from common import *
from solve_l6 import origins
from collections import Counter,defaultdict
import statistics,math
def material_signature(c,p):
    sim=Sim(c);s=sim.initial();rel=sim.target|sim.forbidden;previous=(0,0);trace=[]
    for row in p:
        s=sim.step(s,row);v=(s[2]&rel,s[3])
        if v!=previous:trace.append([str(v[0]),v[1]-previous[1]]);previous=v
    return hashlib.sha256(json.dumps(trace,separators=(',',':')).encode()).hexdigest()
def main():
    profiles={(r['dataset'],r['case']):r for r in json.loads((BASE/'experiments/case_profiles.json').read_text())};proofs=[];birth_novel=0;pure_winners=[];allrows=[]
    prefix={(r['dataset'],r['case']):r['proven_first_acceptance_bound'] for r in json.loads((BASE/'experiments/prefix_bounds.json').read_text()) if r['status']=='INFEASIBLE'}
    for folder in (BASE/'experiments').iterdir():
        if folder.is_dir():
            for f in folder.glob('*.json'):
                x=json.loads(f.read_text())
                for r in x.get('rows',[]):allrows.append(r)
    for ds in DATASETS:
        oo={};cc=cases(ds);baseline=programs(ds,'baseline');final=programs(ds)
        for i,c in enumerate(cc):
            r,pat,K=c;sim=Sim(c);initial=sim.initial();cells=geometry(r)[1];idx={xy:j for j,xy in enumerate(cells)};O=origins(r);tau=0
            for xy in pat:
                dd=[]
                for e in range(6):
                    d=abs(initial[0][e]-O[e][idx[xy]]);dd.append(min(d,6*r-d)+1)
                tau=max(tau,sorted(dd)[1])
            static=json.loads((BASE/'experiments/static_all'/f'{ds}_{i+1}.json').read_text());one_tick_excluded=static['no_one_tick_copy'];interval=2 if one_tick_excluded else 1;first=max(tau,interval,prefix.get((ds,i+1),0));lb=max(profiles[ds,i+1]['lower_bound'],first+interval*(K-1));assert lb<=len(final[i]),(ds,i+1,lb,len(final[i]))
            proofs.append(dict(dataset=ds,case=i+1,first_acceptance_reach_bound=tau,strengthened_first_acceptance_bound=first,minimum_interval_bound=interval,static_status=static['status'],lower_bound=lb,best=len(final[i]),optimality_certified=lb==len(final[i]),proof_scope='complete snapshot model + geometric reach bound + recorded unrestricted short-prefix infeasibility; no production/server acceptance claim'))
            sig=material_signature(c,baseline[i]);p1=json.loads((BASE/'experiments/pass1'/f'{ds}_{i+1}.json').read_text());birth=next(z for z in p1['rows'] if z['strategy']=='B')['birth_program'];birth_novel+=material_signature(c,[tuple(z) for z in birth])!=sig
            rr=[z for z in allrows if z['dataset']==ds and z['case']==i+1 and z['strategy']=='B' and z.get('program')]
            independent_graph=BASE/'cellfirst/pure_graph'/f'{ds}_{i+1}.json'
            if independent_graph.exists():
                gp=json.loads(independent_graph.read_text()).get('program')
                if gp:rr.append(dict(program=gp,pass_name='independent_graph'))
            if rr:
                best=min(rr,key=lambda z:len(z['program']))
                if len(best['program'])<len(baseline[i]):
                    p=[tuple(z) for z in best['program']];exact(c,p);ma,_=trace(c,baseline[i]);mb,_=trace(c,p);pure_winners.append(dict(dataset=ds,case=i+1,baseline=len(baseline[i]),pure=len(p),final=len(final[i]),source=best['pass_name'],radius=r,target_cells=len(pat),K=K,structural_material_trace_changed=material_signature(c,p)!=sig,acceptances_before=ma['acceptances'],acceptances_after=mb['acceptances'],signature_sha256=material_signature(c,p),incumbent_structure_used=False))
    paired=defaultdict(lambda:dict(cases=0,saved=0,improved=0,cpu_seconds=0,wall_seconds=0,valid_candidates=0,invalid_candidates=0,near_rows=0,near_cost_le_12=0,births_valid=0))
    categories=Counter();variance=[];timed=Counter()
    for ds in DATASETS:
        for i in range(len(cases(ds))):
            x=json.loads((BASE/'experiments/pass1'/f'{ds}_{i+1}.json').read_text());arms={r['strategy']:r for r in x['rows']};a,b,c=(arms[s]['saved'] for s in ['A','B','C'])
            if b>a:categories['B_better_than_A']+=1
            if c>max(a,b):categories['C_better_than_both']+=1
            if a>0 and b==c==0:categories['only_A']+=1
            if a==b==c==0:categories['none']+=1
            if b==c and b>a:categories['B_C_tie_above_A']+=1
            for r in x['rows']:
                g=paired[r['strategy']];g['cases']+=1;g['saved']+=r['saved'];g['improved']+=r['saved']>0;g['cpu_seconds']+=r['search_cpu_seconds'];g['wall_seconds']+=r['runtime'];g['valid_candidates']+=r['valid_candidates'];g['invalid_candidates']+=r['invalid_candidates'];g['near_rows']+=bool(r['near_candidates']);g['near_cost_le_12']+=any(0<n['cost']<=12 for n in r['near_candidates']);g['births_valid']+=r['birth_valid']==True
                for q in r['queries']:
                    if q.get('deadline_hit'):timed[r['strategy']]+=1
                if r['strategy']=='B':assert not any(r[k] for k in ['incumbent_structure_used','incumbent_trajectory_used','state_hints_used','incumbent_transitions_used'])
    for r in allrows:
        if r['pass_name'] in ['replicate_2','replicate_3'] or (r['pass_name']=='pass1' and any(z['pass_name'] in ['replicate_2','replicate_3'] and (z['dataset'],z['case'])==(r['dataset'],r['case']) for z in allrows)):
            variance.append({k:r.get(k) for k in ['dataset','case','pass_name','strategy','seed','incumbent','candidate','saved','search_cpu_seconds']})
    atomic_json(BASE/'experiments/lower_bounds.json',proofs);atomic_json(BASE/'experiments/pure_lineage.json',dict(independent_winners=pure_winners,material_trace_definition='remove steps without relevant matter or acceptance changes; hash the remaining matter/acceptance trace',novel_birth_material_traces=birth_novel,total_births=540));atomic_json(BASE/'experiments/comparison.json',dict(primary=dict(paired),categories=dict(categories),deadline_hit_queries=dict(timed),replicate_rows=variance,all_strategy_rows=len(allrows)))
    print('RESEARCH_ANALYSIS_PASS','certified',sum(x['optimality_certified'] for x in proofs),'pure-winning cases',len(pure_winners),flush=True)
if __name__=='__main__':main()
