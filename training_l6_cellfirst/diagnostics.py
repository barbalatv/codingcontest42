from common import *
def main():
    diagnostics=[];pilot={}
    for ds in DATASETS:
        rows=[]
        for i,(c,p) in enumerate(zip(cases(ds),programs(ds))):
            m,_=trace(c,p);m.update(dataset=ds,case=i+1,radius=c[0]);rows.append(m);diagnostics.append(m)
        # Mix redundant-hit, setup and chord/large-geometry opportunities.
        rankers=[lambda m:m['repeat_fraction']*m['target_cells'],lambda m:m['first_copy'],lambda m:m['target_cells']/max(1,m['later_mean'] or m['first_copy'])]
        selected=[];n=5 if ds=='medium' else 8
        ranked=[sorted(rows,key=f,reverse=True) for f in rankers]
        for j in range(n):
            m=next(m for m in ranked[j%3] if m['case'] not in selected);selected.append(m['case'])
        pilot[ds]=selected
    atomic_json(BASE/'experiments/diagnostics.json',diagnostics);atomic_json(BASE/'experiments/pilot.json',pilot)
    print(json.dumps(pilot))
if __name__=='__main__':main()
