"""Run in dependency order; fail immediately and resume completed case groups."""
import subprocess,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
def run(script,*args):subprocess.run([sys.executable,'-B',str(BASE/script),*args],check=True)
def main():
    run('prepare.py');run('make_engine.py');run('build.py');run('tests/test_core.py');run('tests/test_weight_math.py');run('diagnostics.py')
    for stage in ['pilot','universal','modes','dynamic','iterative','deep']:run('bottleneck_runner.py','--stage',stage,'--ms','2500' if stage=='deep' else '1000')
    run('refresh_nears.py');run('repair_search.py');run('normalize_repair.py');run('refresh_nears.py');run('validate.py');run('bottleneck_report.py')
if __name__=='__main__':main()
