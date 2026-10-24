"""Verify the promoted submission, ZIP bytes, and preserved research evidence."""
import sys,zipfile
from pathlib import Path
RELEASE=Path(__file__).resolve().parent
sys.path.insert(0,str(RELEASE.parents[1]/'training_l6_bottleneck'))
from native_bottleneck import *
def main():
    receipt=json.loads((RELEASE/'delivery.json').read_text());E=Engine();datasets={}
    try:
        with zipfile.ZipFile(RELEASE/'answers_level6_15629.zip') as z:
            assert sorted(z.namelist())==sorted(name(ds) for ds in DATASETS)
            for ds in DATASETS:
                p=REPO/'level-6'/name(ds);source=BASE/'best'/name(ds)
                assert p.read_bytes()==source.read_bytes()==z.read(name(ds))
                assert sha(p)==receipt['datasets'][ds]['new_sha256']
                assert sha(RELEASE/'previous_submission'/name(ds))==receipt['datasets'][ds]['previous_sha256']
                pp=load_programs(p);assert len(pp)==len(cases(ds))
                for c,program in zip(cases(ds),pp):exact(c,program);native_check(E,c,program)
                datasets[ds]=dict(cases=len(pp),ticks=sum(map(len,pp)),sha256=sha(p))
    finally:E.close()
    outputs=[]
    for script,args in [(REPO/'validate_l6_sandbox.cjs',[]),(BASE/'validate_sandbox.cjs',['../level-6'])]:
        r=subprocess.run(['node',str(script),*args],text=True,capture_output=True,check=True);outputs.append(r.stdout);print(r.stdout)
    manifest=json.loads((BASE/'artifact_manifest.json').read_text());assert all(sha(BASE/p)==h for p,h in manifest.items())
    allowed={'.gitattributes'}|{str(Path('level-6')/name(ds)) for ds in DATASETS}
    protected=json.loads((BASE/'experiments/protected.json').read_text());changes=[p for p,h in protected.items() if not(REPO/p).exists() or sha(REPO/p)!=h]
    assert set(changes)<=allowed,changes
    result=dict(status='LOCAL_PASS',datasets=datasets,total_ticks=sum(v['ticks'] for v in datasets.values()),cases=sum(v['cases'] for v in datasets.values()),cpp='PASS',python_sim='PASS',solve_l5_verify='PASS',original_js='PASS',strict_js='PASS',zip='BYTE_IDENTICAL',research_manifest_files=len(manifest),protected_changes=changes,allowed_changes=sorted(allowed),platform_submission='NOT_PERFORMED')
    assert result['total_ticks']==15629
    atomic_json(RELEASE/'validation.json',result);(RELEASE/'validation.log').write_text('\n'.join(outputs)+json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
