from native import *
import shutil

def main():
    lines=[];engine=Engine();total=0;count=0
    try:
        for f in (BASE/'checkpoints').glob('*.json'):
            x=json.loads(f.read_text())
            if 'program' in x and 'old' in x:update(x['dataset'],x['case']-1,[tuple(z) for z in x['program']],x['algorithm'])
        for ds in DATASETS:
            cc=cases(ds);bank=programs(ds);assert len(cc)==len(bank)
            for c,p in zip(cc,bank):
                exact(c,p);native=engine.ask(c,mode=9,hint=p);assert len(native)==len(p);sim=Sim(c);st=sim.initial();rel=sim.target|sim.forbidden
                for command,row in zip(p,native):
                    st=sim.step(st,command);assert packed(st)==row[0] and st[3]==row[1]
                    assert st[2]&rel==sum(v<<(64*w) for w,v in enumerate(row[2:]))
                total+=len(p);count+=1
            lines.append(f'{ds}: CPP + INDEPENDENT_PYTHON PASS {len(bank)} cases {sum(map(len,bank))} ticks')
    finally:engine.close()
    js=subprocess.run(['node',str(BASE/'validate_sandbox.cjs'),'best'],check=True,text=True,capture_output=True);lines.append(js.stdout.strip())
    stage=BASE/'experiments/validation_stage';(stage/'level-6').mkdir(parents=True,exist_ok=True)
    shutil.copyfile(REPO/'validate_l6_sandbox.cjs',stage/'validate_l6_sandbox.cjs');shutil.copyfile(REPO/'level-6/sandbox-level-6.html',stage/'level-6/sandbox-level-6.html')
    for ds in DATASETS:
        shutil.copyfile(REPO/'level-6'/f'in_level-6_{DATASETS[ds]}.txt',stage/'level-6'/f'in_level-6_{DATASETS[ds]}.txt');shutil.copyfile(BASE/'best'/name(ds),stage/'level-6'/name(ds))
    js=subprocess.run(['node',str(stage/'validate_l6_sandbox.cjs')],check=True,text=True,capture_output=True);lines.append(js.stdout.strip())
    root=BASE/'experiments/validated_arms';root.mkdir(exist_ok=True);arms=[]
    for arm in 'ABCDE':
        folder=root/arm;folder.mkdir(exist_ok=True);used=0
        for ds in DATASETS:
            bank=programs(ds,'baseline')
            for i in range(len(bank)):
                rec=json.loads((BASE/'experiments/screen'/f'{ds}_{i+1}.json').read_text());r=next(r for r in rec['rows'] if r['arm']==arm)
                assert r['memory_policy']['applied']
                if r['program']:bank[i]=[tuple(z) for z in r['program']];exact(cases(ds)[i],bank[i]);used+=1
            save_programs(folder/name(ds),bank)
        js=subprocess.run(['node',str(BASE/'validate_sandbox.cjs'),str(folder.relative_to(BASE))],check=True,text=True,capture_output=True);arms.append(dict(arm=arm,status='ORIGINAL_JS_PASS',new_programs=used,log=js.stdout))
    atomic_json(BASE/'experiments/arm_validation.json',arms);lines.append('MATCHED_PRIMARY_ARMS_ORIGINAL_JS_PASS A/B/C/D/E, 540 cases each with frozen fallback')
    protected=json.loads((BASE/'experiments/protected_sha256.json').read_text());changed=[]
    for rel,digest in protected.items():
        f=REPO/rel
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=digest:changed.append(rel)
    assert not changed,changed
    assert not subprocess.check_output(['git','diff','--name-only'],cwd=REPO).strip()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()=='929356266a32982e9924fa0914e6c0488408b656'
    lines.append(f'PROTECTED_BYTES_PASS {len(protected)} files; tracked worktree and HEAD unchanged')
    lines.append(f'FULL_LOCAL_PASS {count} cases {total} ticks; exactly K pickups; no commands after final pickup; platform NOT_SUBMITTED')
    (BASE/'validation.log').write_text('\n'.join(lines)+'\n',encoding='utf-8');atomic_json(BASE/'experiments/validation.json',dict(status='PASS',cases=count,ticks=total,cpp='PASS',independent_python='PASS',original_js='PASS',strict_js='PASS',primary_arms='ABCDE_PASS',protected_files=len(protected),protected_changes=changed,head='929356266a32982e9924fa0914e6c0488408b656'))
    print('\n'.join(lines),flush=True)

if __name__=='__main__':main()
