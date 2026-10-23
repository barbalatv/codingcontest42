from functools import lru_cache
from itertools import product
from pathlib import Path
from subprocess import Popen,PIPE
from time import perf_counter
import argparse
from optimize_l6 import ROOT,Machine,Done,load_programs,save_programs
from solve_l6 import parse,delta,origins
from solve_l4 import geometry
from solve_l5 import verify

class Search:
    def __init__(self):
        self.process=Popen([str(Path(__file__).parent/'stripe_search.exe')],stdin=PIPE,stdout=PIPE,text=True,bufsize=1)
    @lru_cache(None)
    def solve(self,track0,track1,allowed):
        if not track0:track0=(0,)
        if not track1:track1=(0,)
        values=[len(track0),len(track1),allowed,*track0,*track1]
        self.process.stdin.write(' '.join(map(str,values))+'\n');self.process.stdin.flush()
        answer=list(map(int,self.process.stdout.readline().split()))
        assert answer and answer[0]>=0 and answer[0]==len(answer)-1,answer
        return tuple(answer[1:])
    def close(self):
        self.process.stdin.close();self.process.wait(timeout=5)


def describe(case,axis,scan,reverse,offset,assign_reverse):
    r,pattern,count=case
    _,cells,_=geometry(r);index={p:i for i,p in enumerate(cells)};o=origins(r)
    initial=[0,5*r,4*r,3*r,2*r,r]
    rows={}
    for p in pattern:
        row=o[axis][index[p]];col=o[scan][index[p]]
        rows.setdefault(row,{})[col]=p
    keys=sorted(rows,key=lambda p:delta(initial[axis],p,6*r),reverse=reverse)
    stripes=[]
    if offset:stripes.append([keys[0]]);keys=keys[1:]
    stripes.extend(keys[k:k+2] for k in range(0,len(keys),2))
    result=[];estimate=0
    for stripe in stripes:
        if assign_reverse:stripe=stripe[::-1]
        data={}
        for j,key in enumerate(stripe):
            row=rows[key];point=next(iter(row.values()));beam=axis+3*j
            data[j]=(beam,o[beam][index[point]],row)
        masks={}
        for j,(_,_,row) in data.items():
            for col in row:masks[col]=masks.get(col,0)|(1<<j)
        cols=sorted(masks,key=lambda p:delta(initial[scan],p,6*r))
        low,high=delta(initial[scan],cols[0],6*r),delta(initial[scan],cols[-1],6*r)
        columns=tuple((initial[scan]+q)%(6*r) for q in range(low,high+1))
        result.append((data,masks,columns))
        estimate+=(len(columns)+1)//2+5
    return estimate,result


def build(case,axis,scan,stripes,search):
    m=Machine(*case);r,pattern,count=case;o=m.origins
    scanners=(scan,scan+3)
    col_origin={}
    for k,p in enumerate(m.cells):col_origin[o[scan][k]]=(o[scan][k],o[scan+3][k])
    try:
        for cycle in range(count):
            for data,masks,columns in (stripes if cycle%2==0 else stripes[::-1]):
                split=(len(columns)+1)//2
                halves=(columns[:split],columns[split:])
                best=None
                for swap,rev0,rev1 in product((False,True),repeat=3):
                    tasks=halves[::-1] if swap else halves
                    tracks=(tasks[0][::-1] if rev0 else tasks[0],tasks[1][::-1] if rev1 else tasks[1])
                    program=search.solve(tuple(masks.get(c,0) for c in tracks[0]),tuple(masks.get(c,0) for c in tracks[1]),(1<<len(data))-1)
                    goals={beam:goal for beam,goal,_ in data.values()}
                    for j,(beam,track) in enumerate(zip(scanners,tracks)):
                        if track:goals[beam]=col_origin[track[0]][j]
                    setup=max(abs(delta(m.pos[i],g,6*r)) for i,g in goals.items())
                    score=setup+len(program)
                    if best is None or score<best[0]:best=score,tracks,program,goals
                _,tracks,program,goals=best
                m.off()
                while any(m.pos[i]!=g for i,g in goals.items()):
                    line=['-']*6
                    for i,g in goals.items():line[i]=m.move(i,g)
                    m.emit(line)
                current=[0,0]
                for action in program:
                    rows,operations=divmod(action,9);a0,a1=divmod(operations,3)
                    line=['-']*6
                    for j,(beam,_,_) in data.items():
                        if bool(rows>>j&1)!=m.active[beam]:line[beam]='T'
                    for j,(beam,operation) in enumerate(zip(scanners,(a0,a1))):
                        if operation==2:line[beam]='T'
                        elif operation==1:
                            current[j]+=1;goal=col_origin[tracks[j][current[j]]][j]
                            assert abs(delta(m.pos[beam],goal,6*r))==1
                            line[beam]=m.move(beam,goal)
                    m.emit(line)
    except Done:return m.program
    raise AssertionError('Not complete')


def optimize(case,incumbent,search,effort):
    if len(case[1])<10:return incumbent
    candidates=[]
    for axis in range(3):
        for scan in range(3):
            if axis==scan:continue
            for reverse,offset,assign_reverse in product((False,True),repeat=3):
                estimate,stripes=describe(case,axis,scan,reverse,offset,assign_reverse)
                candidates.append((estimate,axis,scan,stripes))
    candidates.sort(key=lambda c:c[:3]);best=incumbent
    for _,axis,scan,stripes in candidates[:effort]:
        candidate=build(case,axis,scan,stripes,search)
        if len(candidate)<len(best):best=candidate
    return best


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--file',default='');parser.add_argument('--limit',type=int,default=100000);parser.add_argument('--effort',type=int,default=3)
    args=parser.parse_args();search=Search();started=perf_counter()
    try:
        for source in sorted(ROOT.glob('in_*.txt')):
            if args.file and args.file not in source.name:continue
            target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target);cases=parse(source)
            old=sum(map(len,programs));improved=0
            for i,case in enumerate(cases[:args.limit]):
                candidate=optimize(case,programs[i],search,args.effort)
                if len(candidate)<len(programs[i]):
                    assert verify(case[0],case[1],candidate)==case[2],(source.name,i)
                    programs[i]=candidate;improved+=1
                if (i+1)%20==0:
                    save_programs(target,programs)
                    print(f'{source.name}: {i+1}/{len(cases)}, saved {old-sum(map(len,programs))}; {perf_counter()-started:.1f}s',flush=True)
            save_programs(target,programs)
            print(f'{target.name}: {old} -> {sum(map(len,programs))}, improved {improved}; {perf_counter()-started:.1f}s',flush=True)
    finally:search.close()
