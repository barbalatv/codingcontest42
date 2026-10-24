import hashlib,json,subprocess,shutil,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
def build():
    for name,source,flags in [('driver','driver.cpp',[]),('legacy_probe','driver.cpp',['LEGACY']),('rtds_test','rtds_test.cpp',[]),('witness_probe','witness_probe.cpp',[])]:
        exe=BASE/(name+('.exe' if __import__('os').name=='nt' else ''))
        digest=hashlib.sha256(b''.join(p.read_bytes() for p in [BASE/source,BASE/'legacy_compat.cpp',BASE.parent/'endgame.cpp',BASE.parent/'rtds.cpp',BASE.parent/'portable.hpp'])).hexdigest()
        stamp=BASE/f'{name}.build.json'
        if exe.exists() and stamp.exists() and json.loads(stamp.read_text())['source_hash']==digest:continue
        start=time.perf_counter()
        if shutil.which('g++'):
            command=['g++','-O2','-std=c++20',*['-D'+f for f in flags],str(BASE/source),'-o',str(exe)]
        else:
            vc=Path(r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat')
            command=f'cmd.exe /d /s /c "call "{vc}" >nul && cl.exe /nologo /O2 /EHsc /std:c++20 '+ ' '.join('/D'+f for f in flags)+f' /Fe"{exe}" /Fo"{BASE/(name+".obj")}" "{BASE/source}""'
        r=subprocess.run(command,capture_output=True,text=True)
        (BASE/f'{name}.compile.log').write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0,r.stdout+r.stderr
        stamp.write_text(json.dumps(dict(source_hash=digest,seconds=time.perf_counter()-start,flags=flags,compiler='g++' if shutil.which('g++') else 'MSVC C++20 /O2'),indent=2))
        print('BUILD',name,round(time.perf_counter()-start,2),flush=True)
if __name__=='__main__':build()
