import sys,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_bottleneck import *
from diagnostics import bits
def main():
    A=Engine('reference_beam.exe');B=Engine();tested=0;rng=random.Random(642)
    try:
        for ds,i in [('medium',5),('large',20),('enormous',0),('enormous',48),('enormous',139)]:
            c=cases(ds)[i];sim=Sim(c);cells=list(bits(sim.target))
            for sample in range(8):
                weights={cell:rng.choice([100,150,170,200,230,300,500]) for cell in rng.sample(cells,min(len(cells),12))}
                start=(tuple(rng.randrange(6*c[0]) for _ in range(6)),rng.randrange(64),rng.getrandbits(len(geometry(c[0])[1]))&(sim.target|sim.forbidden),0)
                p=[tuple(rng.choice('-FBT') for _ in range(6)) for _ in range(8)]
                a=A.ask(c,mode=90,start=start,hint=p);b=B.ask(c,mode=90,start=start,hint=p,weights=weights);st=start
                for cmd,aa,bb in zip(p,a,b):
                    st=sim.step(st,cmd);total=sum(v-100 for v in weights.values());filled=sum(v-100 for cell,v in weights.items() if st[2]>>cell&1)
                    assert bb[0]-aa[0]==2*(st[3]*total+filled-total)
                    one=two=three=0
                    for e in range(6):
                        if st[1]>>e&1:
                            ray=sim.rays[st[0][e]][e];three|=two&ray;two|=one&ray;one|=ray
                    delta=0
                    for cell,v in weights.items():
                        d=v-100;old=st[2]>>cell&1;h3=three>>cell&1;h2=two>>cell&1 and not h3
                        delta+=d if h2 and not old else 0
                        delta-=d*85//100 if h3 and old else 0
                        delta-=d*8//100 if h3 else 0
                    assert bb[1]-aa[1]==delta
                    assert aa[2:]==bb[2:];tested+=1
        atomic_json(BASE/'experiments/weight_math_tests.json',dict(status='PASS',scalar_vs_grouped_state_and_snapshot_scores=tested,physics_parity='PASS'))
        print('WEIGHT MATH PASS',tested)
    finally:A.close();B.close()
if __name__=='__main__':main()
