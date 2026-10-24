from native import *
import random
def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--engine',default='cellfirst.exe');args=ap.parse_args()
    engine=Engine(args.engine);rng=random.Random(422026);total=0;traces=[]
    try:
        for ds in DATASETS:
            cc=cases(ds);bank=programs(ds)
            for i,(c,p) in enumerate(zip(cc,bank)):
                p=p+[tuple(rng.choice('-FBT') for _ in range(6)) for _ in range(12)]
                out=engine.ask(c,mode=9,hint=p);sim=Sim(c);states=sim.prefix(p)[1:];rel=sim.target|sim.forbidden;cells=geometry(c[0])[1];relevant=[xy for j,xy in enumerate(cells) if rel>>j&1]
                expected=[]
                for t,(s,row) in enumerate(zip(states,out)):
                    matter=sum(v<<(64*w) for w,v in enumerate(row[2:]))
                    assert packed(s)==row[0] and s[3]==row[1] and s[2]&rel==matter,(ds,i+1,t)
                    expected.append(dict(positions=s[0],active=[bool(s[1]>>e&1) for e in range(6)],accepted=s[3],matter=[xy for j,xy in enumerate(cells) if rel>>j&1 and s[2]>>j&1]))
                    total+=1
                traces.append(dict(dataset=ds,case=i+1,program=p,relevant=relevant,states=expected))
            print('CPP_PYTHON_STATE_EQUIVALENCE_PASS',ds,len(cc),flush=True)
    finally:engine.close()
    atomic_json(BASE/'experiments/expected_traces.json',traces)
    atomic_json(BASE/'experiments/native_tests.json',dict(status='PASS',cases=540,states=total,seed=422026,random_continuation=12,engine=args.engine))
    print('STATES',total,flush=True)
if __name__=='__main__':main()
