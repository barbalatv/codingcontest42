from common import *
from native import Engine
import argparse
def board(c):
    rows=list(map(list,geometry(c[0])[0]))
    for y,x in c[1]:rows[y][x]='M'
    return '\n'.join(map(''.join,rows))
class Reverse:
    def __init__(self,exe):self.p=subprocess.Popen([str(BASE/'engines'/exe)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(BASE/'experiments/reverse_stderr.log').open('a'),text=True,bufsize=1)
    def ask(self,data):
        t=time.perf_counter();self.p.stdin.write(data);self.p.stdin.flush();out=list(map(int,self.p.stdout.readline().split()));assert len(out)>=4;return out,time.perf_counter()-t
    def close(self):self.p.stdin.close();self.p.wait(timeout=10)
def main():
    old=Reverse('regress_old.exe');fix=Reverse('regress_fixed.exe')
    try:
        c=(3,frozenset([(3,6)]),1);sim=Sim(c);cell=geometry(3)[1].index((3,6));s=list(sim.initial()[0])
        for e in range(3):s[e]=next(p for p in range(18) if sim.rays[p][e]>>cell&1)
        bad=packed((s,7,0,0));good=packed((s,3,0,0));data=f'3 1 100 32 200 8 99\n{board(c)}\n{bad}\n{bad} {good}\n'
        a,ta=old.ask(data);b,tb=fix.ask(data);assert a[0]==0 and b[0]>0
        pp=decode(b[4:]);exact(c,pp)
        atomic_json(BASE/'experiments/root_regression_test.json',dict(status='PASS',program=pp,input=f'3 7 13 1\n{board(c)}',invalid_first=bad,valid_second=good,old_length=a[0],fixed_length=b[0],old_seconds=ta,fixed_seconds=tb))
        print('REGRESSION_ROOT_FIX_TEST_PASS',flush=True)
        pilot=json.loads((BASE/'experiments/pilot.json').read_text())
        for ds in DATASETS:
            for idx in pilot[ds]:
                c=cases(ds)[idx-1];p=programs(ds)[idx-1];sim=Sim(c);ss=sim.prefix(p);a=next(t for t in range(1,len(ss)) if ss[t][3]>0);end=packed(ss[a])
                # Exact same root, horizon, width and budget for old/fixed arms.
                for label,engine in [('reverse_old',old),('reverse_fixed',fix)]:
                    data=f'{c[0]} 1 {a+1} 24 300 {a-1} 0\n{board(c)}\n{end}\n';out,secs=engine.ask(data);pp=decode(out[4:]);valid=False
                    if pp:
                        try:exact((c[0],c[1],1),pp);valid=True
                        except AssertionError:pass
                    rec=dict(dataset=ds,case=idx,incumbent=a,candidate=len(pp) if valid else None,saved=max(0,a-len(pp)) if valid else 0,algorithm=label,runtime=secs,evaluations=out[1],seed=0,validation='PYTHON_PASS' if valid else 'NO_VALID_PROGRAM')
                    with (BASE/'experiments/reverse_comparison.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
        print('REVERSE_COMPARISON_COMPLETE',flush=True)
    finally:old.close();fix.close()
if __name__=='__main__':main()
