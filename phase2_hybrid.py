from pathlib import Path
from itertools import combinations
from subprocess import Popen,PIPE
from time import perf_counter
import argparse
from optimize_l6 import ROOT,Machine,Done,load_programs
from phase2_run import atomic_save,CHARS
from phase2_regress import end_pose,regenerate
from solve_l6 import parse,Planner
from solve_l4 import geometry
from solve_l5 import verify


def build(case,pose,ones,zeros,tail):
    r,pattern,count=case;m=Machine(r,pattern,1)
    try:
        if ones:
            points=[p for i,p in enumerate(m.cells) if ones>>i&1]
            best=None
            for a,b in combinations(range(6),2):
                if (a-b)%3==0:continue
                planner=Planner(r,pattern,a,b);planner.target=ones;planner.forbidden=zeros
                planner.points=[(m.origins[a][m.index[p]],m.origins[b][m.index[p]]) for p in points]
                choice=planner.choose(1)
                if best is None or choice[0]<best[0]:best=choice[0],planner,choice[1]
            for line in best[1].program(best[2],1):m.emit(line)
        assert m.matter&ones==ones and not m.matter&zeros
        desired=[(pose>>(8*i))&127 for i in range(6)]
        active=[bool((pose>>(8*i))&128) for i in range(6)]
        m.off()
        while m.pos!=desired:m.emit([m.move(i,p) for i,p in enumerate(desired)])
        if any(active):m.emit(['T' if a else '-' for a in active])
        for line in tail:m.emit(line)
    except Done:return regenerate(case,m.program)
    raise AssertionError('Regression preconditions did not imply a submission')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',default='enormous');p.add_argument('--pilot',action='store_true');p.add_argument('--indices',default='')
    p.add_argument('--width',type=int,default=64);p.add_argument('--ms',type=int,default=1200);p.add_argument('--depth',type=int,default=180);p.add_argument('--variant',type=int,default=0);p.add_argument('--free-end',action='store_true')
    p.add_argument('--limit',type=int,default=100000)
    args=p.parse_args();started=perf_counter();engine=Popen([str(Path(__file__).parent/'phase2_regress.exe')],stdin=PIPE,stdout=PIPE,text=True,bufsize=1)
    try:
        for source in sorted(ROOT.glob('in_*.txt')):
            if args.file not in source.name:continue
            cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
            if args.indices:indices=[int(x)-1 for x in args.indices.split(',')]
            elif args.pilot:
                ranked=sorted(range(len(cases)),key=lambda i:len(cases[i][1]));indices=sorted({ranked[0],ranked[len(ranked)//3],ranked[2*len(ranked)//3],ranked[-1]})
            else:indices=sorted(range(len(cases)),key=lambda i:len(programs[i]),reverse=True)
            indices=indices[:args.limit]
            old=sum(map(len,programs));wins=0
            for j,i in enumerate(indices):
                case=cases[i];r,pattern,count=case;previous=len(programs[i]);rows=list(map(list,geometry(r)[0]))
                for y,x in pattern:rows[y][x]='M'
                mode=50 if args.free_end else 40
                data=f'{r} 1 100000 {args.width} {args.ms} {args.depth} {args.variant+mode}\n'+'\n'.join(map(''.join,rows))+'\n'+str(end_pose(case,programs[i]))+'\n'
                engine.stdin.write(data);engine.stdin.flush();result=list(map(int,engine.stdout.readline().split()));assert len(result)>=4,result
                needed=None
                if result[3]:
                    words=(len(geometry(r)[1])+63)//64
                    ones=sum(v<<(64*k) for k,v in enumerate(result[4:4+words]));zeros=sum(v<<(64*k) for k,v in enumerate(result[4+words:4+2*words]))
                    raw=[tuple(CHARS[(action>>(2*k))&3] for k in range(6)) for action in result[4+2*words:]]
                    assert len(raw)==result[0]
                    candidate=build(case,result[3],ones,zeros,raw);needed=ones.bit_count()
                    if len(candidate)<previous:
                        assert verify(r,pattern,candidate)==count,(source.name,i)
                        programs[i]=candidate;atomic_save(target,programs);wins+=1
                if args.pilot or args.indices or len(programs[i])<previous or (j+1)%20==0:print(f'{source.name} case={i+1}: {previous}->{len(programs[i])}; residual={needed} tail={result[0]} ms={result[2]}; elapsed={perf_counter()-started:.1f}s',flush=True)
            print(f'FILE {target.name}: {old}->{sum(map(len,programs))}, improved={wins}/{len(indices)}',flush=True)
    finally:engine.stdin.close();engine.wait(timeout=15)
