from pathlib import Path
from subprocess import Popen,PIPE
from time import perf_counter
from solve_l6 import parse
from solve_l4 import geometry
from solve_l5 import verify
from optimize_l6 import ROOT,load_programs,save_programs
import argparse,json,os,time

CHARS='-FBT'


def atomic_save(target,programs):
    temporary=target.with_suffix('.phase2.tmp')
    save_programs(temporary,programs)
    for attempt in range(8):
        try:os.replace(temporary,target);return
        except PermissionError:
            if attempt==7:raise
            time.sleep(min(0.05*2**attempt,1))


def main():
    p=argparse.ArgumentParser();p.add_argument('--file',default='');p.add_argument('--pilot',action='store_true');p.add_argument('--indices',default='')
    p.add_argument('--width',type=int,default=16);p.add_argument('--ms',type=int,default=350);p.add_argument('--depth',type=int,default=150);p.add_argument('--variant',type=int,default=0)
    p.add_argument('--engine',default='phase2_beam.exe')
    args=p.parse_args();started=perf_counter();service=Popen([str(Path(__file__).parent/args.engine)],stdin=PIPE,stdout=PIPE,text=True,bufsize=1)
    try:
        for source in sorted(ROOT.glob('in_*.txt')):
            if not any(x in source.name for x in ('medium','large','enormous')):continue
            if args.file and args.file not in source.name:continue
            cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
            if args.indices:indices=[int(x)-1 for x in args.indices.split(',')]
            elif args.pilot:
                ranked=sorted(range(len(cases)),key=lambda i:len(cases[i][1]));indices=sorted({ranked[0],ranked[len(ranked)//3],ranked[2*len(ranked)//3],ranked[-1]})
            else:indices=sorted(range(len(cases)),key=lambda i:len(programs[i]),reverse=True)
            old=sum(map(len,programs));wins=0
            for iteration,i in enumerate(indices):
                r,pattern,count=cases[i];rows=list(map(list,geometry(r)[0]))
                for y,x in pattern:rows[y][x]='M'
                header=f'{r} {count} {len(programs[i])} {args.width} {args.ms} {args.depth} {args.variant}'
                service.stdin.write(header+'\n'+'\n'.join(map(''.join,rows))+'\n');service.stdin.flush()
                result=list(map(int,service.stdout.readline().split()));assert len(result)>=4,result
                length,evaluations,ms,made=result[:4];previous=len(programs[i])
                if length:
                    candidate=[tuple(CHARS[(action>>(2*j))&3] for j in range(6)) for action in result[4:]]
                    assert len(candidate)==length<previous
                    assert verify(r,pattern,candidate)==count,(source.name,i)
                    programs[i]=candidate;atomic_save(target,programs);wins+=1
                if length or args.pilot or args.indices or (iteration+1)%20==0:
                    print(f'{source.name} case={i+1} r={r} cells={len(pattern)} copies={count}: {previous}->{len(programs[i])}; eval={evaluations} ms={ms} made={made}',flush=True)
            print(f'FILE {target.name}: {old}->{sum(map(len,programs))}, improved={wins}/{len(indices)}; elapsed={perf_counter()-started:.2f}s',flush=True)
    finally:service.stdin.close();service.wait(timeout=15)


if __name__=='__main__':main()
