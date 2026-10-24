from common_bn import *
import argparse
def build(stem):
    src=BASE/'engines'/f'{stem}.cpp';out=src.with_suffix('.exe')
    stamp=out.with_suffix('.build.json'); digest=sha(src)+sha(BASE/'engines/pure_engine.hpp')
    if out.exists() and stamp.exists() and json.loads(stamp.read_text())['source_digest']==digest:return
    vc=Path(r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat')
    command=f'call "{vc}" >nul && cl.exe /nologo /O2 /EHsc /std:c++20 /Fe"{out}" /Fo"{src.with_suffix(".obj")}" "{src}"'
    t=time.perf_counter();r=subprocess.run(f'cmd.exe /d /s /c "{command}"',text=True,capture_output=True)
    print(r.stdout,r.stderr);assert r.returncode==0
    atomic_json(stamp,dict(source_digest=digest,wall_seconds=time.perf_counter()-t,compiler='MSVC /O2 /std:c++20'))
if __name__=='__main__':
    for stem in ['reference_beam','bottleneck_beam']:build(stem)
