from common import *
import gzip,difflib,collections,math

OLD=REPO/'training_l6_full540'

def family(c):
    r,pat,K=c;xy=[((x-y-r)//2,y-r) for y,x in pat];variants=[]
    for mirror in [False,True]:
        pts=[(b,a) if mirror else (a,b) for a,b in xy]
        for turn in range(6):
            a0=min(a for a,b in pts);b0=min(b for a,b in pts)
            variants.append(tuple(sorted((a-a0,b-b0) for a,b in pts)))
            pts=[(-b,a+b) for a,b in pts]
    return hashlib.sha256(repr(min(variants)).encode()).hexdigest()[:20]

def detailed(c,p):
    sim=Sim(c);st=sim.initial();rel=sim.target|sim.forbidden;out=[]
    for t,commands in enumerate(p,1):
        old=st;st=sim.step(st,commands);one=two=three=0;rays=[]
        for e in range(6):
            ray=sim.rays[st[0][e]][e]&rel if st[1]>>e&1 else 0;rays.append(str(ray))
            three|=two&ray;two|=one&ray;one|=ray
        h2=two&~three;raw=(old[2]|h2)&~three
        out.append(dict(tick=t,commands=commands,positions=st[0],active=st[1],rays=rays,h2=str(h2),h3=str(three),matter_before=str(old[2]&rel),matter_before_pickup=str(raw&rel),matter_after=str(st[2]&rel),created_target=str(h2&sim.target&~old[2]),erased_target=str(three&sim.target&old[2]),created_skirting=str(h2&sim.forbidden&~old[2]),skirting=str(raw&sim.forbidden),copies=st[3],acceptance=st[3]>old[3]))
    return out

def alignment(a,b,r):
    # Event count dominates; material equality, beam overlap, activity and rail
    # distance refine the match. Equal-cost alternatives are counted explicitly.
    n,m=len(a),len(b);dp=[[0.]*(m+1) for _ in range(n+1)];ways=[[0]*(m+1) for _ in range(n+1)];pred={};ways[0][0]=1
    for i in range(1,n+1):dp[i][0]=i*2;ways[i][0]=1;pred[i,0]=(i-1,0,'delete')
    for j in range(1,m+1):dp[0][j]=j*2;ways[0][j]=1;pred[0,j]=(0,j-1,'insert')
    for i in range(1,n+1):
        for j in range(1,m+1):
            x,y=a[i-1],b[j-1];mx,my=int(x['matter_after']),int(y['matter_after']);union=(mx|my).bit_count()
            material=(mx^my).bit_count()/max(1,union);rail=sum(min(abs(p-q),6*r-abs(p-q)) for p,q in zip(x['positions'],y['positions']))/(18*r)
            beams=sum(u==v for u,v in zip(x['rays'],y['rays']))/6
            cost=abs(x['copies']-y['copies'])*5+int(x['acceptance']!=y['acceptance'])*2+material+rail*.25+(1-beams)*.25
            opts=[(dp[i-1][j-1]+cost,(i-1,j-1,'match')),(dp[i-1][j]+2,(i-1,j,'delete')),(dp[i][j-1]+2,(i,j-1,'insert'))]
            value=min(v for v,_ in opts);dp[i][j]=value;ties=[p for v,p in opts if abs(v-value)<1e-9];ways[i][j]=min(2,sum(ways[p[0]][p[1]] for p in ties));pred[i,j]=ties[0]
    path=[];i,j=n,m
    while i or j:
        u,v,kind=pred[i,j];path.append(dict(before_tick=i if i>u else None,after_tick=j if j>v else None,kind=kind));i,j=u,v
    return dict(cost=dp[n][m],multiple_equal_cost_alignments=ways[n][m]>1,physical_correspondence='heuristic; event/material/beam/pose weighted, not a causal proof',pairs=path[::-1])

def segments(trace,p):
    at=[0]+[row['tick'] for row in trace if row['acceptance']]
    return [(a,b,p[a:b]) for j,a in enumerate(at[:-1]) for b in at[j+1:j+5]]

def reverse_variants(p):
    inv=[tuple({'F':'B','B':'F'}.get(ch,ch) for ch in row) for row in p[::-1]];noop=tuple('------')
    return [inv,[noop]+inv[:-1],inv[1:]+[noop],inv[:-1],inv[1:],p[1:]+p[:1],p[-1:]+p[:-1],p[:-1],p[1:]]

def main():
    if (BASE/'case_profiles.csv').exists() and (BASE/'transformation_catalog.json').exists():
        print('FORENSICS_ALREADY_SAVED: baseline/best will not be reset',flush=True);return
    events=list(csv.DictReader((OLD/'improvements.csv').open()));pairs=[];profiles=[];variants=collections.Counter();rules={};catalog_events=[]
    bycase=collections.defaultdict(list)
    for e in events:bycase[e['dataset'],int(e['case'])].append(e)
    assert len(bycase)==40 and sum(int(e['saved']) for e in events)==64
    # Best-of-all: every named complete bank is examined; only shorter programs
    # incur exact validation, so long independent witnesses do not dominate work.
    baseline={ds:load_programs(REPO/'level-6'/name(ds)) for ds in DATASETS};sources={}
    for ds in DATASETS:
        sources[ds]=[]
        for f in REPO.rglob(name(ds)):
            if BASE in f.parents or '.git' in f.parts:continue
            try:bank=load_programs(f)
            except Exception:continue
            if len(bank)!=len(cases(ds)):continue
            sources[ds].append(str(f.relative_to(REPO)))
            for i,p in enumerate(bank):
                if len(p)<len(baseline[ds][i]):
                    try:exact(cases(ds)[i],p);js_check(ds,i,p)
                    except (AssertionError,subprocess.CalledProcessError):continue
                    baseline[ds][i]=p
        for bankdir in ['baseline','best']:save_programs(BASE/bankdir/name(ds),baseline[ds])
    assert sum(sum(map(len,v)) for v in baseline.values())<=15657
    atomic_json(BASE/'experiments/baseline_sources.json',sources)
    for ds in DATASETS:
        oldbank=load_programs(OLD/'baseline'/name(ds));newbank=baseline[ds]
        for i,(c,p) in enumerate(zip(cases(ds),newbank)):
            exact(c,p);metrics,short=trace(c,p);dt=detailed(c,p);geo=family(c)
            profile=dict(dataset=ds,case=i+1,family=geo,radius=c[0],K=c[2],density=len(c[1])/len(geometry(c[0])[1]),skirting_cells=Sim(c).forbidden.bit_count(),historical_donor=(ds,i+1) in bycase,**metrics)
            profiles.append(profile)
            with gzip.open(BASE/'traces'/f'{ds}_{i+1}_baseline.json.gz','wt',encoding='utf-8') as f:json.dump(dict(dataset=ds,case=i+1,trace=dt),f)
            if (ds,i+1) not in bycase:continue
            current=oldbank[i];before_all=detailed(c,current);after_all=dt;chain=[]
            for z,e in enumerate(bycase[ds,i+1]):
                files=list((OLD/'checkpoints').glob(f"{ds}_{i+1}_{e['incumbent']}_{e['candidate']}_{e['algorithm']}.json"));assert len(files)==1,(ds,i,e)
                x=json.loads(files[0].read_text());after=[tuple(row) for row in x['program']];assert len(current)==int(e['incumbent']) and len(after)==int(e['candidate'])
                exact(c,current);exact(c,after);ta=detailed(c,current);tb=detailed(c,after);ma,_=trace(c,current);mb,_=trace(c,after)
                labels=[]
                if mb['first_copy']<ma['first_copy']:labels.append('setup_compression')
                if ma['acceptances'][:-1]==mb['acceptances'][:-1]:labels.append('terminal_shortcut')
                if [x['positions']+[x['active']] if isinstance(x['positions'],list) else tuple(x['positions'])+(x['active'],) for x in ta if x['acceptance']] != [tuple(x['positions'])+(x['active'],) for x in tb if x['acceptance']]:labels.append('acceptance_pose_replacement')
                if any(a!=b for a,b in zip(ma['acceptances'],mb['acceptances'])):labels.append('cross_acceptance_replanning')
                matched=[]
                for aa,ab,pp in segments(ta,current):
                    for variant,v in enumerate(reverse_variants(pp)):
                        if not v:continue
                        for ba,bb,qq in segments(tb,after):
                            if v==qq:matched.append(dict(variant=variant,before=[aa,ab],after=[ba,bb]));variants[variant]+=1
                if matched:labels.append('observed_reverse_phase_variant')
                # Induce exact command motifs only at short, bounded edit sites.
                matcher=difflib.SequenceMatcher(a=current,b=after,autojunk=False)
                edits=[]
                for tag,a,b,u,v in matcher.get_opcodes():
                    if tag=='equal':continue
                    edits.append(dict(kind=tag,before=[a,b],after=[u,v]))
                    if 1<=b-a<=6 and 0<=v-u<b-a:
                        lo=max(0,a-1);hi=min(len(current),b+1);lu=max(0,u-1);hv=min(len(after),v+1)
                        bef=current[lo:hi];aft=after[lu:hv]
                        if len(bef)<=8 and len(aft)<len(bef):
                            token=tuple(bef),tuple(aft);rr=rules.setdefault(token,dict(before=encode(bef),after=encode(aft),donors=[]));rr['donors'].append([ds,i+1]);labels.append('mined_local_command_rewrite')
                if not labels:labels=['structural_trajectory_replacement_or_unknown']
                event=dict(dataset=ds,case=i+1,index=z,source=str(files[0].relative_to(REPO)),method=e['algorithm'],saved=int(e['saved']),seed=int(e['seed']),runtime=float(e['runtime']),runtime_scope='logged query wall time; graph timing includes query postprocessing',before_ticks=len(current),after_ticks=len(after),before_metrics=ma,after_metrics=mb,taxonomy=sorted(set(labels)),matched_variants=matched,command_edits=edits,alignment=alignment(ta,tb,c[0]),before_program=current,after_program=after)
                path=BASE/'transformations'/f'{ds}_{i+1}_{z}.json';atomic_json(path,event);chain.append(str(path.relative_to(BASE)));catalog_events.append({k:event[k] for k in ['dataset','case','index','method','saved','taxonomy']});pairs.append(event);current=after
            assert current==newbank[i],(ds,i+1)
            with gzip.open(BASE/'traces'/f'{ds}_{i+1}_historical_pair.json.gz','wt',encoding='utf-8') as f:json.dump(dict(before=before_all,after=after_all,alignment=alignment(before_all,after_all,c[0]),chain=chain),f)
    pure=[e for e in pairs if e['method'].startswith('B') or e['method']=='pass1_B'];assert len({(e['dataset'],e['case']) for e in pure})==8 and sum(e['saved'] for e in pure)==9
    # Pure cell-creation order is fitted to geometry ranks, not copied commands.
    motifs=[]
    for e in pure:
        c=cases(e['dataset'])[e['case']-1];r,pat,K=c;cells=geometry(r)[1];ix={xy:j for j,xy in enumerate(cells)};tt=detailed(c,e['after_program']);born={}
        for row in tt:
            for xy in pat:
                if int(row['created_target'])>>ix[xy]&1:born.setdefault(xy,row['tick'])
            if row['acceptance']:break
        fits=[]
        for axis in range(3):
            for direction in [-1,1]:
                for serpentine in [0,1]:
                    def key(xy):
                        y,x=xy;a=[x-y-r,2*(y-r),-x-y+3*r];major=direction*a[axis];minor=a[(axis+1)%3];return major,minor*(-1 if serpentine and major%4 else 1)
                    order=sorted(pat,key=key);dis=sum(born.get(a,999)>born.get(b,999) for j,a in enumerate(order) for b in order[j+1:])
                    fits.append((dis,axis,direction,serpentine))
        dis,axis,direction,serp=min(fits);motifs.append(dict(donor=[e['dataset'],e['case']],radius=r,axis=axis,direction=direction,serpentine=serp,discordant_pairs=dis,total_pairs=len(pat)*(len(pat)-1)//2,scope='best of 12 projection/serpentine hypotheses; ties and multi-cell creation retained; not a proven causal rule',before_metrics=e['before_metrics'],after_metrics=e['after_metrics'],method=e['method']))
    rule_list=sorted(rules.values(),key=lambda r:(-len(set(map(tuple,r['donors']))),len(r['before'])))[:48]
    for i,r in enumerate(rule_list):r['rule_id']=i;r['donors']=sorted(set(map(tuple,r['donors'])))
    defs=[('reverse_transition','accepting transition exists','inverse, endpoint clipping, full replay',list(variants)),('phase_terminal','accepted interval has >=2 commands','phase rotate, hold alignment, end deletion',[5,6,7,8]),('synchronized_retime','2..8 tick window has scheduling slack','preserve each emitter ordered actions; cancel/move only as candidate',[2,3,4,6,8]),('mined_rewrite','exact short historical command motif matches','apply fitted substitution; no arbitrary permutation treated as symmetry',[r['rule_id'] for r in rule_list]),('pure_order_splice','target has fitted projection relation','synthesize target order from geometry then test new accepted prefix',list(range(len(motifs))))]
    operators=[]
    for i,(op,pre,tr,parameters) in enumerate(defs):operators.append(dict(operator_id=i,name=op,preconditions=pre,parameters=parameters,transformation=tr,affected_emitters='all six allowed; actual mask logged',affected_cells='all target and skirting through exact ray masks',predicted_gain='estimated by held-out query policy; not guaranteed',validation_requirements=['CPP','independent solve_l5.verify','original JS'],known_successes=[list(k) for k in bycase] if i<3 else sorted(set(tuple(d) for r in rule_list for d in r['donors'])) if i==3 else [m['donor'] for m in motifs],known_failures=[],estimated_runtime='measured per operator batch in transfer_attempts.csv'))
    donor_families={r['family'] for r in profiles if r['historical_donor']};pilot=[]
    for ds in DATASETS:
        eligible=[r for r in profiles if r['dataset']==ds and r['family'] not in donor_families];eligible.sort(key=lambda r:hashlib.sha256((r['family']+'pilot').encode()).hexdigest());pilot+=eligible[:12]
    pilotfamilies={r['family'] for r in pilot}
    for r in profiles:r['split']='donor_family' if r['family'] in donor_families else 'ranking_train' if r['family'] in pilotfamilies else 'heldout_family'
    with (BASE/'case_profiles.csv').open('w',newline='') as f:
        fields=list(profiles[0]);w=csv.DictWriter(f,fields);w.writeheader();w.writerows(profiles)
    atomic_json(BASE/'similarity_index/profiles.json',profiles);atomic_json(BASE/'similarity_index/split.json',dict(pilot=[(r['dataset'],r['case']) for r in pilot],donor_families=sorted(donor_families),ranking_train_families=sorted(pilotfamilies),method='D6+translation normalized target grouping across radii; K omitted to keep repeated geometries together; no physical symmetry assumed for candidate execution'))
    atomic_json(BASE/'transformation_catalog.json',dict(operators=operators,observed_variant_counts=dict(variants),rewrites=rule_list,pure_motifs=motifs,events=catalog_events,donor_cases=len(bycase),event_count=len(events)))
    print('FORENSICS_PASS',len(profiles),'profiles',len(bycase),'cases',len(pairs),'events',len(pure),'Pure events; learned variants',dict(variants),'rewrites',len(rule_list),'pilot',len(pilot),flush=True)

if __name__=='__main__':main()

