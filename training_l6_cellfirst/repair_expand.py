from native import *
sys.path.insert(0,str(BASE/'repair'))
from exact_model import synth
import argparse
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=24);ap.add_argument('--seconds',type=float,default=4);args=ap.parse_args();choices={}
    for f in (BASE/'repair/near').glob('*.json'):
        x=json.loads(f.read_text());ds=x['dataset'];i=x['case']-1;c=cases(ds)[i];p=programs(ds)[i];sim=Sim(c)
        if ds=='medium' or x['copies']!=c[2] or packed(x['start'])!=packed(sim.initial()) or x['start'][2] or x['goal'] is not None:continue
        if len(x['program'])!=len(p)-1 or len(p)>19 or len(c[1])>55:continue
        key=ds,i
        if key not in choices or x['cost']<choices[key][1]['cost']:choices[key]=(f,x)
    todo=sorted(choices.items(),key=lambda v:(v[1][1]['cost'],v[0][0]!='enormous',len(v[1][1]['program'])))[:args.limit];engine=Engine()
    try:
        for (ds,i),(f,x) in todo:
            c=cases(ds)[i];sim=Sim(c);p=[tuple(row) for row in x['program']];hint=sim.prefix(p);before=len(programs(ds)[i]);seed=x['seed']+91
            q,info=synth(c,sim.initial(),before-1,c[2],hint=hint,free=tuple(range(6)),seconds=args.seconds,seed=seed)
            proof=info['status']=='INFEASIBLE'
            if q:
                cpp=engine.ask(c,mode=9,hint=q);st=sim.initial();end=None
                for t,(row,rr) in enumerate(zip(q,cpp),1):
                    st=sim.step(st,row);assert packed(st)==rr[0] and st[3]==rr[1]
                    if st[3]==c[2] and end is None:end=t
                assert end is not None;update(ds,i,q[:end],'expanded_exact_repair',info['seconds'],info['branches'],seed)
            rec=dict(dataset=ds,case=i+1,incumbent=before,candidate=len(programs(ds)[i]),saved=before-len(programs(ds)[i]),algorithm='expanded_exact_repair',runtime=info['seconds'],evaluations=info['branches'],seed=seed,validation=info['status'],global_bound_proof=proof,proven_minimum_ticks=before if proof else None,free_emitters=list(range(6)),horizon=before-1,near_source=str(f.relative_to(BASE)))
            with (BASE/'experiments/repair_expanded.jsonl').open('a') as log:log.write(json.dumps(rec)+'\n')
            print(ds,i+1,'EXPANDED',info['status'],before,'->',len(programs(ds)[i]),flush=True)
    finally:engine.close()
if __name__=='__main__':main()
