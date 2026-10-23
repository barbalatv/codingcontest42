from pathlib import Path
from subprocess import Popen,PIPE
from time import perf_counter
import argparse
from optimize_l6 import ROOT,load_programs
from phase2_run import atomic_save,CHARS
from phase2_cycle_cp import extract,combine
from phase2_regress import cyclic_free
from solve_l6 import parse
from solve_l4 import geometry
from solve_l5 import verify


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--file',default='medium');parser.add_argument('--limit',type=int,default=10);parser.add_argument('--ms',type=int,default=500);parser.add_argument('--width',type=int,default=128)
    args=parser.parse_args();started=perf_counter();engine=Popen([str(Path(__file__).parent/'phase2_regress.exe')],stdin=PIPE,stdout=PIPE,text=True,bufsize=1)
    try:
        for source in sorted(ROOT.glob('in_*.txt')):
            if args.file not in source.name:continue
            cases=parse(source);target=source.with_name(source.name.replace('in_','answer_',1));programs=load_programs(target)
            ranked=[]
            for i,(case,program) in enumerate(zip(cases,programs)):
                loop=extract(case,program)
                if loop and len(loop[2])>=2:ranked.append(((len(loop[2])-1)*(case[2]-1),i,loop))
            ranked.sort(reverse=True);old=sum(map(len,programs));wins=0
            for iteration,(_,i,loop) in enumerate(ranked[:args.limit]):
                start,seed,oldcycle=loop;case=cases[i];r,pattern,count=case;before=len(programs[i]);period=len(oldcycle)
                rows=list(map(list,geometry(r)[0]));cells=geometry(r)[1];wordcount=(len(cells)+63)//64
                for y,x in pattern:rows[y][x]='M'
                goal=sum(1<<k for k,p in enumerate(cells) if p in pattern)
                pose=sum((p+128*int(start[1]>>j&1))<<(8*j) for j,p in enumerate(start[0]))
                for horizon in sorted({max(1,round(period*0.75)),period-1}):
                    data=f'{r} 1 100000 {args.width} {args.ms} {horizon} 60\n'+'\n'.join(map(''.join,rows))+'\n'+str(pose)+'\n'+str(pose)+' '+' '.join('0' for _ in range(wordcount))+' '+' '.join(str((goal>>(64*w))&((1<<64)-1)) for w in range(wordcount))+'\n'
                    engine.stdin.write(data);engine.stdin.flush();result=list(map(int,engine.stdout.readline().split()));assert len(result)>=4,result
                    if result[0]:
                        cycle=[tuple(CHARS[(code>>(2*j))&3] for j in range(6)) for code in result[4:]]
                        assert len(cycle)==result[0]<=horizon
                        options=[combine(case,seed,cycle,len(programs[i])),cyclic_free(case,programs[i],pose,cycle)]
                        options=[x for x in options if x and len(x)<len(programs[i])]
                        if options:
                            candidate=min(options,key=len);assert verify(r,pattern,candidate)==count,(source.name,i)
                            programs[i]=candidate;atomic_save(target,programs);wins+=1
                    if len(programs[i])<before:break
                if len(programs[i])<before or (iteration+1)%20==0 or args.limit<=10:print(f'{source.name} case={i+1}: period {period}, score {before}->{len(programs[i])}; elapsed={perf_counter()-started:.1f}s',flush=True)
            print(f'FILE {target.name}: {old}->{sum(map(len,programs))}, wins={wins}',flush=True)
    finally:engine.stdin.close();engine.wait(timeout=15)
