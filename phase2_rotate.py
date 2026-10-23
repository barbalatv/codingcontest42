from time import perf_counter
import argparse
from phase2_cycle_cp import extract
from phase2_regress import cyclic_free
from phase2_run import atomic_save
from optimize_l6 import ROOT,load_programs
from solve_l6 import parse
from solve_l5 import verify


def optimize(case,program):
    loop=extract(case,program)
    if not loop:return program
    (poses,active),seed,cycle=loop
    poses=list(poses);length=6*case[0];best=program
    for phase in range(len(cycle)):
        pose=sum((p+128*int(active>>j&1))<<(8*j) for j,p in enumerate(poses))
        rotated=cycle[phase:]+cycle[:phase]
        candidate=cyclic_free(case,best,pose,rotated)
        if candidate and len(candidate)<len(best):best=candidate
        for j,ch in enumerate(cycle[phase]):
            if ch=='F':poses[j]=(poses[j]-1)%length
            elif ch=='B':poses[j]=(poses[j]+1)%length
            elif ch=='T':active^=1<<j
    return best


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',default='medium');p.add_argument('--limit',type=int,default=100000)
    args=p.parse_args();start=perf_counter()
    for source in sorted(ROOT.glob('in_*.txt')):
        if args.file not in source.name:continue
        cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
        ranked=sorted(range(len(cases)),key=lambda i:len(programs[i]),reverse=True)[:args.limit];old=sum(map(len,programs));wins=0
        for iteration,i in enumerate(ranked):
            previous=len(programs[i]);candidate=optimize(cases[i],programs[i])
            if len(candidate)<previous:
                assert verify(cases[i][0],cases[i][1],candidate)==cases[i][2]
                programs[i]=candidate;atomic_save(target,programs);wins+=1
            if (iteration+1)%25==0:print(f'{source.name}: {iteration+1}/{len(ranked)}, saved={old-sum(map(len,programs))}; {perf_counter()-start:.1f}s',flush=True)
        print(f'FILE {target.name}: {old}->{sum(map(len,programs))}, improved={wins}; elapsed={perf_counter()-start:.1f}s',flush=True)
