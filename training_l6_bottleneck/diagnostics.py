from common_bn import *
import importlib.util, statistics
from collections import Counter
spec=importlib.util.spec_from_file_location('archive_diag',BASE/'archive/ccc42_bottleneck_diagnose.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
bits=legacy.bits
def analyze_case(sim,program,**kw):
    rows=legacy.analyze_case(sim,program,**kw)
    st=sim.initial(); trace=[];first={};last={};destroy={};start=0;out=[]
    for t,cmd in enumerate(program,1):
        before=st; st=sim.step(st,cmd);one=two=three=0
        for e in range(6):
            if st[1]>>e&1:
                ray=sim.rays[st[0][e]][e];three|=two&ray;two|=one&ray;one|=ray
        pre=(before[2]|two)&~three
        new=pre&~before[2]&sim.target;erased=before[2]&~pre&sim.target
        for c in bits(new):first.setdefault(c,t);last[c]=t
        for c in bits(erased):destroy[c]=t
        trace.append(dict(tick=t,commands=list(cmd),matter_before=str(before[2]),matter_after_beams_before_acceptance=str(pre),matter_after_acceptance=str(st[2]),accepted=st[3],new_target=list(bits(new)),destroyed_target=list(bits(erased)),skirting_count=(pre&sim.forbidden).bit_count(),motion=sum(ch in 'FB' for ch in cmd),toggles=cmd.count('T'),active_emitters=st[1].bit_count()))
        if st[3]==before[3]:continue
        row=rows[len(out)].copy();wstart=max(start+1,t-kw.get('tail_ticks',5)+1)
        late={c for c,v in last.items() if v>=wstart}
        fresh={c for c in late if first[c]>=wstart}
        earlier=late-fresh;window_churn={c for c in fresh if first[c]!=last[c]}
        interval=trace[start:t]
        row.update(legacy_late_build=row['late_build'],legacy_late_churn=row['late_churn'],first_built_in_tail=len(fresh),first_before_tail_rebuilt_in_tail=len(earlier),first_in_tail_rebuilt_in_tail=len(window_churn),first_built_in_tail_cell_ids=sorted(fresh),earlier_rebuilt_in_tail_cell_ids=sorted(earlier),within_window_churn_cell_ids=sorted(window_churn),first_build=first.copy(),last_build=last.copy(),last_destroy=destroy.copy(),window_start=wstart,motion=sum(x['motion'] for x in interval),toggles=sum(x['toggles'] for x in interval),mean_active_emitters=statistics.mean(x['active_emitters'] for x in interval),skirting_tick_cells=sum(x['skirting_count'] for x in interval),trace=interval,cleanup_tail=int(row['late_clean']>0 or bool(earlier) or row['late_erased']>0),dense_finale=int(row['late_unique_final']>10))
        out.append(row);first.clear();last.clear();destroy.clear();start=t
    return out
def near_diagnostics(c,p,start=None):
    sim=Sim(c);st=start or sim.initial();erased=set()
    for t,cmd in enumerate(p):
        old=st;st=sim.step(st,cmd)
        if t>=len(p)-5:
            one=two=three=0
            for e in range(6):
                if st[1]>>e&1:
                    ray=sim.rays[st[0][e]][e];three|=two&ray;two|=one&ray;one|=ray
            pre=(old[2]|two)&~three
            erased.update(bits(old[2]&~pre&sim.target))
    missing=list(bits(sim.target&~st[2]));dirty=list(bits(sim.forbidden&st[2]))
    distances={}
    for cell in missing:
        ds=[]
        for e in range(6):
            origins=[q for q in range(6*c[0]) if sim.rays[q][e]>>cell&1]
            ds.append(min(min((q-st[0][e])%(6*c[0]),(st[0][e]-q)%(6*c[0]))+int(not(st[1]>>e&1)) for q in origins))
        distances[str(cell)]=sorted(ds)[1]
    return dict(kind='UNFINISHED_TRAJECTORY',accepted=st[3],missing_target=missing,dirty_skirting=dirty,destroyed_in_last_five=sorted(erased),second_emitter_distance=distances,defects=len(missing)+len(dirty),state=st)
def main():
    rows=[];cc=cases('enormous');pp=programs('enormous','baseline')
    for i,(c,p) in enumerate(zip(cc,pp),1):
        exact(c,p);rows.extend(analyze_case(Sim(c),p,dataset='enormous',index=i,radius=c[0],K=c[2],n_target=len(c[1])))
    summary=legacy.summary(rows,sum(map(len,pp)))
    summary.update(first_before_tail_rebuilt_copies=sum(r['first_before_tail_rebuilt_in_tail']>0 for r in rows),first_in_tail_rebuilt_copies=sum(r['first_in_tail_rebuilt_in_tail']>0 for r in rows),cleanup_tail_cases=len({r['case'] for r in rows if r['cleanup_tail']}),dense_finale_cases=len({r['case'] for r in rows if r['dense_finale']}))
    masks={}
    for i,c in enumerate(cc,1):
        rr=[r for r in rows if r['case']==i]; mask=sorted({cell for r in rr for cell in r['bottleneck_cell_ids']})
        # Universal screening retains dense cases, with their actual late cells.
        masks[str(i)]=dict(cell_ids=mask,sparse_tail=any(r['sparse_tail'] for r in rr),cleanup_tail=any(r['cleanup_tail'] for r in rr),dense_finale=any(r['dense_finale'] for r in rr),focused=any(r['focused_candidate'] for r in rr),late_final=min(r['late_unique_final'] for r in rr),slow=any(r['slow_tail'] for r in rr),radius=c[0],target_cells=len(c[1]),K=c[2],boundary_cells=Sim(c).forbidden.bit_count())
    atomic_json(BASE/'experiments/diagnostics.json',dict(summary=summary,copies=rows))
    atomic_json(BASE/'experiments/bottleneck_cases.json',masks)
    fields=[k for k,v in rows[0].items() if not isinstance(v,(list,dict))]
    with (BASE/'experiments/diagnostics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in rows)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
