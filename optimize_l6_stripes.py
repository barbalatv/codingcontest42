from itertools import product
from time import perf_counter
import argparse
from optimize_l6 import ROOT, Machine, Done, load_programs, save_programs
from solve_l6 import parse,delta,origins
from solve_l4 import geometry
from solve_l5 import verify


def build(case,axis,scan,reverse,offset,assign_reverse):
    r,pattern,count=case
    machine=Machine(*case)
    rowbeams=(axis,axis+3)
    initial=machine.pos[:]
    o=machine.origins
    groups={}
    for point in pattern:
        row=o[axis][machine.index[point]]
        col=o[scan][machine.index[point]]
        groups.setdefault(row,{})[col]=point
    rowkeys=sorted(groups,key=lambda p:delta(initial[axis],p,6*r),reverse=reverse)
    stripes=[]
    if offset:
        stripes.append([rowkeys[0]]);rowkeys=rowkeys[1:]
    stripes.extend(rowkeys[k:k+2] for k in range(0,len(rowkeys),2))
    try:
        for cycle in range(count):
            sequence=stripes if cycle%2==0 else stripes[::-1]
            for stripe in sequence:
                if assign_reverse: stripe=stripe[::-1]
                rowdata={}
                for beam,key in zip(rowbeams,stripe):
                    row=groups[key]
                    point=next(iter(row.values()))
                    rowdata[beam]=(o[beam][machine.index[point]],row)
                columns=set().union(*(set(row) for _,row in rowdata.values()))
                start=min(columns,key=lambda p:delta(initial[scan],p,6*r))
                end=max(columns,key=lambda p:delta(initial[scan],p,6*r))
                # Traverse the span in the direction closest to the current scanner.
                if abs(delta(machine.pos[scan],end,6*r)) < abs(delta(machine.pos[scan],start,6*r)):
                    start,end=end,start
                goals={beam:goal for beam,(goal,_) in rowdata.items()}
                goals[scan]=start
                line=['-']*6
                for beam in rowbeams:
                    if machine.active[beam]:line[beam]='T'
                    elif beam in goals:line[beam]=machine.move(beam,goals[beam])
                line[scan]=machine.move(scan,start)
                if any(machine.active[b] for b in rowbeams): machine.emit(line)
                while any(machine.pos[i]!=g for i,g in goals.items()):
                    line=['-']*6
                    for i,g in goals.items():line[i]=machine.move(i,g)
                    machine.emit(line)
                line=['-']*6
                if not machine.active[scan]:line[scan]='T'
                for beam,(_,row) in rowdata.items():
                    if (start in row)!=machine.active[beam]:line[beam]='T'
                machine.emit(line)
                direction=1 if delta(start,end,6*r)>0 else -1
                current=start
                while current!=end:
                    current=(current+direction)%(6*r)
                    line=['-']*6;line[scan]='B' if direction>0 else 'F'
                    for beam,(_,row) in rowdata.items():
                        if (current in row)!=machine.active[beam]:line[beam]='T'
                    machine.emit(line)
    except Done:return machine.program
    raise AssertionError('Not complete')


def optimize(case,incumbent):
    best=incumbent
    for axis in range(3):
        for scan in range(6):
            if scan%3==axis:continue
            for reverse,offset,assign_reverse in product((False,True),repeat=3):
                candidate=build(case,axis,scan,reverse,offset,assign_reverse)
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
            if (i+1)%25==0:
                save_programs(target,programs)
                print(f'{source.name}: {i+1}/{len(cases)}, saved {old-sum(map(len,programs))}; {perf_counter()-start:.1f}s',flush=True)
        save_programs(target,programs)
        print(f'{target.name}: {old} -> {sum(map(len,programs))}, improved {improved}; {perf_counter()-start:.1f}s',flush=True)
