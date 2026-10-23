from pathlib import Path
from subprocess import Popen,PIPE
from time import perf_counter
import argparse
from phase2_partial import finish
from optimize_l6 import ROOT,Machine,Done,load_programs
from phase2_run import atomic_save,CHARS
from solve_l6 import parse
from solve_l4 import geometry
from solve_l5 import verify


def solve(case,incumbent,engine,width,budget,depth,variant):
    r,pattern,count=case;m=Machine(r,pattern,1)
    rows=list(map(list,geometry(r)[0]))
    for y,x in pattern:rows[y][x]='M'
    engine.stdin.write(f'{r} 1 {incumbent} {width} {budget} {depth} {10+variant}\n'+'\n'.join(map(''.join,rows))+'\n');engine.stdin.flush()
    result=list(map(int,engine.stdout.readline().split()));assert len(result)>=4,result
    if not result[0]:return None,result[:4]
    prefix=[tuple(CHARS[(action>>(2*j))&3] for j in range(6)) for action in result[4:]]
    try:
        for line in prefix:m.emit(line)
        m=finish(m)
    except Done:pass
    first=m.program[:]
    if len(first)>=incumbent:return None,(len(prefix),len(first))
    m.required=count
    initial=[0,5*r,4*r,3*r,2*r,r]
    try:
        while m.accepted<count:
            m.off()
            while m.pos!=initial:m.emit([m.move(i,p) for i,p in enumerate(initial)])
            for line in first:m.emit(line)
            if len(m.program)>=incumbent:return None,(len(prefix),len(first))
    except Done:pass
    return m.program,(len(prefix),len(first))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',default='enormous');p.add_argument('--pilot',action='store_true');p.add_argument('--indices',default='')
    p.add_argument('--width',type=int,default=256);p.add_argument('--ms',type=int,default=1500);p.add_argument('--depth',type=int,default=150);p.add_argument('--variant',type=int,default=1)
    args=p.parse_args();started=perf_counter();engine=Popen([str(Path(__file__).parent/'phase2_dual.exe')],stdin=PIPE,stdout=PIPE,text=True,bufsize=1)
    try:
        for source in sorted(ROOT.glob('in_*.txt')):
            if args.file not in source.name:continue
            cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
            if args.indices:indices=[int(x)-1 for x in args.indices.split(',')]
            elif args.pilot:
                ranked=sorted(range(len(cases)),key=lambda i:len(cases[i][1]));indices=sorted({ranked[0],ranked[len(ranked)//3],ranked[2*len(ranked)//3],ranked[-1]})
            else:indices=sorted(range(len(cases)),key=lambda i:len(programs[i]),reverse=True)
            old=sum(map(len,programs));wins=0
            for j,i in enumerate(indices):
                previous=len(programs[i]);candidate,stats=solve(cases[i],previous,engine,args.width,args.ms,args.depth,args.variant)
                if candidate and len(candidate)<previous:
                    assert verify(cases[i][0],cases[i][1],candidate)==cases[i][2],(source.name,i)
                    programs[i]=candidate;atomic_save(target,programs);wins+=1
                if args.pilot or args.indices or candidate or (j+1)%20==0:print(f'{source.name} case={i+1}: {previous}->{len(programs[i])}; prefix/first={stats}; elapsed={perf_counter()-started:.1f}s',flush=True)
            print(f'FILE {target.name}: {old}->{sum(map(len,programs))}, improved={wins}/{len(indices)}',flush=True)
    finally:engine.stdin.close();engine.wait(timeout=15)
