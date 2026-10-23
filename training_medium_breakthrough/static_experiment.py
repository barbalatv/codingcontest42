from chain_experiment import *
engine=Native('geometry_search.exe');started=time.perf_counter()
try:
 for i,c in enumerate(CASES):
  before=len(load_programs(BASE/'best'/NAME)[i]);initial=key(Sim(c).initial());bound=(2*c[0]-1)*3
  if len(c[1])>max(15,bound) or before<=c[2]:continue
  text=f'{c[0]} {c[2]} 1 800 {before-1} 5 0\n{board(c)}\n{packed(initial)} {MAX}\n0\n\n';out,secs=engine.ask(text);pp,extra=unpack_response(out);update(i,pp,'static_chord',secs,0) if pp else None
  rec=dict(case=i+1,method='exact_static',runtime=secs,explored=out[1],program=len(pp),before=before,after=len(load_programs(BASE/'best'/NAME)[i]));print(rec,flush=True)
  with (BASE/'experiments/static.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
finally:engine.close()
print('STATIC_DONE',time.perf_counter()-started,flush=True)
