from native import *
sys.path.insert(0,str(BASE/'repair'))
from exact_model import synth
import argparse
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seconds',type=float,default=6);ap.add_argument('--limit',type=int,default=22);args=ap.parse_args()
    old=[json.loads(line) for line in (BASE/'experiments/repair_expanded.jsonl').read_text().splitlines()]
    chosen=[(x['dataset'],x['case']) for x in old if x['dataset']=='large' and x['validation'] in ('OPTIMAL','FEASIBLE','UNKNOWN')]
    more=[]
    for i,(c,p) in enumerate(zip(cases('large'),programs('large'))):
        if ('large',i+1) not in chosen and c[2]==1 and len(p)<=12 and len(c[1])<=40:more.append((len(p),len(c[1]),i+1))
    for _,_,idx in sorted(more,reverse=True):chosen.append(('large',idx))
    chosen=chosen[:args.limit];engine=Engine('cellfirst_discover.exe');models=BASE/'experiments/exact_models';models.mkdir(exist_ok=True)
    try:
        for j,(ds,idx) in enumerate(chosen):
            c=cases(ds)[idx-1];sim=Sim(c);before=len(programs(ds)[idx-1]);p=programs(ds)[idx-1];besthint=None;bestcost=10**9
            for cut in range(len(p)):
                trial=p[:cut]+p[cut+1:];hint=sim.prefix(trial);st=hint[-1];cost=max(0,c[2]-st[3]-1)*(len(c[1])*3+16)+(sim.target&~st[2]).bit_count()*3+(sim.forbidden&st[2]).bit_count()*4
                if cost<bestcost:bestcost=cost;besthint=hint
            seed=5000000+idx*137;atomic_json(models/f'{ds}_{idx}_{before-1}.json',dict(dataset=ds,case=idx,horizon=before-1,copies=c[2],start=sim.initial(),end=None,free_emitters=list(range(6)),hint=besthint,seconds=args.seconds,seed=seed,memory_mb=1024))
            q,info=synth(c,sim.initial(),before-1,c[2],hint=besthint,free=tuple(range(6)),seconds=args.seconds,seed=seed)
            if q:
                cpp=engine.ask(c,mode=9,hint=q);st=sim.initial();finish=None
                for t,(row,rr) in enumerate(zip(q,cpp),1):
                    st=sim.step(st,row);assert packed(st)==rr[0] and st[3]==rr[1]
                    if st[3]==c[2] and finish is None:finish=t
                assert finish;update(ds,idx-1,q[:finish],'expanded_exact_polish',info['seconds'],info['branches'],seed)
            rec=dict(dataset=ds,case=idx,incumbent=before,candidate=len(programs(ds)[idx-1]),saved=before-len(programs(ds)[idx-1]),algorithm='expanded_exact_polish',runtime=info['seconds'],evaluations=info['branches'],seed=seed,validation=info['status'],global_bound_proof=info['status']=='INFEASIBLE',proven_minimum_ticks=before if info['status']=='INFEASIBLE' else None,horizon=before-1,free_emitters=list(range(6)),initial_defect_cost=bestcost)
            with (BASE/'experiments/exact_polish.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
            print(ds,idx,'POLISH',info['status'],before,'->',len(programs(ds)[idx-1]),flush=True)
    finally:engine.close()
if __name__=='__main__':main()
