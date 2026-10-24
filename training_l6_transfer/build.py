from common import *
import argparse
def build(source):
    src=BASE/'engines'/source;out=src.with_suffix('.exe');obj=src.with_suffix('.obj')
    vcvars=Path(r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat')
    command=f'call "{vcvars}" >nul && cl.exe /nologo /O2 /EHsc /std:c++20 /Fe"{out}" /Fo"{obj}" "{src}"'
    r=subprocess.run(f'cmd.exe /d /s /c "{command}"',text=True,capture_output=True)
    print(r.stdout,r.stderr);assert r.returncode==0
    return out
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source',nargs='?',default='cellfirst.cpp');build(ap.parse_args().source)
