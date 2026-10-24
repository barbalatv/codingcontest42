"""Physical D6 maps: target, emitter role, rail direction and initial pose."""
from common import *
import random

def point(r,xy,turn,mirror):
    y,x=xy;q,s=(x-y-r)//2,y-r
    if mirror:q,s=s,q
    for _ in range(turn):q,s=-s,q+s
    return s+r,2*q+s+2*r

def emitter(e,turn,mirror):return ((1-e if mirror else e)+turn)%6

def state(r,st,turn,mirror):
    pos,active,matter,n=st;pp=[0]*6;aa=0;cells=geometry(r)[1];index={xy:j for j,xy in enumerate(cells)};mm=0
    for e,p in enumerate(pos):
        f=emitter(e,turn,mirror);pp[f]=((5*r-p if mirror else p)-turn*r)%(6*r);aa|=((active>>e)&1)<<f
    for j,xy in enumerate(cells):
        if matter>>j&1:mm|=1<<index[point(r,xy,turn,mirror)]
    return tuple(pp),aa,mm,n

def program(p,turn,mirror):
    out=[]
    for row in p:
        rr=['-']*6
        for e,ch in enumerate(row):rr[emitter(e,turn,mirror)]={'F':'B','B':'F'}.get(ch,ch) if mirror else ch
        out.append(tuple(rr))
    return out

def main():
    rng=random.Random(420612);fixtures=[];checked=0;matches=[]
    actual=[]
    for ds in DATASETS:
        for i,c in enumerate(cases(ds)):actual.append((ds,i+1,c))
    bypattern={}
    for ds,i,c in actual:bypattern.setdefault((c[0],tuple(sorted(c[1])),c[2]),[]).append((ds,i))
    for ds,i,c in actual:
        for mirror in [False,True]:
            for turn in range(6):
                pat=tuple(sorted(point(c[0],xy,turn,mirror) for xy in c[1]))
                for other in bypattern.get((c[0],pat,c[2]),[]):
                    if other!=(ds,i):matches.append(dict(donor=[ds,i],recipient=other,turn=turn,mirror=mirror))
    radii=sorted({c[0] for _,_,c in actual})
    for r in radii:
        cells=geometry(r)[1];pat=set(next(c[1] for _,_,c in actual if c[0]==r));c=(r,pat,1000);p=[tuple(rng.choice('-FBT') for _ in range(6)) for _ in range(28)];original=Sim(c).prefix(p)
        for mirror in [False,True]:
            for turn in range(6):
                transformed=(r,{point(r,xy,turn,mirror) for xy in pat},1000);pp=program(p,turn,mirror);ss=Sim(transformed).prefix(pp)
                for a,b in zip(original,ss):assert state(r,a,turn,mirror)==b
                assert ss[0]==Sim(transformed).initial();checked+=len(ss)-1
                rows=[list(row) for row in geometry(r)[0]]
                for y,x in transformed[1]:rows[y][x]='M'
                input_text=f'{r} {len(rows)} {len(rows[0])} 1000\n'+'\n'.join(''.join(row) for row in rows)
                expected=[dict(positions=s[0],active=[bool(s[1]>>e&1) for e in range(6)],copies=s[3],matter=[xy for j,xy in enumerate(cells) if s[2]>>j&1]) for s in ss[1:]]
                fixtures.append(dict(radius=r,input=input_text,program=pp,states=expected,turn=turn,mirror=mirror))
    atomic_json(BASE/'experiments/symmetry_fixtures.json',fixtures)
    atomic_json(BASE/'similarity_index/exact_dihedral_matches.json',matches)
    atomic_json(BASE/'experiments/symmetry_validation.json',dict(python='PASS',states=checked,radii=radii,fixtures=len(fixtures),exact_cross_case_matches=len(matches),initial_pose_preserved=True,js='PENDING'))
    print('D6_PYTHON_PASS',len(fixtures),checked,'states; exact cross-case analogs',len(matches),flush=True)

if __name__=='__main__':main()
