from itertools import combinations,product
from time import perf_counter
from optimize_l6 import ROOT,Machine,Done,load_programs,save_programs
from solve_l6 import parse
from solve_l5 import verify
import argparse


def masks(rays):
    one=two=three=0
    for ray in rays:
        three|=two&ray;two|=one&ray;one|=ray
    return one,two,three


def potentials(m,direction,remaining,future):
    length=6*m.r
    quality=[]
    for p in range(length):
        ray=m.rays[p][direction]
        hit=(ray&future&remaining).bit_count()
        quality.append(24*hit+(ray&remaining).bit_count()//3 if hit or ray&remaining else -1000)
    values=quality*3
    for k in range(1,len(values)):values[k]=max(values[k],values[k-1]-1)
    for k in range(len(values)-2,-1,-1):values[k]=max(values[k],values[k+1]-1)
    return values[length:2*length]


def add_helpers(case,program,helpers):
    m=Machine(*case);r,pattern,count=case
    fixed=[];pos=m.pos[:];active=[False]*6;matter=0
    for line in program:
        for i,ch in enumerate(line):
            if ch=='F':pos[i]=(pos[i]-1)%(6*r)
            elif ch=='B':pos[i]=(pos[i]+1)%(6*r)
            elif ch=='T':active[i]=not active[i]
        one,two,three=masks(m.rays[pos[i]][i] for i in range(6) if active[i])
        matter=(matter|two)&~three
        # This optimization is reserved for programs that keep the boundary clear.
        if matter&m.forbidden:return None
        if matter&m.target==m.target:matter&=~m.target
        fixed.append((one,two,three))
    try:
        for tick,line in enumerate(program):
            baseone,basetwo,basethree=fixed[tick]
            remaining=m.target&~m.matter
            future=0
            for one,two,_ in fixed[tick:tick+4]:future|=one&~two
            pvalues=[potentials(m,i,remaining,future) for i in helpers]
            options=[]
            for i in helpers:
                choices=[]
                for ch in '-FBT':
                    p=m.pos[i];a=m.active[i]
                    if ch=='F':p=(p-1)%(6*r)
                    elif ch=='B':p=(p+1)%(6*r)
                    elif ch=='T':a=not a
                    choices.append((ch,p,a,m.rays[p][i] if a else 0))
                options.append(choices)
            best=None
            for opt in product(*options):
                one,two,three=baseone,basetwo,basethree
                for ch,p,a,ray in opt:
                    three|=two&ray;two|=one&ray;one|=ray
                result=(m.matter|two)&~three
                if result&m.forbidden or (m.matter&m.target)&~result:continue
                score=(result&m.target).bit_count()*10000+sum(pvalues[j][p]*10-(ch!='-')*2-a for j,(ch,p,a,ray) in enumerate(opt))
                if best is None or score>best[0]:best=score,opt
            if best is None:return None
            output=list(line)
            for i,(ch,p,a,ray) in zip(helpers,best[1]):output[i]=ch
            m.emit(output)
    except Done:return m.program
    return None


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--file',default='');parser.add_argument('--limit',type=int,default=100000)
    args=parser.parse_args();start=perf_counter()
    for source in sorted(ROOT.glob('in_*.txt')):
        if args.file and args.file not in source.name:continue
        cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
        old=sum(map(len,programs));improved=0
        for i,case in enumerate(cases[:args.limit]):
            original=programs[i]
            free=[j for j in range(6) if all(line[j]=='-' for line in original)]
            for helpers in combinations(free,2):
                candidate=add_helpers(case,original,helpers)
                if candidate and len(candidate)<len(programs[i]):
                    assert verify(case[0],case[1],candidate)==case[2],(source.name,i)
                    programs[i]=candidate
            improved+=len(programs[i])<len(original)
            if (i+1)%20==0:
                save_programs(target,programs)
                print(f'{source.name}: {i+1}/{len(cases)}, saved {old-sum(map(len,programs))}; {perf_counter()-start:.1f}s',flush=True)
        save_programs(target,programs)
        print(f'{target.name}: {old} -> {sum(map(len,programs))}, improved {improved}; {perf_counter()-start:.1f}s',flush=True)
