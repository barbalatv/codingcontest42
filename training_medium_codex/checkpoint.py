from exact_acceptance import *
import hashlib,csv,collections
baseline=load_programs(BASE/'baseline'/NAME);best=load_programs(BASE/'best'/NAME);results=[]
for i,(a,b) in enumerate(zip(baseline,best)):
 if len(b)<len(a):
  sim=Sim(CASES[i]);aacc=[t for t,s in enumerate(sim.prefix(a)) if t and s[3]>sim.prefix(a)[t-1][3]];bs=sim.prefix(b);bacc=[t for t in range(1,len(bs)) if bs[t][3]>bs[t-1][3]]
  results.append(dict(case=i+1,before=len(a),after=len(b),gain=len(a)-len(b),baseline_acceptances=aacc,best_acceptances=bacc))
print(results)
(BASE/'experiments/improvements.json').write_text(json.dumps(results,indent=2))
# Record source hashes, input and untouched competition answers.
manifest={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list((REPO/'level-6').glob('*.txt'))+[BASE/'baseline'/NAME,BASE/'best'/NAME]}
(BASE/'experiments/sha256.json').write_text(json.dumps(manifest,indent=2))
for p in (REPO/'level-6').glob('*.txt'):
 raw=subprocess.run(['git','show','HEAD:'+p.relative_to(REPO).as_posix()],stdout=subprocess.PIPE,check=True).stdout
 assert raw.replace(b'\r\n',b'\n')==p.read_bytes().replace(b'\r\n',b'\n'),p
print('COMPETITION_INPUTS_AND_ANSWERS_UNCHANGED')
