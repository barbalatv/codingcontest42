"""Bounded reuse of existing Cell-Assignment LNS and acceptance-aware CP-SAT."""
from bottleneck_runner import *
import importlib.util
import bottleneck_runner as runner
def get_synth():
    path=BASE/'repair/exact_model.py'
    spec=importlib.util.spec_from_file_location('bn_exact_model',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.synth
def select_nears(limit=24):
    choices={}
    for folder in ['universal','dynamic','iterative','deep']:
        for f in (BASE/'experiments'/folder).glob('case_*.json'):
            for r in json.loads(f.read_text())['rows']:
                d=r['near_diagnostics'];ctx=r['context']
                if not d or not r['near_program'] or ctx['horizon']>12 or d['accepted']>=ctx['copies']:continue
                if d['defects']>12:continue
                key=r['case'];rank=(d['defects'],len(r['near_program']),r['case'])
                if key not in choices or rank<choices[key][0]:choices[key]=(rank,r,str(f.relative_to(BASE)))
    return [(r,source) for _,r,source in sorted(choices.values(),key=lambda x:x[0])[:limit]]
def repair_task(job):
    r,source=job;c=cases('enormous')[r['case']-1];inc=programs('enormous','baseline')[r['case']-1];ctx=r['context'];ctx['start']=(tuple(ctx['start'][0]),*ctx['start'][1:]);H=ctx['horizon'];near=[tuple(z) for z in r['near_program']];seed=r['seed']+900000
    if len(near)<H:near +=[tuple('------')]*(H-len(near))
    rows=[]
    # Mode C: same proven beam prefix, then the existing unweighted LNS repair.
    method='weighted_beam_plus_LNS' if r.get('weights') else 'standard_beam_plus_LNS'
    row=run_query(c,inc,ctx,method,{},seed,1500,mode=7,hint=near);row.update(case=r['case'],stage='repair',source=source,prefix_source_method=r['method'],prefix_source_weighted=bool(r.get('weights')));rows.append(row)
    sim=Sim(c);ss=[ctx['start']]
    for cmd in near:ss.append(sim.step(ss[-1],cmd))
    synth=get_synth();attempts=[]
    # Replan all six emitters jointly, first in the last 3, then last 5 ticks.
    for window in [3,5]:
        lo=max(0,H-window);st=ss[lo];remaining=ctx['copies']-st[3]
        if remaining<1:continue
        local=(st[0],st[1],st[2],0);hint=[(s[0],s[1],s[2],s[3]-st[3]) for s in ss[lo:]]
        end=None
        if ctx['goal'] is not None:
            q=ctx['goal'];end=(tuple((q>>(8*e))&127 for e in range(6)),sum(((q>>(8*e+7))&1)<<e for e in range(6)),0,remaining)
        wall=time.perf_counter();cpu=time.process_time()
        try:p,info=synth(c,local,H-lo,remaining,end=end,hint=hint,free=tuple(range(6)),seconds=2,seed=seed+window)
        except MemoryError:
            p=None;info=dict(status='RESOURCE_LIMIT_MEMORY',branches=0,seconds=time.perf_counter()-wall)
        candidate=[tuple(z) for z in ctx['prefix']]+near[:lo]+p+[tuple(z) for z in ctx['suffix']] if p else None
        valid=False;error=None
        if candidate:
            try:exact(c,candidate);native_check(runner.ENGINE,c,candidate);valid=len(candidate)<len(inc)
            except Exception as e:error=repr(e);candidate=None
        attempts.append(dict(case=r['case'],method='exact_repair',stage='repair',source=source,window=window,all_six_emitters=True,seed=seed+window,width=None,budget_ms=2000,incumbent=len(inc),candidate=len(candidate) if candidate else None,saved=len(inc)-len(candidate) if candidate else 0,valid=valid,program=candidate,error=error,evaluations=info['branches'],cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall,solver=info,memory_policy=runner.MEMORY,near_source=r['method']))
        atomic_json(BASE/'checkpoints/repair_attempts'/f"case_{r['case']}.json",dict(case=r['case'],rows=rows+attempts))
        if valid:break
    return dict(case=r['case'],rows=rows+attempts)
def main():
    path=BASE/'repair/exact_model.py';path.write_text(path.read_text().replace('from common import *','from common_bn import *').replace('num_search_workers=2','num_search_workers=1').replace('max_memory_in_mb=1024','max_memory_in_mb=896'))
    jobs=select_nears();folder=BASE/'experiments/repair';folder.mkdir(exist_ok=True)
    atomic_json(folder/'selection.json',[dict(case=r['case'],source=s,method=r['method'],defects=r['near_diagnostics']['defects']) for r,s in jobs])
    todo=[j for j in jobs if not(folder/f"case_{j[0]['case']}.json").exists()];E=Engine()
    try:
        for f in folder.glob('case_*.json'):
            x=json.loads(f.read_text())
            for r in x['rows']:
                if r['valid']:promote(E,'enormous',x['case']-1,[tuple(z) for z in r['program']],r['method'],str(f.relative_to(BASE)))
        with concurrent.futures.ProcessPoolExecutor(max_workers=1,initializer=init_worker,initargs=(1024,)) as pool:
            for x in pool.map(repair_task,todo):
                f=folder/f"case_{x['case']}.json";atomic_json(f,x)
                for r in x['rows']:
                    if r['valid']:promote(E,'enormous',x['case']-1,[tuple(z) for z in r['program']],r['method'],str(f.relative_to(BASE)))
                print('REPAIR',x['case'],[(r['method'],r.get('solver',{}).get('status'),r['saved']) for r in x['rows']],flush=True)
    finally:E.close()
if __name__=='__main__':main()
