"""Validate promoted submission bytes without rewriting research snapshots."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'training_l6_full540'))
from common import *
from native import Engine
import zipfile

def main():
    release=Path(__file__).resolve().parent
    manifest=json.loads((release/'delivery.json').read_text())
    lines=[];total=0;count=0;engine=Engine('cellfirst.exe')
    try:
        with zipfile.ZipFile(release/'answers_level6_15657.zip') as archive:
            assert archive.testzip() is None
            assert set(archive.namelist())=={name(ds) for ds in DATASETS}
            for row in manifest['artifacts']:
                ds=row['dataset'];target=ROOT/row['path'];data=target.read_bytes()
                assert data==(ROOT/row['source']).read_bytes()==archive.read(name(ds))
                assert hashlib.sha256(data).hexdigest()==row['sha256']
                bank=load_programs(target);assert len(bank)==len(cases(ds))==row['cases']
                for c,p in zip(cases(ds),bank):
                    exact(c,p);native=engine.ask(c,mode=9,hint=p);assert len(native)==len(p)
                    sim=Sim(c);st=sim.initial();rel=sim.target|sim.forbidden
                    for command,rr in zip(p,native):
                        st=sim.step(st,command)
                        assert rr[0]==packed(st) and rr[1]==st[3]
                        assert sum(v<<(64*w) for w,v in enumerate(rr[2:]))==st[2]&rel
                    count+=1;total+=len(p)
                assert sum(map(len,bank))==row['ticks']
                lines.append(f"{ds}: CPP + INDEPENDENT_PYTHON + SOURCE_AND_ZIP_BYTES PASS; {len(bank)} cases; {row['ticks']} ticks")
    finally:engine.close()
    assert total==manifest['total']==15657 and count==540
    assert hashlib.sha256((release/'answers_level6_15657.zip').read_bytes()).hexdigest()==manifest['zip_sha256']
    result=subprocess.run(['node',str(ROOT/'validate_l6_sandbox.cjs')],check=True,text=True,capture_output=True)
    lines.append(result.stdout.strip())
    allowed={row['path'].replace('\\','/') for row in manifest['artifacts']}|{'.gitattributes','.gitignore'}
    protected=json.loads((BASE/'experiments/protected_sha256.json').read_text());changed=[]
    for relpath,digest in protected.items():
        p=ROOT/relpath;assert p.is_file(),relpath
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(relpath.replace('\\','/'))
    assert set(changed)==allowed,(changed,allowed)
    lines.append(f'PROMOTION_SCOPE_PASS: {len(protected)} protected files; exactly 3 submission answers and 2 Git publication rules changed')
    lines.append('SUBMISSION_LOCAL_PASS: 540 cases; 15657 ticks; no commands after Kth pickup; platform submission NOT_PERFORMED')
    (release/'validation.log').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    manifest.update(status='SUBMISSION_LOCAL_PASS',cases=count,validation=dict(cpp='PASS',independent_python='PASS',original_js='PASS',source_and_zip_bytes='PASS',protected_files=len(protected),authorized_protected_changes=changed))
    atomic_json(release/'delivery.json',manifest)
    print('\n'.join(lines),flush=True)

if __name__=='__main__':main()
