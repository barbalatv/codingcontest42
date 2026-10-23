from graph_cycles import *
def swapq(q,mask,r):
 if q==START:return q
 pos=list(q[:6]);active=q[6]
 for e in range(3):
  if mask>>e&1:
   pos[e]=((3-2*e)*r-q[e+3])%(6*r);pos[e+3]=((3-2*e)*r-q[e])%(6*r)
   a,b=(q[6]>>e)&1,(q[6]>>(e+3))&1
   active=(active&~((1<<e)|(1<<(e+3))))|(b<<e)|(a<<(e+3))
 return tuple(pos)+(active,)
def swapprog(prog,mask):
 out=[]
 for row in prog:
  z=list(row)
  for e in range(3):
   if mask>>e&1:
    z[e]={'F':'B','B':'F'}.get(row[e+3],row[e+3]);z[e+3]={'F':'B','B':'F'}.get(row[e],row[e])
  out.append(tuple(z))
 return out
def symmetry(g):
 r=g.case[0];rays=g.sim.rays
 for e in range(3):
  for p in range(6*r):assert rays[p][e]==rays[((3-2*e)*r-p)%(6*r)][e+3]
 edges=list(g.E.values())
 for e in edges:
  for mask in range(1,8):g.add(swapq(e['start'],mask,r),swapq(e['end'],mask,r),e['copies'],swapprog(e['program'],mask),'opposed_symmetry')
def restore(idx):
 g=Graph(idx-1);f=BASE/'edges'/f'case{idx}.json'
 if f.exists():
  data=json.loads(f.read_text())
  for e in data['edges']:
   a=e['start'];a=START if a==START else tuple(a);b=tuple(e['end']);g.add(a,b,e['copies'],[tuple(row) for row in e['program']],e['origin'])
 return g
if __name__=='__main__':
 for idx in PILOT:
  f=BASE/'edges'/f'case{idx}.json'
  if not f.exists():continue
  t=time.perf_counter();g=restore(idx);symmetry(g);p=load_programs(BASE/'best'/NAME)[idx-1];dp,path=g.dp(len(p),frontier=2048);update(idx-1,dp,'symmetry_graph_dp',time.perf_counter()-t);g.persist();print('SYMMETRY',idx,len(g.nodes),len(g.E),flush=True)
