"""Regression gate first, then the bounded historical eight-case pilot."""
import sys,os,json,subprocess,time,hashlib,argparse
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE.parent))
from sim import Machine,cases,decode
from build import build
def save(path,x):
    tmp=path.with_suffix('.pending');tmp.write_text(json.dumps(x,indent=2),encoding='utf-8');os.replace(tmp,path)
def exe(name):return str(BASE/(name+('.exe' if os.name=='nt' else '')))
def invoke(name,args,filename,timeout=180):
    p=subprocess.Popen([exe(name),*args],cwd=BASE,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:stdout,stderr=p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:p.kill();p.communicate();raise
    cpu=None
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        k=ctypes.windll.kernel32;k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4;k.GetProcessTimes.restype=wintypes.BOOL
        a,b,c,d=(wintypes.FILETIME() for _ in range(4))
        assert k.GetProcessTimes(wintypes.HANDLE(int(p._handle)),ctypes.byref(a),ctypes.byref(b),ctypes.byref(c),ctypes.byref(d))
        cpu=(((c.dwHighDateTime<<32)|c.dwLowDateTime)+((d.dwHighDateTime<<32)|d.dwLowDateTime))/1e7
    (BASE/filename).write_text(stdout+stderr,encoding='utf-8');assert p.returncode==0,(name,p.returncode,stdout,stderr)
    rows=[json.loads(line) for line in stdout.splitlines() if line.strip()]
    for r in rows:
        if 'cpu_seconds' in r:
            r['reported_clock_seconds']=r.pop('cpu_seconds');r['case_process_cpu_seconds']=cpu;r['cpu_measurement']='GetProcessTimes per complete case process' if cpu is not None else 'NOT_MEASURED'
    return rows
def js(fixture,program,label,explicit_input=None):
    f=BASE/'programs'/f'{label}.txt';f.parent.mkdir(exist_ok=True)
    f.write_text('\n'.join(' '.join(row) for row in program)+'\n',encoding='utf-8')
    r=subprocess.run(['node',str(BASE.parent/'validate_case.cjs'),fixture['dataset'],str(fixture['case']),str(f),*([str(explicit_input)] if explicit_input else [])],text=True,capture_output=True)
    result=json.loads(r.stdout);result['exit_code']=r.returncode
    return result
def verify_protected():
    root=BASE.parents[2];frozen=json.loads((BASE/'protected.json').read_text())
    assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==v for p,v in frozen.items())
    return len(frozen)
def regress(fixtures):
    legacy=invoke('legacy_probe',['regression'],'legacy_probe.jsonl')
    assert len(legacy)==12 and all(not r['can_finish'] and r['found']==0 for r in legacy)
    raw=invoke('driver',['regression'],'regression_cpp.jsonl');assert raw[0]['synthetic']=='PASS'
    controls=[]
    for r in raw[1:]:
        f=fixtures[r['case']];p=decode(r['program']);m=Machine(cases(f['dataset'])[f['case']-1]);st,aa,_=m.run(p)
        assert r['can_finish'] and r['found']==1 and st[3]==f['K'] and aa[-1]==len(p)
        result=js(f,p,f"positive_{r['case']}");assert result['pass'] and result['acceptances']==aa
        controls.append(dict(fixture=f['local'],dataset=f['dataset'],case=f['case'],K=f['K'],ticks=len(p),can_finish=True,search_found=1,js=result))
    assert len(controls)==12
    negative=[];f=next(f for f in fixtures if f['K']==1);p=[tuple(r) for r in f['program']];m=Machine(cases(f['dataset'])[f['case']-1]);st,_,_=m.run(p)
    off=tuple('T' if st[1]>>e&1 else '-' for e in range(6))
    for label,pp,reason,expected in [('early_final_accept',p+[off],'TRAILING_COMMANDS',1),('commands_after_K',p+[off,tuple('------')],'TRAILING_COMMANDS',1),('incomplete_target',p[:-1],'INSUFFICIENT_COPIES',0)]:
        result=js(f,pp,label);assert not result['pass'] and result['reason']==reason and result['accepted']==expected
        negative.append(dict(name=label,expected_reason=reason,result=result))
    f2=next(f for f in fixtures if f['K']>1);pp=[tuple(r) for r in f2['program'][:f2['acceptances'][0]]]
    result=js(f2,pp,'insufficient_copies');assert result['reason']=='INSUFFICIENT_COPIES' and result['accepted']==1 and result['required']==f2['K'];negative.append(dict(name='insufficient_copies',result=result))
    # Turn off all beams, return to the known initial pose, replay a fresh copy.
    reset=[off];pos=list(st[0]);L=6*m.r
    while tuple(pos)!=m.initial:
        row=[]
        for e in range(6):
            delta=(m.initial[e]-pos[e])%L
            ch='-' if delta==0 else 'B' if delta<=L//2 else 'F';row.append(ch)
            pos[e]=(pos[e]+(1 if ch=='B' else -1 if ch=='F' else 0))%L
        reset.append(tuple(row))
    result=js(f,p+reset+p,'excess_copies');assert result['reason']=='EXCESS_COPIES' and result['accepted']==2;negative.append(dict(name='excess_copies',result=result))
    blocked=js(dict(dataset='fixture',case=1),[tuple('T--T--')],'forbidden_painting',BASE/'forbidden_input.txt')
    toy=Machine((2,frozenset([(2,4)]),1));end,_,_=toy.run([tuple('T--T--')])
    assert end[2]&toy.target==toy.target and end[2]&toy.forbidden and blocked['accepted']==0 and blocked['reason']=='INSUFFICIENT_COPIES'
    negative.append(dict(name='forbidden_painting',target_full=True,dirty_skirting=(end[2]&toy.forbidden).bit_count(),result=blocked))
    rt=invoke('rtds_test',[],'rtds_test.jsonl');assert rt[0]['rtds_suffix']=='PASS'
    # Verify the simulation body itself was not changed by terminal repairs.
    for name in ['endgame.cpp','rtds.cpp']:
        a=(BASE/'original'/name).read_text();b=(BASE.parent/name).read_text();start='static inline void apply(';end='\n}\n'
        def body(s):i=s.index(start);return s[i:s.index(end,i)+len(end)]
        assert body(a)==body(b)
    gate=dict(status='PASS',legacy_false_negatives=len(legacy),positive_controls=controls,negative_js=negative,negative_cpp=raw[0],rtds=rt[0],transition_physics='UNCHANGED',protected_files=verify_protected())
    save(BASE/'regression.json',gate);print('REGRESSION PASS 12 positives, 6 exact JS negatives, synthetic forbidden/early/excess controls, RTDS, dedup, reconstruction',flush=True)
def pilot(fixtures,budget_ms,measured=False,run_name=None):
    assert json.loads((BASE/'regression.json').read_text())['status']=='PASS'
    config=dict(indices=[f['global_index'] for f in fixtures[:8]],incumbent_ticks=sum(f['ticks'] for f in fixtures[:8]),WMIN=4,WMAX=10,WIDTH=300,actions=4096,seed='NONE_DETERMINISTIC_FULL_ACTIONS_AND_STATE_TIEBREAK',window_budget_ms=budget_ms,legacy_parameters='defaults recovered; original environment not recorded; deadline is an explicit new bound',expansion_scope='ONLY_HISTORICAL_8_CASES')
    stem=run_name or ('pilot_measured' if measured else 'pilot');config_path=BASE/f'{stem}_config.json'
    if config_path.exists():assert json.loads(config_path.read_text())==config
    else:save(config_path,config)
    output=BASE/stem;output.mkdir(exist_ok=True)
    for f in fixtures[:8]:
        path=output/f"case_{f['global_index']}.json"
        if path.exists():continue
        records=invoke('driver',['pilot',str(f['local']),'4','10','300',str(budget_ms)],f"{stem}_{f['global_index']}.jsonl",timeout=7*budget_ms/1000+120)
        for r in records:
            r.update(dataset=f['dataset'],official_case=f['case'],K=f['K'],incumbent=f['ticks'],budget_ms=budget_ms)
            if r['program']:
                p=decode(r['program']);m=Machine(cases(f['dataset'])[f['case']-1]);st,aa,_=m.run(p)
                replay_valid=st[3]==f['K'] and bool(aa) and aa[-1]==len(p) and r['cpp_valid']
                check=js(f,p,f"pilot_{f['global_index']}_W{r['W']}");r['js']=check
                r['outcome']='RECONSTRUCTION_REPLAY_REJECTED' if not replay_valid else 'REJECTED_JS' if not check['pass'] else 'INDEPENDENTLY_VALID_SHORTER' if len(p)<f['ticks'] else 'VALID_NOT_SHORTER'
                if replay_valid and check['pass']:
                    r['repeat_js']=js(f,p,f"repeat_{f['global_index']}_W{r['W']}");assert r['repeat_js']==check
            else:r['outcome']='RESOURCE_LIMIT_BEFORE_TERMINAL' if r['timeout'] else 'INVALID_START_COPY_COUNT' if r['invalid_start'] else 'NO_TERMINAL_FOUND'
            r['saved']=f['ticks']-len(r['program']) if r['outcome']=='INDEPENDENTLY_VALID_SHORTER' else 0
        save(path,dict(fixture=f,windows=records,case_cpu_seconds=records[0].get('case_process_cpu_seconds')));print('PILOT',f['dataset'],f['case'],'windows',len(records),'terminals',sum(r['terminal_transitions'] for r in records),'best_saved',max(r['saved'] for r in records),'timeouts',sum(r['timeout'] for r in records),flush=True)
    protected=verify_protected();allrows=[r for p in output.glob('case_*.json') for r in json.loads(p.read_text())['windows']]
    assert len(list(output.glob('case_*.json')))==8
    best={f['global_index']:max([r['saved'] for r in json.loads((output/f"case_{f['global_index']}.json").read_text())['windows']],default=0) for f in fixtures[:8]}
    cpu_values=[json.loads(p.read_text()).get('case_cpu_seconds') for p in output.glob('case_*.json')]
    save(BASE/f'{stem}_summary.json',dict(status='COMPLETED_BOUNDED_PILOT',cases=8,incumbent=324,best_ticks=324-sum(best.values()),saved=sum(best.values()),best_per_case=best,windows=len(allrows),timeouts=sum(r['timeout'] for r in allrows),terminal_transitions=sum(r['terminal_transitions'] for r in allrows),reconstructed=sum(r['reconstructed'] for r in allrows),cpu_seconds=sum(cpu_values) if all(v is not None for v in cpu_values) else None,wall_seconds=sum(r['wall_seconds'] for r in allrows),protected_files_unchanged=protected))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',action='store_true');ap.add_argument('--measured',action='store_true');ap.add_argument('--budget-ms',type=int,default=5000);ap.add_argument('--run-name',help='New isolated result name for a fresh search; existing names resume');args=ap.parse_args()
    if args.run_name and (not args.run_name.replace('_','').replace('-','').isalnum() or not args.run_name.isascii()):ap.error('run-name must contain only ASCII letters, digits, underscore or hyphen')
    build();fixtures=json.loads((BASE/'fixtures.json').read_text());regress(fixtures)
    if args.pilot:pilot(fixtures,args.budget_ms,args.measured,args.run_name)
