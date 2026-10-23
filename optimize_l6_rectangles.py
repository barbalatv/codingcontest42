from itertools import product
from time import perf_counter
import argparse
from optimize_l6 import ROOT,Machine,Done,load_programs,save_programs
from solve_l6 import parse,delta
from solve_l5 import verify


def build(case,axis,scan,reverse,offset,assign_reverse,grouporder):
    r,pattern,count=case
    m=Machine(*case);o=m.origins;initial=m.pos[:]
    rowbeams=(axis,axis+3);scanners=(scan,scan+3)
    rows={};representative={}
    for point in pattern:
        row=o[axis][m.index[point]];col=o[scan][m.index[point]]
        rows.setdefault(row,{})[col]=point
        representative[col]=point
    keys=sorted(rows,key=lambda p:delta(initial[axis],p,6*r),reverse=reverse)
    stripes=[]
    if offset:stripes.append([keys[0]]);keys=keys[1:]
    stripes.extend(keys[k:k+2] for k in range(0,len(keys),2))
    try:
        for cycle in range(count):
            for stripe in (stripes if cycle%2==0 else stripes[::-1]):
                if assign_reverse:stripe=stripe[::-1]
                rowdata={}
                for j,(beam,key) in enumerate(zip(rowbeams,stripe)):
                    row=rows[key];p=next(iter(row.values()))
                    rowdata[j]=(beam,o[beam][m.index[p]],row)
                masks={}
                for j,(_,_,row) in rowdata.items():
                    for col in row:masks[col]=masks.get(col,0)|(1<<j)
                for mask in grouporder:
                    columns=[col for col,kind in masks.items() if kind==mask]
                    if not columns:continue
                    columns.sort(key=lambda p:delta(initial[scan],p,6*r))
                    # Divide work between two opposite scanners, keeping their lines distinct.
                    split=(len(columns)+1)//2
                    halves=[columns[:split],columns[split:]]
                    # Assign halves to minimize the first relocation.
                    options=[]
                    for swap in (False,True):
                        tasks=halves[::-1] if swap else halves
                        for rev0,rev1 in product((False,True),repeat=2):
                            tracks=[tasks[0][::-1] if rev0 else tasks[0],tasks[1][::-1] if rev1 else tasks[1]]
                            score=0
                            for beam,track in zip(scanners,tracks):
                                if track:
                                    goal=o[beam][m.index[representative[track[0]]]]
                                    score=max(score,abs(delta(m.pos[beam],goal,6*r)))
                            options.append((score,tracks))
                    _,tracks=min(options,key=lambda p:p[0])
                    m.off()
                    goals={beam:goal for j,(beam,goal,_) in rowdata.items()}
                    for beam,track in zip(scanners,tracks):
                        if track:goals[beam]=o[beam][m.index[representative[track[0]]]]
                    while any(m.pos[i]!=g for i,g in goals.items()):
                        line=['-']*6
                        for i,g in goals.items():line[i]=m.move(i,g)
                        m.emit(line)
                    line=['-']*6
                    for j,(beam,_,_) in rowdata.items():
                        if mask>>j&1:line[beam]='T'
                    for beam,track in zip(scanners,tracks):
                        if track:line[beam]='T'
                    m.emit(line)
                    schedules=[]
                    for beam,track in zip(scanners,tracks):
                        sequence=[]
                        if track:
                            current=track[0]
                            for target in track[1:]:
                                d=delta(current,target,6*r);sign=1 if d>0 else -1
                                intermediate=[(current+sign*k)%(6*r) for k in range(1,abs(d)+1)]
                                safe=all(masks.get(col,0)&mask==mask for col in intermediate)
                                if not safe:sequence.append('T')
                                for col in intermediate:
                                    p=representative.get(col)
                                    # Origin positions for opposite beams vary in the opposite direction.
                                    previous=o[beam][m.index[representative[current]]]
                                    goal=o[beam][m.index[representative[target]]]
                                    move='B' if delta(previous,goal,6*r)>0 else 'F'
                                    sequence.append(move)
                                if not safe:sequence.append('T')
                                current=target
                        schedules.append(sequence)
                    for tick in range(max(map(len,schedules))):
                        line=['-']*6
                        for beam,schedule in zip(scanners,schedules):
                            if tick<len(schedule):line[beam]=schedule[tick]
                        m.emit(line)
    except Done:return m.program
    raise AssertionError('Not complete')


def optimize(case,incumbent):
    best=incumbent
    if len(case[1])<15:return best
    for axis in range(3):
        for scan in range(3):
            if scan==axis:continue
            for reverse,offset,assign_reverse in product((False,True),repeat=3):
                for grouporder in ((3,1,2),(1,2,3),(2,1,3)):
                    candidate=build(case,axis,scan,reverse,offset,assign_reverse,grouporder)
                    if len(candidate)<len(best):best=candidate
    return best


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--file',default='');parser.add_argument('--limit',type=int,default=100000)
    args=parser.parse_args();start=perf_counter()
    for source in sorted(ROOT.glob('in_*.txt')):
        if args.file and args.file not in source.name:continue
        target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target);cases=parse(source)
        old=sum(map(len,programs));improved=0
        for i,case in enumerate(cases[:args.limit]):
            candidate=optimize(case,programs[i])
            if len(candidate)<len(programs[i]):
                assert verify(case[0],case[1],candidate)==case[2],(source.name,i)
                programs[i]=candidate;improved+=1
            if (i+1)%20==0:
                save_programs(target,programs)
                print(f'{source.name}: {i+1}/{len(cases)}, saved {old-sum(map(len,programs))}; {perf_counter()-start:.1f}s',flush=True)
        save_programs(target,programs)
        print(f'{target.name}: {old} -> {sum(map(len,programs))}, improved {improved}; {perf_counter()-start:.1f}s',flush=True)
