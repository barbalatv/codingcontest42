from common_bn import *
import shutil, zipfile, stat
def main():
    for d in ['archive','engines','baseline','best','results','experiments','checkpoints','tests','repair']:(BASE/d).mkdir(parents=True,exist_ok=True)
    manifest=BASE/'experiments/protected.json'
    if not manifest.exists():
        paths=[p for p in REPO.rglob('*') if p.is_file() and BASE not in p.parents and '.git' not in p.parts and '__pycache__' not in p.parts and p.suffix not in ('.exe','.obj','.pyc')]
        atomic_json(manifest,{str(p.relative_to(REPO)):sha(p) for p in paths})
    archive=REPO/'ccc42_enormous_bottleneck_phase1.zip'
    with zipfile.ZipFile(archive) as z:
        seen=set()
        for f in z.infolist():
            s=f.filename.replace('\\','/'); dest=(BASE/'archive'/s).resolve()
            assert not s.startswith('/') and ':' not in s and '..' not in Path(s).parts and dest.is_relative_to((BASE/'archive').resolve())
            assert s.casefold() not in seen and f.file_size<10000000 and not f.flag_bits&1
            assert not stat.S_ISLNK(f.external_attr>>16); seen.add(s.casefold())
        for f in z.infolist():
            if f.is_dir():continue
            dest=BASE/'archive'/f.filename; dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists():assert dest.read_bytes()==z.read(f)
            else:dest.write_bytes(z.read(f))
    shutil.copyfile(archive,BASE/'archive'/archive.name)
    shutil.copyfile(REPO/'training_l6_full540/validate_sandbox.cjs',BASE/'validate_sandbox.cjs')
    shutil.copyfile(REPO/'training_l6_full540/repair/exact_model.py',BASE/'repair/exact_model.py')
    shutil.copyfile(REPO/'training_l6_full540/windows_limits.py',BASE/'windows_limits.py')
    records={}; rejected=[]
    for ds in DATASETS:
        cc=cases(ds); source=REPO/'training_l6_full540/best'/name(ds); best=load_programs(source)
        assert len(best)==len(cc)
        sources=[str(source.relative_to(REPO))]*len(cc)
        banks=sorted(p for p in REPO.rglob(name(ds)) if BASE not in p.parents and p!=source)
        for path in banks:
            try:
                pp=load_programs(path)
                if len(pp)!=len(cc):continue
                for i,p in enumerate(pp):
                    if len(p)<len(best[i]):
                        try:exact(cc[i],p)
                        except Exception as e:rejected.append(dict(path=str(path),case=i+1,error=str(e))); continue
                        best[i]=p; sources[i]=str(path.relative_to(REPO))
            except Exception as e:rejected.append(dict(path=str(path),error=str(e)))
        for c,p in zip(cc,best):exact(c,p)
        frozen=BASE/'baseline'/name(ds)
        if frozen.exists():assert load_programs(frozen)==best,'baseline changed; start a separate experiment'
        else:save_programs(frozen,best)
        if not (BASE/'best'/name(ds)).exists():save_programs(BASE/'best'/name(ds),best)
        records[ds]=dict(cases=len(cc),ticks=sum(map(len,best)),banks_inspected=len(banks)+1,sha256=sha(BASE/'baseline'/name(ds)),sources=sources)
    atomic_json(BASE/'experiments/baseline.json',dict(datasets=records,rejected=rejected,archive_sha256=sha(archive)))
    r=subprocess.run(['node',str(BASE/'validate_sandbox.cjs'),'baseline'],text=True,capture_output=True,check=True)
    (BASE/'validation.log').write_text(r.stdout,encoding='utf-8');print(r.stdout,flush=True)
if __name__=='__main__':main()
