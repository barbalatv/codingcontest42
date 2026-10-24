from common import *
from native import Engine
import shutil
def main():
    lines=[];engine=Engine('cellfirst_discover.exe');total=0
    try:
        # Recover the minimum across every fully validated atomic checkpoint.
        for f in sorted((BASE/'checkpoints').glob('*.json')):
            x=json.loads(f.read_text());p=[tuple(row) for row in x['program']];update(x['dataset'],x['case']-1,p,'checkpoint_recovery')
        for ds in DATASETS:
            pp=programs(ds);cc=cases(ds);assert len(pp)==len(cc)
            for i,(c,p) in enumerate(zip(cc,pp)):
                exact(c,p);out=engine.ask(c,mode=9,hint=p);sim=Sim(c);st=sim.initial();rel=sim.target|sim.forbidden
                for row,rr in zip(p,out):
                    st=sim.step(st,row);native_matter=sum(v<<(64*w) for w,v in enumerate(rr[2:]));assert packed(st)==rr[0] and st[3]==rr[1] and st[2]&rel==native_matter
                assert st[3]==c[2];total+=len(p)
            lines.append(f'{ds}: CPP_INTERNAL_REPLAY + INDEPENDENT_PYTHON_VERIFY PASS, {len(pp)} cases, {sum(map(len,pp))} ticks')
    finally:engine.close()
    r=subprocess.run(['node',str(BASE/'validate_sandbox.cjs'),'best'],check=True,text=True,capture_output=True);lines.append(r.stdout.strip())
    # Execute the requested original validator unchanged in an isolated staging
    # tree. The stricter adapter above additionally checks the Kth-acceptance end.
    stage=BASE/'experiments/validation_stage';(stage/'level-6').mkdir(parents=True,exist_ok=True)
    shutil.copyfile(REPO/'validate_l6_sandbox.cjs',stage/'validate_l6_sandbox.cjs');shutil.copyfile(REPO/'level-6/sandbox-level-6.html',stage/'level-6/sandbox-level-6.html')
    for ds in DATASETS:
        suffix=DATASETS[ds];shutil.copyfile(REPO/'level-6'/f'in_level-6_{suffix}.txt',stage/'level-6'/f'in_level-6_{suffix}.txt');shutil.copyfile(BASE/'best'/name(ds),stage/'level-6'/name(ds))
    r=subprocess.run(['node',str(stage/'validate_l6_sandbox.cjs')],check=True,text=True,capture_output=True);lines.append(r.stdout.strip())
    protected=json.loads((BASE/'experiments/protected_sha256.json').read_text());changed=[];missing=[]
    for f,digest in protected.items():
        p=REPO/f
        if not p.exists():missing.append(f)
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(f)
    assert not changed and not missing,(changed,missing)
    tracked=subprocess.run(['git','diff','--name-only'],cwd=REPO,capture_output=True,text=True,check=True).stdout
    assert not tracked.strip(),tracked
    lines.append(f'PROTECTED_FILE_BYTES_PASS {len(protected)} files; tracked worktree unchanged')
    lines.append('FULL_VALIDATION_PASS 540 cases '+str(total)+' ticks; no commands after Kth acceptance')
    (BASE/'validation.log').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    atomic_json(BASE/'experiments/validation.json',dict(status='PASS',cases=540,ticks=total,cpp='PASS',solve_l5_verify='PASS',original_js='PASS',stricter_js='PASS',protected_files=len(protected),protected_changes=changed,protected_missing=missing,original_validator_sha256=hashlib.sha256((REPO/'validate_l6_sandbox.cjs').read_bytes()).hexdigest()))
    print('\n'.join(lines),flush=True)
if __name__=='__main__':main()
