import subprocess, sys

def compile_cpp(src_file, exe_file=None, extra_args=None):
    if extra_args is None: extra_args = []
    vcvars = r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat'
    args_str = ' '.join(extra_args)
    cmd = f'call "{vcvars}" >nul && cl.exe /O2 /EHsc /std:c++17 {args_str} {src_file}'
    print('Compiling:', cmd)
    p = subprocess.run(f'cmd.exe /c "{cmd}"', shell=True, capture_output=True, text=True)
    print('Return code:', p.returncode)
    if p.stdout: print(p.stdout)
    if p.stderr: print(p.stderr)
    return p.returncode == 0

if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else 'stripe_search.cpp'
    compile_cpp(src)
