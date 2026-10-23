from pathlib import Path
from subprocess import Popen,PIPE
from time import perf_counter
import argparse
from optimize_l6 import ROOT,Machine,Done,load_programs
from phase2_run import atomic_save,CHARS
from solve_l6 import parse
from solve_l4 import geometry
from solve_l5 import verify
from optimize_l6_compact import Sim


def end_pose(case,program):
    sim=Sim(case);state=sim.initial()
    for line in program:
        state=sim.step(state,line)
        if state[3]:break
    pos,active,_,_=state
    return sum((p+128*int(active>>i&1))<<(8*i) for i,p in enumerate(pos))


def regenerate(case,raw):
    r,pattern,count=case
    first=Machine(r,pattern,1)
    try:
        for line in raw:first.emit(line)
    except Done:pass
    assert first.accepted==1
    # The first activation defines an equivalent initial pose for repeated copies.
    pos=[0,5*r,4*r,3*r,2*r,r];active=[False]*6;activation=None
    for k,line in enumerate(first.program):
        for i,ch in enumerate(line):
            if ch=='F':pos[i]=(pos[i]-1)%(6*r)
            elif ch=='B':pos[i]=(pos[i]+1)%(6*r)
            elif ch=='T':active[i]=not active[i]
        if any(active):activation=k;break
    assert activation is not None
    desiredPos,desiredActive=pos[:],active[:]
    tail=first.program[activation+1:]
    m=Machine(*case)
    try:
        while m.accepted<count:
            if m.pos==desiredPos and m.active==desiredActive:m.emit(['-']*6)
            else:
                m.off()
                while m.pos!=desiredPos:m.emit([m.move(i,p) for i,p in enumerate(desiredPos)])
                m.emit(['T' if a else '-' for a in desiredActive])
            for line in tail:m.emit(line)
    except Done:return m.program
    raise AssertionError('Regenerated program incomplete')


def cyclic(case,incumbent,cycle):
    r,pattern,count=case
    m=Machine(r,pattern,1)
    try:
        for line in incumbent:m.emit(line)
    except Done:pass
    m.required=count
    if count<=1:return incumbent
    try:
        for _ in range(count*3):
            for line in cycle:
                m.emit(line)
                if len(m.program)>=len(incumbent):return None
    except Done:return m.program
    return None


def cyclic_free(case,incumbent,pose,cycle):
    m=Machine(*case);count=case[2]
    pos=[(pose>>(8*i))&127 for i in range(6)]
    active=[bool((pose>>(8*i))&128) for i in range(6)]
    try:
        while m.pos!=pos:m.emit([m.move(i,p) for i,p in enumerate(pos)])
        if any(active):m.emit(['T' if a else '-' for a in active])
        for _ in range(count*3):
            for line in cycle:
                m.emit(line)
                if len(m.program)>=len(incumbent):return None
    except Done:return m.program
    return None


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',default='');p.add_argument('--pilot',action='store_true');p.add_argument('--indices',default='')
    p.add_argument('--width',type=int,default=64);p.add_argument('--ms',type=int,default=1000);p.add_argument('--depth',type=int,default=160);p.add_argument('--variant',type=int,default=1)
    p.add_argument('--cycle',action='store_true')
    p.add_argument('--free-end',action='store_true')
    args=p.parse_args();started=perf_counter();engine=Popen([str(Path(__file__).parent/'phase2_regress.exe')],stdin=PIPE,stdout=PIPE,text=True,bufsize=1)
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
            for j,i in enumerate(indices):
                case=cases[i];r,pattern,count=case;previous=len(programs[i]);rows=list(map(list,geometry(r)[0]))
                if args.cycle and count<=1:continue
                for y,x in pattern:rows[y][x]='M'
                mode=(20 if args.free_end else 0)+(10 if args.cycle else 0)
                data=f'{r} 1 100000 {args.width} {args.ms} {args.depth} {args.variant+mode}\n'+'\n'.join(map(''.join,rows))+'\n'+str(end_pose(case,programs[i]))+'\n'
                engine.stdin.write(data);engine.stdin.flush();result=list(map(int,engine.stdout.readline().split()));assert len(result)>=4,result
                if result[0]:
                    raw=[tuple(CHARS[(action>>(2*k))&3] for k in range(6)) for action in result[4:]]
                    candidate=(cyclic_free(case,programs[i],result[3],raw) if args.free_end else cyclic(case,programs[i],raw)) if args.cycle else regenerate(case,raw)
                    if candidate and len(candidate)<previous:
                        assert verify(r,pattern,candidate)==count,(source.name,i)
                        programs[i]=candidate;atomic_save(target,programs);wins+=1
                if args.pilot or args.indices or len(programs[i])<previous or (j+1)%20==0:print(f'{source.name} case={i+1}: {previous}->{len(programs[i])}; result={result[:4]}; elapsed={perf_counter()-started:.1f}s',flush=True)
            print(f'FILE {target.name}: {old}->{sum(map(len,programs))}, improved={wins}/{len(indices)}',flush=True)
    finally:engine.stdin.close();engine.wait(timeout=15)
