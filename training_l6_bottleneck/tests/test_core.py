import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_bottleneck import *
from diagnostics import analyze_case
import importlib.util,random
def main():
    spec=importlib.util.spec_from_file_location('old_tests',BASE/'archive/ccc42_bottleneck_tests.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    old.test_reset_at_acceptance();old.test_churn_in_tail();old.test_skirting_clean()
    def run(actions):
        sim=old.ToySim(3,rays_by_emitter={0:1,1:1,2:1,3:2,4:2})
        return analyze_case(sim,[tuple(r) for r in actions],dataset='toy',index=1,radius=1,K=1,n_target=2)[0]
    inside=run(['TT----','--T---','--TTT-'])
    assert inside['first_built_in_tail']==2 and inside['first_in_tail_rebuilt_in_tail']==1 and inside['first_before_tail_rebuilt_in_tail']==0
    earlier=run(['TT----']+['------']*4+['--T---','--TTT-'])
    assert earlier['first_built_in_tail']==1 and earlier['first_before_tail_rebuilt_in_tail']==1 and earlier['first_in_tail_rebuilt_in_tail']==0
    engines=[Engine('reference_beam.exe'),Engine()];counts=dict(audit_states=0,deterministic_beams=0,protocol_checks=0)
    try:
        for ds,idx in [('medium',0),('large',42),('enormous',0),('enormous',48),('enormous',139)]:
            c=cases(ds)[idx];p=programs(ds,'baseline')[idx];sim=Sim(c)
            a,b=[e.ask(c,mode=90,seed=71,hint=p) for e in engines];assert a==b
            counts['audit_states']+=len(p);native_check(engines[1],c,p)
            # Different states, actions, and filled target/skirting patterns.
            rng=random.Random(81+idx)
            for _ in range(5):
                st=(tuple(rng.randrange(6*c[0]) for e in range(6)),rng.randrange(64),rng.getrandbits(len(geometry(c[0])[1]))&(sim.target|sim.forbidden),0)
                pp=[tuple(rng.choice('-FBT') for _ in range(6)) for j in range(8)]
                assert engines[0].ask(c,mode=90,start=st,hint=pp)==engines[1].ask(c,mode=90,start=st,hint=pp,weights={cell:100 for cell in list(__import__('diagnostics').bits(sim.target))[:3]})
                counts['audit_states']+=len(pp)
        for idx in [0,48,115]:
            c=cases('enormous')[idx];T=len(programs('enormous','baseline')[idx])
            for mode in [0,1,3,7]:
                hint=programs('enormous','baseline')[idx] if mode==7 else ()
                rr=[e.ask(c,k=c[2],mode=mode,horizon=T-1,width=8,ms=100000,seed=851+idx,eval_limit=25000,hint=hint) for e in engines]
                assert rr[0][:2]==rr[1][:2]
                for key in ['near_program','near_cost','evaluations','configurations','expanded_depth','selection_digest','configuration_digest']:assert rr[0][2][key]==rr[1][2][key],key
                counts['deterministic_beams']+=1
        c=cases('enormous')[0];cells=list(__import__('diagnostics').bits(Sim(c).target));e=engines[1]
        for mask in [{},{cells[0]:200},{c:300 for c in cells[:3]}]:
            e.ask(c,mode=9,hint=programs('enormous','baseline')[0],weights=mask);counts['protocol_checks']+=1
        frame=e.frame(c,mode=9,hint=[tuple('------')])
        for malformed in ['BAD',frame+' 1',frame.rsplit(' ',1)[0]+' 1',frame.rsplit(' ',1)[0]+' 1 999999 200',frame.rsplit(' ',1)[0]+' 2 '+str(cells[0])+' 200']:
            try:e.exchange(malformed);raise AssertionError('accepted malformed')
            except ValueError:pass
            e.ask(c,mode=9,hint=[tuple('------')]);counts['protocol_checks']+=1
        try:e.exchange(e.frame(c,k=c[2],horizon=80,ms=3000),timeout=0.001);raise AssertionError('timeout failed')
        except TimeoutError:pass
        e.ask(c,mode=9,hint=[tuple('------')]);counts['protocol_checks']+=1
        atomic_json(BASE/'experiments/core_tests.json',dict(status='PASS',**counts,synthetic_classes=['acceptance_reset','first_in_tail_with_churn','first_before_tail_rebuilt','cleanup'],baseline_parity='zero-delta scoring, physics, configurations, selected result and near trajectory under identical evaluation limit'))
        print('CORE PASS',counts)
    finally:
        for e in engines:e.close()
if __name__=='__main__':main()
