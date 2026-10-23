import sys, json, csv, math
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).parent; REMOTE=ROOT.resolve().parents[1]
sys.path.insert(0,str(REMOTE))
from solve_l6 import parse, origins, delta
from solve_l4 import geometry, STEPS
from optimize_l6 import load_programs
from optimize_l6_compact import Sim

def transform(p,r,k,reflect=False):
    y,x=p; a=y-r; b=(x-2*r-a)//2
    if reflect:a,b=b,a
    for _ in range(k):a,b=-b,a+b
    return (a+r,2*b+a+2*r)

def variants(pattern,r):
    return [frozenset(transform(p,r,k,f) for p in pattern) for f in (False,True) for k in range(6)]

def main():
    records=[]; bundles={};canon=defaultdict(list)
    for kind in ('2-medium','3-large','4-enormous'):
        cases=parse(REMOTE/f'level-6/in_level-6_{kind}.txt')
        programs=load_programs(REMOTE/f'level-6/answer_level-6_{kind}.txt')
        bundles[kind]=[]
        for j,(case,program) in enumerate(zip(cases,programs),1):
            r,P,K=case;sim=Sim(case);states=sim.prefix(program);o=origins(r)
            _,cells,rays=geometry(r);ix={p:i for i,p in enumerate(cells)}
            groups=[Counter(o[d][ix[p]] for p in P) for d in range(3)]
            widths=[len(g) for g in groups];mx=[max(g.values()) for g in groups]
            # Overestimate the maximum number of target cells created in a tick.
            capacity=max(12,max(mx)+4,sum(sorted(mx)[-2:]),sum(mx))
            earliest=max(sorted(abs(delta(sim.initial()[0][d],o[d][ix[p]],6*r))+1 for d in range(6))[1] for p in P)
            lower=max(K,math.ceil(K*len(P)/capacity),earliest+K-1)
            vv=variants(P,r);sym=sum(v==P for v in vv)
            key=(r,min(tuple(sorted(v)) for v in vv));canon[key].append((kind,j))
            accepts=[t for t in range(1,len(states)) if states[t][3]>states[t-1][3]]
            gaps=[b-a for a,b in zip(accepts,accepts[1:])]
            endpoint=defaultdict(list)
            for t in accepts:endpoint[states[t][:2]].append(t)
            loops=[(b-a,n) for ts in endpoint.values() for n,a in enumerate(ts[:-1],1) for b in ts[n:]]
            rec=dict(kind=kind,case=j,radius=r,target_cells=len(P),copies=K,length=len(program),per_copy=len(program)/K,
                skirting=sim.forbidden.bit_count(),irrelevant=len(cells)-(sim.target|sim.forbidden).bit_count(),
                rotations=sum(v==P for v in vv[:6]),reflections=sum(v==P for v in vv[6:]),symmetries=sym,
                axis_lines=widths,line_maxima=mx,capacity_upper=capacity,lower_bound=lower,gap=len(program)-lower,
                accept_times=accepts,accept_gaps=gaps,distinct_endpoints=len(endpoint),static='pending')
            records.append(rec);bundles[kind].append(dict(case=j,r=r,P=sorted(P),K=K,program=program))
    with (ROOT/'cases.csv').open('w',newline='',encoding='utf-8') as f:
        fields=list(records[0]);wr=csv.DictWriter(f,fields);wr.writeheader();wr.writerows(records)
    (ROOT/'inventory.json').write_text(json.dumps(dict(records=records,bundles=bundles),indent=1))
    for kind in bundles:
        rr=[x for x in records if x['kind']==kind]
        print(kind,'cases',len(rr),'score',sum(x['length'] for x in rr),'r',dict(Counter(x['radius'] for x in rr)),
              'K',dict(Counter(x['copies'] for x in rr)),'targets',min(x['target_cells'] for x in rr),max(x['target_cells'] for x in rr),
              'LB',sum(x['lower_bound'] for x in rr),'nontrivsym',sum(x['symmetries']>1 for x in rr))
        print('TOP',[(x['case'],x['radius'],x['target_cells'],x['copies'],x['length'],x['accept_gaps']) for x in sorted(rr,key=lambda x:x['length'],reverse=True)[:10]])
    print('canonical classes',len(canon),'duplicates',sum(len(v)-1 for v in canon.values()))
    print('duplicate examples',[v for v in canon.values() if len(v)>1][:15])

if __name__=='__main__':main()
