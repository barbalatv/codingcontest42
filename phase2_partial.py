from pathlib import Path
from itertools import combinations,product
from subprocess import Popen,PIPE
from time import perf_counter
import argparse
from optimize_l6 import ROOT,Machine,Done,boundary_orders,load_programs
from phase2_run import atomic_save,CHARS
from solve_l6 import parse,Planner,delta
from solve_l4 import geometry
from solve_l5 import verify


def clone(m):
    new=Machine(m.r,m.pattern,m.required)
    new.pos=m.pos[:];new.active=m.active[:];new.matter=m.matter
    new.accepted=m.accepted;new.program=m.program[:]
    return new


def complete_two(m):
    missing=m.target&~m.matter
    assert missing
    m.off()
    points=[p for i,p in enumerate(m.cells) if missing>>i&1]
    best=None
    for a,b in combinations(range(6),2):
        if (a-b)%3==0:continue
        planner=Planner(m.r,m.pattern,a,b)
        planner.target=missing
        planner.points=[(m.origins[a][m.index[p]],m.origins[b][m.index[p]]) for p in points]
        planner.initial=m.pos[a],m.pos[b]
        candidate=planner.choose(1)
        if best is None or candidate[0]<best[0]:best=candidate[0],planner,candidate[1]
    for line in best[1].program(best[2],1):m.emit(line)
    raise AssertionError('Missing cells completion did not submit')


def finish(m):
    dirty=frozenset(p for k,p in enumerate(m.cells) if (m.matter&m.forbidden)>>k&1)
    if not dirty:
        try:complete_two(m)
        except Done:return m
    orders,paths=boundary_orders(m.r,m.pattern,dirty)
    candidates=[]
    for order in orders:
        for choice in product((0,3),repeat=3):
            triplet=tuple(i+choice[i] for i in range(3))
            first=order[0]
            estimate=max(abs(delta(m.pos[i],m.origins[i][m.index[first]],6*m.r)) for i in triplet)+2
            for p,q in zip(order,order[1:]):
                jump=max(abs(delta(m.origins[i][m.index[p]],m.origins[i][m.index[q]],6*m.r)) for i in triplet)+2
                route=paths.get((p,q));estimate+=min(len(route),jump) if route else jump
            candidates.append((estimate,triplet,order))
    candidates.sort();best=None
    for _,triplet,order in candidates[:2]:
        candidate=clone(m)
        try:
            candidate.setup(triplet,order[0]);current=order[0]
            for point in order[1:]:
                route=paths.get((current,point))
                jump=max(abs(delta(candidate.pos[i],candidate.origins[i][candidate.index[point]],6*m.r)) for i in triplet)+2
                if route is None or len(route)>jump:candidate.setup(triplet,point)
                else:
                    for p in route:
                        line=['-']*6
                        for i in triplet:
                            goal=candidate.origins[i][candidate.index[p]]
                            assert abs(delta(candidate.pos[i],goal,6*m.r))<=1
                            line[i]=candidate.move(i,goal)
                        candidate.emit(line)
                current=point
            assert not candidate.matter&candidate.forbidden
            complete_two(candidate)
        except Done:
            if best is None or len(candidate.program)<len(best.program):best=candidate
    assert best is not None
    return best


class Engine:
    def __init__(self):self.p=Popen([str(Path(__file__).parent/'phase2_partial.exe')],stdin=PIPE,stdout=PIPE,text=True,bufsize=1)
    def get(self,m,width,budget,depth,variant):
        rows=list(map(list,geometry(m.r)[0]))
        for y,x in m.pattern:rows[y][x]='M'
        pose=sum((p+128*int(a))<<(8*i) for i,(p,a) in enumerate(zip(m.pos,m.active)))
        words=(len(m.cells)+63)//64
        data=f'{m.r} 1 100000 {width} {budget} {depth} {variant}\n'+'\n'.join(map(''.join,rows))+'\n'+str(pose)+' '+' '.join(str((m.matter>>(64*k))&((1<<64)-1)) for k in range(words))+'\n'
        self.p.stdin.write(data);self.p.stdin.flush()
        result=list(map(int,self.p.stdout.readline().split()));assert len(result)>=4,result
        return [tuple(CHARS[(code>>(2*i))&3] for i in range(6)) for code in result[4:]],result[:4]
    def close(self):self.p.stdin.close();self.p.wait(timeout=15)


def solve(case,incumbent,engine,width,budget,depth,variant):
    r,pattern,count=case;m=Machine(*case);seen={};evaluations=0
    while m.accepted<count:
        m.required=m.accepted+1
        fragment,stats=engine.get(m,width,budget,depth,variant);evaluations+=stats[1]
        try:
            for line in fragment:m.emit(line)
            m=finish(m)
        except Done:pass
        if len(m.program)>=incumbent:return None,evaluations
        m.required=count
        key=tuple(m.pos),tuple(m.active)
        if key in seen:
            previousCount,previousIndex=seen[key];cycleCopies=m.accepted-previousCount
            block=m.program[previousIndex:]
            try:
                while m.accepted+cycleCopies<=count:
                    for line in block:m.emit(line)
                    if len(m.program)>=incumbent:return None,evaluations
            except Done:pass
        seen[key]=m.accepted,len(m.program)
    return m.program,evaluations


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--file',default='enormous');parser.add_argument('--pilot',action='store_true');parser.add_argument('--indices',default='')
    parser.add_argument('--width',type=int,default=32);parser.add_argument('--ms',type=int,default=500);parser.add_argument('--depth',type=int,default=50);parser.add_argument('--variant',type=int,default=1)
    args=parser.parse_args();engine=Engine();started=perf_counter()
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
                candidate,evaluations=solve(cases[i],len(programs[i]),engine,args.width,args.ms,args.depth,args.variant)
                previous=len(programs[i])
                if candidate and len(candidate)<previous:
                    assert verify(cases[i][0],cases[i][1],candidate)==cases[i][2],(source.name,i)
                    programs[i]=candidate;atomic_save(target,programs);wins+=1
                if args.pilot or args.indices or candidate or (j+1)%20==0:print(f'{source.name} case={i+1}: {previous}->{len(programs[i])}; eval={evaluations}; elapsed={perf_counter()-started:.1f}s',flush=True)
            print(f'FILE {target.name}: {old}->{sum(map(len,programs))}, improved={wins}/{len(indices)}',flush=True)
    finally:engine.close()
