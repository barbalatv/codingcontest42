from common import *
s=(BASE/'repair/exact_model.py').read_text()
s=s.replace('states={};hit={};accept=[];cells=', 'states={};hit={};accept=[];creations={};cells=')
needle="v=m.new_int_var(0,2*L-1,f's{t}_{e}');states[t,e]=v"
replacement="""allowed=[]
   for aa in range(2):
    for pp in range(L):
     d=abs(pp-start[0][e]);d=min(d,L-d)+int(aa!=((start[1]>>e)&1))
     if d<=t:allowed.append(pp+L*aa)
   v=m.new_int_var_from_domain(cp_model.Domain.from_values(allowed),f's{t}_{e}');states[t,e]=v"""
assert needle in s;s=s.replace(needle,replacement)
needle="n=m.new_int_var(0,6,f'n{t}_{k}');m.add(n==sum(hits));v=m.new_bool_var"
replacement="""n=m.new_int_var(0,6,f'n{t}_{k}');m.add(n==sum(hits))
   if sim.target>>k&1:
    created=m.new_bool_var(f'create_{t}_{k}');m.add(n==2).only_enforce_if(created);m.add(n!=2).only_enforce_if(created.Not());creations.setdefault(k,[]).append(created)
   v=m.new_bool_var"""
assert needle in s;s=s.replace(needle,replacement)
s=s.replace(' m.add(sum(accept)==copies)', ' for k,flags in creations.items():m.add(sum(flags)>=copies)\n m.add(sum(accept)==copies)')
s=s.replace('solver.parameters.num_search_workers=2','solver.parameters.num_search_workers=1')
s=s.replace('solver.parameters.max_time_in_seconds=seconds','solver.parameters.max_time_in_seconds=max(0.001,seconds-(time.perf_counter()-t0))')
s+='\n\ndef pure_synth(case,H,seconds=5,seed=0):\n assert H>=0\n return synth(case,Sim(case).initial(),H,case[2],end=None,closed=False,hint=None,seconds=seconds,seed=seed,free=tuple(range(6)),root_radius=0,free_slots=None)\n'
(BASE/'cellfirst/pure_model.py').write_text(s)
print('PURE_CELL_CREATION_MODEL_READY')
