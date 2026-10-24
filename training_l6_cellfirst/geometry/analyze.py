from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *
from solve_l6 import origins
from itertools import combinations
from math import ceil
def main():
    maps=[];bounds=[];productive=[]
    for ds in DATASETS:
        for i,(c,p) in enumerate(zip(cases(ds),programs(ds))):
            r,pat,K=c;sim=Sim(c);cells=geometry(r)[1];idx={xy:j for j,xy in enumerate(cells)};oo=origins(r);root=sim.initial();L=6*r
            assignments=[];earliest=0
            for xy in sorted(pat):
                j=idx[xy];rr=[oo[e][j] for e in range(6)];dist=[]
                for e,q in enumerate(rr):
                    d=abs(q-root[0][e]);dist.append(min(d,L-d)+1)
                tau=sorted(dist)[1];earliest=max(earliest,tau);assignments.append(dict(cell=xy,rails=rr,earliest_creation=tau))
            chordmax=[max((sim.rays[pos][axis]&sim.target).bit_count() for pos in range(L)) for axis in range(3)]
            upper=min(len(pat),sum(chordmax)+12)
            lower=max(earliest+K-1,ceil(K*len(pat)/upper))
            assert lower<=len(p),(ds,i+1,lower,len(p))
            bounds.append(dict(dataset=ds,case=i+1,nt=len(pat),copies=K,earliest_first_acceptance=earliest,chord_maxima=chordmax,target_creation_upper=upper,production_bound=ceil(K*len(pat)/upper),lower_bound=lower,best=len(p),bound_tight=lower==len(p)))
            maps.append(dict(dataset=ds,case=i+1,radius=r,cells=assignments))
            st=root
            for t,row in enumerate(p,1):
                old=st;st=sim.step(st,row);one=two=three=0
                for e in range(6):
                    if st[1]>>e&1:
                        ray=sim.rays[st[0][e]][e];three|=two&ray;two|=one&ray;one|=ray
                useful=(two&~three&sim.target&~old[2]).bit_count();chords=[]
                for axis in range(3):
                    a,b=axis,axis+3
                    if st[1]>>a&1 and st[1]>>b&1:
                        ra,rb=sim.rays[st[0][a]][a],sim.rays[st[0][b]][b]
                        if ra and ra==rb:chords.append(axis)
                productive.append(dict(dataset=ds,case=i+1,tick=t,new_target=useful,h2_target=(two&~three&sim.target).bit_count(),skirting_created=(two&~three&sim.forbidden&~old[2]).bit_count(),target_erased=(three&sim.target&old[2]).bit_count(),opposed_chord_axes=chords,pose=packed(st),commands=row))
    atomic_json(BASE/'geometry/cell_assignments.json',dict(pairs=list(combinations(range(6),2)),triples=list(combinations(range(6),3)),families=[[0,3],[1,4],[2,5]],cases=maps))
    atomic_json(BASE/'geometry/lower_bounds.json',bounds)
    productive.sort(key=lambda x:x['new_target'],reverse=True)
    atomic_json(BASE/'geometry/productive_configurations.json',productive[:200])
    print('CELL_GEOMETRY_PASS',len(maps),'simple bounds tight',sum(x['bound_tight'] for x in bounds),flush=True)
if __name__=='__main__':main()
