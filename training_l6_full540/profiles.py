from common import *
from solve_l6 import origins
from collections import Counter,defaultdict
import statistics,math
def profile(ds,i,c,p):
    r,pat,K=c;sim=Sim(c);ss=sim.prefix(p);m,_=trace(c,p);aa=m['acceptances'];poses=[packed(ss[t]) for t in aa];oo=origins(r);cells=geometry(r)[1];idx={xy:j for j,xy in enumerate(cells)};tau=0
    for xy in pat:
        distances=[]
        for e in range(6):
            d=abs(ss[0][0][e]-oo[e][idx[xy]]);distances.append(min(d,6*r-d)+1)
        tau=max(tau,sorted(distances)[1])
    maxima=[max((sim.rays[q][a]&sim.target).bit_count() for q in range(6*r)) for a in range(3)];upper=min(len(pat),sum(maxima)+12);lb=max(tau+K-1,math.ceil(K*len(pat)/upper))
    active=[s[1].bit_count() for s in ss[1:]];counts=Counter(poses);boundary=sim.forbidden.bit_count()
    return dict(dataset=ds,case=i+1,radius=r,K=K,target_cells=len(pat),density=len(pat)/len(cells),score=len(p),first_copy=aa[0],later_intervals=[b-a for a,b in zip(aa,aa[1:])],average_copy=len(p)/K,unique_acceptance_poses=len(counts),cycle_pairs=sum(n*(n-1)//2 for n in counts.values()),toggles=m['toggles'],noops=sum(row.count('-') for row in p),productive_intersections=m['new_target'],repeated_intersections=m['repeated_target'],target_destructions=m['erased_target'],temporary_skirting=m['new_skirting'],repeat_fraction=m['repeat_fraction'],productive_per_tick=m['new_target']/len(p),active_mean=statistics.mean(active),active_max=max(active),skirting_cells=boundary,geometric_complexity=boundary/len(pat),lower_bound=lb,estimated_reserve=len(p)-lb,acceptances=aa)
def main():
    previous=json.loads((REPO/'training_l6_cellfirst/summary.json').read_text());prior={(x['dataset'],x['case']):x['saved'] for x in previous['changes']};pp=[]
    for ds in DATASETS:
        for i,(c,p) in enumerate(zip(cases(ds),programs(ds,'baseline'))):
            row=profile(ds,i,c,p);row['prior_improved']=int((ds,i+1) in prior);row['prior_saved']=prior.get((ds,i+1),0);pp.append(row)
    atomic_json(BASE/'experiments/case_profiles.json',pp)
    with (BASE/'case_profiles.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,list(pp[0]));w.writeheader();w.writerows({k:json.dumps(v) if isinstance(v,list) else v for k,v in x.items()} for x in pp)
    groups={}
    keys=['radius','K','target_cells','density','geometric_complexity','productive_per_tick','repeat_fraction','active_mean','score']
    for val in [0,1]:
        rows=[x for x in pp if x['prior_improved']==val];groups[str(val)]=dict(n=len(rows),means={key:statistics.mean(x[key] for x in rows) for key in keys})
    def ranks(values):
        order=sorted(range(len(values)),key=values.__getitem__);out=[0.]*len(values);j=0
        while j<len(order):
            k=j+1
            while k<len(order) and values[order[k]]==values[order[j]]:k+=1
            for t in range(j,k):out[order[t]]=(j+k-1)/2
            j=k
        return out
    y=ranks([x['prior_saved'] for x in pp]);my=statistics.mean(y);corr={}
    for key in keys:
        x=ranks([r[key] for r in pp]);mx=statistics.mean(x);num=sum((a-mx)*(b-my) for a,b in zip(x,y));den=math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y));corr[key]=num/den if den else None
    atomic_json(BASE/'experiments/prior_40_vs_500.json',dict(groups=groups,spearman_descriptive=corr,causality='NOT_ESTABLISHED'))
    print('PROFILES_PASS',len(pp),'prior groups',Counter(x['prior_improved'] for x in pp),flush=True)
if __name__=='__main__':main()
