from common import *
from ortools.sat.python import cp_model
from solve_l6 import origins
def static_synth(case,seconds=1,seed=0):
    begin=time.perf_counter();r,pat,K=case;sim=Sim(case);root=sim.initial();L=6*r;rel=sim.target|sim.forbidden;cells=geometry(r)[1]
    maxima=[max((sim.rays[p][a]&sim.target).bit_count() for p in range(L)) for a in range(3)]
    if len(pat)>sum(maxima)+12:return None,dict(status='INFEASIBLE_PAIR_BOUND',seconds=time.perf_counter()-begin,no_one_tick_copy=True,maxima=maxima)
    model=cp_model.CpModel();states=[];choices=[];costs=[]
    for e in range(6):
        opts=[(root[0][e],0,0)]
        for p in range(L):
            mask=sim.rays[p][e]&rel
            if mask:
                d=abs(p-root[0][e]);opts.append((p+128,mask,min(d,L-d)))
        choices.append(opts);v=model.new_int_var(0,len(opts)-1,f'ray_{e}');states.append(v);cost=model.new_int_var(0,L//2,f'd_{e}');model.add_element(v,[x[2] for x in opts],cost);costs.append(cost)
    for c in range(len(cells)):
        if not rel>>c&1:continue
        hits=[]
        for e in range(6):
            hit=model.new_bool_var(f'h_{e}_{c}');model.add_element(states[e],[int(mask>>c&1) for _,mask,_ in choices[e]],hit);hits.append(hit)
        if sim.target>>c&1:model.add(sum(hits)==2)
        else:model.add(sum(hits)!=2)
    distance=model.new_int_var(0,L//2,'max_distance');model.add_max_equality(distance,costs);model.minimize(distance)
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1;solver.parameters.random_seed=seed;solver.parameters.max_memory_in_mb=1024;solver.parameters.max_time_in_seconds=max(.001,seconds-(time.perf_counter()-begin));status=solver.solve(model);p=None
    if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:
        q=[choices[e][solver.value(states[e])][0] for e in range(6)];D=solver.value(distance);p=[]
        for t in range(D):
            row=[]
            for e,b in enumerate(q):
                d=((b&127)-root[0][e]+L+L//2)%L-L//2;row.append(('B' if d>0 else 'F') if b&128 and t<abs(d) else '-')
            p.append(tuple(row))
        p.append(tuple('T' if b&128 else '-' for b in q));p += [tuple('------')]*(K-1);exact(case,p)
    info=dict(status=solver.status_name(status),seconds=time.perf_counter()-begin,no_one_tick_copy=status==cp_model.INFEASIBLE,branches=solver.num_branches,maxima=maxima,objective=solver.objective_value if p else None,class_lower_bound=solver.best_objective_bound if p else None)
    return p,info
