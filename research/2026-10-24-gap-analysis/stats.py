import sys
sys.dont_write_bytecode=True
from sim import *
import statistics, json, collections

def build():
    rows=[]
    for ds in ('medium','large','enormous'):
        cs=cases(ds); ps=programs(ds)
        assert len(cs)==len(ps),(ds,len(cs),len(ps))
        for i,(c,p) in enumerate(zip(cs,ps),1):
            m=Machine(c); st,acc,tr=m.run(p, want_trace=True)
            assert st[3]==c[2], (ds,i,st[3],c[2])
            T=len(p); K=c[2]
            iv=[b-a for a,b in zip(acc,acc[1:])]
            rows.append(dict(ds=ds,case=i,r=c[0],K=K,T=T,nT=m.target.bit_count(),nF=m.forbidden.bit_count(),
                             rel=m.rel.bit_count(),
                             first=acc[0], iv_mean=(statistics.mean(iv) if iv else None), iv_min=(min(iv) if iv else None),
                             iv_mode=(statistics.mode(iv) if iv else None),
                             newt=sum(t['new_target'] for t in tr), h2=sum(t['new_target']+t['repeat_target'] for t in tr),
                             motion=sum(t['motion'] for t in tr), toggles=sum(t['toggles'] for t in tr),
                             idle=sum(1 for t in tr if t['new_target']==0), kills=sum(t['kill_target'] for t in tr)))
    return rows

if __name__=='__main__':
    rows=build(); json.dump(rows, open('case_stats.json','w'), indent=0)
    agg=collections.defaultdict(collections.Counter)
    for r in rows:
        a=agg[r['ds']]
        for k in ('T','K','nT','newt','h2','motion','toggles','idle','kills','rel'): a[k]+=r[k]
        a['n']+=1
    for ds,a in agg.items():
        print(ds, dict(a))
        print('   T/K=%.2f new_target/tick=%.2f h2/tick=%.2f idle=%.2f motion/tick=%.2f'%(a['T']/a['K'],a['newt']/a['T'],a['h2']/a['T'],a['idle']/a['T'],a['motion']/a['T']))
    print('TOTAL T',sum(r['T'] for r in rows),'K',sum(r['K'] for r in rows),'nT',sum(r['nT'] for r in rows))
    c=collections.Counter()
    for r in rows:
        if r['K']>1: c[r['iv_mode']]+=1
    print('interval mode distribution (K>1):', dict(sorted(c.items())))
    print('interval min distribution (K>1):', dict(sorted(collections.Counter(r['iv_min'] for r in rows if r['K']>1).items())))
    pot=sum((r['iv_mean']-max(1,r['iv_mean']-1))*(r['K']-1) for r in rows if r['K']>1 and r['iv_mean'])
    print('potential if every per-copy interval -1:', round(pot))
