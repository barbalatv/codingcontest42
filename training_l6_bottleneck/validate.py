from native_bottleneck import *
def main():
    begin=time.perf_counter();E=Engine();requests=[];datasets={};improved=[]
    try:
        for ds in DATASETS:
            cc=cases(ds);pp=programs(ds);baseline=programs(ds,'baseline');assert len(cc)==len(pp)
            for i,(c,p,b) in enumerate(zip(cc,pp,baseline)):
                assert len(p)<=len(b),(ds,i+1);aa=exact(c,p);native_check(E,c,p)
                sim=Sim(c);st=sim.initial();trace=[]
                for cmd in p:
                    before=st;st=sim.step(st,cmd);one=two=three=0
                    for e in range(6):
                        if st[1]>>e&1:
                            ray=sim.rays[st[0][e]][e];three|=two&ray;two|=one&ray;one|=ray
                    trace.append(dict(before=str(before[2]),pre=str((before[2]|two)&~three),post=str(st[2]),pos=st[0],active=st[1],accepted=st[3]))
                requests.append(dict(dataset=ds,case=i+1,cells=geometry(c[0])[1],program=p,trace=trace))
                if len(p)<len(b):improved.append(dict(dataset=ds,case=i+1,old=len(b),new=len(p),saved=len(b)-len(p),acceptances=aa))
            datasets[ds]=dict(cases=len(cc),baseline=sum(map(len,baseline)),best=sum(map(len,pp)),sha256=sha(BASE/'best'/name(ds)))
            print('CPP_PYTHON_VERIFY_PASS',ds,len(cc),datasets[ds]['best'],flush=True)
    finally:E.close()
    r=subprocess.run(['node',str(BASE/'verify_trace.cjs')],input=json.dumps(requests),text=True,capture_output=True)
    assert r.returncode==0,(r.stdout,r.stderr)
    js=json.loads(r.stdout);print(js,flush=True)
    protected=json.loads((BASE/'experiments/protected.json').read_text());changed=[p for p,h in protected.items() if not (REPO/p).exists() or sha(REPO/p)!=h]
    assert not changed,changed
    result=dict(status='PASS',datasets=datasets,improved=improved,cpp='ALL_TICKS_RELEVANT_MATTER_PASS',python_sim='PASS',solve_l5_verify='PASS',original_js=js,protected_files=len(protected),protected_changes=changed,wall_seconds=time.perf_counter()-begin,platform_acceptance='NOT_SUBMITTED')
    atomic_json(BASE/'experiments/final_validation.json',result)
    with (BASE/'validation.log').open('a',encoding='utf-8') as f:f.write(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
